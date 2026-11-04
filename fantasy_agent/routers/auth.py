"""Signup and login: creates/authenticates User rows and issues JWTs.

League linking (league_id/team_id/espn_s2/swid) happens later, via routers/me.py -
signup only establishes the account.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fantasy_agent.auth import create_token, hash_password, verify_password
from fantasy_agent.db import SessionLocal, User

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/api/signup")
async def signup(req: SignupRequest):
    db = SessionLocal()
    try:
        user = User(email=req.email, password_hash=hash_password(req.password))
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="email already registered")
    finally:
        db.close()
    return {"status": "ok"}


@router.post("/api/login")
async def login(req: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == req.email).first()
    finally:
        db.close()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return {"token": create_token(user.id)}
