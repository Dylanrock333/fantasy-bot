# espn_api — Command Reference (Football)

Source: [cwendt94/espn-api](https://github.com/cwendt94/espn-api), reflecting the installed
version `0.46.0` (`espn_api/football/*`, `espn_api/base_league.py`).

```python
from espn_api.football import League

league = League(
    league_id=1992397255,
    year=2026,
    espn_s2="...",   # required for private leagues
    swid="...",      # required for private leagues
)
```

`League(league_id, year, espn_s2=None, swid=None, fetch_league=True, debug=False)` —
on construction it fetches league settings, all players, all teams, and the draft (if
`fetch_league=True`, the default). `debug=True` logs raw request/response info.

---

## League object — attributes (set on init/refresh)

| Attribute | Type | Description |
|---|---|---|
| `league.teams` | `List[Team]` | All teams, sorted by `team_id` |
| `league.members` | `List[dict]` | Raw league member/owner data |
| `league.draft` | `List[BasePick]` | Draft picks (if draft has occurred) |
| `league.player_map` | `dict` | Two-way map of `{playerId: name}` and `{name: playerId}` |
| `league.settings` | `Settings` | League settings object (see below) |
| `league.currentMatchupPeriod` | `int` | Current matchup period number |
| `league.scoringPeriodId` | `int` | Current scoring period (week) |
| `league.current_week` | `int` | Current week, clamped to final scoring period |
| `league.nfl_week` | `int` | Latest NFL scoring period |
| `league.firstScoringPeriod` / `finalScoringPeriod` | `int` | Season boundaries |
| `league.previousSeasons` | `List[int]` | Prior seasons for this league ID |

---

## League object — methods

### General (inherited from `BaseLeague`, same across all sports)

| Method | Returns | Description |
|---|---|---|
| `league.standings()` | `List[Team]` | Teams sorted by final/current standing |
| `league.get_team_data(team_id)` | `Team \| None` | Look up a team by ID |
| `league.refresh()` | `None` | Re-fetches league + team data (use instead of re-instantiating) |

### Football-specific

| Method | Returns | Description |
|---|---|---|
| `league.standings_weekly(week)` | `List[Team]` | Standings as of a given week, applying the league's real tiebreaker hierarchy (H2H, points for/against, division record, coin flip) |
| `league.top_scorer()` | `Team` | Team with most total points for |
| `league.least_scorer()` | `Team` | Team with fewest total points for |
| `league.most_points_against()` | `Team` | Team that has allowed the most points |
| `league.top_scored_week()` | `Tuple[Team, float]` | Highest single-week score so far |
| `league.least_scored_week()` | `Tuple[Team, float]` | Lowest single-week score so far |
| `league.power_rankings(week=None)` | `List[Tuple[str, Team]]` | Two-step-dominance power rankings; defaults to current week |
| `league.scoreboard(week=None)` | `List[Matchup]` | Lightweight matchups (score only, no rosters) for a week |
| `league.box_scores(week=None, player_team_cache=None)` | `List[BoxScore]` | Full box scores incl. lineups/projections for a week. **2019+ only.** `player_team_cache` is an optional dict you can reuse across calls to correctly resolve bye-week players' teams |
| `league.free_agents(week=None, size=50, position=None, position_id=None)` | `List[BoxPlayer]` | Free agents / waiver players, optionally filtered by position (e.g. `"RB"`) or raw `position_id`. **2019+ only** |
| `league.player_info(name=None, playerId=None)` | `Player \| List[Player] \| None` | Look up a player by name or ID (`playerId` can be a single id or list) |
| `league.recent_activity(size=25, msg_type=None, offset=0)` | `List[Activity]` | Recent adds/drops/trades. `msg_type` can be `"FA"`, `"WAIVER"`, or `"TRADED"`. **2019+ only** |
| `league.transactions(scoring_period=None, types={"FREEAGENT","WAIVER","WAIVER_ERROR"})` | `List[Transaction]` | Transactions for a scoring period, filtered by type set (see `TRANSACTION_TYPES`) |
| `league.message_board(msg_types=None)` | `List[dict]` | Raw league message board posts |
| `league.load_roster_week(week)` | `None` | Mutates `team.roster` in place to reflect a given week's lineup |
| `league.refresh_draft(refresh_players=False, refresh_teams=False)` | `None` | Re-fetches draft picks, optionally players/teams too |

---

## Return objects

### `Team`

| Attribute | Description |
|---|---|
| `team_id`, `team_abbrev`, `team_name` | Identity |
| `division_id`, `division_name` | Division |
| `wins`, `losses`, `ties` | Overall record |
| `points_for`, `points_against` | Season totals |
| `standing` | Current playoff seed |
| `final_standing` | Final rank (0 if season in progress) |
| `streak_type`, `streak_length` | e.g. `"WIN"`, `3` |
| `waiver_rank` | Current waiver priority |
| `acquisitions`, `acquisition_budget_spent`, `drops`, `trades`, `move_to_ir` | Transaction counters |
| `playoff_pct` | ESPN's simulated playoff odds (%) |
| `draft_projected_rank` | Preseason projected rank |
| `logo_url` | Team logo |
| `owners` | `List[dict]` of owner member data |
| `roster` | `List[Player]` — current roster |
| `schedule` | `List[Team]` — opponent for each week |
| `scores` | `List[float]` — score for each week |
| `outcomes` | `List[str]` — `"W"`/`"L"`/`"T"`/`"U"` per week |
| `mov` | `List[float]` — margin of victory per week |
| `stats` | `dict` — season stat totals keyed by stat name |
| `get_player_name(playerId)` | Method: roster player's name by ID |

### `Player` (and `BoxPlayer`, which extends it with per-matchup data)

| Attribute | Description |
|---|---|
| `name`, `playerId` | Identity |
| `position`, `eligibleSlots`, `lineupSlot` | Position info |
| `proTeam` | NFL team abbreviation |
| `posRank` | Positional ranking |
| `injuryStatus`, `injured` | Injury info |
| `percent_owned`, `percent_started` | Ownership % |
| `total_points`, `projected_total_points` | Season totals |
| `avg_points`, `projected_avg_points` | Per-game averages |
| `stats` | `dict` keyed by scoring period, each with `points`, `breakdown`, `points_breakdown`, `projected_points`, etc. |
| `schedule` | `dict` keyed by scoring period → `{'team': opponent_abbrev, 'date': datetime}` |

**`BoxPlayer` additions** (only on players returned from `box_scores()` / `free_agents()`):

| Attribute | Description |
|---|---|
| `slot_position` | Where they were started this week (e.g. `"RB"`, `"BE"`, `"IR"`) |
| `points`, `projected_points` | This week's actual/projected points |
| `breakdown`, `points_breakdown` | Raw stat / fantasy-point breakdown for the week |
| `pro_opponent` | This week's NFL opponent |
| `pro_pos_rank` | Opponent's defensive rank against this position |
| `game_played` | `0` or `100` (percent of game completed) |
| `on_bye_week` | `bool` |

### `BoxScore` (from `league.box_scores()`)

`home_team` / `away_team` (`Team`), `home_score` / `away_score` (`float`),
`home_projected` / `away_projected` (`float`), `home_lineup` / `away_lineup`
(`List[BoxPlayer]`), `is_playoff` (`bool`), `matchup_type` (`str`).

### `Matchup` (from `league.scoreboard()`)

`home_team` / `away_team` (`Team`), `home_score` / `away_score` (`float`),
`is_playoff` (`bool`), `matchup_type` (`str`). Lighter-weight than `BoxScore` — no rosters.

### `Activity` (from `league.recent_activity()`)

`date` (epoch ms), `actions` — `List[Tuple[Team, action_str, Player, bid_amount]]` where
`action_str` is one of `"FA ADDED"`, `"WAIVER ADDED"`, `"DROPPED"`, `"TRADE_SENT"`,
`"TRADE_RECEIVED"`.

### `Transaction` (from `league.transactions()`)

`team` (`Team`), `type` (`str`, e.g. `"WAIVER"`), `status`, `scoring_period`, `date`,
`bid_amount`, `items` — `List[TransactionItem]` each with `type`, `playerId`, `player` (name).

### `Settings` (`league.settings`)

| Attribute | Description |
|---|---|
| `name` | League name |
| `team_count` | Number of teams |
| `reg_season_count` | Number of regular season weeks |
| `playoff_team_count` | Teams that make playoffs |
| `playoff_matchup_period_length` | Weeks per playoff round |
| `veto_votes_required` | Votes needed to veto a waiver claim |
| `keeper_count` | Number of keepers allowed |
| `trade_deadline` | Epoch ms of trade deadline |
| `division_map` | `{division_id: division_name}` |
| `tie_rule`, `playoff_tie_rule`, `playoff_seed_tie_rule` | Tiebreaker rules |
| `scoring_type` | e.g. `"H2H_POINTS"` |
| `median_scoring` | `bool` — top-half scoring bonus enabled |
| `faab` | `bool` — league uses FAAB budget instead of waiver priority |
| `acquisition_budget` | FAAB budget total |
| `position_slot_counts` | `{position_label: count}` roster construction |
| `scoring_format` | `List[dict]` — every scored stat with `abbr`, `label`, `points`, `id` |

### `BasePick` (`league.draft`)

`team` (`Team`), `playerId`, `playerName`, `round_num`, `round_pick`, `bid_amount`
(auction leagues), `keeper_status` (`bool`), `nominatingTeam` (auction leagues).

---

## Useful constant maps (`espn_api.football.constant`)

- `POSITION_MAP` — slot ID ↔ label (`"QB"`, `"RB"`, `"FLEX"`, `"D/ST"`, `"BE"`, `"IR"`, etc.), bidirectional
- `PRO_TEAM_MAP` — NFL pro team ID → abbreviation (`"KC"`, `"SF"`, ...)
- `PLAYER_STATS_MAP` — raw ESPN stat ID → readable stat name (passing/rushing/receiving/kicking/defense/punting), ~230 entries, used to build `Player.stats` breakdowns
- `SETTINGS_SCORING_FORMAT_MAP` — stat ID → `{abbr, label}`, used to build `Settings.scoring_format`
- `ACTIVITY_MAP` — message type ID → activity label
- `TRANSACTION_TYPES` — valid values for the `types` filter on `league.transactions()`

---

## Notes / gotchas

- `box_scores()`, `free_agents()`, and `recent_activity()` all raise if `league.year < 2019` — ESPN's API doesn't expose this data for older seasons.
- `league.refresh()` is cheaper than re-instantiating `League(...)` for polling loops.
- Private leagues need **both** `espn_s2` and `swid`, or ESPN silently returns public-only (often empty) data instead of an auth error.
- `Team.final_standing` is `0` until the season officially ends — use `Team.standing` (current playoff seed) mid-season.
