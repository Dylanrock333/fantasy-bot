# ESPN NFL Public API Checklist — Team

Part of a 5-way split of
[`NFL_PUBLIC_API_CHECKLIST.md`](../NFL_PUBLIC_API_CHECKLIST.md), clustered to match
[`nfl_team_tools.py`](../nfl_team_tools.py). See the main checklist for the full
Placeholders table and Notes/gotchas (not duplicated here). 23 of 72 total checklist items.

Scope: team identity, rosters, injuries, depth charts, league org structure, and reference
data tied to teams/leagues (venues, franchises, betting/casino partners).

---

## Site API — `site.api.espn.com`

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}`

- [x] `GET teams`
  - Params: none
  - Summary: Lists all 32 NFL teams with basic identity info (name, abbreviation, logos, links).
  - Returns: All 32 teams — shape `{sports: list[dict]}`; teams live at `sports[0]['leagues'][0]['teams']` (list[dict], each `{team: dict}`).
  - Wired: `nfl_team_tools.get_nfl_teams`

- [x] `GET teams/{id}`
  - Params: `{id}` (team ID)
  - Summary: Returns the full profile for one team (identity, current record, division/conference groups, franchise info, links to next game).
  - Returns: Single team — `{team: dict}` with keys incl. `id, uid, slug, location, name, nickname, abbreviation, displayName, color, logos: list[dict], record: dict, groups: dict, links: list[dict], franchise: dict, nextEvent: list[dict]`. Verified with team 6 (Dallas Cowboys).
  - Wired: `nfl_team_tools.get_team_info` (record pulled from the `record.items` entry with `type: "total"`; also surfaces `franchise.venue.fullName` as home venue)

- [x] `GET teams/{id}/roster`
  - Params: `{id}` (team ID)
  - Summary: Returns the team's full active roster grouped by position, plus coaching staff.
  - Returns: Team roster — `{timestamp: str, status: dict, season: dict, athletes: list[dict], coach: list[dict], team: dict}`. `athletes` is grouped by position (6 groups for team 6, e.g. offense/defense/special teams/etc.), each `{position: str, items: list[dict]}` where `items` are player objects.
  - Wired: `nfl_team_tools.get_nfl_team_roster` (named with an `nfl_` infix, not `get_team_roster`, to avoid colliding with the fantasy-roster tool of that name in `fantasy_roster_tools.py`)

- [x] `GET teams/{id}/schedule`
  - Params: `{id}` (team ID)
  - Summary: Returns the team's full season schedule (past results and upcoming games).
  - Returns: Team schedule — `{timestamp: str, status: dict, season: dict, team: dict, events: list[dict], requestedSeason: dict}`. `events` is a list of game objects (3 for team 6 at time of check — early/limited season data).
  - Wired: `nfl_team_tools.get_team_schedule`

- [ ] `GET teams/{id}/record`
  - Params: `{id}` (team ID)
  - Summary: Intended to return the team's W-L record, but the live endpoint currently returns nothing — record data is actually available embedded in `GET teams/{id}` instead (its `record` key).
  - Returns: Verified with team 6 — HTTP 200 but body is a genuinely empty `{}` (content-length: 2). Same empty result observed for team 1. This sub-resource path appears non-functional/dead on the current site API; do not rely on it.
  - Not wired: dead endpoint (confirmed empty `{}` per checklist research); record is served instead via `get_team_info`, which reads the embedded `record` key from `GET teams/{id}`.

- [x] `GET teams/{id}/depthcharts`
  - Params: `{id}` (team ID)
  - Summary: Returns the team's depth chart (starters and backups by position) broken out by formation package.
  - Returns: Depth chart — useful for start/sit calls. Shape: `{timestamp: str, status: dict, season: dict, team: dict, depthchart: list[dict]}`. `depthchart` has 3 entries for team 6 (e.g. "Base 3-4 D", "Special Teams", "3WR 1TE" formations), each `{id: str, name: str, positions: dict}` where `positions` maps position code (e.g. `"lde"`) -> `{position: dict, athletes: list[dict]}` (athletes ranked starter-to-backup, each including a nested per-player `injuries` list).
  - Wired: `nfl_team_tools.get_team_depth_chart`

- [x] `GET teams/{id}/injuries`
  - Params: `{id}` (team ID)
  - Summary: Intended to return the team's injury report, but the live endpoint currently returns nothing for a given team — real per-team injury data is actually reachable via the league-wide `GET injuries` endpoint below (filter its `injuries` array by team `id`), or via the per-player `injuries` list nested inside `GET teams/{id}/depthcharts`.
  - Returns: Team injury report — verified with team 6 (and team 1) — HTTP 200 but body is a genuinely empty `{}` (content-length: 2). The wired code already handles this gracefully via `report.get("items", report.get("injuries", []))` falling back to an empty list.
  - Wired: `nfl_team_tools.get_team_injuries`

- [ ] `GET teams/{id}/leaders`
  - Params: `{id}` (team ID)
  - Summary: Intended to return the team's statistical leaders, but the live endpoint currently returns nothing.
  - Returns: Team statistical leaders — verified with team 6 — HTTP 200 but body is a genuinely empty `{}` (content-length: 2). Like `/record` and `/injuries` above, this sub-resource path appears non-functional/dead on the current site API.
  - Not wired: dead endpoint (confirmed empty `{}` per checklist research), no working replacement found.

- [x] `GET injuries`
  - Params: none
  - Summary: Returns the current injury report for every NFL team in a single call — this is the real, working source for injury data (unlike the empty per-team `/teams/{id}/injuries`).
  - Returns: League-wide injury report (all 32 teams, one call) — shape `{timestamp: str, status: dict, season: dict, injuries: list[dict]}`. `injuries` has 32 entries (one per team), each `{id: str, displayName: str, injuries: list[dict]}` with that team's individual player injury entries.
  - Wired: `nfl_team_tools.get_league_injury_report` — genuine standalone value distinct from the (dead) `get_team_injuries`: this is the only endpoint that actually returns real injury data, confirmed live (e.g. Cowboys entry present with real player names/statuses).

- [x] `GET groups`
  - Params: none
  - Summary: Returns the NFL's org structure — conferences broken into divisions, each listing its member teams.
  - Returns: Conferences and divisions — shape `{status: str, groups: list[dict]}`. `groups` has 2 entries (AFC, NFC), each `{name: str, abbreviation: str, children: list[dict]}` where `children` are the 4 divisions per conference (e.g. AFC East), each with a `teams: list[dict]` of basic team identity info.
  - Wired: `nfl_team_tools.get_nfl_divisions`

- [ ] `GET rankings`
  - Params: none documented
  - Summary: Confirmed non-functional for NFL — the site API has no poll-rankings resource under the `nfl` sport path.
  - Returns: Poll rankings — source doc flags this as college-football-only content; confirmed HTTP 404 with body `{code: int, message: str}` when called against `.../football/nfl/rankings`. Empty/irrelevant for NFL as expected.
  - Not wired: confirmed 404, no NFL data exists (college-football-only endpoint).

## Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>` unless noted

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues`
  - Method ID: (not specified)
  - Params: `page`, `limit`
  - Summary: Lists every football league ESPN tracks at this API tier, as $ref stubs — used to discover league slugs (e.g. `nfl`, `college-football`), not to get NFL data directly.
  - Returns: All football leagues (CFL, college-football, NFL, UFL, XFL) — use to discover league slugs, not NFL data itself. Shape: `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed `count: 5`; `items` are `{$ref: url}` stubs pointing at `cfl`, `college-football`, `nfl`, `ufl`, `xfl`.
  - Not wired: reference-dump endpoint (league-slug discovery only, no standalone chat value; out of scope per task guidance).

