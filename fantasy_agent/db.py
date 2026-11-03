"""Postgres connection and users table. Per-user model: league_id/team_name
live directly on the user row since each user has exactly one league."""
import os

from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

_db_url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg2://", 1)
engine = create_engine(_db_url)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    league_id = Column(Integer, nullable=True)
    team_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db():
    Base.metadata.create_all(engine)
