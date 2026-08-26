# ESPN NFL Public API Checklist — Scores

Part of a 5-way split of
[`NFL_PUBLIC_API_CHECKLIST.md`](../NFL_PUBLIC_API_CHECKLIST.md), clustered to match
[`nfl_scores_tools.py`](../nfl_scores_tools.py). See the main checklist for the full
Placeholders table and Notes/gotchas (not duplicated here). 12 of 72 total checklist items.

Scope: general, league-wide scores/schedule/standings/season data — not scoped to one game
(that split out to the Game checklist).

---

## Site API — `site.api.espn.com`

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}` (unless noted)

- [x] `GET scoreboard`
  - Params: none
  - Summary: Returns the live/current-week NFL scoreboard (defaults to whatever week ESPN considers "now").
  - Returns: `{leagues: list[dict], season: dict, week: dict, events: list[dict], provider: list[dict]}`. `season` is `{type: int, year: int}`, `week` is `{number: int}`. `events` is a list of full game/event objects (not stub refs) — id, name, date, competitions, status, etc. Verified live (2026-08-25): returned preseason week 3 (`season.type=1`, `week.number=3`), 16 events.
  - Wired: `nfl_scores_tools.get_nfl_scoreboard`

- [x] `GET scoreboard?week={week}&seasontype={seasontype}`
  - Params: `week`, `seasontype` (also accepts `year`, e.g. `year=2025`, to pin the season — without it ESPN defaults to the current season)
  - Summary: Returns the scoreboard for one specific week/season-type (e.g. regular season week 1) instead of whatever week is currently live.
  - Returns: Same shape as base `scoreboard`: `{leagues: list[dict], season: dict, week: dict, events: list[dict], provider: list[dict]}`. Verified live with `week=1&seasontype=2&year=2025` — returned `events` for regular-season week 1 of 2025.
  - Wired: folded into `nfl_scores_tools.get_nfl_scoreboard` as optional `week`/`seasontype` args. Re-tested live 2026-08-25: `year` did NOT actually pin an old season (tried `year=2019/2023/2024/2025` combined with `week`/`seasontype` — all returned current-season 2026 events regardless of `year`'s value); only `week`/`seasontype` reliably changed results. Folded `year` out of the tool signature/docstring accordingly — only `week`, `seasontype`, `dates` are exposed.

- [x] `GET scoreboard?dates={YYYYMMDD}`
  - Params: `dates` (format `YYYYMMDD`)
  - Summary: Returns the scoreboard for the week containing a specific calendar date.
  - Returns: Same shape as base `scoreboard`: `{leagues: list[dict], events: list[dict], provider: list[dict], week: dict}` (no top-level `season` key was present in this response, unlike the base/week-scoped calls). Verified live with `dates=20250907` — returned events for that date's week.
  - Wired: folded into `nfl_scores_tools.get_nfl_scoreboard` as optional `dates` arg.

- [x] `GET https://site.api.espn.com/apis/v2/sports/football/nfl/standings`
  - Params: none
  - Summary: Returns full league standings (division/conference records, win %, point differential, etc.) grouped by conference, with no fetch-per-team needed.
  - Returns: `{uid, id, name, abbreviation, shortName, children: list[dict], isConference: bool, season: dict, links: list[dict], seasons: list[dict]}`. `children` (verified 2 entries: AFC/NFC) each is `{uid, id, name, abbreviation, isConference, standings: dict}`, where `standings` is `{id, name, displayName, links, season, seasonType, seasonDisplayName, entries: list[dict]}`. Each `entries[i]` is `{team: dict, stats: list[dict]}` — `stats` is a flat list of stat objects like `{name, displayName, shortDisplayName, description, abbreviation, type, value, displayValue}` (e.g. `differential`, wins, losses, win%, etc). Fully-inlined data — no stub refs. (note different base path — `apis/v2/...`, not `apis/site/v2/...`; the `apis/site/v2/.../standings` variant returns only a stub, so use this URL instead)
  - Wired: `nfl_scores_tools.get_nfl_standings`

## Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>`

- [ ] `GET /calendar`
  - Method ID: `getCalendars`
  - Params: `dates`, `seasontype`, `weeks` (verified live: passing these did not change the shape of the top-level response — it always returns the same 4-item index below; params may only affect the content of the sub-resources it links to)
  - Summary: Returns an index of 4 calendar sub-resources (on-days, off-days, blacklist, whitelist) rather than calendar data itself — each item must be fetched separately to get actual dates/sections.
  - Returns: `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}` where `items` is a list of 4 stub refs (`{$ref: url}`) — no inline data. Verified live: refs point to `/calendar/ondays`, `/calendar/offdays`, `/calendar/blacklist`, `/calendar/whitelist`. Fetching `ondays` returns `{$ref, type, startDate, endDate, eventDate, sections: list[dict], season: dict}` with the actual per-week date ranges.
  - Not wired: raw stub-ref list endpoint (index of 4 refs, no inline data) — no standalone chat value.

- [ ] `GET /seasons`
  - Method ID: `getSeasons`
  - Params: none (supports standard paging params `page`/`limit` implicitly, per the `pageIndex`/`pageSize`/`pageCount` in the response)
  - Summary: Lists all NFL seasons ESPN has on record, as stub references (one per year) rather than full season objects.
  - Returns: `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Verified live: `count=105`, `items` are all `{$ref: url}` stubs pointing at `/seasons/{year}` (e.g. `.../seasons/2026`) — each needs a follow-up fetch for season detail.
  - Not wired: raw stub-ref list endpoint (105 refs, no inline data) — no standalone chat value.

- [ ] `GET /events`
  - Method ID: (not specified)
  - Params: none (accepts paging params `page`/`limit`, per the paging fields in the response; with no date/season params it defaults to the current week's events)
  - Summary: Lists events (games) as stub references, defaulting to the current week — each item needs a follow-up fetch for game details.
  - Returns: `{$meta: dict, count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`. Verified live: `count=16` (matches current preseason week's game count), `items` are all `{$ref: url}` stubs pointing at `/events/{eventId}`.
  - Not wired: raw stub-ref list endpoint (no inline data) — no standalone chat value; `get_nfl_scoreboard` already covers current-week events with full inline data.

- [ ] `GET /season`
  - Method ID: `getCurrentSeason`
  - Params: none required — returns whatever ESPN considers the current season
  - Summary: Returns full detail for the current season, including its current season-type (pre/regular/post) and current week, fully inlined (not a stub).
  - Returns: `{$ref, year: int, startDate: str, endDate: str, displayName: str, type: dict, types: dict($ref), rankings: dict($ref), coaches: dict($ref), athletes: dict($ref), futures: dict($ref), leaders: dict($ref)}`. `type` is inlined with the current season-type detail: `{id, type: int, name, abbreviation, year, startDate, endDate, hasGroups, hasStandings, hasLegs, groups: {$ref}, week: {..., number, startDate, endDate, text, rankings: {$ref}, events: {$ref}}, weeks: {$ref}, corrections: {$ref}, leaders: {$ref}, slug}`. Verified live (2026-08-25): `year=2026`, current type = Preseason (`type=1`), current week = Preseason Week 2 (`number=3`, ESPN's internal week numbering).
  - Not wired: judgment call — skipped as redundant. The current season-type/week it surfaces (`type.type`, `type.week.number`) is the same info already embedded in `get_nfl_scoreboard`'s response (`season.type`, `week.number`) for every call; not enough net-new value over the already-wired scoreboard tool to justify a separate tool.

- [ ] `GET /standings`
  - Method ID: (not specified)
  - Params: none required — resolves to the current season's default standings group
  - Summary: Redirects (via a single `$ref`) to the current season/season-type's default standings group rather than returning standings data directly — a third variant, distinct from both Site API standings entries above, and the least convenient (needs 2+ follow-up fetches to reach actual entries).
  - Returns: A single stub object `{$ref: url}` pointing at `/seasons/{year}/types/{n}/groups/{groupId}/standings` (verified live: resolved to `.../seasons/2026/types/1/groups/9/standings`). Fetching that ref returns `{count, pageIndex, pageSize, pageCount, items: list[dict]}` where `items` are themselves stub refs like `{$ref, id, name: "overall", displayName: "Standings", links}` (4 items seen) — each needs yet another fetch to reach the actual entries/stats seen in the Site API standings endpoint above.
  - Not wired: too indirect (3+ follow-up fetches to reach actual entries/stats) vs the Site API `standings` variant, which is fully inlined and already wired as `get_nfl_standings`.

- [ ] `GET /tournaments`
  - Method ID: `getTournaments`
  - Params: `majorsOnly`, `page`, `limit` — irrelevant for NFL; the call fails regardless of params
  - Summary: Not applicable to football — this method exists on the generic Core API but ESPN explicitly rejects it for the NFL league.
  - Returns: FAILS. Verified live: `GET /tournaments` returns HTTP 200 with body `{"error": {"message": "getTournaments() not supported for football/nfl", "code": 400}}`. Do not use for NFL.
  - Not wired: unsupported for NFL (400 error body), unusable.

- [ ] `GET /v3/sports/{sport}/{league}/seasons/{season}`
  - Method ID: `getSeason`
  - Params: large generic set incl. `page`, `limit`, `lang`, `region`, `season` — many params are cross-sport/inherited and won't apply to football; in practice only the path params (`{sport}=football`, `{league}=nfl`, `{season}=2025` or `2026`) are needed
  - Summary: A minimal, sport-agnostic lookup of a season's start/end dates — much less detailed than the v2 Core API `/season`/`/seasons/{year}` endpoints.
  - Returns: `{year: int, startDate: str, endDate: str}` only — no `type`, `week`, or nested refs. Verified live for both `.../nfl/seasons/2026` (`{"year":2026,"startDate":"2026-08-06T07:00Z","endDate":"2027-08-01T06:59Z"}`) and `.../nfl/seasons/2025` (same shape) — V3 generic endpoint, base `https://sports.core.api.espn.com/v3/sports/football`, use `{league}=nfl`
  - Not wired: thinner duplicate of the Core API v2 `/season` endpoint above (just start/end dates, no type/week detail), which itself was skipped as redundant with `get_nfl_scoreboard`.

## CDN Game Data — `cdn.espn.com`

- [ ] `GET core/nfl/scoreboard?xhr=1`
  - Params: `xhr=1` (required — without it the CDN returns a rendered HTML page instead of JSON)
  - Summary: Returns the full ESPN.com NFL scoreboard page's data payload (news, ads/analytics metadata, nav, and the scoreboard itself) — much heavier than the Site API scoreboard since it's the same data that backs the website page, not a purpose-built API response.
  - Returns: `{news: dict, pinnedCount: int, nowFeedMD5Hash: str, type: str, content: dict, analytics: dict, nowFeed: ..., ads: dict, nowFeedCount: int, meta: dict, nowFeedSupported: bool, sport: str, tier2Nav: ...}` — verified live, ~345KB response. The actual scores live at `content.sbData`, which mirrors the Site API scoreboard shape: `{week: dict, leagues: list[dict], provider: list[dict], season: dict, events: list[dict]}` (16 events seen, matching current week). `content` also carries page-rendering fields (`sbGroup`, `isWeekOriented`, `dateParams`, `calendar`, `defaults`, `title`, `description`, `og_type`, `canonical`) not present in the Site API response.
  - Not wired: heavier duplicate (~345KB, mostly page-rendering/ads/nav noise) of the already-wired, purpose-built `get_nfl_scoreboard` (Site API), which returns the same `events` data far more cheaply — no net-new value.
