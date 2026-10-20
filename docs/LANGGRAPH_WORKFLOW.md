# LangGraph Workflow

`fantasy_agent/graphs/graph.py` builds a bounded pipeline for every
message: figure out what's being asked, go fetch the data for it (in
parallel if more than one topic applies), write one reply, then have a
critic check it. It's not a free-form network of agents chatting with each
other — each step runs once (the data-fetching step once per topic), tool
calls are hard-capped, and the critic can send the graph back to the
supervisor at most once. That keeps things predictable and stops the graph
from ever looping forever.

```mermaid
flowchart TD
    U[User message] --> S["supervisor\n(classify into 0–N categories)"]
    S -->|no categories| P
    S -->|fan out, one branch per category| RC1
    S -->|fan out| RC2
    S -->|fan out| RCn

    subgraph "run_category (parallel, one per chosen category)"
        RC1["run_category: fantasy_roster\ncall tools ⇄ read results\n(up to 5 rounds)"]
        RC2["run_category: nfl_scores\ncall tools ⇄ read results\n(up to 5 rounds)"]
        RCn["run_category: ...\n(fixed tool list per category)"]
    end

    RC1 --> P
    RC2 --> P
    RCn --> P
    P["personality\n(one synthesis pass)"] --> C["critique\n(needs more data?)"]
    C -->|satisfied, or retry already used| R[Reply]
    C -->|not satisfied, at most once| S
```

## Node functions: chat graph (`fantasy_agent/graphs/graph.py`)

#### `supervisor_node(state) -> {categories, reasoning}`
```python
choice = invoke_llm(..., with_structured_output(CategoryChoice))  # {reasoning, categories}
valid = [c for c in choice.categories if c in CATEGORY_REGISTRY]
return {"categories": valid, "reasoning": choice.reasoning}
```
- Runs once. Classifies the message into 0–N categories from `CATEGORY_REGISTRY`
  (`fantasy_*` = private league, `nfl_*` = real-world data). Never calls a tool.
- Invalid category names the model invents are dropped silently.
- On a critique loop-back, the retry prompt carries the critique's `missing` note as the replan.

#### `route_to_categories(state) -> "personality" | list[Send]`
```python
if not state["categories"]:
    return "personality"
return [Send("run_category", {"messages": ..., "category": c, "reasoning": ...}) for c in state["categories"]]
```
- Conditional edge (not a node). Fans out one `run_category` branch per category, or skips to `personality` if none were picked.

