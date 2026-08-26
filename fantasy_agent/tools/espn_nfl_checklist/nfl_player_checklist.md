# ESPN NFL Public API Checklist — Player

Part of a 5-way split of
[`NFL_PUBLIC_API_CHECKLIST.md`](../NFL_PUBLIC_API_CHECKLIST.md), clustered to match
[`nfl_player_tools.py`](../nfl_player_tools.py). See the main checklist for the full
Placeholders table and Notes/gotchas (not duplicated here). 17 of 72 total checklist items.

Scope: individual athlete data — stats, splits, game logs, QBR, and reference lists tied to
players (positions, equipment, recruiting).

---

## Site API — `site.api.espn.com`

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}`

- [x] `GET statistics`
  - Params: none (confirmed live — 200 OK)
  - Summary: Returns league-wide statistical leaders (top athlete per stat category, e.g. passing yards) for the current season.
  - Returns: League statistical leaders — top-level keys: `timestamp` (str), `status` (str), `season` (dict: year/displayName/type/name), `league` (dict: id/name/abbreviation/shortName/slug/isTournament/links/logos), `stats` (dict: id/name/abbreviation/`categories` — list of stat categories, each with a `leaders` list of {displayValue, value, athlete}).
  - Wired: `nfl_player_tools.get_nfl_stat_leaders`

## Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>` unless noted

- [ ] `GET /seasons/{year}/athletes`
  - Method ID: `getAthletes`
  - Params: `{year}` (confirmed live — 200 OK for year=2025); also accepts `limit`/`page`
  - Summary: Returns a paginated list of stub references to every athlete tracked for the given NFL season — no inline athlete data, each item must be dereferenced.
  - Returns: Athletes for a given season — top-level keys: `count` (int), `pageIndex` (int), `pageSize` (int), `pageCount` (int), `items` (list of `{"$ref": url}` stub references, e.g. `.../seasons/2025/athletes/4246273?...`).
  - Not wired: raw paginated stub-reference list, not directly useful to the calling LLM without per-item dereferencing; superseded by name-based `resolve_athlete` lookups used throughout this module.

- [ ] `GET /athletes`
  - Method ID: `getAthletes`
  - Params: `active`, `position`, `limit` (confirmed live — 200 OK with `active=true&limit=3`; no `{year}` segment, defaults to current season)
  - Summary: Same as `/seasons/{year}/athletes` but without an explicit season segment — returns a paginated stub-reference list of athletes for the current season.
  - Returns: top-level keys: `count` (int), `pageIndex` (int), `pageSize` (int), `pageCount` (int), `items` (list of `{"$ref": url}` stub references, same shape as the season-scoped endpoint).
  - Not wired: raw paginated stub-reference list, same reason as `/seasons/{year}/athletes` above.

- [ ] `GET /positions`
  - Method ID: `getPositions`
  - Params: none required (confirmed live — 200 OK); accepts `limit`
  - Summary: Returns a paginated list of stub references to every player-position entry (QB, RB, OT, etc.) in the league's position reference table.
  - Returns: Position reference list — top-level keys: `count` (int), `pageIndex` (int), `pageSize` (int), `pageCount` (int), `items` (list of `{"$ref": url}` stub references, e.g. `.../positions/0?...`).
  - Not wired: raw paginated stub-reference list of little standalone value to the calling LLM.

- [ ] `GET /seasons/{year}/manufacturers`
  - Method ID: `getManufacturers`
  - Params: `{year}` — confirmed NOT supported for NFL; tested year=2024 and year=2025, both fail regardless of value
  - Summary: Endpoint fails outright — ESPN's core API explicitly rejects `getManufacturers()` for the football/nfl league (this method exists for other sports but not football).
  - Returns: Equipment manufacturers — **fails, 400**: `{"error": {"message": "getManufacturers() not supported for football/nfl", "code": 400}}`.
  - Not wired: endpoint confirmed to 400 for football/nfl regardless of params.

- [ ] `GET /recruiting`
  - Method ID: `getRecruitingSeasons`
  - Params: `page`, `limit`, `sort`, `position`, `status` (confirmed live — 200 OK, no params required)
  - Summary: Confirmed the doc's suspicion — for `league=nfl` the call succeeds but always returns zero results, since ESPN's recruiting data only exists under `league=college-football`.
  - Returns: (not specified) — source doc's recruiting content is NCAAF-oriented; **confirmed empty for `league=nfl`**: `{"count": 0, "pageIndex": 0, "pageSize": 25, "pageCount": 0, "items": []}`, kept in per request rather than pre-filtered
  - Not wired: always returns zero results for league=nfl.

