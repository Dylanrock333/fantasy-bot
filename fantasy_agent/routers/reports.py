"""Weekly recap and matchup preview reports, each with an optional base64 PNG."""
import asyncio
import base64
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fantasy_agent.clients.espn_fantasy_client import current_league_id
from fantasy_agent.logging.trace import emit


class WeeklyRecapRequest(BaseModel):
    league_id: int
    week: int = 0


class MatchupPreviewRequest(BaseModel):
    league_id: int
    week: int = 0
    previous_recap_context: str | None = None


def create_router(weekly_recap_graph, matchup_preview_graph) -> APIRouter:
    """Build the reports router around the already-compiled, shared graph singletons."""
    router = APIRouter()

    # Weekly recap; the power-ranking image is base64 PNG or null if generation failed.
    @router.post("/api/weekly-recap")
    async def weekly_recap(req: WeeklyRecapRequest):
        current_league_id.set(req.league_id)
        t0 = time.monotonic()
        try:
            result = await asyncio.to_thread(
                weekly_recap_graph.invoke, {"week": req.week}
            )
        except Exception as err:
            emit("error", route="weekly_recap", error=str(err))
            raise HTTPException(status_code=500, detail="internal server error")
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

    # Matchup preview; the matchup image is base64 PNG or null if generation failed.
    @router.post("/api/matchup-preview")
    async def matchup_preview(req: MatchupPreviewRequest):
        current_league_id.set(req.league_id)
        t0 = time.monotonic()
        try:
            result = await asyncio.to_thread(
                matchup_preview_graph.invoke,
                {"week": req.week, "previous_recap_context": req.previous_recap_context},
            )
        except Exception as err:
            emit("error", route="matchup_preview", error=str(err))
            raise HTTPException(status_code=500, detail="internal server error")
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

    return router
