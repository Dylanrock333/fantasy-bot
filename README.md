# Fantasy Bot

An API that answers fantasy-football questions by pulling live data from
your private ESPN fantasy league and public NFL sources, then replying in a
short, opinionated voice. Built as a LangGraph supervisor + parallel
category-worker graph so each data domain (roster, standings, injuries,
scores, ...) is fetched by its own small, isolated tool-calling loop instead
of one agent with every tool in scope.

The [Discord bot](https://github.com/Dylanrock333/the-fantasy-zone-discord)
is the only client: it calls this API's `/api/chat` endpoint and streams
back the reply.

## Layout

```
fantasy_espn/       Private ESPN fantasy-league client (espn_api-based) - needs league auth
fantasy_agent/       The LangGraph agent itself
  graph.py             Builds the graph: supervisor -> Send(run_category) x N -> personality
  trace.py             emit() event hook nodes call instead of print() - prints, and also
                        forwards to a sink when one's bound (see api/server.py)
  tools/                One module per category (fantasy_*, nfl_*), each exporting TOOLS;
                         tools/__init__.py wires them into CATEGORY_REGISTRY
  clients/              Shared singletons (fantasy league client, public NFL data client)
api/                 FastAPI server - the whole surface Discord talks to
  server.py            /api/chat (SSE: trace events + streamed reply tokens), /api/reset
docs/                Consolidated reference docs (see below)
```

Add a new data source by adding a `@tool` function to the right module in
`fantasy_agent/tools/` (or a new module + one line in `tools/__init__.py` for
a new category) - the supervisor and graph pick it up automatically, no
graph changes needed. See `docs/NFL_PUBLIC_API.md` / `docs/FANTASY_ESPN_API.md`
for what's available to call, and `docs/LANGGRAPH_WORKFLOW.md` for how the
graph itself works.

## Setup

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
```

`.env` (gitignored) needs:
```
GOOGLE_API_KEY=AIza...
GOOGLE_API_KEY_BACKUP=AIza...          # optional - graph.py retries on this if the
                                        # primary key is rate-limited or out of quota
ESPN_S2=...                           # from your browser's espn.com cookies, private league auth
SWID=...                              # same
```
`fantasy_espn/espn_client.py` hardcodes `LEAGUE_ID` and `YEAR` for the
private league - update those two constants there if either changes.

## Running it

```bash
venv/bin/uvicorn api.server:app --reload --reload-dir api --reload-dir fantasy_agent --port 8787
```
Point the Discord bot's `FANTASY_AGENT_URL` at `http://localhost:8787` (its
default). To reach it from another machine without opening a public port,
`tailscale serve --bg 8787` shares it tailnet-only (never use `tailscale
funnel` here - the app has no auth, and funnel makes it internet-public).

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
missed something. See `docs/LANGGRAPH_WORKFLOW.md` for the node-level detail.

## Notes for whoever (human or agent) picks this up next

- **Tracing**: every node emits structured events via `fantasy_agent/trace.py`'s
  `emit()` instead of `print()` directly. `emit()` always prints; `api/server.py`
  additionally binds a per-request `asyncio.Queue` for the duration of one
  `graph.invoke()` call and forwards each event to that request's caller over
  SSE. If you add a new node or a new kind of step worth surfacing, emit a
  `node_start`/`node_end` pair (with `duration_ms`) around it - no consumer
  changes needed, unrecognized event types just pass through.
- **Streaming and message history don't mix carelessly**: `personality_node`
  used to merge raw `AIMessageChunk`s from `.stream()` with `+`, which could
  leave a stray *empty* text content block in the stored message. That
  message then gets resent as conversation history on the next turn, and
  the model provider rejects the whole request 400
  (`"text content blocks must be non-empty"`). Fixed by collecting streamed
  text into a plain string and wrapping it in a clean `AIMessage(content=...)`
  before it goes into graph state - don't revert to storing raw chunks.
- **Session state is in-memory only**, in `api/server.py`'s `_sessions` dict
  (keyed by the caller-supplied `session_id`). Nothing persists across a
  process restart - there's no database yet.
- **Secrets**: `.env` and `venv/` are gitignored - keep it that way, never
  commit `ESPN_S2`/`SWID`/API keys.
- **This repo**: private GitHub repo at `github.com/Dylanrock333/fantasy-bot`,
  `main` branch. `gh` CLI is installed and authenticated as `Dylanrock333`
  on this machine if you need it for PRs/issues.