- [ ] `GET /v3/sports/{sport}/athletes`
  - Method ID: `getAthletes`
  - Params: large generic set incl. `page`, `limit`, `lang`, `region`, `active`, `position`, `season`, `sort` — many params are cross-sport/inherited and won't apply to football; **as literally documented (`/v3/sports/football/athletes`, no league segment) this 404s** with `{"error": {"message": "no instance found", "code": 404}}` (same for a single-athlete sub-path). The path that actually works includes the league segment: `GET /v3/sports/football/nfl/athletes?limit=N` → 200 OK.
  - Summary: The doc's path is missing the league segment and does not resolve; the corrected path `/v3/sports/football/nfl/athletes` returns a paginated list of lightweight athlete objects (inline data, not `$ref` stubs) including some placeholder/non-roster entries (e.g. names like `"[35]"`).
  - Returns: (not specified) — V3 generic endpoint, base `https://sports.core.api.espn.com/v3/sports/football`. **Corrected path `/v3/sports/football/nfl/athletes` returns**: top-level keys `count` (int), `pageIndex` (int), `pageSize` (int), `pageCount` (int), `items` (list of dicts with `id`, `uid`, `guid`, `lastName`, `fullName`, `displayName`, `shortName`, `jersey`, `active` — inline, not refs).
  - Not wired: as documented, path 404s; even the corrected path is just a raw paginated athlete stub list (name/jersey only, including placeholder entries), not worth a dedicated tool alongside `resolve_athlete`-backed lookups.

