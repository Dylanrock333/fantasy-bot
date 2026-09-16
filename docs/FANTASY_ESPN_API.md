# Fantasy ESPN (Private League) API Reference

Your **private fantasy league** via the `espn_api` Python package (installed
version `0.46.0`, source: [cwendt94/espn-api](https://github.com/cwendt94/espn-api)).
Needs `ESPN_S2`/`SWID` auth cookies — contrast with
[`NFL_PUBLIC_API.md`](./NFL_PUBLIC_API.md), which covers ESPN's public,
unauthenticated real-NFL data.

The singleton client lives at `fantasy_agent/clients/fantasy_client.py`
(`league_singleton()`); `LEAGUE_ID`/`YEAR` are hardcoded in
`fantasy_agent/clients/espn_fantasy_client.py` — update those two constants there if either
changes.

```python
from espn_api.football import League

league = League(
    league_id=1992397255,
    year=2026,
    espn_s2="...",   # required for private leagues
    swid="...",      # required for private leagues
)
```

| Construction param | Meaning | Notes |
|---|---|---|
| `league_id` | Your ESPN fantasy league ID | required |
| `year` | Season year | required |
| `espn_s2`, `swid` | Auth cookies | **both** required for private leagues — ESPN silently returns public-only (often empty) data instead of an auth error if either is missing |
| `fetch_league` | Fetch settings/players/teams/draft on init | default `True` |
| `debug` | Log raw request/response info | default `False` |

---

## League attributes (`league.<attr>`, set on init/refresh)

| Attribute | Type | Wired as |
|---|---|---|
| `teams` | `List[Team]`, sorted by `team_id` | ✅ `fantasy_roster_tools.get_team_roster` (name-based lookup) |
| `settings` | `Settings` | ✅ `fantasy_roster_tools.get_league_settings` / `get_scoring_rules` |
| `draft` | `List[BasePick]` | ✅ `fantasy_roster_tools.get_draft_results` |
| `currentMatchupPeriod`, `scoringPeriodId`, `current_week`, `nfl_week` | `int` | ✅ folded into one `fantasy_matchup_tools.get_current_week` |
| `members` | `List[dict]` — raw account/member data | Not wired — redundant with `Team.owners` |
| `player_map` | `dict`, two-way `{playerId: name}` | Not wired — internal only, used by `player_info()` |
| `firstScoringPeriod` / `finalScoringPeriod` | `int` — season boundaries | Not wired — too low-level standalone |
| `previousSeasons` | `List[int]` | Not wired — no standalone chat value; historical `recent_activity`/`message_board` fail for past seasons on this league anyway |

## League methods

"Network" = `cached` (reads the snapshot from construction/last `refresh()`) vs. `live` (hits ESPN fresh every call). None of these can write back to your real ESPN league — a "mutates" note only means it overwrites the local Python object.

### General

| Method | Returns | Network | Wired as |
|---|---|---|---|
| `standings()` | `List[Team]` sorted by standing | cached | ✅ `fantasy_standings_tools.get_standings` (`week=0`) |
| `get_team_data(team_id)` | `Team \| None` | cached | Not wired — no standalone value, users don't refer to teams by numeric ID |
| `refresh()` | re-fetches league+team data | live, mutates | Not wired as a tool — see [`clients/refresh.py`](../fantasy_agent/clients/refresh.py) note below |

### Football-specific

| Method | Returns | Network | Wired as |
|---|---|---|---|
| `standings_weekly(week)` | `List[Team]`, real tiebreaker hierarchy applied | cached | ✅ folded into `get_standings(week)` |
| `top_scorer()` | `Team` with most points for | cached | ✅ `fantasy_standings_tools.get_top_scorer` |
| `least_scorer()` | `Team` with fewest points for | cached | ✅ `fantasy_standings_tools.get_least_scorer` |
| `most_points_against()` | `Team` allowed the most points | cached | ✅ `fantasy_standings_tools.get_most_points_against` |
| `top_scored_week()` | `Tuple[Team, float]`, best single week | cached | ✅ `fantasy_matchup_tools.get_top_scored_week` — raises `ValueError` preseason (empty range); caught and turned into a friendly string |
| `least_scored_week()` | `Tuple[Team, float]`, worst single week | cached | ✅ `fantasy_standings_tools.get_least_scored_week` — same preseason `ValueError` handling |
| `power_rankings(week=None)` | `List[Tuple[str, Team]]`, two-step-dominance | live (calls `box_scores()` internally) | ✅ `fantasy_standings_tools.get_power_rankings` (always current week) |
| `scoreboard(week=None)` | `List[Matchup]`, score only, no rosters | live | ✅ `fantasy_matchup_tools.get_matchup_scoreboard` |
| `box_scores(week=None, player_team_cache=None)` | `List[BoxScore]`, full lineups+projections. **2019+ only** | live | ✅ `fantasy_matchup_tools.get_box_scores` — raises `KeyError` pre-draft (no roster data yet); caught and turned into a friendly string |
| `free_agents(week=None, size=50, position=None, position_id=None)` | `List[BoxPlayer]`. **2019+ only** | live | ✅ `fantasy_player_tools.get_free_agents` |
| `player_info(name=None, playerId=None)` | `Player \| List[Player] \| None` | live | ✅ `fantasy_player_tools.get_player_info` |
| `recent_activity(size=25, msg_type=None, offset=0)` | `List[Activity]`. **2019+ only, current season only** | live | ✅ `fantasy_transaction_tools.get_recent_activity` |
| `transactions(scoring_period=None, types=...)` | `List[Transaction]` | live | ✅ `fantasy_transaction_tools.get_transactions` — raises `Exception('No transactions found')` when empty (not an empty list!); caught and turned into a friendly string |
| `load_roster_week(week)` | mutates `team.roster` in place, returns `None` | live, mutates | Not wired — can't be exposed as a plain string return without extra plumbing; `get_team_roster` already covers current-roster queries |
| `refresh_draft(refresh_players=False, refresh_teams=False)` | re-fetches draft, returns `None` | live, mutates | Not wired — cache-refresh, not a chat action |
| `message_board(msg_types=None)` | `List[dict]`, raw member chat/banter | live | Not wired — author fields are opaque member GUIDs with no name resolution; not roster/league data |

---

## Return object shapes

### `Team`
`team_id`, `team_abbrev`, `team_name`, `division_id`, `division_name`, `wins`, `losses`, `ties`, `points_for`, `points_against`, `standing` (current playoff seed), `final_standing` (**0 until the season officially ends** — use `standing` mid-season), `streak_type`, `streak_length`, `waiver_rank`, `acquisitions`, `acquisition_budget_spent`, `drops`, `trades`, `move_to_ir`, `playoff_pct`, `draft_projected_rank`, `logo_url`, `owners` (`List[dict]`), `roster` (`List[Player]`), `schedule` (`List[Team]` — opponent/week), `scores` (`List[float]`), `outcomes` (`List[str]` — W/L/T/U), `mov` (`List[float]`), `stats` (`dict`), `get_player_name(playerId)` method.

### `Player` (and `BoxPlayer`, extends it with per-matchup data)
`name`, `playerId`, `position`, `eligibleSlots`, `lineupSlot`, `proTeam`, `posRank`, `injuryStatus`, `injured`, `percent_owned`, `percent_started`, `total_points`, `projected_total_points`, `avg_points`, `projected_avg_points`, `stats` (dict keyed by scoring period), `schedule` (dict keyed by scoring period).

**`BoxPlayer` additions** (only from `box_scores()`/`free_agents()`): `slot_position`, `points`, `projected_points`, `breakdown`, `points_breakdown`, `pro_opponent`, `pro_pos_rank`, `game_played` (0 or 100), `on_bye_week`.

### `BoxScore` (from `box_scores()`)
`home_team`/`away_team` (`Team`), `home_score`/`away_score`, `home_projected`/`away_projected`, `home_lineup`/`away_lineup` (`List[BoxPlayer]`), `is_playoff`, `matchup_type`.

### `Matchup` (from `scoreboard()`)
`home_team`/`away_team`, `home_score`/`away_score`, `is_playoff`, `matchup_type` — lighter than `BoxScore`, no rosters.

### `Activity` (from `recent_activity()`)
`date` (epoch ms), `actions`: `List[Tuple[Team, action_str, Player, bid_amount]]`, `action_str` ∈ `"FA ADDED"`/`"WAIVER ADDED"`/`"DROPPED"`/`"TRADE_SENT"`/`"TRADE_RECEIVED"`.

### `Transaction` (from `transactions()`)
`team`, `type` (e.g. `"WAIVER"`), `status`, `scoring_period`, `date`, `bid_amount`, `items` (`List[TransactionItem]`, each with `type`, `playerId`, `player` name).

### `Settings` (`league.settings`)
`name`, `team_count`, `reg_season_count`, `playoff_team_count`, `playoff_matchup_period_length`, `veto_votes_required`, `keeper_count`, `trade_deadline` (epoch ms), `division_map`, `tie_rule`, `playoff_tie_rule`, `playoff_seed_tie_rule`, `scoring_type` (e.g. `"H2H_POINTS"`), `median_scoring` (bool), `faab` (bool), `acquisition_budget`, `position_slot_counts` (`{slot: count}`), `scoring_format` (`List[dict]`, each stat's `abbr`/`label`/`points`/`id` — `get_scoring_rules` filters this to non-zero entries).

### `BasePick` (`league.draft`)
`team`, `playerId`, `playerName`, `round_num`, `round_pick`, `bid_amount` (auction), `keeper_status`, `nominatingTeam` (auction).

---

## Constant maps (`espn_api.football.constant`)

| Map | Description |
|---|---|
| `POSITION_MAP` | Slot ID ↔ label (`QB`, `RB`, `FLEX`, `D/ST`, `BE`, `IR`, ...), bidirectional |
| `PRO_TEAM_MAP` | NFL pro team ID → abbreviation |
| `PLAYER_STATS_MAP` | Raw ESPN stat ID → readable name (~230 entries) |
| `SETTINGS_SCORING_FORMAT_MAP` | Stat ID → `{abbr, label}` |
| `ACTIVITY_MAP` | Message type ID → activity label |
| `TRANSACTION_TYPES` | Valid values for `transactions()`'s `types` filter |

---

## Notes / gotchas

- `box_scores()`, `free_agents()`, and `recent_activity()` all raise if `league.year < 2019`.
- `refresh()` is cheaper than re-instantiating `League(...)` for polling loops — see [`clients/refresh.py`](../fantasy_agent/clients/refresh.py): it exists for a future periodic-refresh timer that isn't wired up yet, since every tool currently re-fetches live through the same `league_singleton()` on each call.
- Several methods raise instead of returning an empty result when there's no data yet (pre-draft/preseason): `box_scores()` → `KeyError`, `transactions()` → `Exception('No transactions found')`, `least_scored_week()`/`top_scored_week()` → `ValueError`. Every wired tool above already catches its specific case and returns a friendly string — don't remove that handling.
- `Team.final_standing` is `0` until the season officially ends — use `Team.standing` mid-season.
- Fantasy `playerId` (this API) and ESPN's public athlete ID (`NFL_PUBLIC_API.md`) are different ID spaces with no automatic mapping — bridging them (e.g. to cross-reference a fantasy roster player against real-NFL stats) goes through `nfl_client.resolve_athlete(pro_team, player_name)`, matching by team + name.
