# Fantasy ESPN Checklist — Matchup

Part of a 5-way split of
[`FANTASY_ESPN_API_CHECKLIST.md`](../FANTASY_ESPN_API_CHECKLIST.md), clustered to match
[`fantasy_matchup_tools.py`](../fantasy_matchup_tools.py). See the main checklist for
Construction params, Return object shapes, Constant maps, and Notes/gotchas (not duplicated
here). 7 of 31 total checklist items.

> Requires an already-constructed `league` object.

- [x] `league.scoreboard(week=None)`
  - Params: `week` (optional int; defaults to `league.current_week` when falsy)
  - Summary: Returns each matchup pairing and running score for a given week, with no lineup/roster detail — just the two teams and their totals.
  - Returns: `List[Matchup]` — Lightweight matchups (score only, no rosters) for a week. Confirmed live on this league, week 1 of the 2026 (preseason) season: `len == 6` (12-team league, 6 pairings). Each `Matchup` has `.home_team`/`.away_team` (`Team` objects, e.g. `Team(Fuentes Crusaders)`), `.home_score`/`.away_score` (`float`, e.g. `0.0` before games start), `.is_playoff` (`bool`, e.g. `False`), `.matchup_type` (`str`, e.g. `'NONE'` in the regular season).
  - Network: live — Side effects: none
  - Wired: `fantasy_matchup_tools.get_matchup_scoreboard`

- [x] `league.box_scores(week=None, player_team_cache=None)`
  - Params: `week` (optional int; only honored if `<= league.current_week`, otherwise falls back to the current matchup/scoring period), `player_team_cache` (optional dict, mutated in place — pass the same dict across multiple calls so it can correctly resolve bye-week/traded players' pro team)
  - Summary: Returns full box scores for a week, each including both teams' complete starting lineups (plus bench/IR) with per-player scored and projected points. Raises `Exception` outright for `league.year < 2019`; raises `KeyError` if ESPN has no roster data yet for that week (e.g., before the league has drafted).
  - Returns: `List[BoxScore]` — Full box scores incl. lineups/projections for a week. **2019+ only.** Confirmed against this same league's completed 2025 season, week 1: `len == 6`. Each `BoxScore` has `.home_team`/`.away_team` (`Team` objects, resolved from ESPN's raw team id), `.home_score`/`.away_score` (`float`, e.g. `88.66`), `.home_projected`/`.away_projected` (`float`, e.g. `125.88`), `.is_playoff` (`bool`), `.matchup_type` (`str`), `.home_lineup`/`.away_lineup` (`List[BoxPlayer]`, 16 entries observed = full roster incl. bench/IR slots). Each `BoxPlayer` has `.name`, `.playerId`, `.position`/`.slot_position`/`.lineupSlot`, `.proTeam`/`.pro_opponent`, `.points`/`.projected_points` (`float`), `.on_bye_week` (`bool`), `.injuryStatus` (`str`), `.eligibleSlots` (`List[str]`), `.game_date` (`datetime`), plus `.breakdown`/`.projected_breakdown` stat-category dicts. On this league's *current* 2026 season (pre-draft, week 1) the call instead raised `KeyError: 'rosterForCurrentScoringPeriod'` — ESPN has no roster data until the league drafts.
  - Network: live — Side effects: none
  - Wired: `fantasy_matchup_tools.get_box_scores` (KeyError from the pre-draft case is caught live and turned into a friendly "not available yet" string)

- [x] `league.currentMatchupPeriod`
  - Type: `int`
  - Summary: The current fantasy matchup period index (ESPN's grouping of one-or-more scoring periods into a single head-to-head week), set from `data['status']['currentMatchupPeriod']` at league construction time.
  - Returns: Current matchup period number. Observed live on this league, 2026 preseason (before week 1 games): `1`.
  - Wired: `fantasy_matchup_tools.get_current_week` (folded together with `scoringPeriodId`/`current_week`/`nfl_week` into one "what week is it" tool rather than four near-identical one-liners)

- [x] `league.scoringPeriodId`
  - Type: `int`
  - Summary: The scoring period ESPN currently considers "live," set directly from `data['scoringPeriodId']`; it's `0` before any games in the season have been played (unclamped, unlike `current_week`).
  - Returns: Current scoring period (week). Observed live on this league, 2026 preseason: `0`.
  - Wired: `fantasy_matchup_tools.get_current_week` (folded, see `currentMatchupPeriod` above)

- [x] `league.current_week`
  - Type: `int`
  - Summary: The library's preferred "week to use by default" — equal to `scoringPeriodId`, but capped so it never exceeds the league's `finalScoringPeriod`; used internally as the default `week` arg for `scoreboard()`/`box_scores()`. Note it's `0` (not 1) before the season starts, so callers must guard against that (this repo's own scripts do `week = league.current_week or 1`).
  - Returns: Current week, clamped to final scoring period. Observed live on this league, 2026 preseason: `0`. (For contrast, on this same league's completed 2025 season it was `17`.)
  - Wired: `fantasy_matchup_tools.get_current_week` (folded, see `currentMatchupPeriod` above)

- [x] `league.nfl_week`
  - Type: `int`
  - Summary: The real-world NFL's latest scoring period per ESPN's global schedule (`data['status']['latestScoringPeriod']`), independent of this fantasy league's own matchup settings.
  - Returns: Latest NFL scoring period. Observed live on this league, 2026 preseason: `0`.
  - Wired: `fantasy_matchup_tools.get_current_week` (folded, see `currentMatchupPeriod` above)

- [x] `league.top_scored_week()`
  - Params: none
  - Summary: Looks at every team's per-week score history through `league.current_week` and returns whichever team/week combo posted the single highest score.
  - Returns: `Tuple[Team, float]` — Highest single-week score so far. Confirmed against this league's completed 2025 season: `(Team(1x CHAMP), 181.98)` — first element a `Team` object, second the `float` point total for that team's best week. (On this league's current 2026 preseason data, `current_week` is `0`, so this would return an empty-range max and error/be meaningless until week 1 is played.)
  - Network: cached — Side effects: none
  - Wired: `fantasy_matchup_tools.get_top_scored_week` (confirmed live: raises `ValueError: max() iterable argument is empty` in preseason, caught and turned into a friendly string)