- [x] `GET /seasons/{year}/types/2/groups/1/qbr/0`
  - Params: `{year}`; final segment `0`=totals, `1`=home only, `2`=away only (confirmed live — 200 OK for year=2025, groups/1, final segment 0)
  - Summary: Returns season-total advanced QBR (ESPN's Total QBR metric) for group 1 (all qualified NFL QBs), one entry per player with links to the athlete/team/season plus a detailed breakdown of named QBR sub-metrics.
  - Returns: Season totals QBR — top-level keys: `$ref` (str), `count` (int), `pageIndex` (int), `pageSize` (int), `pageCount` (int), `items` (list of dicts: `athlete` {$ref}, `team` {$ref}, `season` {$ref}, `splits` {id, name, abbreviation, `categories`: list of {name, displayName, stats: [{name, displayName, description, abbreviation, value, displayValue}, ...]}}). For 2025/groups/1/qbr/0, `count` was only 3 (small qualified-QB result set on the default page).
  - Wired: `nfl_player_tools.get_nfl_qbr_leaders` (week=0 default)

- [x] `GET /seasons/{year}/types/2/weeks/{week}/qbr/0`
  - Params: `{year}`, `{week}`; final segment `0`=totals, `1`=home only, `2`=away only (confirmed live — 200 OK for year=2025, week=1, final segment 0)
  - Summary: Same QBR metric shape as the season-totals endpoint above but scoped to a single week; returns one entry per QB who played that week.
  - Returns: Weekly QBR — same top-level shape as the season endpoint: `$ref` (str), `count` (int), `pageIndex`/`pageSize`/`pageCount` (int), `items` (list of {athlete $ref, team $ref, season $ref, splits {...}}). For 2025 week 1, `count` was 28.
  - Wired: `nfl_player_tools.get_nfl_qbr_leaders` (week param)

## Athlete Data — `site.web.api.espn.com`

Base: `https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/`

- [x] `GET athletes/{id}/overview`
  - Params: `{id}` (ESPN athlete ID — see ID note below) (confirmed live — 200 OK for id=2577417, Dak Prescott)
  - Summary: Returns a one-stop player overview bundle — current season stat highlights, next scheduled game, recent news, and fantasy outlook — for a single athlete.
  - Returns: Player overview (season stats + next game + notes) — matches `get_nfl_player_summary`. Top-level keys: `statistics` (dict), `news` (list), `nextGame` (dict), `gameLog` (dict), `rotowire` (dict), `awards` (list), `fantasy` (dict).
  - Wired: `nfl_player_tools.get_nfl_player_summary`

- [x] `GET athletes/{id}/stats`
  - Params: `{id}` (confirmed live — 200 OK for id=2577417)
  - Summary: Returns a single athlete's season/career statistics broken out by category (passing, rushing, etc.), organized by team stint, with a glossary explaining each stat abbreviation.
  - Returns: Season stats — top-level keys: `filters` (list), `teams` (dict), `categories` (list), `glossary` (list).
  - Wired: `nfl_player_tools.get_nfl_player_career_stats`

- [x] `GET athletes/{id}/gamelog`
  - Params: `{id}` (confirmed live — 200 OK for id=2577417)
  - Summary: Returns a single athlete's game-by-game statistical log, keyed by event, across season types (regular/post), with labels and a glossary for the stat columns.
  - Returns: Game-by-game log — top-level keys: `categories` (list), `filters` (list), `labels` (list), `names` (list), `displayNames` (list), `events` (dict), `seasonTypes` (list), `glossary` (list).
  - Wired: `nfl_player_tools.get_nfl_player_gamelog`

- [x] `GET athletes/{id}/splits`
  - Params: `{id}` (confirmed live — 200 OK for id=2577417)
  - Summary: Returns a single athlete's statistical splits (e.g. home/away, by opponent) broken into named split categories with human-readable descriptions and a stat glossary.
  - Returns: Home/Away/Opponent splits — top-level keys: `filters` (list), `displayName` (str), `categories` (list), `labels` (list), `names` (list), `displayNames` (list), `descriptions` (list), `splitCategories` (list).
  - Wired: `nfl_player_tools.get_nfl_player_splits`

- [ ] `GET statistics/byathlete`
  - Params: none — confirmed this path does not exist on the live API
  - Summary: Fails outright — there is no `statistics/byathlete` resource under the site API; every request 404s regardless of params.
  - Returns: All-athlete stats leaderboard — **fails, 404**: `{"code": 404}` (also confirmed `statistics/players` 404s the same way; `statistics?type=byathlete` returns 200 but ignores the param and returns the same leaders payload as plain `GET statistics`).
  - Not wired: path does not exist on the live API (404 regardless of params).

> ID note: athlete `{id}` here is ESPN's public athlete ID, **not** the fantasy `playerId`
> from `espn_api`. The two ID spaces don't line up automatically — look it up via the
> `athletes/{id}/overview` search or the roster endpoints in the Team checklist.

## Other-League — no NFL equivalent (see main checklist Section 6)

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/recruits`
  - Params: `{year}` (confirmed live — 200 OK for year=2025); also accepts `limit`
  - Summary: Returns a paginated list of stub references to individual recruit records (high-school prospects) for the given class year — dereferencing an item yields full recruit detail (name, high school, position, grade, committed schools).
  - Returns: Top recruiting class by year (NCAAF only) — top-level keys: `count` (int), `pageIndex` (int), `pageSize` (int), `pageCount` (int), `items` (list of `{"$ref": url}` stub references, e.g. `.../recruits/266099?...`). A dereferenced recruit item has keys `$ref`, `athlete`, `recruitingClass`, `status`, `grade`, `gradeDisplayValue`, `attributes`, `schools`, `activity`.
  - Not wired: no NFL equivalent — college-football-only recruiting data, out of scope for this NFL fantasy bot.

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/classes/{teamId}`
  - Params: `{year}`, `{teamId}` — **confirmed this path 404s** (`{"error": {"message": "application error", "code": 404}}`); tested with year=2025 and several real college team IDs (8=Arkansas, 52) and path variants (`teams/{teamId}/recruiting`, `recruiting/classes/{teamId}`, `seasons/{year}/recruiting/classes/{teamId}`) — all 404. No working equivalent found; per-team recruiting class does not appear to be exposed at this or a nearby path on the live API.
  - Summary: Endpoint fails outright — the documented `classes/{teamId}` resource does not resolve on the live core API for any team/year tried.
  - Returns: Recruiting class by team (NCAAF only) — **fails, 404**, no data returned.
  - Not wired: no NFL equivalent, and the path 404s outright even for NCAAF.

- [ ] `GET https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/{year}/types/2/groups/80/qbr/0`
  - Params: `{year}`; `groups/80` is the NCAAF group ID (NFL uses `groups/1`, above) (confirmed live — 200 OK for year=2025, final segment 0)
  - Summary: Season-total advanced QBR for FBS college quarterbacks (group 80), same metric family and shape as the NFL QBR endpoint above but with a much larger qualified-player pool.
  - Returns: College Football QBR — duplicate shape of the QBR entries above, NCAAF-scoped. Top-level keys: `$ref` (str), `count` (int), `pageIndex`/`pageSize`/`pageCount` (int), `items` (list of {athlete $ref, team $ref, season $ref, splits {id, name, abbreviation, categories: [...]}}). For 2025, `count` was 135 (much larger than the NFL equivalent's count of 3).
  - Not wired: no NFL equivalent — this bot is NFL-fantasy-scoped; the NFL QBR endpoints above are already wired via `get_nfl_qbr_leaders`.
