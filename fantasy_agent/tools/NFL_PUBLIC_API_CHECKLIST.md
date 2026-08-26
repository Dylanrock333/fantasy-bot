# ESPN NFL Public API — Endpoint Checklist

Source: [`espn_nfl_public/NFL_PUBLIC_API_REFERENCE.md`](../../espn_nfl_public/NFL_PUBLIC_API_REFERENCE.md)
(itself sourced from [pseudo-r/Public-ESPN-API](https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md))

Scope: **ESPN NFL public/undocumented endpoints only** — no auth required. Does not cover the
private fantasy league API (`espn_api` / `espn_s2`+`swid`), and does not cover other leagues
(CFL, college football, UFL, XFL) even though the underlying host supports them.

Check items off as you build/wire a tool for that endpoint in this `tools/` folder.

### Placeholders used below

| Placeholder | Meaning | Example |
|---|---|---|
| `{id}` | Team ID or Athlete ID (context-dependent) | `6` (Cowboys), `3918298` (athlete) |
| `{event}` | Game/event ID | `401547635` |
| `{competition}` | Competition ID (same as `{event}` for NFL) | `401547635` |
| `{competitor}` | Competitor (team-in-game) ID | `6` |
| `{play}` | Play ID within a game | — |
| `{week}` | Week number | `1` |
| `{year}` | Season year | `2025` |
| `{seasontype}` | `1`=pre, `2`=regular, `3`=post | `2` |

---

## 1. Site API — `site.api.espn.com`

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}` (unless noted otherwise)

- [x] `GET scoreboard`
  - Params: none
  - Returns: Live scores & schedule, current week
  - Wired: `nfl_scores_tools.get_nfl_scoreboard`

- [ ] `GET scoreboard?week={week}&seasontype={seasontype}`
  - Params: `week`, `seasontype`
  - Returns: Scores for a specific week

- [ ] `GET scoreboard?dates={YYYYMMDD}`
  - Params: `dates` (format `YYYYMMDD`)
  - Returns: Scores for a specific date

- [ ] `GET teams`
  - Params: none
  - Returns: All 32 teams

- [ ] `GET teams/{id}`
  - Params: `{id}` (team ID)
  - Returns: Single team

- [ ] `GET teams/{id}/roster`
  - Params: `{id}` (team ID)
  - Returns: Team roster

- [ ] `GET teams/{id}/schedule`
  - Params: `{id}` (team ID)
  - Returns: Team schedule

- [ ] `GET teams/{id}/record`
  - Params: `{id}` (team ID)
  - Returns: Team record

- [ ] `GET teams/{id}/news`
  - Params: `{id}` (team ID)
  - Returns: Team news

- [x] `GET teams/{id}/depthcharts`
  - Params: `{id}` (team ID)
  - Returns: Depth chart — useful for start/sit calls
  - Wired: `nfl_team_tools.get_team_depth_chart`

- [x] `GET teams/{id}/injuries`
  - Params: `{id}` (team ID)
  - Returns: Team injury report
  - Wired: `nfl_team_tools.get_team_injuries`

- [ ] `GET teams/{id}/leaders`
  - Params: `{id}` (team ID)
  - Returns: Team statistical leaders

- [ ] `GET injuries`
  - Params: none
  - Returns: League-wide injury report (all 32 teams, one call)

- [ ] `GET transactions`
  - Params: none
  - Returns: Recent signings/trades/waivers (real NFL, not fantasy league)

- [ ] `GET statistics`
  - Params: none
  - Returns: League statistical leaders

- [ ] `GET groups`
  - Params: none
  - Returns: Conferences and divisions

- [ ] `GET draft`
  - Params: none
  - Returns: NFL draft board

- [x] `GET news`
  - Params: none
  - Returns: Latest league news
  - Wired: `nfl_news_tools.get_nfl_news`

- [ ] `GET athletes/{id}/news`
  - Params: `{id}` (athlete ID)
  - Returns: Athlete-specific news

- [ ] `GET summary?event={event}`
  - Params: `event`
  - Returns: Full game summary + boxscore

- [ ] `GET https://site.api.espn.com/apis/v2/sports/football/nfl/standings`
  - Params: none
  - Returns: Standings (note different base path — `apis/v2/...`, not `apis/site/v2/...`; the `apis/site/v2/.../standings` variant returns only a stub, so use this URL instead)

- [ ] `GET rankings`
  - Params: none documented
  - Returns: Poll rankings — source doc flags this as college-football-only content; likely empty/irrelevant for NFL, kept in per request rather than pre-filtered

---

## 2. Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>`

Common params on list endpoints: `page`, `limit`.

### All Leagues (not NFL-scoped — lists every football league ESPN tracks)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues`
  - Method ID: (not specified)
  - Params: `page`, `limit`
  - Returns: All football leagues (CFL, college-football, NFL, UFL, XFL) — use to discover league slugs, not NFL data itself

### Seasons & Calendar

