"""Signup and login: creates/authenticates User rows and issues JWTs."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fantasy_agent.auth import create_token, hash_password, verify_password
from fantasy_agent.clients.espn_fantasy_client import current_league_id, league_singleton
from fantasy_agent.db import SessionLocal, User

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str
    league_id: int
    team_id: int


class LoginRequest(BaseModel):
    email: str
    password: str


async def _resolve_team(league_id: int, team_id: int) -> dict:
    current_league_id.set(league_id)
    league = await asyncio.to_thread(league_singleton)
    for t in league.teams:
        if t.team_id == team_id:
            owner_id = t.owners[0]["id"] if t.owners else None
            return {"team_name": t.team_name, "espn_owner_id": owner_id}
    raise HTTPException(status_code=400, detail="team_id not found in that league")


@router.post("/api/signup")
async def signup(req: SignupRequest):
    team = await _resolve_team(req.league_id, req.team_id)
    db = SessionLocal()
    try:
        user = User(
            email=req.email,
            password_hash=hash_password(req.password),
            league_id=req.league_id,
            team_id=req.team_id,
            team_name=team["team_name"],
            espn_owner_id=team["espn_owner_id"],
        )
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
