# ESPN Public NFL API Reference

Real-world NFL data (scores, rosters, injuries, stats, news) via ESPN's
**public, undocumented, unauthenticated** endpoints — no API key, `espn_s2`,
or `SWID` needed. Community-reverse-engineered (source:
[pseudo-r/Public-ESPN-API](https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md)),
so treat every response defensively (parse missing/renamed fields
gracefully) — there's no uptime or schema guarantee.

Contrast with [`FANTASY_ESPN_API.md`](./FANTASY_ESPN_API.md), which covers
your **private fantasy league** (rosters, matchups, waivers — needs auth).

The client for everything below lives at
`fantasy_agent/clients/nfl_client.py` (`get_json`, `resolve_team`,
`resolve_athlete`, `resolve_event`) — it's a standalone vendored copy with
no dependency on any reference-script package, so the agent can be deployed
on its own.

## Placeholders

| Placeholder | Meaning | Example |
|---|---|---|
| `{id}` | Team ID or Athlete ID (context-dependent) | `6` (Cowboys), `3918298` (athlete) |
| `{event}` | Game/event ID | `401547635` |
| `{week}` | Week number | `1` |
| `{year}` | Season year | `2025` |
| `{seasontype}` | `1`=pre, `2`=regular, `3`=post | `2` |

Team IDs run 1–34 (skipping 31/32); look them up live with `GET teams` if
needed rather than hardcoding a table here.

Athlete `{id}` is ESPN's **public** athlete ID — a different ID space than
the fantasy `playerId` from `espn_api`. `resolve_athlete(pro_team,
player_name)` in `nfl_client.py` is the bridge: it resolves a team, fetches
that team's ~53-man roster (or falls back to the depth chart for teams
whose `/roster` 404s, e.g. Cardinals/team 22), and fuzzy-matches the name.

---

## 1. Site API — `site.api.espn.com` (start here for most lookups)

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}`

| Endpoint | Returns | Status |
|---|---|---|
| `scoreboard` | Current-week scores/schedule | ✅ `nfl_scores_tools.get_nfl_scoreboard` |
| `scoreboard?week=&seasontype=&dates=` | Scores for a specific week or date (`dates=YYYYMMDD`) | ✅ same tool, optional args. `year=` does **not** pin an old season (tested 2019–2025, always returns current season) — don't rely on it. |
| `teams` | All 32 teams, identity only | ✅ `nfl_team_tools.get_nfl_teams` |
| `teams/{id}` | One team's profile (record, conference/division, franchise, venue) | ✅ `nfl_team_tools.get_team_info` |
| `teams/{id}/statistics` | Team season offense/defense stats (points, yards, sacks, takeaways) | ✅ `nfl_team_tools.get_team_stats` |
| `teams/{id}/roster` | Full roster grouped by position + coaching staff | ✅ `nfl_team_tools.get_nfl_team_roster` (also `get_team_coach`, same endpoint) |
| `teams/{id}/schedule` | Full season schedule | ✅ `nfl_team_tools.get_team_schedule` |
| `teams/{id}/record` | — | ❌ dead: always returns empty `{}`. Use `teams/{id}`'s embedded `record` instead. |
| `teams/{id}/depthcharts` | Depth chart by formation, starters→backups, nested per-player injuries | ✅ `nfl_team_tools.get_team_depth_chart` |
| `teams/{id}/injuries` | — | ❌ dead: always empty `{}`. Use league-wide `injuries` below instead. |
| `teams/{id}/leaders` | — | ❌ dead: always empty `{}`, no working replacement found. |
| `teams/{id}/news` | — | ❌ dead: always empty `{}` (tested 3 teams). |
| `injuries` | League-wide injury report, all 32 teams in one call | ✅ `nfl_team_tools.get_league_injury_report` — the real source, unlike the dead per-team variant |
| `groups` | Conferences → divisions → member teams | ✅ `nfl_team_tools.get_nfl_divisions` |
| `statistics` | League-wide statistical leaders by category | ✅ `nfl_player_tools.get_nfl_stat_leaders` |
| `news` | Latest league headlines | ✅ `nfl_news_tools.get_nfl_news` |
| `athletes/{id}/news` | — | ❌ dead: `articles` always empty even for star players. |
| `transactions?limit=&page=` | League-wide real-NFL transactions (signings/trades/waivers) | ✅ `nfl_news_tools.get_nfl_transactions` |
| `draft` | Full current-year draft board, all picks | ✅ `nfl_news_tools.get_nfl_draft` |
| `summary?event={event}` | Full gamecast bundle (boxscore+drives+odds+injuries+news) | Not wired — kitchen-sink duplicate of the more targeted endpoints below |
| `rankings` | — | ❌ 404, college-football only, no NFL data |
| `apis/v2/.../standings` (note: different base — `apis/v2/`, not `apis/site/v2/`) | Full standings, conference→division, all stats inline | ✅ `nfl_scores_tools.get_nfl_standings`. The `apis/site/v2/.../standings` variant is a stub — don't use it. |

## 2. Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl{sub-path}`. Common params: `page`, `limit`.

