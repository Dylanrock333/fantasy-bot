"""API server for fantasy_agent - the Discord bot is its only client.

Run: uvicorn api.server:app --reload --reload-dir api --reload-dir fantasy_agent --port 8787

One in-memory conversation per caller-supplied session_id (no auth, no DB).
/api/chat runs the graph and returns the reply as plain JSON.
/api/chart renders a `bar`/`comparison` chart JSON payload to a PNG.
"""
import asyncio
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

from fantasy_agent.chart_render import render_chart_png
from fantasy_agent.graph import build_graph

app = FastAPI()
graph = build_graph()

_sessions: dict[str, list] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = _sessions.setdefault(req.session_id, [])
    messages.append(HumanMessage(content=req.message))

    try:
        result = await asyncio.to_thread(graph.invoke, {"messages": messages})
    except Exception as err:
        messages.pop()  # drop the failed user turn so it isn't replayed next call
        raise HTTPException(status_code=500, detail=str(err))

    _sessions[req.session_id] = result["messages"]
    return {"reply": result["messages"][-1].text}


@app.post("/api/chart")
async def chart(req: dict):
    png_bytes = await asyncio.to_thread(render_chart_png, req)
    if png_bytes is None:
        raise HTTPException(status_code=422, detail="unrecognized chart shape")
    return Response(content=png_bytes, media_type="image/png")


@app.post("/api/reset")
async def reset(req: dict):
    _sessions.pop(req.get("session_id"), None)
    return {"ok": True}