- [ ] `GET /calendar`
  - Method ID: `getCalendars`
  - Params: `dates`, `seasontype`, `weeks`
  - Returns: (not specified)

- [ ] `GET /seasons`
  - Method ID: `getSeasons`
  - Params: none
  - Returns: All seasons on record

- [ ] `GET /seasons/{year}/athletes`
  - Method ID: `getAthletes`
  - Params: `{year}`
  - Returns: Athletes for a given season

- [ ] `GET /seasons/{year}/draft`
  - Method ID: `getDraftByYear`
  - Params: `{year}`, `position`, `team`
  - Returns: NFL draft picks

- [ ] `GET /seasons/{year}/freeagents`
  - Method ID: `getFreeAgents`
  - Params: `{year}`
  - Returns: Real NFL free agents (not fantasy)

- [ ] `GET /seasons/{year}/manufacturers`
  - Method ID: `getManufacturers`
  - Params: `{year}`
  - Returns: Equipment manufacturers

### Teams / Athletes

- [ ] `GET /teams`
  - Method ID: `getTeams`
  - Params: `limit` (use `50` for all 32)
  - Returns: (not specified)

- [ ] `GET /athletes`
  - Method ID: `getAthletes`
  - Params: `active`, `position`, `limit`
  - Returns: (not specified)

### Events / Games

- [ ] `GET /events`
  - Method ID: (not specified)
  - Params: none
  - Returns: List of events (games)

- [ ] `GET /events/{event}`
  - Method ID: `getEvent`
  - Params: `{event}`
  - Returns: Single game

- [ ] `GET /events/{event}/competitions/{competition}`
  - Method ID: `getCompetition`
  - Params: `{event}`, `{competition}` (same ID as event for NFL)
  - Returns: (not specified)

- [ ] `GET /events/{event}/competitions/{competition}/broadcasts`
  - Method ID: `getBroadcasts`
  - Params: `{event}`, `{competition}`
  - Returns: TV/streaming info

- [ ] `GET /events/{event}/competitions/{competition}/competitors/{competitor}`
  - Method ID: `getCompetitor`
  - Params: `{event}`, `{competition}`, `{competitor}`
  - Returns: Per-team game data

- [ ] `GET /events/{event}/competitions/{competition}/odds`
  - Method ID: `getCompetitionOdds`
  - Params: `{event}`, `{competition}`
  - Returns: Betting odds

- [ ] `GET /events/{event}/competitions/{competition}/officials`
  - Method ID: `getOfficials`
  - Params: `{event}`, `{competition}`
  - Returns: Referee crew

- [ ] `GET /events/{event}/competitions/{competition}/plays/{play}/personnel`
  - Method ID: `getPersonnel`
  - Params: `{event}`, `{competition}`, `{play}`
  - Returns: On-field personnel for a play

### News, Rankings, Venues, Misc.

- [ ] `GET /media`
  - Method ID: `getMedia`
  - Params: (not specified)
  - Returns: (not specified)

- [ ] `GET /rankings`
  - Method ID: `getRankings`
  - Params: (not specified)
  - Returns: (not specified)

- [ ] `GET /venues`
  - Method ID: `getVenues`
  - Params: (not specified)
  - Returns: Stadiums

- [ ] `GET /positions`
  - Method ID: `getPositions`
  - Params: (not specified)
  - Returns: Position reference list

- [ ] `GET /franchises`
  - Method ID: `getFranchises`
  - Params: (not specified)
  - Returns: (not specified)

- [ ] `GET /providers`
  - Method ID: `getProviders`
  - Params: (not specified)
  - Returns: Odds providers

- [ ] `GET /season`
  - Method ID: `getCurrentSeason`
  - Params: (not specified)
  - Returns: (not specified)

- [ ] `GET /casinos`
  - Method ID: `getCasinos`
  - Params: `page`, `limit`
  - Returns: (not specified)

- [ ] `GET /circuits`
  - Method ID: `getCircuits`
  - Params: `page`, `limit`
  - Returns: (not specified)

- [ ] `GET /countries`
  - Method ID: `getCountries`
  - Params: `page`, `limit`
  - Returns: (not specified)

- [ ] `GET /tournaments`
  - Method ID: `getTournaments`
  - Params: `majorsOnly`, `page`, `limit`
  - Returns: (not specified)

- [ ] `GET /recruiting`
  - Method ID: `getRecruitingSeasons`
  - Params: `page`, `limit`, `sort`, `position`, `status`
  - Returns: (not specified) — source doc's recruiting content is NCAAF-oriented; likely empty/irrelevant for `league=nfl`, kept in per request rather than pre-filtered

- [ ] `GET /standings`
  - Method ID: (not specified)
  - Params: (not specified)
  - Returns: Standings — a **third** standings variant, distinct from both Site API standings entries in Section 1 (`apis/site/v2/.../standings` stub and the working `apis/v2/.../standings`); shape not yet verified against those two

### V3 Endpoints (generic, cross-sport — superseded by the v2 league-scoped endpoints above for most uses)

