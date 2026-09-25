# Fantasy Bot

An API that answers fantasy-football questions by pulling live data from
your private ESPN fantasy league and public NFL sources, then replying in a
short, opinionated voice. Built as a LangGraph supervisor + parallel
category-worker graph so each data domain (roster, standings, injuries,
scores, ...) is fetched by its own small, isolated tool-calling loop instead
of one agent with every tool in scope. Two standalone LangGraph flows ride
alongside the chat graph: a weekly recap (league summary + power rankings +
a generated poster graphic) and a matchup preview (look-ahead summary +
projections + a generated scoreboard graphic).

The [Discord bot](https://github.com/Dylanrock333/the-fantasy-zone-discord)
is the only client: it calls this API's endpoints and gets JSON back (no
streaming - there's no web app to stream to).

## Layout

```
fantasy_agent/       The LangGraph agent and the FastAPI server around it
  graphs/               graph.py builds the main graph: supervisor -> Send(run_category) x N
                        -> personality -> critique (one optional retry); weekly_recap_graph.py and matchup_preview_graph.py
                        are the other two LangGraph entry points
  logging/              trace.py's emit() event hook nodes call instead of print(), for a
                        consistent, greppable log shape
  tools/                One module per category (fantasy_*, nfl_*), each exporting TOOLS;
                         tools/__init__.py wires them into CATEGORY_REGISTRY
  clients/              espn_fantasy_client.py (private league auth + League cache) and
                        espn_nfl_client.py (public NFL data API, no auth)
  utils/                chart_render.py renders the bot's ```chart``` JSON (bar/comparison)
                        to a PNG - shared by server.py's /api/chart and tests/chat_audit.py;
                        openai_image_gen.py generates recap/preview poster images
  server.py            FastAPI server - the whole surface Discord talks to:
                        /api/chat, /api/league/{league_id}/teams,
                        /api/league/{league_id}/teams/{team_id}/players,
                        /api/chart (chart JSON -> PNG), /api/weekly-recap,
                        /api/matchup-preview - plain JSON in/out (the two recap/preview
                        endpoints embed their poster PNG as base64 in the JSON, or
                        null if image generation failed), no streaming
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
OPENAI_API_KEY=sk-...                 # poster/scoreboard image generation for recap + preview
ESPN_S2=...                           # from your browser's espn.com cookies, private league auth
SWID=...                              # same
```
Optional overrides: `FANTASY_AGENT_MODEL` (text model, default `gemini-3.7-flash`) and
`FANTASY_AGENT_OPENAI_IMAGE_MODEL` (default `gpt-image-2`).

`league_id` is passed per-request (in the `/api/chat`, `/api/weekly-recap`,
`/api/matchup-preview`, and `/api/leaderboard` bodies), not hardcoded.
`fantasy_agent/clients/espn_fantasy_client.py` hardcodes `YEAR` and `SEASON_KICKOFF`
(Thursday of NFL week 1) - update both there once the season rolls over.

## Running it

```bash
venv/bin/uvicorn fantasy_agent.server:app --reload --reload-dir fantasy_agent --port 8787
```
Point the Discord bot's `FANTASY_AGENT_URL` at `http://localhost:8787` (its
default). To reach it from another machine without opening a public port,
`tailscale serve --bg 8787` shares it tailnet-only (never use `tailscale
funnel` here - the app has no auth, and funnel makes it internet-public).

## Architecture

```
START -> supervisor -> Send(run_category) x N (parallel, or none) -> personality -> critique -> END
                ^                                                                       |
                +------------------ not satisfied (at most one retry) -------------------+
```
- **supervisor** classifies the incoming message into zero or more data
  categories via structured output. No tools, never talks to the user.
- **run_category** - one instance per chosen category, dispatched in
  parallel via `Send`. Loops tool-calls <-> itself (capped at
  `MAX_TOOL_ROUNDS`, currently 5) until it has enough data or hits the cap.
  It is dispatched for one category but has every category's tools bound,
  so the split parallelizes and labels the work rather than restricting it.
