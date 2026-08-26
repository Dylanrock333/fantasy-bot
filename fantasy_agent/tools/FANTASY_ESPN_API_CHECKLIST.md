# espn_api (Fantasy Football) — Command Checklist

Source: [`fantasy_espn/ESPN_API_REFERENCE.md`](../../fantasy_espn/ESPN_API_REFERENCE.md)
(itself sourced from [cwendt94/espn-api](https://github.com/cwendt94/espn-api), reflecting the
installed version `0.46.0` — `espn_api/football/*`, `espn_api/base_league.py`)

Scope: **`espn_api` Python wrapper for your private/public fantasy league only** — rosters,
matchups, standings, transactions, draft. Not the real-NFL public data API (see
[`NFL_PUBLIC_API_CHECKLIST.md`](./NFL_PUBLIC_API_CHECKLIST.md) for that).

Check items off as you build/wire a tool for that attribute or method in this `tools/` folder.

### Construction (not a checklist item — required before calling anything below)

```python
from espn_api.football import League

league = League(
    league_id=1992397255,
    year=2026,
    espn_s2="...",   # required for private leagues
    swid="...",      # required for private leagues
)
```

| Param | Meaning | Notes |
|---|---|---|
| `league_id` | Your ESPN fantasy league ID | required |
| `year` | Season year | required |
| `espn_s2` | Auth cookie | required for private leagues |
| `swid` | Auth cookie | required for private leagues |
| `fetch_league` | Fetch settings/players/teams/draft on init | default `True` |
| `debug` | Log raw request/response info | default `False` |

> Private leagues need **both** `espn_s2` and `swid`, or ESPN silently returns public-only
> (often empty) data instead of an auth error.

---

## 1. League object — attributes

Set on init/refresh. Accessed as `league.<attribute>`, not called.

- [ ] `league.teams`
  - Type: `List[Team]`
  - Returns: All teams, sorted by `team_id`

- [ ] `league.members`
  - Type: `List[dict]`
  - Returns: Raw league member/owner data

- [ ] `league.draft`
  - Type: `List[BasePick]`
  - Returns: Draft picks (if draft has occurred)

- [ ] `league.player_map`
  - Type: `dict`
  - Returns: Two-way map of `{playerId: name}` and `{name: playerId}`

- [ ] `league.settings`
  - Type: `Settings`
  - Returns: League settings object (see Reference section below)

- [ ] `league.currentMatchupPeriod`
  - Type: `int`
  - Returns: Current matchup period number

- [ ] `league.scoringPeriodId`
  - Type: `int`
  - Returns: Current scoring period (week)

- [ ] `league.current_week`
  - Type: `int`
  - Returns: Current week, clamped to final scoring period

- [ ] `league.nfl_week`
  - Type: `int`
  - Returns: Latest NFL scoring period

- [ ] `league.firstScoringPeriod`
  - Type: `int`
  - Returns: Season start boundary

- [ ] `league.finalScoringPeriod`
  - Type: `int`
  - Returns: Season end boundary

- [ ] `league.previousSeasons`
  - Type: `List[int]`
  - Returns: Prior seasons for this league ID

---

## 2. League object — methods

Each entry below adds two fields beyond params/returns:
- **Network** — `cached` (reads the `league.teams`/`league.settings` snapshot taken at
  construction or last `refresh()`, no new request) vs. `live` (hits ESPN fresh on every call).
- **Side effects** — `none` (read-only) vs. what local state it overwrites. None of these can
  make changes to your real ESPN league (no write-back methods exist in this library) — a
  "mutates" note only means it overwrites the local Python object.

### General (inherited from `BaseLeague`, same across all sports)

- [ ] `league.standings()`
  - Params: none
  - Returns: `List[Team]` — Teams sorted by final/current standing
  - Network: cached — Side effects: none

- [ ] `league.get_team_data(team_id)`
  - Params: `team_id`
  - Returns: `Team | None` — Look up a team by ID
  - Network: cached — Side effects: none

- [ ] `league.refresh()`
  - Params: none
  - Returns: `None` — Re-fetches league + team data (use instead of re-instantiating)
  - Network: live — Side effects: overwrites `league.teams`, `league.settings`, `league.draft`, and other cached attributes with fresh data

### Football-specific

- [ ] `league.standings_weekly(week)`
  - Params: `week`
  - Returns: `List[Team]` — Standings as of a given week, applying the league's real tiebreaker hierarchy (H2H, points for/against, division record, coin flip)
  - Network: cached (computed from `league.teams`) — Side effects: none

- [ ] `league.top_scorer()`
  - Params: none
  - Returns: `Team` — Team with most total points for
  - Network: cached — Side effects: none

- [ ] `league.least_scorer()`
  - Params: none
  - Returns: `Team` — Team with fewest total points for
  - Network: cached — Side effects: none

- [ ] `league.most_points_against()`
  - Params: none
  - Returns: `Team` — Team that has allowed the most points
  - Network: cached — Side effects: none

- [ ] `league.top_scored_week()`
  - Params: none
  - Returns: `Tuple[Team, float]` — Highest single-week score so far
  - Network: cached — Side effects: none

- [ ] `league.least_scored_week()`
  - Params: none
  - Returns: `Tuple[Team, float]` — Lowest single-week score so far
  - Network: cached — Side effects: none

- [ ] `league.power_rankings(week=None)`
  - Params: `week` (optional, defaults to current week)
  - Returns: `List[Tuple[str, Team]]` — Two-step-dominance power rankings
  - Network: live (calls `box_scores()` internally to factor in current-week scoring) — Side effects: none

- [ ] `league.scoreboard(week=None)`
  - Params: `week` (optional)
  - Returns: `List[Matchup]` — Lightweight matchups (score only, no rosters) for a week
  - Network: live — Side effects: none

- [ ] `league.box_scores(week=None, player_team_cache=None)`
  - Params: `week` (optional), `player_team_cache` (optional dict, reusable across calls to correctly resolve bye-week players' teams)
  - Returns: `List[BoxScore]` — Full box scores incl. lineups/projections for a week. **2019+ only.**
  - Network: live — Side effects: none

- [ ] `league.free_agents(week=None, size=50, position=None, position_id=None)`
  - Params: `week` (optional), `size` (default `50`), `position` (e.g. `"RB"`), `position_id` (raw ID)
  - Returns: `List[BoxPlayer]` — Free agents / waiver players, optionally filtered by position. **2019+ only.**
  - Network: live — Side effects: none

- [ ] `league.player_info(name=None, playerId=None)`
  - Params: `name` (optional), `playerId` (optional — single ID or list)
  - Returns: `Player | List[Player] | None` — Look up a player by name or ID
  - Network: live — Side effects: none

- [ ] `league.recent_activity(size=25, msg_type=None, offset=0)`
  - Params: `size` (default `25`), `msg_type` (`"FA"`, `"WAIVER"`, or `"TRADED"`), `offset` (default `0`)
  - Returns: `List[Activity]` — Recent adds/drops/trades. **2019+ only.**
  - Network: live — Side effects: none

- [ ] `league.transactions(scoring_period=None, types={"FREEAGENT","WAIVER","WAIVER_ERROR"})`
  - Params: `scoring_period` (optional), `types` (set filter — see `TRANSACTION_TYPES`)
  - Returns: `List[Transaction]` — Transactions for a scoring period, filtered by type set
  - Network: live — Side effects: none

- [ ] `league.message_board(msg_types=None)`
  - Params: `msg_types` (optional)
  - Returns: `List[dict]` — Raw league message board posts
  - Network: live — Side effects: none

- [ ] `league.load_roster_week(week)`
  - Params: `week`
  - Returns: `None` — Mutates `team.roster` in place to reflect a given week's lineup
  - Network: live — Side effects: overwrites `team.roster` on every team in `league.teams` (local only — does not touch your real ESPN lineup)

- [ ] `league.refresh_draft(refresh_players=False, refresh_teams=False)`
  - Params: `refresh_players` (default `False`), `refresh_teams` (default `False`)
  - Returns: `None` — Re-fetches draft picks, optionally players/teams too
  - Network: live — Side effects: overwrites `league.draft`, and optionally `league.player_map`/`league.teams`

---

## Reference: Return object shapes

These are the shapes of what the methods/attributes above return — not independently callable,
so not checklist items, but included for completeness since tools consuming the above will need
to know these fields.

### `Team`

`team_id`, `team_abbrev`, `team_name`, `division_id`, `division_name`, `wins`, `losses`, `ties`,
`points_for`, `points_against`, `standing` (current playoff seed), `final_standing` (0 if season
in progress), `streak_type`, `streak_length`, `waiver_rank`, `acquisitions`,
`acquisition_budget_spent`, `drops`, `trades`, `move_to_ir`, `playoff_pct`,
`draft_projected_rank`, `logo_url`, `owners` (`List[dict]`), `roster` (`List[Player]`),
`schedule` (`List[Team]` — opponent per week), `scores` (`List[float]` — per week),
`outcomes` (`List[str]` — `"W"`/`"L"`/`"T"`/`"U"` per week), `mov` (`List[float]` — margin of
victory per week), `stats` (`dict` — season stat totals keyed by stat name),
`get_player_name(playerId)` (method — roster player's name by ID)

### `Player` (and `BoxPlayer`, which extends it with per-matchup data)

`name`, `playerId`, `position`, `eligibleSlots`, `lineupSlot`, `proTeam` (NFL team abbreviation),
`posRank`, `injuryStatus`, `injured`, `percent_owned`, `percent_started`, `total_points`,
`projected_total_points`, `avg_points`, `projected_avg_points`, `stats` (`dict` keyed by scoring
period, each with `points`, `breakdown`, `points_breakdown`, `projected_points`, etc.),
`schedule` (`dict` keyed by scoring period → `{'team': opponent_abbrev, 'date': datetime}`)

**`BoxPlayer` additions** (only on players returned from `box_scores()` / `free_agents()`):
`slot_position` (where they were started this week, e.g. `"RB"`, `"BE"`, `"IR"`), `points`,
`projected_points` (this week's actual/projected), `breakdown`, `points_breakdown` (raw stat /
fantasy-point breakdown for the week), `pro_opponent` (this week's NFL opponent), `pro_pos_rank`
(opponent's defensive rank against this position), `game_played` (`0` or `100`, percent of game
completed), `on_bye_week` (`bool`)

### `BoxScore` (from `league.box_scores()`)

`home_team` / `away_team` (`Team`), `home_score` / `away_score` (`float`), `home_projected` /
`away_projected` (`float`), `home_lineup` / `away_lineup` (`List[BoxPlayer]`), `is_playoff`
(`bool`), `matchup_type` (`str`)

### `Matchup` (from `league.scoreboard()`)

`home_team` / `away_team` (`Team`), `home_score` / `away_score` (`float`), `is_playoff`
(`bool`), `matchup_type` (`str`). Lighter-weight than `BoxScore` — no rosters.

### `Activity` (from `league.recent_activity()`)

`date` (epoch ms), `actions` — `List[Tuple[Team, action_str, Player, bid_amount]]` where
`action_str` is one of `"FA ADDED"`, `"WAIVER ADDED"`, `"DROPPED"`, `"TRADE_SENT"`,
`"TRADE_RECEIVED"`

### `Transaction` (from `league.transactions()`)

`team` (`Team`), `type` (`str`, e.g. `"WAIVER"`), `status`, `scoring_period`, `date`,
`bid_amount`, `items` — `List[TransactionItem]` each with `type`, `playerId`, `player` (name)

### `Settings` (`league.settings`)

`name` (league name), `team_count`, `reg_season_count`, `playoff_team_count`,
`playoff_matchup_period_length`, `veto_votes_required`, `keeper_count`, `trade_deadline`
(epoch ms), `division_map` (`{division_id: division_name}`), `tie_rule`, `playoff_tie_rule`,
`playoff_seed_tie_rule`, `scoring_type` (e.g. `"H2H_POINTS"`), `median_scoring` (`bool`),
`faab` (`bool` — FAAB budget vs. waiver priority), `acquisition_budget`,
`position_slot_counts` (`{position_label: count}`), `scoring_format` (`List[dict]` — every
scored stat with `abbr`, `label`, `points`, `id`)

### `BasePick` (`league.draft`)

`team` (`Team`), `playerId`, `playerName`, `round_num`, `round_pick`, `bid_amount` (auction
leagues), `keeper_status` (`bool`), `nominatingTeam` (auction leagues)

---

## Constant maps (`espn_api.football.constant`)

| Map | Description |
|---|---|
| `POSITION_MAP` | Slot ID ↔ label (`"QB"`, `"RB"`, `"FLEX"`, `"D/ST"`, `"BE"`, `"IR"`, etc.), bidirectional |
| `PRO_TEAM_MAP` | NFL pro team ID → abbreviation (`"KC"`, `"SF"`, ...) |
| `PLAYER_STATS_MAP` | Raw ESPN stat ID → readable stat name (passing/rushing/receiving/kicking/defense/punting), ~230 entries, used to build `Player.stats` breakdowns |
| `SETTINGS_SCORING_FORMAT_MAP` | Stat ID → `{abbr, label}`, used to build `Settings.scoring_format` |
| `ACTIVITY_MAP` | Message type ID → activity label |
| `TRANSACTION_TYPES` | Valid values for the `types` filter on `league.transactions()` |

---

## Notes / gotchas (carried over from the source reference)

- `box_scores()`, `free_agents()`, and `recent_activity()` all raise if `league.year < 2019` —
  ESPN's API doesn't expose this data for older seasons.
- `league.refresh()` is cheaper than re-instantiating `League(...)` for polling loops.
- Private leagues need **both** `espn_s2` and `swid`, or ESPN silently returns public-only
  (often empty) data instead of an auth error.
- `Team.final_standing` is `0` until the season officially ends — use `Team.standing` (current
  playoff seed) mid-season.