- [ ] `GET /teams`
  - Method ID: `getTeams`
  - Params: `limit` (use `50` for all 32) — confirmed `limit=1` also works and correctly reports `pageCount: 32`.
  - Summary: Lists all 32 NFL teams as $ref stubs (Core API's lighter-weight team index — resolve each ref for full team detail).
  - Returns: Shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed `count: 32`; `items` are `{$ref: url}` stubs pointing at each team's full resource (e.g. `.../nfl/seasons/2026/teams/{id}`).
  - Not wired: redundant with the Site API `GET teams` already wired as `get_nfl_teams` (same 32-team list, but that one returns full identity inline instead of `$ref` stubs that need a second fetch per team).

- [ ] `GET /rankings`
  - Method ID: `getRankings`
  - Params: none required (bare call works)
  - Summary: Poll-rankings list endpoint for the NFL league resource — returns nothing, since the NFL has no AP/Coaches-style poll (unlike college football).
  - Returns: Shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`, but confirmed `count: 0` / `items: []` for NFL — empty as expected, not an error.
  - Not wired: confirmed empty for NFL (no poll rankings exist for this league).

- [ ] `GET /venues`
  - Method ID: `getVenues`
  - Params: none required (bare call works); supports `page`/`limit` like other Core list endpoints
  - Summary: Lists venues/stadiums known to the football data model (not NFL-only — includes college and other stadiums) as $ref stubs.
  - Returns: Stadiums — shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed `count: 681`; `items` are `{$ref: url}` stubs. A resolved venue (e.g. venue 16) has `{$ref, id, fullName, address, grass: bool, indoor: bool, images: list[dict]}`.
  - Not wired: cross-sport reference-dump endpoint, no standalone chat value (out of scope per task guidance).

- [ ] `GET /franchises`
  - Method ID: `getFranchises`
  - Params: none required (bare call works)
  - Summary: Lists the 32 permanent NFL franchises (org identity independent of season/roster) as $ref stubs.
  - Returns: Shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed `count: 32`; `items` are `{$ref: url}` stubs. A resolved franchise (e.g. franchise 1) has `{$ref, id, uid, slug, location, name, nickname, abbreviation, displayName, shortDisplayName, color, isActive: bool, venue: dict, team: dict}`.
  - Not wired: reference-dump endpoint, no standalone chat value beyond identity info already covered by `get_nfl_teams`/`get_team_info` (out of scope per task guidance).

- [ ] `GET /providers`
  - Method ID: `getProviders`
  - Params: none required (bare call works)
  - Summary: Lists betting-odds providers (sportsbooks/data providers) ESPN sources odds from, as $ref stubs.
  - Returns: Odds providers — shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed `count: 73`; `items` are `{$ref: url}` stubs. A resolved provider (e.g. provider 0) has `{$ref, id, name, priority: int}`.
  - Not wired: reference-dump endpoint, no standalone chat value (out of scope per task guidance).

- [ ] `GET /casinos`
  - Method ID: `getCasinos`
  - Params: `page`, `limit` (both optional — bare call works)
  - Summary: Generic reference list of casino/sportsbook partner entities used elsewhere in ESPN's betting data model; not NFL-specific and not meaningful on its own.
  - Returns: Shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed non-empty: `count: 63`; `items` are `{$ref: url}` stubs. Generic reference data, of limited direct use for NFL team/roster tooling.
  - Not wired: reference-dump endpoint, no standalone chat value (out of scope per task guidance).

- [ ] `GET /circuits`
  - Method ID: `getCircuits`
  - Params: `page`, `limit` (both optional — bare call works)
  - Summary: Generic reference list endpoint (racing-style "circuits" concept inherited from the shared cross-sport Core API schema); no data exists for football.
  - Returns: Shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`, but confirmed `count: 0` / `items: []` for NFL — empty as expected, not meaningful for football.
  - Not wired: confirmed empty for football (out of scope, non-football concept per task guidance).

- [ ] `GET /countries`
  - Method ID: `getCountries`
  - Params: `page`, `limit` (both optional — bare call works)
  - Summary: Generic reference list of countries (used for athlete nationality/flags elsewhere in the API); not NFL-specific.
  - Returns: Shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Confirmed non-empty: `count: 255`. Unlike most Core list endpoints, `items` here are inline objects, not just `$ref` stubs: each has `{$ref, id, slug, name, abbreviation, flag: dict, athletes: {$ref: url}}` (e.g. `{id: "1", slug: "usa", name: "USA", ...}`).
  - Not wired: reference-dump endpoint, no standalone chat value (out of scope per task guidance).

- [ ] `GET /v3/sports/{sport}/{league}`
  - Method ID: `getLeague`
  - Params: large generic set incl. `page`, `limit`, `lang`, `region` — many params are cross-sport/inherited and won't apply to football; none are required, bare call works
  - Summary: Returns a compact top-level identity record for the league itself (NFL), not team/roster data.
  - Returns: V3 generic endpoint, base `https://sports.core.api.espn.com/v3/sports/football`, use `{league}=nfl`. Confirmed shape: flat dict `{id: str, uid: str, guid: str, groupId: str, name: str, displayName: str, abbreviation: str, shortName: str, color: str, slug: str}` — e.g. `{"id": "28", "name": "National Football League", "abbreviation": "NFL", "slug": "nfl", ...}`.
  - Not wired: reference-dump endpoint (top-level league identity only, no standalone chat value; out of scope per task guidance).

## Other-League — no NFL equivalent (see main checklist Section 6)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/powerindex`
  - Params: `{year}`
  - Summary: Returns ESPN's Football Power Index (FPI) ratings for every FBS team in a season — despite the doc's "SP+" label, the actual metric returned is FPI (predictive rating, projected W/L, efficiency breakdowns), not SP+. NCAAF only, confirmed no NFL equivalent path exists.
  - Returns: Season SP+ ratings (NCAAF only — team rating system, no NFL equivalent). Verified with `year=2025`: HTTP 200, shape `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}` with `count: 136` (all FBS teams). Each item is inline (not a stub): `{team: {$ref: url}, season: int, lastUpdated: str, runDateTimeKey: int, predictives: list[dict], efficiencies: list[dict]}` — `predictives`/`efficiencies` are lists of named metric objects like `{name, displayName, description, abbreviation, value: float, displayValue: str}`.
  - Not wired: college-football-only, no NFL equivalent (out of scope per task guidance).

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/powerindex/leaders`
  - Params: `{year}`
  - Summary: Intended to return the top-ranked teams/metric leaders from the power index, but the live endpoint returns nothing for this season.
  - Returns: SP+ leaders (NCAAF only). Verified with `year=2025`: HTTP 200, same list shape as `/powerindex` above (`{count, pageIndex, pageSize, pageCount, items}`), but `count: 0` and `items: []` — empty at time of check, not an error.
  - Not wired: college-football-only, no NFL equivalent (out of scope per task guidance).
