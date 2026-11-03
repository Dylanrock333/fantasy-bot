"""League lookups: teams, rosters, and the player leaderboard."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fantasy_agent.clients.espn_fantasy_client import current_league_id, league_singleton
from fantasy_agent.logging.trace import emit
from fantasy_agent.tools.fantasy_player_tools import get_player_leaderboard

router = APIRouter()


@router.get("/api/league/{league_id}/teams")
async def league_teams(league_id: int):
    current_league_id.set(league_id)
    try:
        league = await asyncio.to_thread(league_singleton)
    except Exception as err:
        emit("error", route="league_teams", error=str(err))
        raise HTTPException(status_code=500, detail="internal server error")

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


@router.get("/api/league/{league_id}/teams/{team_id}/players")
async def team_players(league_id: int, team_id: int):
    current_league_id.set(league_id)
    try:
        league = await asyncio.to_thread(league_singleton)
    except Exception as err:
        emit("error", route="team_players", error=str(err))
        raise HTTPException(status_code=500, detail="internal server error")

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


class LeaderboardRequest(BaseModel):
    league_id: int
    position: str
    size: int = 15
    sort_by: str = "points"


# Fantasy player leaderboard for a position, sorted by the requested stat.
@router.post("/api/leaderboard")
async def leaderboard(req: LeaderboardRequest):
    current_league_id.set(req.league_id)
    try:
        players = await asyncio.to_thread(get_player_leaderboard, req.position, req.size, req.sort_by)
    except Exception as err:
        emit("error", route="leaderboard", error=str(err))
        raise HTTPException(status_code=500, detail="internal server error")

    return {"position": req.position, "players": players}
