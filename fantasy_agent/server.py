"""API server for fantasy_agent - the Discord bot is its only client.

Run: uvicorn fantasy_agent.server:app --reload --reload-dir fantasy_agent --port 8787

/api/chat runs the graph and returns the reply as plain JSON.
/api/league/{league_id}/teams lists a league's teams (id + name).
/api/league/{league_id}/teams/{team_id}/players lists a team's roster.
/api/chart renders a `bar`/`comparison` chart JSON payload to a PNG.
/api/weekly-recap's power_ranking_image_base64 is base64 PNG, or null if
image generation failed - see weekly_recap_graph.py's power_ranking_image_node.
/api/matchup-preview's matchup_image_base64 is base64 PNG, or null if
image generation failed - see matchup_preview_graph.py's matchup_image_node.
"""
import asyncio
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException, Response
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from fantasy_agent.utils.chart_render import render_chart_png
from fantasy_agent.graphs.graph import build_graph
from fantasy_agent.graphs.weekly_recap_graph import build_weekly_recap_graph
from fantasy_agent.graphs.matchup_preview_graph import build_matchup_preview_graph
from fantasy_agent.clients.espn_fantasy_client import current_league_id, league_singleton

app = FastAPI()
graph = build_graph()
weekly_recap_graph = build_weekly_recap_graph()
matchup_preview_graph = build_matchup_preview_graph()

class ChatRequest(BaseModel):
    message: str
    league_id: int


@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = [HumanMessage(content=req.message)]
    current_league_id.set(req.league_id)

    try:
        # asyncio.to_thread propagates the current contextvars context
        # (including current_league_id) into the executor thread.
        result = await asyncio.to_thread(graph.invoke, {"messages": messages})
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    return {"reply": result["messages"][-1].text}


@app.get("/api/league/{league_id}/teams")
async def league_teams(league_id: int):
    current_league_id.set(league_id)
    try:
        league = await asyncio.to_thread(league_singleton)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    return {"teams": [{"id": t.team_id, "name": t.team_name} for t in league.teams]}


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


@app.post("/api/chart")
async def chart(req: dict):
    png_bytes = await asyncio.to_thread(render_chart_png, req)
    if png_bytes is None:
        raise HTTPException(status_code=422, detail="unrecognized chart shape")
    return Response(content=png_bytes, media_type="image/png")


class WeeklyRecapRequest(BaseModel):
    league_id: int
    week: int = 0


@app.post("/api/weekly-recap")
async def weekly_recap(req: WeeklyRecapRequest):
    current_league_id.set(req.league_id)
    try:
        result = await asyncio.to_thread(
            weekly_recap_graph.invoke, {"week": req.week}
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

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


@app.post("/api/matchup-preview")
async def matchup_preview(req: MatchupPreviewRequest):
    current_league_id.set(req.league_id)
    try:
        result = await asyncio.to_thread(
            matchup_preview_graph.invoke,
            {"week": req.week, "previous_recap_context": req.previous_recap_context},
        )
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

    image_bytes = result.get("matchup_image")
    return {
        "week": result["week"],
        "league_preview": result["league_preview"],
        "matchups": result["matchups"],
        "matchup_image_base64": (
            base64.b64encode(image_bytes).decode("ascii") if image_bytes else None
        ),
    }
