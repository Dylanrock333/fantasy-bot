"""Stripe subscription billing: Checkout session creation, Customer Portal
session creation, and the webhook that syncs our own users table as the
single source of truth for plan_status."""
import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from fantasy_agent.auth import get_current_user
from fantasy_agent.db import SessionLocal, User
from fantasy_agent.logging.trace import emit

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]
STRIPE_PRICE_ID = os.environ["STRIPE_PRICE_ID"]

BILLING_SUCCESS_URL = os.environ.get("BILLING_SUCCESS_URL", "https://example.com/billing/success")
BILLING_CANCEL_URL = os.environ.get("BILLING_CANCEL_URL", "https://example.com/billing/cancel")
BILLING_PORTAL_RETURN_URL = os.environ.get("BILLING_PORTAL_RETURN_URL", "https://example.com/account")

router = APIRouter()


@router.post("/api/billing/checkout-session")
async def create_checkout_session(user: User = Depends(get_current_user)):
    if user.plan_status in ("active", "trialing", "past_due"):
        raise HTTPException(status_code=400, detail="subscription already active")

    db = SessionLocal()
    try:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
            db.query(User).filter(User.id == user.id).update({"stripe_customer_id": customer.id})
            db.commit()
            customer_id = customer.id
        else:
            customer_id = user.stripe_customer_id
    finally:
        db.close()

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=str(user.id),
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{BILLING_SUCCESS_URL}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=BILLING_CANCEL_URL,
            # Managed Payments requires a product tax code we don't set; tax
            # handling is out of scope for now, so opt out of it here.
            managed_payments={"enabled": False},
        )
    except Exception as err:
        emit("error", route="billing_checkout", error=str(err))
        raise HTTPException(status_code=500, detail="internal server error")

    return {"checkout_url": session.url}


@router.post("/api/billing/portal-session")
async def create_portal_session(user: User = Depends(get_current_user)):
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="no billing account for this user")
    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id, return_url=BILLING_PORTAL_RETURN_URL
        )
    except Exception as err:
        emit("error", route="billing_portal", error=str(err))
        raise HTTPException(status_code=500, detail="internal server error")
    return {"portal_url": session.url}


@router.post("/api/billing/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as err:
        emit("error", route="billing_webhook", error=str(err))
        raise HTTPException(status_code=400, detail="invalid signature")

    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _sync_from_checkout(obj)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _sync_from_subscription(obj)
    elif event_type == "invoice.payment_failed":
        emit("billing_payment_failed", customer=obj.get("customer"))

    return {"status": "ok"}


def _find_user_by_customer(db, customer_id: str) -> User | None:
    return db.query(User).filter(User.stripe_customer_id == customer_id).first()


def _period_end(sub) -> datetime | None:
    """current_period_end lives on each subscription item, not the subscription itself,
    as of the account's current Stripe API version. `sub` may be a webhook event's
    dict-like payload or a stripe.Subscription SDK object - neither supports .get(),
    so use bracket access with a KeyError fallback to cover both."""
    try:
        items = sub["items"]["data"]
        end = items[0]["current_period_end"] if items else None
    except (KeyError, IndexError):
        end = None
    return datetime.fromtimestamp(end, tz=timezone.utc) if end else None


def _sync_from_checkout(session: dict) -> None:
    db = SessionLocal()
    try:
        user = _find_user_by_customer(db, session["customer"])
        if not user and session.get("client_reference_id"):
            user = db.query(User).filter(User.id == int(session["client_reference_id"])).first()
            if user:
                user.stripe_customer_id = session["customer"]
        if not user:
            emit("error", route="billing_webhook", error=f"no user for customer {session['customer']}")
            return

        sub = stripe.Subscription.retrieve(session["subscription"])
        user.stripe_subscription_id = sub.id
        user.plan_status = sub.status
        user.current_period_end = _period_end(sub)
        db.commit()
        emit("billing_subscription_started", user_id=user.id, status=sub.status)
    finally:
        db.close()


def _sync_from_subscription(sub: dict) -> None:
    db = SessionLocal()
    try:
        user = _find_user_by_customer(db, sub["customer"])
        if not user:
            emit("error", route="billing_webhook", error=f"no user for customer {sub['customer']}")
            return
        user.stripe_subscription_id = sub["id"]
        user.plan_status = sub["status"]
        user.current_period_end = _period_end(sub)
        db.commit()
        emit("billing_subscription_synced", user_id=user.id, status=sub["status"])
    finally:
        db.close()
