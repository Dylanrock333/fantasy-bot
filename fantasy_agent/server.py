"""FastAPI server exposing the agent graphs to the Discord bot and the web client.

Run: uvicorn fantasy_agent.server:app --reload --reload-dir fantasy_agent --port 8787

Routes are grouped by responsibility under fantasy_agent/routers/ (auth, chat,
league, reports). This module only wires up the app: shared graph singletons,
the DB, CORS, a catch-all error handler, and router mounting.
"""
import os
import sys
from pathlib import Path

# Make the repo root importable and load .env before importing project modules.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fantasy_agent.logging.trace import emit
from fantasy_agent.graphs.graph import build_graph
from fantasy_agent.graphs.weekly_recap_graph import build_weekly_recap_graph
from fantasy_agent.graphs.matchup_preview_graph import build_matchup_preview_graph
from fantasy_agent.db import init_db
from fantasy_agent.routers import auth, chat, league, reports

# Graphs are compiled once at import time and shared across requests.
app = FastAPI()
graph = build_graph()
weekly_recap_graph = build_weekly_recap_graph()
matchup_preview_graph = build_matchup_preview_graph()
init_db()

_cors_origins = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _cors_origins == "*" else [o.strip() for o in _cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Backstop for any exception a route doesn't explicitly catch - never leak
# internals to the client, just log and return a generic 500.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, err: Exception):
    emit("error", route=request.url.path, error=str(err))
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


app.include_router(auth.router)
app.include_router(chat.create_router(graph))
app.include_router(league.router)
app.include_router(reports.create_router(weekly_recap_graph, matchup_preview_graph))