Base: `https://sports.core.api.espn.com/v3/sports/{sport}` — for football, `{sport}` = `football`.

- [ ] `GET /v3/sports/{sport}/athletes`
  - Method ID: `getAthletes`
  - Params: large generic set incl. `page`, `limit`, `lang`, `region`, `active`, `position`, `season`, `sort` — many params are cross-sport/inherited and won't apply to football
  - Returns: (not specified)

- [ ] `GET /v3/sports/{sport}/{league}`
  - Method ID: `getLeague`
  - Params: same large generic set as above
  - Returns: (not specified) — generic league descriptor, use `{league}=nfl`

- [ ] `GET /v3/sports/{sport}/{league}/seasons/{season}`
  - Method ID: `getSeason`
  - Params: same large generic set as above
  - Returns: (not specified)

---

## 3. Athlete Data — `site.web.api.espn.com`

Base: `https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/`

- [x] `GET athletes/{id}/overview`
  - Params: `{id}` (ESPN athlete ID — see ID note below)
  - Returns: Player overview (season stats + next game + notes)
  - Wired: `nfl_player_tools.get_nfl_player_summary`

- [ ] `GET athletes/{id}/stats`
  - Params: `{id}`
  - Returns: Season stats

- [ ] `GET athletes/{id}/gamelog`
  - Params: `{id}`
  - Returns: Game-by-game log

- [ ] `GET athletes/{id}/splits`
  - Params: `{id}`
  - Returns: Home/Away/Opponent splits

- [ ] `GET statistics/byathlete`
  - Params: none
  - Returns: All-athlete stats leaderboard

> ID note: athlete `{id}` here is ESPN's public athlete ID, **not** the fantasy `playerId`
> from `espn_api`. The two ID spaces don't line up automatically — look it up via the
> `athletes/{id}/overview` search or the roster endpoints in Section 1.

---

## 4. CDN Game Data — `cdn.espn.com`

All endpoints require `?xhr=1`. Payload lives under `gamepackageJSON`.

- [ ] `GET core/nfl/game?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId`
  - Returns: Full game package

- [x] `GET core/nfl/boxscore?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId`
  - Returns: Boxscore only
  - Wired: `nfl_game_tools.get_game_result`

- [x] `GET core/nfl/playbyplay?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId`
  - Returns: Play-by-play (scoring plays only, in `nfl_game_tools`)
  - Wired: `nfl_game_tools.get_game_key_plays`

- [ ] `GET core/nfl/matchup?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId`
  - Returns: Pre-game matchup page

- [ ] `GET core/nfl/scoreboard?xhr=1`
  - Params: `xhr=1`
  - Returns: Current scoreboard

---

## 5. Specialized — QBR

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl`

- [ ] `GET /seasons/{year}/types/2/groups/1/qbr/0`
  - Params: `{year}`; final segment `0`=totals, `1`=home only, `2`=away only
  - Returns: Season totals QBR

- [ ] `GET /seasons/{year}/types/2/weeks/{week}/qbr/0`
  - Params: `{year}`, `{week}`; final segment `0`=totals, `1`=home only, `2`=away only
  - Returns: Weekly QBR

---

## 6. Other-League Endpoints — no NFL equivalent exists

These are hardcoded to `league=college-football` in the source doc (no `{league}` template, so
they cannot be pointed at `nfl`). Out of scope for an NFL-only file, but included per request
rather than pre-filtered — expect to cut these.

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/recruits`
  - Params: `{year}`
  - Returns: Top recruiting class by year (NCAAF only)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/classes/{teamId}`
  - Params: `{year}`, `{teamId}`
  - Returns: Recruiting class by team (NCAAF only)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/powerindex`
  - Params: `{year}`
  - Returns: Season SP+ ratings (NCAAF only)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/powerindex/leaders`
  - Params: `{year}`
  - Returns: SP+ leaders (NCAAF only)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/types/2/groups/80/qbr/0`
  - Params: `{year}`; `groups/80` is the NCAAF group ID (NFL uses `groups/1`, already in Section 5)
  - Returns: College Football QBR — duplicate of Section 5's QBR shape, NCAAF-scoped

---

## Notes / gotchas (carried over from the source reference)

- No auth needed anywhere in this file — all endpoints are public.
- These are **undocumented** ESPN endpoints (community-reverse-engineered) — no uptime/schema
  guarantee, no versioning contract. Parse defensively; don't hard-fail on unexpected fields.
- Event ID and Competition ID are the same number for NFL games (no multi-competition events).
- Rate limiting is undocumented; cache static data (`teams`, `venues`, `positions`) instead of
  re-fetching per request.
- Section 6's Recruiting and Power Index/SP+ endpoints are college-football-only with no NFL
  equivalent — included per request rather than pre-filtered so nothing is hidden; expect to
  prune these first.
- The V3 generic endpoints (Section 2) and several "Other" reference lists (`casinos`,
  `circuits`, `countries`) have undocumented/unverified return shapes — everything above is
  documented at the "endpoint exists" level, not confirmed against a live NFL response.
