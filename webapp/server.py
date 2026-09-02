"""Chat UI + live graph-trace server for fantasy_agent.

Run: uvicorn webapp.server:app --reload --reload-dir webapp --reload-dir fantasy_agent --port 8787
Then open http://localhost:8787

One in-memory conversation per browser session_id (no auth, no DB - this is
a local dev tool). /api/chat streams two kinds of events over SSE:
  - trace events from fantasy_agent.trace (node_start/node_end/tool_call/
    tool_result/node_warning) - one per graph step, as it happens.
  - token events - the personality node's reply, streamed word-by-word.
  - a final `done` event with the full reply text, or `error` on failure.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from fantasy_agent import trace
from fantasy_agent.graph import build_graph

app = FastAPI()
graph = build_graph()


def _server_version() -> str:
    # Derived from git, not hand-maintained, so it can never drift from what
    # code is actually running - the one thing a manual version string can't
    # promise. "+dirty" flags uncommitted edits (e.g. mid-development reload).
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"{sha}+dirty" if dirty else sha
    except Exception:
        return "unknown"


VERSION = _server_version()


@app.get("/api/version")
async def version():
    return {"version": VERSION}

_sessions: dict[str, list] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    messages = _sessions.setdefault(req.session_id, [])
    messages.append(HumanMessage(content=req.message))

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    async def run_graph():
        try:
            with trace.bind(loop, queue):
                result = await asyncio.to_thread(graph.invoke, {"messages": messages})
            _sessions[req.session_id] = result["messages"]
            await queue.put({"type": "done", "text": result["messages"][-1].text})
        except Exception as err:
            messages.pop()  # drop the failed user turn, mirrors chat.py
            await queue.put({"type": "error", "message": str(err)})
        finally:
            await queue.put(None)  # sentinel: closes the stream

    asyncio.create_task(run_graph())

    async def event_stream():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/reset")
async def reset(req: dict):
    _sessions.pop(req.get("session_id"), None)
    return {"ok": True}


@app.middleware("http")
async def no_cache_static(request, call_next):
    # Local dev tool: static files change frequently and a stale cached
    # app.js/style.css left over from before an edit is easy to mistake for
    # a real bug. no-store (not just no-cache) so browsers never reuse a
    # cached copy at all, even without revalidating first - a plain reload
    # was still serving stale JS straight from disk cache under no-cache.
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
