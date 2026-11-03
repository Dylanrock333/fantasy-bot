"""FastAPI server exposing the agent graphs to the Discord bot (its only client).

Run: uvicorn fantasy_agent.server:app --reload --reload-dir fantasy_agent --port 8787

/api/chat runs the graph and returns the reply as plain JSON.
/api/league/{league_id}/teams lists a league's teams (id + name).
/api/league/{league_id}/teams/{team_id}/players lists a team's roster.
/api/weekly-recap's power_ranking_image_base64 is base64 PNG, or null if
image generation failed - see weekly_recap_graph.py's power_ranking_image_node.
/api/matchup-preview's matchup_image_base64 is base64 PNG, or null if
image generation failed - see matchup_preview_graph.py's matchup_image_node.
"""
import asyncio
import base64
import sys
import time
from pathlib import Path

# Make the repo root importable and load .env before importing project modules.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fastapi import Depends, FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fantasy_agent.logging.trace import emit
from fantasy_agent.graphs.graph import build_graph
from fantasy_agent.graphs.weekly_recap_graph import build_weekly_recap_graph
from fantasy_agent.graphs.matchup_preview_graph import build_matchup_preview_graph
from fantasy_agent.tools.fantasy_player_tools import get_player_leaderboard
from fantasy_agent.clients.espn_fantasy_client import current_league_id
from fantasy_agent.clients.espn_fantasy_client import current_league_id, league_singleton, current_team_context
from fantasy_agent.db import SessionLocal, User, init_db
from fantasy_agent.auth import hash_password, verify_password, create_token, get_current_user

# Graphs are compiled once at import time and shared across requests.
app = FastAPI()
graph = build_graph()
weekly_recap_graph = build_weekly_recap_graph()
matchup_preview_graph = build_matchup_preview_graph()
init_db()


class SignupRequest(BaseModel):
    email: str
    password: str
    league_id: int
    team_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/signup")
async def signup(req: SignupRequest):
    db = SessionLocal()
    try:
        user = User(
            email=req.email,
            password_hash=hash_password(req.password),
            league_id=req.league_id,
            team_name=req.team_name,
        )
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="email already registered")
    finally:
        db.close()
    return {"status": "ok"}


@app.post("/api/login")
async def login(req: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == req.email).first()
    finally:
        db.close()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return {"token": create_token(user.id)}

class ChatRequest(BaseModel):
    message: str
    league_id: int
    # team_id: int | None = None
    team_name: str | None = None
    # espn_owner_id: str | None = None


class MeChatRequest(BaseModel):
    message: str


async def _run_chat(message: str, league_id: int, team_name: str | None) -> dict:
    messages = [HumanMessage(content=message)]
    current_league_id.set(league_id)
    current_team_context.set(team_name)

    t0 = time.monotonic()
    try:
        # to_thread copies contextvars, so current_league_id reaches the worker thread.
        result = await asyncio.to_thread(graph.invoke, {"messages": messages})
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        emit("graph_end", graph="chat", duration_ms=int((time.monotonic() - t0) * 1000))

    return {"reply": result["messages"][-1].text}


# Discord's path: caller supplies league_id/team_name directly, no auth.
@app.post("/api/chat")
async def chat(req: ChatRequest):
    return await _run_chat(req.message, req.league_id, req.team_name)


# Web path: league_id/team_name come from the authenticated user, not the request.
@app.post("/api/me/chat")
async def me_chat(req: MeChatRequest, user: User = Depends(get_current_user)):
    if user.league_id is None:
        raise HTTPException(status_code=400, detail="no league linked to this account")
    return await _run_chat(req.message, user.league_id, user.team_name)


@app.get("/api/league/{league_id}/teams")
async def league_teams(league_id: int):
    current_league_id.set(league_id)
    try:
        league = await asyncio.to_thread(league_singleton)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    return {
        "teams": [
            {
                "id": t.team_id,
                "name": t.team_name,
                "owners": [{"id": o["id"]} for o in t.owners],
            }
            for t in league.teams
        ]
    }


@app.get("/api/league/{league_id}/teams/{team_id}/players")
async def team_players(league_id: int, team_id: int):
    current_league_id.set(league_id)
    try:
        league = await asyncio.to_thread(league_singleton)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    team = league.get_team_data(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"team_id {team_id} not found in league {league_id}")

    return {
        "id": team.team_id,
        "name": team.team_name,
        "players": [
            {"id": p.playerId, "name": p.name, "position": p.position, "proTeam": p.proTeam}
            for p in team.roster
        ],
    }


class WeeklyRecapRequest(BaseModel):
    league_id: int
    week: int = 0


# Weekly recap; the power-ranking image is base64 PNG or null if generation failed.
@app.post("/api/weekly-recap")
async def weekly_recap(req: WeeklyRecapRequest):
    current_league_id.set(req.league_id)
    t0 = time.monotonic()
    try:
        result = await asyncio.to_thread(
            weekly_recap_graph.invoke, {"week": req.week}
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        emit("graph_end", graph="weekly_recap", duration_ms=int((time.monotonic() - t0) * 1000))

    image_bytes = result.get("power_ranking_image")
    return {
        "week": result["week"],
        "league_summary": result["league_summary"],
        "power_rankings": result["power_rankings"],
        "power_ranking_image_base64": (
            base64.b64encode(image_bytes).decode("ascii") if image_bytes else None
        ),
    }


class MatchupPreviewRequest(BaseModel):
    league_id: int
    week: int = 0
    previous_recap_context: str | None = None


# Matchup preview; the matchup image is base64 PNG or null if generation failed.
@app.post("/api/matchup-preview")
async def matchup_preview(req: MatchupPreviewRequest):
    current_league_id.set(req.league_id)
    t0 = time.monotonic()
    try:
        result = await asyncio.to_thread(
            matchup_preview_graph.invoke,
            {"week": req.week, "previous_recap_context": req.previous_recap_context},
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        emit("graph_end", graph="matchup_preview", duration_ms=int((time.monotonic() - t0) * 1000))

    image_bytes = result.get("matchup_image")
    return {
        "week": result["week"],
        "league_preview": result["league_preview"],
        "matchups": result["matchups"],
        "matchup_image_base64": (
            base64.b64encode(image_bytes).decode("ascii") if image_bytes else None
        ),
    }


class LeaderboardRequest(BaseModel):
    league_id: int
    position: str
    size: int = 15
    sort_by: str = "points"


# Fantasy player leaderboard for a position, sorted by the requested stat.
@app.post("/api/leaderboard")
async def leaderboard(req: LeaderboardRequest):
    current_league_id.set(req.league_id)
    try:
        players = await asyncio.to_thread(get_player_leaderboard, req.position, req.size, req.sort_by)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    return {"position": req.position, "players": players}
