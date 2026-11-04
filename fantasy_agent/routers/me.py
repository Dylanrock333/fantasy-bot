"""The logged-in user's own profile: onboarding state, ESPN team preview, and league linking.

Signup only creates the account (auth.py); league_id/team_id/espn_s2/swid get attached here,
after the user has pasted their ESPN cookies and picked their team from a preview list.
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from fantasy_agent.auth import get_current_user
from fantasy_agent.clients.espn_fantasy_client import current_espn_cookies, current_league_id, league_singleton
from fantasy_agent.db import SessionLocal, User
from fantasy_agent.logging.trace import emit

router = APIRouter()


@router.get("/api/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "email": user.email,
        "league_id": user.league_id,
        "team_id": user.team_id,
        "team_name": user.team_name,
        "espn_linked": user.espn_s2 is not None,
        "plan_status": user.plan_status,
    }


async def _fetch_teams(league_id: int, espn_s2: str, swid: str):
    current_league_id.set(league_id)
    current_espn_cookies.set((espn_s2, swid))
    try:
        league = await asyncio.to_thread(league_singleton)
    except Exception as err:
        emit("error", route="me_league_teams", error=str(err))
        raise HTTPException(status_code=400, detail="couldn't reach that league - check league_id and cookies")
    return league.teams


class TeamsPreviewRequest(BaseModel):
    league_id: int
    espn_s2: str
    swid: str


@router.post("/api/me/league/teams")
async def preview_teams(req: TeamsPreviewRequest, user: User = Depends(get_current_user)):
    """List a league's teams for the user to pick theirs from - doesn't save anything yet."""
    teams = await _fetch_teams(req.league_id, req.espn_s2, req.swid)
    return {
        "teams": [
            {"id": t.team_id, "name": t.team_name, "owners": [{"id": o["id"]} for o in t.owners]}
            for t in teams
        ]
    }


class LinkLeagueRequest(BaseModel):
    league_id: int
    team_id: int
    espn_s2: str
    swid: str


@router.post("/api/me/link-league")
async def link_league(req: LinkLeagueRequest, user: User = Depends(get_current_user)):
    teams = await _fetch_teams(req.league_id, req.espn_s2, req.swid)
    team = next((t for t in teams if t.team_id == req.team_id), None)
    if team is None:
        raise HTTPException(status_code=400, detail="team_id not found in that league")
    owner_id = team.owners[0]["id"] if team.owners else None

    db = SessionLocal()
    try:
        db.query(User).filter(User.id == user.id).update(
            {
                "league_id": req.league_id,
                "team_id": req.team_id,
                "team_name": team.team_name,
                "espn_owner_id": owner_id,
                "espn_s2": req.espn_s2,
                "swid": req.swid,
            }
        )
        db.commit()
    finally:
        db.close()

    return {"league_id": req.league_id, "team_id": req.team_id, "team_name": team.team_name}