#### `run_category_node(state) -> {messages}`
```python
for _ in range(MAX_TOOL_ROUNDS):          # MAX_TOOL_ROUNDS = 5
    response = invoke_llm(..., bind_tools(_ALL_TOOLS))
    if not response.tool_calls:
        break
    for tc in response.tool_calls:
        ...  # tool_node.invoke, append result to `local`
return {"messages": local}
```
- Runs once per chosen category, in parallel. Every instance is bound to `_ALL_TOOLS` (every tool, not just its own category's).
- Loops up to `MAX_TOOL_ROUNDS`; stops early once the model replies with no tool calls.
- Hard rule in its prompt: call tools only, never answer — that's `personality`'s job.

#### `personality_node(state) -> {messages}`
```python
full_text = _chunk_text(invoke_llm(_llm, context))
if not full_text.strip():
    full_text = "Sorry, I didn't quite catch that - could you rephrase?"
return {"messages": [AIMessage(content=full_text)]}
```
- Runs once; the only node the user sees output from. One model call, grounded strictly in this turn's tool results.
- A checklist message lists which categories actually ran, so the model can't claim data "wasn't pulled."
- Falls back to a fixed apology line if the model returns empty text.

#### `critique_node(state) -> {critique_rounds, critique_satisfied, reasoning}`
```python
result = invoke_llm(..., with_structured_output(Critique))  # {satisfied, missing}
return {
    "critique_rounds": state.get("critique_rounds", 0) + 1,
    "critique_satisfied": result.satisfied,
    "reasoning": result.missing or state.get("reasoning", ""),
}
```
- Runs once after every `personality` pass. Flags unsatisfied only if more data would meaningfully change the answer — never for style/tone/length.
- `missing` (if any) overwrites `reasoning`, becoming the supervisor's next plan.

#### `route_after_critique(state) -> "supervisor" | END`
```python
if state.get("critique_satisfied", True):
    return END
if state.get("critique_rounds", 0) > MAX_CRITIQUE_ROUNDS:   # MAX_CRITIQUE_ROUNDS = 1
    return END
return "supervisor"
```
- Conditional edge. At most one retry loop back to `supervisor`; ends otherwise.

## Node functions: weekly recap graph (`fantasy_agent/graphs/weekly_recap_graph.py`)

`START -> get_matchups -> league_summary -> power_ranking_image -> END`, all nodes run exactly once.

#### `get_matchups_node(state) -> {week, matchups}`
```python
week = state.get("week") or nfl_game_week()
box_scores = league_singleton().box_scores(week=week)
return {"week": week, "matchups": [{"home_team", "away_team", "home_score", "away_score"}, ...]}
```
- Fetches the week's final box scores; defaults to the current NFL week.

#### `league_summary_node(state) -> {league_summary, power_rankings}`
```python
result = invoke_llm(_llm, [system, prompt])  # with_structured_output(WeeklySummaryOutput)
return {"league_summary": result.league_summary.strip(), "power_rankings": [...]}
```
- One model call turns this week's scores + current standings into recap beats and a ranked, tagged list of every team.

#### `power_ranking_image_node(state) -> {power_ranking_image}`
```python
try:
    image_bytes = generate_image(prompt, size="1536x1024")
except Exception as err:
    emit("node_error", node="power_ranking_image", error=str(err))
return {"power_ranking_image": image_bytes}
```
- Renders the poster graphic from the matchups + power rankings. On failure, leaves the image `None` instead of raising.

## Node functions: matchup preview graph (`fantasy_agent/graphs/matchup_preview_graph.py`)

`START -> get_matchup_data -> flag_lineup_changes -> matchup_preview -> matchup_image -> END`, all nodes run exactly once.

#### `get_matchup_data_node(state) -> {week, matchups}`
```python
box_scores = league.box_scores(week=week)
return {"week": week, "matchups": [{"team_a", "proj_a", "record_a", "team_b", "proj_b", "record_b", "winner", "margin"}, ...]}
```
- Builds each matchup's projections, records, and projected winner/margin from box scores + standings.

#### `flag_lineup_changes_node(state) -> {lineup_flags}`
```python
duds = [p for p in last_week_lineup if p.slot_position not in BENCH_SLOTS and not p.on_bye_week and p.points == 0]
# then check this week's roster/starters to classify each dud as dropped/benched/still-starting
return {"lineup_flags": {team: [{"player", "status", "injury_status"?}, ...]}}
```
- Flags last week's zero-point starters and tags each as `dropped/traded away`, `benched`, or `still starting despite the zero`.

#### `matchup_preview_node(state) -> {league_preview, matchups}`
```python
result = invoke_llm(_llm, [system, prompt])  # with_structured_output(MatchupPreviewOutput)
return {"league_preview": result.league_preview.strip(), "matchups": state["matchups"]}
```
- One model call writes one joke beat per matchup, folding in `lineup_flags` and, if present, last week's recap as callback color.

#### `matchup_image_node(state) -> {matchup_image}`
```python
for attempt in range(1, attempts + 1):   # attempts = 2
    try:
        image_bytes = generate_image(prompt, size="1536x1024")
        break
    except Exception as err:
        emit("node_error", node="matchup_image", error=str(err), attempt=attempt)
return {"matchup_image": image_bytes}
```
- Renders the scoreboard graphic; retries once on failure, leaves the image `None` if both attempts fail.

## Model, keys, and retry

Every node uses the same Gemini model (`FANTASY_AGENT_MODEL` env var,
default `gemini-3.7-flash`), just with different prompts/tools/settings per
node. Reasoning effort is `high` for `supervisor` and `personality` and `medium`
for `run_category` and `critique`. High effort on `personality` once caused
empty replies on off-topic turns, so re-verify that after prompt changes.

`invoke_llm()` wraps every model call with `GOOGLE_API_KEY`.

`personality` has one fallback of its own: if the model call comes back
with no text at all, it falls back to a fixed "Sorry, I didn't quite
catch that" instead of showing the user an empty message.

## State shape

`AgentState` (a `MessagesState` subclass) carries `messages` — the running
conversation, shared across every node — plus `categories` and `reasoning`,
which the supervisor sets and `run_category` reads, a `category` field
naming which category a given parallel branch belongs to, and
`critique_rounds` / `critique_satisfied`, which `critique` sets to drive the
retry routing.

## Tracing

Every node calls `fantasy_agent/logging/trace.py`'s `emit()` around its work
(`node_start`/`node_end` pairs, plus `tool_call`/`tool_result` inside
`run_category`) rather than printing directly. `emit()` just prints
(`[trace] <event> <data>`) — it's a local log line, nothing consumes these
over the network. `tests/chat_audit.py` is the one place that reads them
back, by temporarily monkeypatching `trace.emit` to also capture events
into its report.

## Adding a new data source

Add a `@tool`-decorated function to the right module under
`fantasy_agent/tools/` (or a new module, registered in
`fantasy_agent/tools/__init__.py`'s `_MODULES` dict, if it's a whole new
category). The supervisor and graph pick it up automatically from
`CATEGORY_REGISTRY`/`CATEGORY_DESCRIPTIONS` — `graph.py` itself doesn't
need to change. See [`NFL_PUBLIC_API.md`](./NFL_PUBLIC_API.md) and
[`FANTASY_ESPN_API.md`](./FANTASY_ESPN_API.md) for what each existing tool
calls.
