# Fantasy ESPN Checklist — Player

Part of a 5-way split of
[`FANTASY_ESPN_API_CHECKLIST.md`](../FANTASY_ESPN_API_CHECKLIST.md), clustered to match
[`fantasy_player_tools.py`](../fantasy_player_tools.py). See the main checklist for
Construction params, Return object shapes, Constant maps, and Notes/gotchas (not duplicated
here). 6 of 31 total checklist items.

> Requires an already-constructed `league` object.

- [ ] `league.player_map`
  - Type: `dict`
  - Summary: A single dict containing a two-way lookup, built at League construction time from the league's full player pool (5220 entries in this league) — int keys map `playerId -> name`, and string keys map `name -> playerId`.
  - Returns: `dict` with 5220 items total (2610 players × 2 directions). Sample entries: `4685266: 'Jaishawn Barham'` and `'Jaishawn Barham': 4685266`. Used internally by `player_info()` to resolve a name to an ID before hitting the network.
  - Not wired: internal two-way lookup dict used only by `player_info()` to resolve names to IDs; no standalone chat value.

- [x] `league.free_agents(week=None, size=50, position=None, position_id=None)`
  - Params: `week` (optional, defaults to `league.current_week`), `size` (default `50`), `position` (e.g. `"RB"`, must be a key in the library's internal `POSITION_MAP`), `position_id` (raw ESPN slot ID, appended to the filter alongside `position` if both given)
  - Summary: Fetches up to `size` players from ESPN's free-agent/waiver endpoint for the given week, optionally filtered to one position. In this league (preseason, before the draft) it actually returns top overall players like Jahmyr Gibbs and Bijan Robinson at ~99.9% owned — "free agent" here just means "not yet on any of the 12 rosters in this league," not that they're unowned league-wide.
  - Returns: `List[BoxPlayer]`. Confirmed real attributes on a sample element (`vars()`): `.acquisitionType` (list, empty), `.active_status` (str, e.g. `'inactive'`), `.avg_points` (float), `.breakdown` (dict), `.eligibleSlots` (list of str, e.g. `['RB','RB/WR','RB/WR/TE','OP','BE','IR']`), `.game_played` (int), `.injured` (bool), `.injuryStatus` (str, e.g. `'ACTIVE'`), `.jersey` (str), `.lineupSlot` (str), `.name` (str), `.onTeamId` (int, `0` if unrostered), `.on_bye_week` (bool), `.percent_owned` (float), `.percent_started` (float), `.playerId` (int), `.points` (float), `.points_breakdown` (dict), `.posRank` (list), `.position` (str, e.g. `'RB'`), `.proTeam` (str, e.g. `'DET'`), `.pro_opponent` (str), `.pro_pos_rank` (int), `.projected_avg_points` (float), `.projected_breakdown` (dict of stat-category floats), `.projected_points` (float), `.projected_points_breakdown` (dict), `.projected_total_points` (float), `.schedule` (dict), `.slot_position` (str, e.g. `'FA'`), `.stats` (dict keyed by scoring period, each value a dict with `projected_points`/`projected_breakdown`/etc.), `.total_points` (float). `free_agents(position="RB", size=5)` returned exactly 5 RBs (Gibbs, Robinson, McCaffrey, Taylor, Cook) confirming the position filter and size cap both work.
  - Network: live — Side effects: none
  - Wired: `fantasy_player_tools.get_free_agents`

- [x] `league.player_info(name=None, playerId=None)`
  - Params: `name` (optional, str — resolved to an ID via `league.player_map` before the network call), `playerId` (optional — single `int` or `List[int]`)
  - Summary: Looks up one or more players by name or ID via ESPN's player-card endpoint. Internally, `name` is first converted to a `playerId` using `league.player_map`, so a name not present in that map (or an ID that doesn't exist) returns `None` rather than raising.
  - Returns: `Player` when a single ID/name resolves to one result, `List[Player]` when `playerId` is passed a list of 2+ IDs, `None` when the name/ID isn't found (confirmed: `player_info(name="NonexistentPlayerXYZ123")` → `None`, `player_info(playerId=999999999)` → `None`). Real attributes on a sample `Player` (`vars()`, e.g. for "Jahmyr Gibbs"): `.acquisitionType`, `.active_status`, `.avg_points`, `.eligibleSlots`, `.injured`, `.injuryStatus`, `.jersey`, `.lineupSlot`, `.name`, `.onTeamId`, `.percent_owned`, `.percent_started`, `.playerId`, `.posRank`, `.position`, `.proTeam`, `.projected_avg_points`, `.projected_total_points`, `.schedule` (dict keyed by week number as a string, each value `{'team': ..., 'date': datetime}`), `.stats` (dict keyed by scoring period, `0` = season total, each value has `projected_points`/`projected_breakdown`/etc.), `.total_points`. Note: this `Player` object has fewer fields than the `BoxPlayer` returned by `free_agents()` (no `.breakdown`, `.points_breakdown`, `.pro_opponent`, `.pro_pos_rank`, `.slot_position`, `.on_bye_week`, `.game_played`).
  - Network: live — Side effects: none
  - Wired: `fantasy_player_tools.get_player_info`

- [ ] `league.refresh_draft(refresh_players=False, refresh_teams=False)`
  - Params: `refresh_players` (default `False`), `refresh_teams` (default `False`)
  - Summary: Re-fetches draft-pick data from ESPN and overwrites `league.draft` in place; with the optional flags it also re-fetches the full player pool and/or team rosters. In this league the 2026 draft hasn't happened yet, so `league.draft` was `[]` both before and after the call, and `player_map`/`teams` were unchanged in size (5220 / 12) after a full refresh — confirms the call runs without error even pre-draft.
  - Returns: `None` (confirmed — always returns `None`, mutates `league.draft` and, with the flags, `league.player_map`/`league.teams` as side effects rather than returning anything)
  - Network: live — Side effects: overwrites `league.draft`, and optionally `league.player_map`/`league.teams`
  - Not wired: cache-refresh operation on internal state (`league.draft`/`player_map`/`teams`), not something a user asks the bot to do in chat.

- [ ] `league.firstScoringPeriod`
  - Type: `int`
  - Summary: The scoring-period number the season starts at for this league.
  - Returns: `1` for this league (2026 season) — bounds the window player stats/schedules are valid for
  - Not wired: raw season-boundary int, too low-level to stand alone as a chat tool; no other item in this cluster needed it folded in.

- [ ] `league.finalScoringPeriod`
  - Type: `int`
  - Summary: The scoring-period number the regular/full season ends at for this league; also used internally as the scoring period passed to ESPN's player-card endpoint by `player_info()`.
  - Returns: `17` for this league (2026 season) — bounds the window player stats/schedules are valid for
  - Not wired: raw season-boundary int, used internally by `player_info()`'s underlying implementation; too low-level to stand alone as a chat tool.
