# Fantasy ESPN Checklist — Standings

Part of a 5-way split of
[`FANTASY_ESPN_API_CHECKLIST.md`](../FANTASY_ESPN_API_CHECKLIST.md), clustered to match
[`fantasy_standings_tools.py`](../fantasy_standings_tools.py). See the main checklist for
Construction params, Return object shapes, Constant maps, and Notes/gotchas (not duplicated
here). 7 of 31 total checklist items.

> Requires an already-constructed `league` object.

- [x] `league.standings()`
  - Params: none
  - Summary: Returns all 12 league teams sorted by `final_standing` (falls back to `standing` when `final_standing` is 0, i.e. before the season/postseason has resolved).
  - Returns: `List[Team]` (12 elements) — each `Team` has `.team_name` (e.g. `"Fuentes Crusaders"`), `.team_id`, `.wins`, `.losses`, `.ties`, `.points_for`, `.points_against`, `.standing`, `.final_standing`, `.division_name`. Preseason (current_week=0), every team is 0-0 with 0.0 points, so the sort order is currently arbitrary/tied; first team returned is `Fuentes Crusaders`.
  - Network: cached — Side effects: none
  - Wired: `fantasy_standings_tools.get_standings`

- [x] `league.standings_weekly(week)`
  - Params: `week` (int, required, positional)
  - Summary: Returns standings as of the given week, applying the league's configured tiebreaker hierarchy; if the league's `currentMatchupPeriod <= 1` (no matchup period completed yet — true right now, preseason) it just returns `league.standings()` unchanged instead of computing weekly data.
  - Returns: `List[Team]` (12 elements), same `Team` shape as `standings()`. This league's `settings.playoff_seed_tie_rule` is `"TOTAL_POINTS_SCORED"`, so once games are played the order is win_pct → points_for → head-to-head → division record → points_against → coin flip, with division winners placed first. Called with `week=1` right now returns the same fallback list as `standings()` (all teams 0-0, `Fuentes Crusaders` first).
  - Network: cached (computed from `league.teams`) — Side effects: none
  - Wired: folded into `fantasy_standings_tools.get_standings` as an optional `week` arg (a separate near-duplicate tool wasn't warranted; `week=0`/omitted calls `standings()`, else `standings_weekly(week)`) — tested live with `week=1`, returns the documented fallback list.

- [x] `league.top_scorer()`
  - Params: none
  - Summary: Sorts `league.teams` by `.points_for` descending and returns the single top team.
  - Returns: `Team` (single object, not a list) with `.team_name`, `.points_for`, etc. Right now every team is tied at `points_for=0.0` (preseason), so the "top scorer" returned is just the first team in `league.teams` order after the tie: `Fuentes Crusaders` (`points_for=0.0`).
  - Network: cached — Side effects: none
  - Wired: `fantasy_standings_tools.get_top_scorer`

- [x] `league.least_scorer()`
  - Params: none
  - Summary: Sorts `league.teams` by `.points_for` ascending and returns the single lowest-scoring team.
  - Returns: `Team` (single object, not a list) with `.team_name`, `.points_for`, etc. Right now every team is tied at `points_for=0.0` (preseason), so the returned team is `Fuentes Crusaders` (`points_for=0.0`) — same object `top_scorer()` returns because of the tie.
  - Network: cached — Side effects: none
  - Wired: `fantasy_standings_tools.get_least_scorer`

- [x] `league.most_points_against()`
  - Params: none
  - Summary: Sorts `league.teams` by `.points_against` descending and returns the single team that has had the most points scored on it.
  - Returns: `Team` (single object, not a list) with `.team_name`, `.points_against`, etc. Right now every team is tied at `points_against=0.0` (preseason), so the returned team is `Fuentes Crusaders` (`points_against=0.0`).
  - Network: cached — Side effects: none
  - Wired: `fantasy_standings_tools.get_most_points_against`

- [x] `league.power_rankings(week=None)`
  - Params: `week` (int, optional keyword/positional; if falsy, <=0, or > `current_week`, it's clamped to `league.current_week`)
  - Summary: Builds a win matrix from each team's margin-of-victory (`.mov`) history through the given week, runs two-step dominance on it, then blends it with average score and average margin into a single power score per team, sorted descending.
  - Returns: `List[Tuple[str, Team]]` (12 elements) — each tuple is `(power_score: str, team: Team)`, where `power_score` is a string formatted to 2 decimals (e.g. `'0.00'`), NOT a float, computed as `dominance*0.8 + int(avg_score)*0.15 + int(avg_mov)*0.05`. Right now (no games played, `current_week=0`) every team scores `'0.00'` and the list order is effectively arbitrary; first entry is `('0.00', Team(Fuentes Crusaders))`.
  - Network: live (calls `box_scores()` internally to factor in current-week scoring) — Side effects: none
  - Wired: `fantasy_standings_tools.get_power_rankings` (no `week` param exposed — always current week, matching the checklist's documented default)

- [x] `league.least_scored_week()`
  - Params: none
  - Summary: For each team, takes `min(team.scores[:current_week])` (lowest scoring week so far this season), then returns the team/score pair with the overall lowest such value.
  - Returns: `Tuple[Team, float]` — element 0 is the `Team`, element 1 is that team's lowest weekly score. **Errors right now**: with `league.current_week == 0` (preseason, no weeks completed yet), `team.scores[:0]` is an empty list and `min()` raises `ValueError: min() iterable argument is empty` — this call currently throws rather than returning a value. Should work once at least one week has been played.
  - Network: cached — Side effects: none
  - Wired: `fantasy_standings_tools.get_least_scored_week` — wraps the documented `ValueError` and returns `"No weekly low score yet — season hasn't started."` instead of raising; tested live in current preseason state, confirmed friendly string not a traceback.
