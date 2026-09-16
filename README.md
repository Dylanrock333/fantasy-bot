# Fantasy Bot

An API that answers fantasy-football questions by pulling live data from
your private ESPN fantasy league and public NFL sources, then replying in a
short, opinionated voice. Built as a LangGraph supervisor + parallel
category-worker graph so each data domain (roster, standings, injuries,
scores, ...) is fetched by its own small, isolated tool-calling loop instead
of one agent with every tool in scope.

The [Discord bot](https://github.com/Dylanrock333/the-fantasy-zone-discord)
is the only client: it calls this API's `/api/chat` endpoint and gets the
reply back as plain JSON (no streaming - there's no web app to stream to).

## Layout

```
fantasy_agent/       The LangGraph agent itself
  graph.py             Builds the graph: supervisor -> Send(run_category) x N -> personality
  trace.py             emit() event hook nodes call instead of print(), for a consistent,
                        greppable log shape
  chart_render.py       Renders the bot's ```chart``` JSON (bar/comparison) to a PNG -
                         shared by api/server.py's /api/chart and tests/chat_audit.py
  tools/                One module per category (fantasy_*, nfl_*), each exporting TOOLS;
                         tools/__init__.py wires them into CATEGORY_REGISTRY
  clients/              espn_fantasy_client.py (private league auth + League cache) and
                        espn_nfl_client.py (public NFL data API, no auth)
api/                 FastAPI server - the whole surface Discord talks to
  server.py            /api/chat, /api/chart (chart JSON -> PNG) - plain
                        JSON in, JSON/PNG out, no streaming
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
git config core.hooksPath .githooks   # strips AI co-author/session-link trailers - this repo is public
```

`.env` (gitignored) needs:
```
GOOGLE_API_KEY=AIza...
ESPN_S2=...                           # from your browser's espn.com cookies, private league auth
SWID=...                              # same
```
`fantasy_agent/clients/espn_fantasy_client.py` hardcodes `LEAGUE_ID` and `YEAR` for the
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
  gathered this turn, nothing from model memory.

It's a deliberately one-shot pipeline, not a network where agents call each
other: supervisor classifies once, categories run once, personality
synthesizes once. That bounds it structurally - fixed fan-out, capped tool
rounds, single synthesis step - so it can't infinite-loop, at the cost of
not being able to request more data mid-reply if the initial classification
missed something. See `docs/LANGGRAPH_WORKFLOW.md` for the node-level detail.