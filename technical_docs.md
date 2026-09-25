# Fantasy Bot - Technical Docs (audit groundwork)

Python 3 / FastAPI / LangGraph. Client: Discord bot (`the-fantasy-zone-discord`). Text LLM: Google Gemini via `langchain_google_genai`. Images: OpenAI `gpt-image-2`.

## 1. Features & responsibilities

- Answers free-text fantasy-football questions using live private ESPN league data (`espn_api`, needs `ESPN_S2`/`SWID`) + public unauthenticated ESPN NFL endpoints.
- Chat graph: supervisor classifies -> parallel tool-gathering per category -> in-character reply -> critique (one optional retry).
- Weekly recap: LLM league summary + power rankings + generated poster image.
- Matchup preview: projections + lineup-change flags -> LLM preview + generated scoreboard image.
- Player leaderboard by position (rostered + free agents), no LLM.
- Chart rendering: bot emits ```chart``` JSON in replies; `/api/chart` renders it to PNG (matplotlib).
- Multi-league: `league_id` arrives per request, set in a `ContextVar`; League objects cached in-process 30 min.
- NOT: stateless per request (no conversation memory/DB; chat takes a single message, no history), no auth on the API, no streaming, no write actions to ESPN (read-only), no scheduling (Discord bot triggers recap/preview), no persistence, no rate limiting.
- Config via env: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ESPN_S2`, `SWID`, `FANTASY_AGENT_MODEL` (default `gemini-3.7-flash`), `FANTASY_AGENT_OPENAI_IMAGE_MODEL`. Season is hardcoded (`YEAR=2026`, `SEASON_KICKOFF`) in `espn_fantasy_client.py`.

## 2. Repo tree

Line counts via `wc -l`. Total tracked Python ~2,560 lines.

```
fantasy-bot/
├── README.md (158)                  project overview, layout, endpoints, run instructions
├── requirements.txt (13)            deps (langgraph, langchain-google-genai, openai, espn-api, fastapi, uvicorn, matplotlib, rapidfuzz, deepeval, google-genai...)
├── .gitignore (14)                  ignores .env, secrets/, venv/, __pycache__, tests/audit_output/, beads/dolt files
├── .env                             local secrets (gitignored; not read)
├── secrets/                         folder only (gitignored; holds a service-account file; contents not inspected)
├── venv/                            local virtualenv (ignored)
├── api/, fantasy_espn/              stale dirs: contain only __pycache__ (old server.py / espn_client.pyc); no source; ignored by .gitignore
├── .claude/settings.json (8)        Claude Code plugin toggles
├── .codex/{config.toml (2), hooks.json (51)}   Codex hook config (tooling, not app code)
├── .agents/skills/                  agent-tooling skill docs, not app code
│   ├── beads/ (SKILL.md 80, agents/openai.yaml 4)   beads issue-tracker skill
│   └── gemini-api/ (SKILL.md 251, references/*.md ~970 total, 8 files)   Gemini API reference docs
├── docs/
│   ├── FANTASY_ESPN_API.md (132)    espn_api private-league reference
│   ├── NFL_PUBLIC_API.md (127)      ESPN public NFL endpoint reference
│   └── LANGGRAPH_WORKFLOW.md (147)  chat-graph explainer 
├── scripts/run_weekly_recap.py (43) CLI: run recap graph for --league-id/--week, print results
├── tests/chat_audit.py (107)        manual audit: run canned prompts through chat graph, write traces/charts to tests/audit_output/ (no assertions, not a test suite)
└── fantasy_agent/
    ├── server.py (137)              FastAPI app; compiles 3 graphs at import; 5 endpoints
    ├── graphs/
    │   ├── graph.py (427)           chat graph: supervisor/run_category/personality/critique; also `invoke_llm`, `MODEL`, `API_KEY`
    │   ├── weekly_recap_graph.py (238)   linear 3-node recap graph
    │   └── matchup_preview_graph.py (256) linear 4-node preview graph
    ├── clients/
    │   ├── espn_fantasy_client.py (56)   League factory, per-league TTL cache, `current_league_id` ContextVar, `nfl_game_week()`
    │   └── espn_nfl_client.py (92)       requests helpers + fuzzy team/athlete lookup for public ESPN NFL API
    ├── tools/                       LangChain @tool modules, one per category
    │   ├── __init__.py (43)         CATEGORY_REGISTRY / CATEGORY_DESCRIPTIONS (module docstrings = supervisor prompt text)
    │   ├── fantasy_matchup_tools.py (69)     4 tools
    │   ├── fantasy_player_tools.py (80)      2 tools + non-tool `get_player_leaderboard` (used by /api/leaderboard)
    │   ├── fantasy_roster_tools.py (88)      4 tools (roster, settings, scoring, draft)
    │   ├── fantasy_standings_tools.py (77)   6 tools
    │   ├── fantasy_transaction_tools.py (19) 1 tool (recent activity)
    │   ├── nfl_game_tools.py (152)           6 tools (result, plays, odds, broadcast, officials, leaders)
    │   ├── nfl_news_tools.py (98)            4 tools
    │   ├── nfl_player_tools.py (213)         6 tools
    │   ├── nfl_scores_tools.py (57)          2 tools (scoreboard, standings)
    │   └── nfl_team_tools.py (217)           10 tools
    ├── utils/
    │   ├── chart_render.py (56)     matplotlib `bar`/`comparison` JSON -> PNG bytes
    │   ├── openai_image_gen.py (26) `generate_image(prompt,size,quality)` via OpenAI
    │   └── __init__.py
    ├── logging/trace.py (7)         `emit()` = print("[trace] ...")
    └── (clients|graphs|logging|utils)/__init__.py   empty package markers
```

## 3. Graph summary

Shared: all LLM calls go through `invoke_llm(build_llm, ...)` (graph.py) which builds a fresh `ChatGoogleGenerativeAI(model=MODEL, google_api_key=API_KEY, reasoning_effort=...)` per call. Graphs are compiled once at import and shared across requests; no checkpointer.

### 3.1 Chat graph (`graphs/graph.py`, `build_graph`)

State `AgentState(MessagesState)`: `messages`, `categories: list[str]`, `category: str` (per parallel branch), `reasoning: str`, `critique_rounds: int`, `critique_satisfied: bool`.

| Node | Model / effort | Prompt | Tools | Output |
|---|---|---|---|---|
| `supervisor` | MODEL, high, `with_structured_output(CategoryChoice)` | `_supervisor_system()`: date + category list (from tool module docstrings) + 3 few-shot examples | none | `categories` (filtered to valid registry keys), `reasoning` |
| `run_category` (xN parallel via `Send`) | MODEL, medium, `bind_tools(_ALL_TOOLS)` | inline system: date, dispatched category, supervisor plan, team-name-is-not-player rule | ALL 45 tools from all 10 categories (category only labels the branch) | manual loop, max `MAX_TOOL_ROUNDS=5`, tool calls run one at a time through `ToolNode(handle_tool_errors=True)`; returns appended messages |
| `personality` | MODEL, high, plain | `_personality_system()`: grounding hard rule, 1-6 sentences, bold player names, one link, chart JSON format | none | one `AIMessage`; fallback text if empty |
| `critique` | MODEL, medium, `with_structured_output(Critique)` | inline strict-reviewer prompt | none | `critique_satisfied`, `critique_rounds+1`, `reasoning`=missing |

Edges / routing:
- `START -> supervisor`
- `supervisor -> route_to_categories`: no categories -> `personality`; else `Send("run_category", {...})` per category
- `run_category -> personality` (fan-in)
- `personality -> critique`
- `critique -> route_after_critique`: END if satisfied OR `critique_rounds > MAX_CRITIQUE_ROUNDS(1)`; else `supervisor`

```
START -> supervisor --(none)--------------------------> personality -> critique --satisfied--> END
            |                                              ^              |
            +--Send x N--> run_category (tool loop <=5) ---+              +--not satisfied (<=1 retry)--> supervisor
```

Note: `critique_rounds > 1` means a retry can happen once (round 1 -> loops; round 2 -> END). Retry appends to same `messages`, so `personality` answers again from the accumulated transcript.

Tool categories (45 tools): fantasy_standings 6, fantasy_roster 4, fantasy_matchup 4, fantasy_player 2, fantasy_transaction 1, nfl_scores 2, nfl_team 10, nfl_player 6, nfl_news 4, nfl_game 6.

### 3.2 Weekly recap graph (`graphs/weekly_recap_graph.py`)

State `WeeklyRecapState` (TypedDict): `week, matchups, league_summary, power_rankings, power_ranking_image`. No tools.

| Node | Work | Model |
|---|---|---|
| `get_matchups` | `league.box_scores(week or nfl_game_week())` -> matchup dicts | none |
| `league_summary` | standings + results -> structured `WeeklySummaryOutput` (3-5 beat summary + ranked teams w/ tags); "max unhinged" roast prompt | MODEL, high |
| `power_ranking_image` | builds poster prompt, `generate_image(size="1536x1024")`; exception -> `node_error`, image None | OpenAI gpt-image-2 |

Flow: `START -> get_matchups -> league_summary -> power_ranking_image -> END` (linear, no conditions).

### 3.3 Matchup preview graph (`graphs/matchup_preview_graph.py`)

State `MatchupPreviewState`: `week, previous_recap_context, matchups, lineup_flags, league_preview, matchup_image`. No tools.

| Node | Work | Model |
|---|---|---|
| `get_matchup_data` | box scores + standings records -> projections, projected winner, margin (`week or league.current_week`) | none |
| `flag_lineup_changes` | last week's zero-point non-bye starters per team; status dropped / benched / still starting; injury | none |
| `matchup_preview` | structured `MatchupPreviewOutput` (one joke beat per matchup), optional previous recap as color | MODEL, high |
| `matchup_image` | scoreboard table prompt -> `generate_image`; failure -> None | OpenAI gpt-image-2 |

Flow: `START -> get_matchup_data -> flag_lineup_changes -> matchup_preview -> matchup_image -> END` (linear).

## 4. API map (`fantasy_agent/server.py`)

FastAPI, no auth, no CORS, no middleware. `current_league_id.set(league_id)` before work; `asyncio.to_thread` copies the contextvar to the worker. Run: `uvicorn fantasy_agent.server:app --port 8787`.

| Method | Path | Request body | Response | Internals | Errors |
|---|---|---|---|---|---|
| POST | `/api/chat` | `{message: str, league_id: int}` | `{reply: str}` | `graph.invoke({"messages":[HumanMessage]})` in thread (chat graph) | 500 `{detail: str(err)}` |
| POST | `/api/chart` | untyped `dict` (chart JSON: `type` bar/comparison, ...) | `image/png` bytes | `render_chart_png(req)` in thread; direct, no LLM | 422 if shape unrecognized; render exceptions not caught (500 default) |
| POST | `/api/weekly-recap` | `{league_id: int, week: int=0}` | `{week, league_summary: str, power_rankings: [{rank,team,tag}], power_ranking_image_base64: str\|null}` | `weekly_recap_graph.invoke` in thread | 500 `{detail}` |
| POST | `/api/matchup-preview` | `{league_id: int, week: int=0, previous_recap_context: str\|null}` | `{week, league_preview: str, matchups: [{team_a,proj_a,record_a,team_b,proj_b,record_b,winner,margin}], matchup_image_base64: str\|null}` | `matchup_preview_graph.invoke` in thread | 500 `{detail}` |
| POST | `/api/leaderboard` | `{league_id: int, position: str, size: int=15, sort_by: str="points"}` (sort_by: points/avg_points/projected_points/percent_owned; unknown -> points) | `{position, players: [{rank,name,pro_team,total_points,avg_points,projected_total_points,percent_owned,owner_team_name\|null}]}` | `get_player_leaderboard(...)` direct in thread; no LLM | 500 `{detail}` |

Notes: `/api/chart` sets no league id. `week=0` means "default" (recap: `nfl_game_week()`; preview: `league.current_week`). Error `detail` leaks raw exception strings.

## 5. Audit notes

- Stale dirs `api/` and `fantasy_espn/` hold only `__pycache__` (old `server.py`/`espn_client` pyc); no source. Ignored by git but dead clutter.
- `requirements.txt` lists `deepeval` and `google-genai`; no import of either in `fantasy_agent/`, `scripts/`, `tests/` (only `langchain_google_genai` is used). `.agents/skills/gemini-api/` docs are tooling, not app code.
- README and `docs/LANGGRAPH_WORKFLOW.md` were updated to match the code (critique loop, 5 tool rounds, `gemini-3.7-flash`, `/api/leaderboard`, no `image_gen.py`).
- `graphs/graph.py::run_category_node` gives every branch all 45 tools (`_ALL_TOOLS`), so the category split only parallelizes/labels; also rebuilds `ToolNode` and an LLM per round and runs tool calls sequentially.
- Fuzzy-match logic duplicated: `tools/fantasy_roster_tools.py:get_team_roster` (substring then `process.extractOne`, cutoff 75) vs `clients/espn_nfl_client.py` (cutoffs 70 and 80 in two lookups).
- Near-duplicate LLM builder lambdas (`ChatGoogleGenerativeAI(... reasoning_effort=...)`) repeated in `graph.py` (4x), `weekly_recap_graph.py`, `matchup_preview_graph.py`; recap/preview `try: generate_image / except emit node_error` blocks and base64 encoding in `server.py` are also copy-pasted.
- Season constants hardcoded in `clients/espn_fantasy_client.py` (`YEAR=2026`, `SEASON_KICKOFF`); `sys.path` hacks repeated in `server.py`, `tools/__init__.py`, `scripts/run_weekly_recap.py`, `tests/chat_audit.py`; `load_dotenv()` called in both `server.py` and `espn_fantasy_client.py`.
- `tests/chat_audit.py` is the only "test": manual, no assertions; `API_KEY` is read at import time (`graph.py`, `openai_image_gen.py`) so a missing key only fails at first call. `/api/chart` accepts an untyped `dict` and has no size/shape validation; `logging/trace.py` is `print`-based (a package named `logging` inside `fantasy_agent` is easy to confuse with stdlib).

## Backlog: code debt

- Empty `api/` and `fantasy_espn/` dirs (only `__pycache__`).
- Unused deps: `deepeval`, `google-genai`.
- `run_category_node` (`graphs/graph.py`) binds all 45 tools to every branch; the category split is cosmetic.
- Duplicated fuzzy-match, LLM-builder and image-gen boilerplate across files.
