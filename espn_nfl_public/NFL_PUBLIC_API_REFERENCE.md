# ESPN Public API — Football / NFL Reference

Source: [pseudo-r/Public-ESPN-API](https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md)
(community-documented, unofficial, undocumented ESPN endpoints — **no API key or auth
required**, unlike the fantasy league API).

**Different from [`ESPN_API_REFERENCE.md`](./ESPN_API_REFERENCE.md):** that file covers the
`espn_api` Python wrapper for your *private fantasy league* (rosters, matchups, waivers —
needs `espn_s2`/`swid`). This file covers ESPN's *public sports-data* API — real NFL scores,
injuries, depth charts, stats, news — useful to enrich fantasy decisions with data the
fantasy API doesn't expose.

Every URL below was hit live on 2026-08-14 and returned `200`. `{league}` examples are
pre-filled with `nfl`; swap for `cfl`, `college-football`, `ufl`, or `xfl` if you ever need
another football league.

---

## Placeholders

| Placeholder | Meaning | Example |
|---|---|---|
| `{id}` | Team ID or Athlete ID (context-dependent) | `6` (Cowboys), `3918298` (athlete) |
| `{event}` | Game/event ID | `401547635` |
| `{week}` | Week number | `1` |
| `{year}` | Season year | `2025` |
| `{seasontype}` | `1`=pre, `2`=regular, `3`=post | `2` |

### NFL team IDs (verified live, `site.api.espn.com/.../nfl/teams`)

| ID | Abbr | Team | ID | Abbr | Team |
|---|---|---|---|---|---|
| 1 | ATL | Atlanta Falcons | 18 | NO | New Orleans Saints |
| 2 | BUF | Buffalo Bills | 19 | NYG | New York Giants |
| 3 | CHI | Chicago Bears | 20 | NYJ | New York Jets |
| 4 | CIN | Cincinnati Bengals | 21 | PHI | Philadelphia Eagles |
| 5 | CLE | Cleveland Browns | 22 | ARI | Arizona Cardinals |
| 6 | DAL | Dallas Cowboys | 23 | PIT | Pittsburgh Steelers |
| 7 | DEN | Denver Broncos | 24 | LAC | Los Angeles Chargers |
| 8 | DET | Detroit Lions | 25 | SF | San Francisco 49ers |
| 9 | GB | Green Bay Packers | 26 | SEA | Seattle Seahawks |
| 10 | TEN | Tennessee Titans | 27 | TB | Tampa Bay Buccaneers |
| 11 | IND | Indianapolis Colts | 28 | WSH | Washington Commanders |
| 12 | KC | Kansas City Chiefs | 29 | CAR | Carolina Panthers |
| 13 | LV | Las Vegas Raiders | 30 | JAX | Jacksonville Jaguars |
| 14 | LAR | Los Angeles Rams | 33 | BAL | Baltimore Ravens |
| 15 | MIA | Miami Dolphins | 34 | HOU | Houston Texans |
| 16 | MIN | Minnesota Vikings | | | |
| 17 | NE | New England Patriots | | | |

(IDs 31/32 are unused by ESPN.)

---

## 1. Site API — `site.api.espn.com` (start here)

Human-friendly JSON: scores, rosters, injuries, news. This is the tier you'll want for most
fantasy-bot lookups.

```
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}
```

| Endpoint (append to base above) | Description |
|---|---|
| `scoreboard` | Live scores & schedule, current week |
| `scoreboard?week={week}&seasontype={seasontype}` | Scores for a specific week |
| `scoreboard?dates={YYYYMMDD}` | Scores for a specific date |
| `teams` | All 32 teams |
| `teams/{id}` | Single team |
| `teams/{id}/roster` | Team roster |
| `teams/{id}/schedule` | Team schedule |
| `teams/{id}/record` | Team record |
| `teams/{id}/news` | Team news |
| `teams/{id}/depthcharts` | **Depth chart** — great for start/sit calls |
| `teams/{id}/injuries` | Team injury report |
| `teams/{id}/leaders` | Team statistical leaders |
| `injuries` | **League-wide** injury report (all 32 teams, one call) |
| `transactions` | Recent signings/trades/waivers (real NFL, not your league) |
| `statistics` | League statistical leaders |
| `groups` | Conferences and divisions |
| `draft` | NFL draft board |
| `news` | Latest league news |
| `athletes/{id}/news` | Athlete-specific news |
| `summary?event={event}` | Full game summary + boxscore |

> ⚠️ **Standings caveat:** `apis/site/v2/.../standings` returns only a stub. Use instead:
> `GET https://site.api.espn.com/apis/v2/sports/football/nfl/standings`

**Ready-to-run examples:**
```bash
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=1&seasontype=2"
curl "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/depthcharts"
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/6/injuries"
```

---

## 2. Core API v2 — `sports.core.api.espn.com`

Structured, paginated data. Base for every row below:

```
https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>
```

Common params on list endpoints: `page`, `limit`.

### Seasons & Calendar