Almost everything here returns paginated `{$ref}` stub lists needing a
second fetch per item, and is superseded by an inline Site API equivalent
above — kept only where it's the *only* source for something.

| Endpoint | Returns | Status |
|---|---|---|
| `/seasons/{year}/types/2/groups/1/qbr/0` | Season-total QBR (all qualified QBs) | ✅ `nfl_player_tools.get_nfl_qbr_leaders` |
| `/seasons/{year}/types/2/weeks/{week}/qbr/0` | Weekly QBR | ✅ same tool, `week` arg |
| `/events/{event}/competitions/{event}/broadcasts` | TV/streaming carriers for a game | ✅ `nfl_game_tools.get_game_broadcast` |
| `/events/{event}/competitions/{event}/odds` | Betting odds (spread/ML/O-U) for a game | ✅ `nfl_game_tools.get_game_odds` |
| `/events/{event}/competitions/{event}/officials` | Officiating crew for a game | ✅ `nfl_game_tools.get_game_officials` |
| `/events/{event}/competitions/{event}/plays/{play}/personnel` | — | ❌ dead: HTTP 500 on every play tried. `.../plays/{play}` (no `/personnel`) works and has a `participants` field that covers most of the same need. |
| `/calendar`, `/seasons`, `/events`, `/season`, `/standings`, `/teams`, `/athletes`, `/venues`, `/franchises`, `/providers`, `/media`, `/positions` | Reference/index data | Not wired — all either raw `$ref` stub dumps with no inline data, or duplicate a richer Site API endpoint above (e.g. `/standings` needs 3+ follow-up fetches vs. the Site API's one-shot inline standings) |
| `/tournaments`, `/rankings` (core), `/seasons/{year}/manufacturers`, `/recruiting` | — | ❌ not supported for NFL (400 error or always empty) |
| `/v3/sports/football/...` (generic v3 endpoints) | — | Not wired — cross-sport generic shapes, thinner and less useful than the v2 league-scoped equivalents above |

## 3. Athlete Data — `site.web.api.espn.com` (per-player deep dives)

Base: `https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/`

| Endpoint | Returns | Status |
|---|---|---|
| `athletes/{id}/overview` | Season stat highlights, next game, news, fantasy outlook | ✅ `nfl_player_tools.get_nfl_player_summary` |
| `athletes/{id}/stats` | Season/career stats by category, with glossary | ✅ `nfl_player_tools.get_nfl_player_career_stats` |
| `athletes/{id}/gamelog` | Game-by-game log | ✅ `nfl_player_tools.get_nfl_player_gamelog` |
| `athletes/{id}/splits` | Home/away/opponent splits | ✅ `nfl_player_tools.get_nfl_player_splits` |
| `statistics/byathlete` | — | ❌ 404, doesn't exist |

## 4. CDN Game Data — `cdn.espn.com` (deep per-game internals)

All require `?xhr=1`; payload lives under `gamepackageJSON`.

| Endpoint | Returns | Status |
|---|---|---|
| `core/nfl/boxscore?xhr=1&gameId={event}` | Boxscore, header, standings | ✅ `nfl_game_tools.get_game_result` |
| `core/nfl/playbyplay?xhr=1&gameId={event}` | Full drive-by-drive plays (each play has a numeric `id` reusable elsewhere) | ✅ `nfl_game_tools.get_game_key_plays` (extracts scoring plays; full drive/play detail is present if more granularity is ever needed) |
| `core/nfl/matchup?xhr=1&gameId={event}` | Team leaders, pickcenter odds, game info (no drives) | ✅ `nfl_game_tools.get_game_leaders` |
| `core/nfl/game?xhr=1&gameId={event}` | Kitchen-sink superset of all three above | Not wired — no unique content |
| `core/nfl/scoreboard?xhr=1` | Full ESPN.com scoreboard page bundle | Not wired — same `events` data as the Site API `scoreboard`, ~345KB heavier |

---

## Notes / gotchas

- Every "dead" endpoint above was confirmed live (HTTP 200 + empty body, or
  an explicit error) — not assumed. Don't re-litigate them without a fresh
  live check; ESPN's public API has no changelog.
- Event ID and Competition ID are the same number for NFL games.
- Cache static lookups (`teams`, positions) — `resolve_team` already caches
  the team list for the process lifetime; `resolve_athlete` lazily caches
  each team's roster the first time it's looked up.
- Rate limiting is undocumented; avoid re-fetching static data per request.
- Anything scoped to college-football/other leagues (recruiting, Power
  Index/SP+, `groups/80` QBR) has no NFL equivalent and is intentionally
  left out of this file.
