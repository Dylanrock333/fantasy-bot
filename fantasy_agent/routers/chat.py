"""Chat: runs the main agent graph for Discord's unauth path and the web's auth path."""
import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from fantasy_agent.auth import get_subscribed_user
from fantasy_agent.clients.espn_fantasy_client import current_espn_cookies, current_league_id, current_team_context
from fantasy_agent.db import User
from fantasy_agent.logging.trace import emit


class ChatRequest(BaseModel):
    message: str
    league_id: int
    team_name: str | None = None
    # Optional per-caller ESPN cookies. Omitted today (Discord falls back to the shared
    # ESPN_S2/SWID env vars); once Discord is issued its own credentials, it can send these
    # instead of relying on that shared fallback.
    espn_s2: str | None = None
    swid: str | None = None


class MeChatRequest(BaseModel):
    message: str


def create_router(graph) -> APIRouter:
    """Build the chat router around the already-compiled, shared graph singleton."""
    router = APIRouter()

    async def _run_chat(
        message: str, league_id: int, team_name: str | None, espn_cookies: tuple[str, str] | None = None
    ) -> dict:
        messages = [HumanMessage(content=message)]
        current_league_id.set(league_id)
        current_team_context.set(team_name)
        current_espn_cookies.set(espn_cookies)

        t0 = time.monotonic()
        try:
            # to_thread copies contextvars, so current_league_id reaches the worker thread.
            result = await asyncio.to_thread(
                graph.invoke, {"messages": messages}, config={"recursion_limit": 30}
            )
        except Exception as err:
            emit("error", route="chat", error=str(err))
            raise HTTPException(status_code=500, detail="internal server error")
        finally:
            emit("graph_end", graph="chat", duration_ms=int((time.monotonic() - t0) * 1000))

        return {"reply": result["messages"][-1].text}

    # Discord's path: caller supplies league_id/team_name directly, no auth.
    @router.post("/api/chat")
    async def chat(req: ChatRequest):
        cookies = (req.espn_s2, req.swid) if req.espn_s2 and req.swid else None
        return await _run_chat(req.message, req.league_id, req.team_name, cookies)

    # Web path: league_id/team_name come from the authenticated user, not the request.
    @router.post("/api/me/chat")
    async def me_chat(req: MeChatRequest, user: User = Depends(get_subscribed_user)):
        if user.league_id is None:
            raise HTTPException(status_code=400, detail="no league linked to this account")
        return await _run_chat(req.message, user.league_id, user.team_name, (user.espn_s2, user.swid))

    return router