| Endpoint suffix | Method ID | Notes |
|---|---|---|
| `/calendar` | `getCalendars` | `?dates=`, `?seasontype=`, `?weeks=` |
| `/seasons` | `getSeasons` | All seasons on record |
| `/seasons/{year}/athletes` | `getAthletes` | Athletes for a given season |
| `/seasons/{year}/draft` | `getDraftByYear` | NFL draft picks, `?position=`, `?team=` |
| `/seasons/{year}/freeagents` | `getFreeAgents` | Real NFL free agents (not fantasy) |
| `/seasons/{year}/manufacturers` | `getManufacturers` | Equipment manufacturers |

### Teams / Athletes

| Endpoint suffix | Method ID | Notes |
|---|---|---|
| `/teams` | `getTeams` | `?limit=50` for all 32 |
| `/athletes` | `getAthletes` | `?active=true`, `?position=`, `?limit=` |

### Events / Games

| Endpoint suffix | Method ID | Notes |
|---|---|---|
| `/events` | — | List of events (games) |
| `/events/{event}` | `getEvent` | Single game |
| `/events/{event}/competitions/{competition}` | `getCompetition` | Same ID as event for NFL |
| `/events/{event}/competitions/{competition}/broadcasts` | `getBroadcasts` | TV/streaming info |
| `/events/{event}/competitions/{competition}/competitors/{competitor}` | `getCompetitor` | Per-team game data |
| `/events/{event}/competitions/{competition}/odds` | `getCompetitionOdds` | Betting odds |
| `/events/{event}/competitions/{competition}/officials` | `getOfficials` | Referee crew |
| `/events/{event}/competitions/{competition}/plays/{play}/personnel` | `getPersonnel` | On-field personnel for a play |

### News, Rankings, Venues, Misc.

| Endpoint suffix | Method ID | Notes |
|---|---|---|
| `/media` | `getMedia` | |
| `/rankings` | `getRankings` | |
| `/venues` | `getVenues` | Stadiums |
| `/positions` | `getPositions` | Position reference list |
| `/franchises` | `getFranchises` | |
| `/providers` | `getProviders` | Odds providers |
| `/season` | `getCurrentSeason` | |

**Ready-to-run examples:**
```bash
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/teams?limit=50"
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes?limit=100&active=true"
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events"
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/draft"
curl "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/freeagents"
```

---

## 3. Athlete Data — `site.web.api.espn.com` (per-player deep dives)

Best source for individual player stats/game logs to cross-reference against your fantasy
roster.

```bash
# Player overview (season stats + next game + notes)
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/overview"

# Season stats
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/stats"

# Game-by-game log
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/gamelog"

# Home/Away/Opponent splits
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{id}/splits"

# All-athlete stats leaderboard
curl "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/statistics/byathlete"
```

> Athlete `{id}` here is ESPN's athlete ID, **not** the fantasy `playerId` from
> `espn_api`. Look it up via `athletes/{id}/overview` search or the roster endpoints above —
> the two ID spaces don't line up automatically.

---

## 4. CDN Game Data — `cdn.espn.com` (deep game internals)

Richest per-game data: drives, play-by-play, win probability, live scoring. Requires `?xhr=1`.
Payload lives under `gamepackageJSON`.

```bash
curl "https://cdn.espn.com/core/nfl/game?xhr=1&gameId={event}"       # full game package
curl "https://cdn.espn.com/core/nfl/boxscore?xhr=1&gameId={event}"   # boxscore only
curl "https://cdn.espn.com/core/nfl/playbyplay?xhr=1&gameId={event}" # play-by-play
curl "https://cdn.espn.com/core/nfl/matchup?xhr=1&gameId={event}"    # pre-game matchup page
curl "https://cdn.espn.com/core/nfl/scoreboard?xhr=1"                # current scoreboard
```

---

## 5. Specialized — QBR

```bash
# Season totals QBR
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/2/groups/1/qbr/0

# Weekly QBR
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/types/2/weeks/{week}/qbr/0
```
`/qbr/0` = season/week totals, `/qbr/1` = home only, `/qbr/2` = away only.

(Recruiting and Power Index/SP+ endpoints from the source doc are **college-football only** —
omitted here since this file is NFL-scoped. See the source doc if you ever need NCAAF.)

---

## Notes / gotchas

- No auth needed anywhere in this file — all public. Contrast with `ESPN_API_REFERENCE.md`,
  where fantasy league calls need `espn_s2`/`swid` for private leagues.
- These are **undocumented** ESPN endpoints (community-reverse-engineered) — no uptime/schema
  guarantee, no versioning contract. Don't hard-fail your bot on unexpected fields; parse
  defensively.
- Event ID and Competition ID are the same number for NFL games (no multi-competition events).
- The Core API v3 generic endpoints (`/v3/sports/{sport}/{league}`, `/v3/sports/{sport}/athletes`)
  are broad, low-signal, and mostly superseded by the v2 league-scoped and Site API endpoints
  above — skip them unless you need the exact generic shape.
- Rate limiting is undocumented; cache responses (especially `teams`, `venues`, `positions` —
  static data) instead of re-fetching per request.
