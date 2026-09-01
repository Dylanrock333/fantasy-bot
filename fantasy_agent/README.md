# Fantasy Agent

A supervisor + category-node LangGraph agent on top of `fantasy_espn/`
(private league) and `espn_nfl_public/` (public NFL data):

- **`supervisor`** — classifies the user's latest message into zero or more
  categories: `fantasy_*` (your private league) or `nfl_*` (real-world NFL
  data). No tools, never talks to the user.
- **`run_category`** — one instance per chosen category, dispatched in
  parallel. Only sees that category's own small tool list and loops
  tool-calls until it has enough data.
- **`personality`** — the only node the user sees. Takes everything every
  category gathered and writes a short, in-character reply. No tools.

```
START -> supervisor -> Send(run_category) x N (parallel, or none) -> personality -> END
```

Files:
- `tools/` — one module per category, prefixed `fantasy_*_tools.py` (your
  private league) or `nfl_*_tools.py` (real-world NFL), each exporting a
  `TOOLS` list; `tools/__init__.py` wires them into `CATEGORY_REGISTRY`.
- `graph.py` — builds the graph, the supervisor/category/personality prompts.
- `chat.py` — CLI loop.

Add a data source by adding a `@tool` function to the right category module
(or a new module + registry entry for a new category) — the supervisor and
graph pick it up automatically.

## Setup

1. Add your key to `.env` (already has an empty placeholder):
   ```
   GOOGLE_API_KEY=AIza...
   ```
2. Run:
   ```bash
   python3 fantasy_agent/chat.py
   ```

## Tuning

- Model: set `FANTASY_AGENT_MODEL` env var (defaults to `claude-sonnet-5`) —
  same model powers every node, just with different system prompts/tools.
- Reply length: edit `PERSONALITY_SYSTEM` in `graph.py`.
- Max tool-call rounds per category: `MAX_TOOL_ROUNDS` in `graph.py`.
