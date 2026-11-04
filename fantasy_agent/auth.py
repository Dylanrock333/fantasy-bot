"""Password hashing and JWT issuance/verification for email+password auth."""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

from fantasy_agent.db import SessionLocal, User

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = 60 * 24 * 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except JWTError:
        raise ValueError("invalid or expired token")


_security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)) -> User:
    try:
        user_id = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


ACTIVE_PLAN_STATUSES = {"active", "trialing"}


def get_subscribed_user(user: User = Depends(get_current_user)) -> User:
    if user.plan_status not in ACTIVE_PLAN_STATUSES:
        raise HTTPException(status_code=402, detail="active subscription required")
    return user
