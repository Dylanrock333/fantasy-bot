# Fantasy ESPN Checklist — Roster

Part of a 5-way split of
[`FANTASY_ESPN_API_CHECKLIST.md`](../FANTASY_ESPN_API_CHECKLIST.md), clustered to match
[`fantasy_roster_tools.py`](../fantasy_roster_tools.py). See the main checklist for
Construction params, Return object shapes, Constant maps, and Notes/gotchas (not duplicated
here). 6 of 31 total checklist items.

> Requires an already-constructed `league` object.

- [x] `league.teams`
  - Type: `List[Team]`
  - Summary: Returns all 12 teams in this league, already sorted ascending by `team_id` (1-12).
  - Returns: `List[Team]`, sorted by `team_id`. Each `Team` object's `vars()` keys: `acquisition_budget_spent`, `acquisitions`, `division_id`, `division_name`, `draft_projected_rank`, `drops`, `final_standing`, `logo_url`, `losses`, `mov`, `move_to_ir`, `outcomes`, `owners` (`List[dict]` of member info), `points_against`, `points_for`, `roster` (`List[Player]` — empty pre-draft/preseason), `schedule`, `scores`, `standing`, `stats`, `streak_length`, `streak_type`, `team_abbrev`, `team_id`, `team_name`, `ties`, `trades`, `waiver_rank`, `wins`.
  - Wired: `fantasy_roster_tools.get_team_roster` (name-based lookup into `league.teams`, handles empty `.roster` with a friendly message). Does NOT cover `get_team_data(team_id)`/`load_roster_week(week)`/`settings`/`members`/`draft` below — those are separate items.

- [ ] `league.get_team_data(team_id)`
  - Params: `team_id` (`int`, e.g. `league.teams[0].team_id`)
  - Summary: Looks up a single team from the already-loaded `league.teams` list by its `team_id`; returns `None` if no team has that ID (tested with `team_id=9999`).
  - Returns: `Team | None` — same `Team` object/shape as an entry in `league.teams` (see above), or `None` when the ID doesn't match any team.
  - Network: cached — Side effects: none
  - Not wired: redundant with `get_team_roster`'s name-based lookup over `league.teams` — a raw team_id lookup has no standalone chat value (users don't refer to teams by numeric ID); folding it in would just add an unused param.

- [ ] `league.load_roster_week(week)`
  - Params: `week` (`int`, e.g. `league.current_week` or an explicit week number like `1`)
  - Summary: Fetches that week's boxscore/roster data from ESPN and overwrites `.roster` on every `Team` in `league.teams` in place; for this league (2026 season, preseason — `league.current_week` is `0`, no draft yet) `.roster` stayed an empty list `[]` both for week `0` and week `1` since no rosters have been drafted yet.
  - Returns: `None` — Mutates `team.roster` in place to reflect a given week's lineup
  - Network: live — Side effects: overwrites `team.roster` on every team in `league.teams` (local only — does not touch your real ESPN lineup)
  - Not wired: mutates shared local state and returns `None`, so it can't be exposed as a plain `str`-returning tool without extra plumbing to read the roster back out afterward; no clean standalone chat use case, and `get_team_roster` already covers current-roster chat queries.

- [x] `league.settings`
  - Type: `Settings`
  - Summary: Returns this league's settings object; for this league it's named "Brotherhood of the Gridiron", 12 teams, `H2H_POINTS` scoring, 6 playoff teams.
  - Returns: `Settings` object. `vars()` keys: `_raw_schedule_settings`, `_raw_scoring_settings`, `acquisition_budget`, `division_map`, `faab`, `keeper_count`, `matchup_periods`, `median_scoring`, `name`, `playoff_matchup_period_length`, `playoff_seed_tie_rule`, `playoff_team_count`, `playoff_tie_rule`, `position_slot_counts`, `reg_season_count`, `scoring_format`, `scoring_type`, `team_count`, `tie_rule`, `trade_deadline`, `veto_votes_required`. For this league: `name='Brotherhood of the Gridiron'`, `team_count=12`, `scoring_type='H2H_POINTS'`, `playoff_team_count=6`, `trade_deadline` is a ms-epoch timestamp (e.g. `1796230800000`), and `position_slot_counts` is a `Dict[str, int]` mapping every roster-slot code to how many of that slot exist — for this league: `{'QB': 1, 'TQB': 0, 'RB': 2, 'RB/WR': 0, 'WR': 2, 'WR/TE': 0, 'TE': 1, 'OP': 0, 'DT': 0, 'DE': 0, 'LB': 0, 'DL': 0, 'CB': 0, 'S': 0, 'DB': 0, 'DP': 0, 'D/ST': 1, 'K': 1, 'P': 0, 'HC': 0, 'BE': 7, 'IR': 1, '': 0, 'RB/WR/TE': 1, 'ER': 0}` (i.e. starters: 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX(RB/WR/TE), 1 D/ST, 1 K, plus 7 bench and 1 IR slot).
  - Wired: `fantasy_roster_tools.get_league_settings`

- [ ] `league.members`
  - Type: `List[dict]`
  - Summary: Returns the 12 raw league-member records (one per user in the league), each a plain dict of ESPN account/profile data — not tied to a specific team here (use `Team.owners` for that link).
  - Returns: `List[dict]`, one dict per member with keys: `displayName`, `firstName`, `id` (ESPN account GUID string like `'{207F5513-...}'`), `lastName`, `notificationSettings` (`List[dict]` of that member's per-notification-type enabled/disabled prefs — not roster-relevant). `Team.owners` is the same dict shape, filtered to the member(s) who own that specific team.
  - Not wired: raw account/member dicts (GUIDs, notification prefs) are mostly redundant with `Team.owners`, which already surfaces the owner-team link through `get_team_roster`; no standalone "who owns which team" tool needed beyond that.

- [x] `league.draft`
  - Type: `List[BasePick]`
  - Summary: Returns every draft pick made in this league's draft; for this league (2026 season, currently preseason — `league.current_week == 0`) the draft has not happened yet, so it returned an empty list `[]`.
  - Returns: `List[BasePick]` — empty `[]` pre-draft (confirmed live for this league). Once a draft has occurred, each `BasePick` element exposes attributes such as `team`, `playerId`, `playerName`, `round_num`, `round_pick`, `bid_amount`, `keeper_status`, `nominatingTeam` (per the `espn_api` source) describing how each team's initial roster was formed.
  - Wired: `fantasy_roster_tools.get_draft_results` (returns a friendly "draft hasn't happened yet" message pre-draft; confirmed live)
