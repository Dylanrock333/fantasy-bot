# Fantasy Bot

A chat agent that answers fantasy-football questions by pulling live data
from your private ESPN fantasy league and public NFL sources, then replying
in a short, opinionated voice. Built as a LangGraph supervisor + parallel
category-worker graph so each data domain (roster, standings, injuries,
scores, ...) is fetched by its own small, isolated tool-calling loop instead
of one agent with every tool in scope.

Two ways to talk to it: a CLI (`fantasy_agent/chat.py`) and a local web chat
UI (`webapp/`) with a live side panel that shows the graph working -
supervisor's category picks, each tool call and its result, and the final
reply streaming in token by token.

## Layout

```
espn_nfl_public/   Public NFL data client + scripts (scores, rosters, news, ...) - no auth needed
fantasy_espn/       Private ESPN fantasy-league client (espn_api-based) - needs league auth
fantasy_agent/       The LangGraph agent itself
  graph.py             Builds the graph: supervisor -> Send(run_category) x N -> personality
  trace.py             emit() event hook nodes call instead of print() - no-ops with no sink bound
  tools/                One module per category (fantasy_*, nfl_*), each exporting TOOLS;
                         tools/__init__.py wires them into CATEGORY_REGISTRY
  clients/              Shared singletons (league client, per-conversation session history)
  chat.py               CLI entry point
  README.md             Detail on the graph's three node types and how to tune them
webapp/               FastAPI + vanilla JS/HTML/CSS chat UI, no build step
  server.py              /api/chat (SSE: trace events + streamed reply tokens), /api/reset
  static/                index.html / app.js / style.css - chat pane + collapsible trace pane
scripts/               One-off utilities (e.g. find_rookies.py)
```

Add a new data source by adding a `@tool` function to the right module in
`fantasy_agent/tools/` (or a new module + one line in `tools/__init__.py` for
a new category) - the supervisor and graph pick it up automatically, no
graph changes needed.

## Setup

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
```

`.env` (gitignored) needs:
```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_API_KEY_BACKUP=sk-ant-...   # optional - graph.py retries on this if the
                                       # primary key is rate-limited or out of credits
ESPN_S2=...                           # from your browser's espn.com cookies, private league auth
SWID=...                              # same
```
`fantasy_espn/espn_client.py` hardcodes `LEAGUE_ID` and `YEAR` for the
private league - update those two constants there if either changes.

## Running it

CLI:
```bash
venv/bin/python3 fantasy_agent/chat.py
```

Web UI (chat pane + live graph-trace pane):
```bash
venv/bin/uvicorn webapp.server:app --reload --port 8787
```
then open `http://localhost:8787`. To reach it from other devices without
opening a public port, `tailscale serve --bg 8787` shares it tailnet-only
(never use `tailscale funnel` here - the app has no auth, and funnel makes
it internet-public).

## Architecture

```
START -> supervisor -> Send(run_category) x N (parallel, or none) -> personality -> END
```
- **supervisor** classifies the incoming message into zero or more data
  categories via structured output. No tools, never talks to the user.
- **run_category** - one instance per chosen category, dispatched in
  parallel via `Send`. Only sees that category's own small tool list, loops
  tool-calls <-> itself (capped at `MAX_TOOL_ROUNDS`) until it has enough
  data or hits the cap.
- **personality** is the only node the user sees. It's under a hard
  grounding rule - every fact in its reply must come from tool results
  gathered this turn, nothing from model memory - and streams its reply
  token by token rather than returning it all at once.

It's a deliberately one-shot pipeline, not a network where agents call each
other: supervisor classifies once, categories run once, personality
synthesizes once. That bounds it structurally - fixed fan-out, capped tool
rounds, single synthesis step - so it can't infinite-loop, at the cost of
not being able to request more data mid-reply if the initial classification
missed something. See `fantasy_agent/README.md` for the node-level detail.

## Notes for whoever (human or agent) picks this up next

- **Tracing**: every node emits structured events via `fantasy_agent/trace.py`'s
  `emit()` instead of `print()` directly. With no sink bound it just prints
  (so the CLI is unaffected); `webapp/server.py` binds a per-request
  `asyncio.Queue` for the duration of one `graph.invoke()` call and forwards
  each event to that browser tab over SSE. If you add a new node or a new
  kind of step worth surfacing, emit a `node_start`/`node_end` pair (with
  `duration_ms`) around it and the trace panel picks it up with no frontend
  changes - `webapp/static/app.js`'s `addTraceEvent()` already has a
  fallback rendering for unrecognized event types.
- **Streaming and message history don't mix carelessly**: `personality_node`
  used to merge raw `AIMessageChunk`s from `.stream()` with `+`, which could
  leave a stray *empty* text content block in the stored message. That
  message then gets resent as conversation history on the next turn, and
  Anthropic's API rejects the whole request 400
  (`"text content blocks must be non-empty"`). Fixed by collecting streamed
  text into a plain string and wrapping it in a clean `AIMessage(content=...)`
  before it goes into graph state - don't revert to storing raw chunks.
- **Session state is in-memory only**, both in `fantasy_agent/clients/session.py`
  (used by anything with multiple conversations, e.g. a future Discord bot)
  and in `webapp/server.py`'s `_sessions` dict (keyed by a browser-generated
  `session_id` in `localStorage`). Nothing persists across a process
  restart - there's no database yet.
- **Secrets**: `.env` and `venv/` are gitignored - keep it that way, never
  commit `ESPN_S2`/`SWID`/Anthropic keys.
- **This repo**: private GitHub repo at `github.com/Dylanrock333/fantasy-bot`,
  `main` branch. `gh` CLI is installed and authenticated as `Dylanrock333`
  on this machine if you need it for PRs/issues.