- **personality** is the only node the user sees. It's under a hard
  grounding rule - every fact in its reply must come from tool results
  gathered this turn, nothing from model memory.
- **critique** reviews the reply against the gathered data. If more data
  would meaningfully improve the answer, it stores what's missing as the new
  plan and loops back to the supervisor, once at most (`MAX_CRITIQUE_ROUNDS`).

It's a deliberately bounded pipeline, not a network where agents call each
other: supervisor classifies, categories run, personality synthesizes, and
critique may send it around exactly one more time. Fixed fan-out, capped tool
rounds, and a capped retry mean it can't infinite-loop. See `docs/LANGGRAPH_WORKFLOW.md` for the node-level detail.

### Player leaderboard

`/api/leaderboard` ranks players at a position across rostered and free-agent
pools (sortable by total points, average points, projected points, or
ownership %). It calls `get_player_leaderboard` directly - no LLM or graph.

### Weekly recap and matchup preview

Two more LangGraph entry points, both linear (no supervisor/fan-out): a
Gemini call writes the text, then an image-generation call renders a
poster-style PNG:

```
weekly_recap_graph:     get_matchups -> league_summary -> power_ranking_image -> END
matchup_preview_graph:  get_matchup_data -> flag_lineup_changes -> matchup_preview -> matchup_image -> END
```

- **weekly_recap_graph** pulls the given week's box scores + standings and
  has one LLM call write a league summary and a full power-ranking list with
  an award-style tag per team, then generates a recap poster graphic from
  those rankings. Served at `/api/weekly-recap`; `scripts/run_weekly_recap.py`
  can also trigger it directly from the command line, no server needed.
- **matchup_preview_graph** pulls the upcoming week's projected matchups,
  flags any starter who scored zero last week (benched/dropped/still
  started, plus injury status), then has one LLM call write a look-ahead
  summary before generating a scoreboard-style preview graphic. Served at
  `/api/matchup-preview`.

Both image calls go through `fantasy_agent/utils/openai_image_gen.py`
(`generate_image`, backed by `OPENAI_API_KEY`). Either call can fail
independently of the text generation; the server returns the JSON payload
with the image field `null` rather than erroring the whole request.

## Roadmap / infra TODOs

Cross-cutting ops work spanning this repo and the
[Discord bot](https://github.com/Dylanrock333/the-fantasy-zone-discord).
Tracked here (and mirrored in the Discord repo's README) until there's a
shared issue tracker.

1. **Per-user private channels** - let a member get a private channel/thread
   with the bot (strategy chat, personal stats) that other league members
   can't read. Discord-side feature (permission overwrites or private
   threads); this API is stateless per-request so it just needs the caller
   to pass through a user-scoped channel id, no server change expected.
2. **Prod vs. test deployments** - split into a prod deployment (the real
   league list) and a test deployment (a small set of leagues Dylan
   controls) so new features/changes land in test first. Needs each
   deployment to run its own bot process + API instance with its own env
   vars/league config; this API is already stateless so running two copies
   should be cheap.
3. **Zero-downtime prod updates** - deploy changes to prod without a hard
   restart/reset that drops in-flight commands or scheduled jobs. Likely a
   process-manager or rolling-deploy concern more than an app-code concern.
4. **Consolidate commands/commish tools** - unify admin (commissioner-only)
   commands and any "reset the server" style operations behind one
   consistent surface instead of ad hoc scripts/commands.
5. **(Bonus) One-click server duplication** - an endpoint that spins up a
   duplicate Discord server from a name + league id and returns a commish
   invite link. First joiner claims commish (1 per league, needs a
   succession/hierarchy plan for if they leave); team names get pulled in
   automatically; each subsequent joiner picks a team that then sticks to
   their Discord user id (admin-resettable) so the bot knows whose team is
   asking by default. This is the biggest lift of the five - needs a
   user/team/league identity model that doesn't exist yet on either side.
