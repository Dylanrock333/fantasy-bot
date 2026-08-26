# ESPN NFL Public API Checklist — News

Part of a 5-way split of
[`NFL_PUBLIC_API_CHECKLIST.md`](../NFL_PUBLIC_API_CHECKLIST.md), clustered to match
[`nfl_news_tools.py`](../nfl_news_tools.py). See the main checklist for the full
Placeholders table and Notes/gotchas (not duplicated here). 8 of 72 total checklist items.

Scope: headlines, transactions, the draft, and free agents.

---

## Site API — `site.api.espn.com`

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}`

- [x] `GET news`
  - Params: none
  - Summary: Returns the latest league-wide NFL headlines shown on ESPN's NFL news feed.
  - Returns: JSON object — `header` (str), `link` (dict, 7 keys), `articles` (list, 6 items each with `id`, `nowId`, `contentKey`, `dataSourceIdentifier`, `type`, `headline`, `description`, `lastModified`, `published`, `images`, `categories`, `byline`, `links`, `premium`)
  - Wired: `nfl_news_tools.get_nfl_news`

- [ ] `GET teams/{id}/news`
  - Params: `{id}` (team ID)
  - Summary: Intended to return team-specific news, but live-tested against team 6 (Cowboys) and two other teams (12, 2) it consistently returns an empty response — endpoint appears broken/deprecated.
  - Returns: HTTP 200 with body `{}` (empty JSON object, no keys) for every team ID tried — no `articles` or other data observed.
  - Not wired: dead endpoint, always returns `{}` — no data to expose.

- [ ] `GET athletes/{id}/news`
  - Params: `{id}` (athlete ID)
  - Summary: Intended to return athlete-specific news; live-tested against Israel Abanikanda (4429202), CeeDee Lamb (4241389), and Dak Prescott (2577417) — request succeeds (HTTP 200) but the `articles` list is always empty, even for a starting QB.
  - Returns: JSON object — `header` (str, e.g. `"{0} News"` — note the unsubstituted `{0}` placeholder in the response itself), `articles` (list, always empty `[]` in testing).
  - Not wired: `articles` list is always empty — no data to expose.

- [x] `GET transactions`
  - Params: `limit` (page size, e.g. `limit=5`), `page` (page number, e.g. `page=2`) — both confirmed working; no other params tested
  - Summary: Returns a paginated, league-wide feed of real NFL roster transactions (signings, trades, waivers, IR moves, etc.), newest first.
  - Returns: JSON object — `timestamp` (str), `status` (str), `season` (dict, 4 keys), `requestedYear` (dict, 2 keys), `count` (int, e.g. 1282 total), `pageIndex` (int), `pageSize` (int, default 25), `pageCount` (int), `transactions` (list of dicts, each with `date`, `description`, `team` (dict with id/location/name/abbreviation/logos/etc.))
  - Wired: `nfl_news_tools.get_nfl_transactions`

- [x] `GET draft`
  - Params: none (defaults to current draft year, 2026)
  - Summary: Returns the full NFL draft board — all picks across all rounds for the current draft year, with each pick's prospect/athlete info.
  - Returns: JSON object — `broadcasts` (list, 4 items), `displayName` (str, e.g. "2026 National Football League Draft"), `picks` (list, 257 items, each with `athlete`, `overall`, `pick`, `round`, `status`, `teamId`, `tradeNote`, `traded`), `positions` (list, 16), `rounds` (int, 7), `shortDisplayName` (str), `status` (dict, 4 keys), `teams` (list, 32), `uid` (str), `year` (int)
  - Wired: `nfl_news_tools.get_nfl_draft`

## Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>`

- [ ] `GET /seasons/{year}/draft`
  - Method ID: `getDraftByYear`
  - Params: `{year}` (confirmed, e.g. `2026`). `position` and `team` do NOT work as query params on this endpoint — `?position=QB` returns HTTP 404 `{"error": {...}}`, and `?team=6` is silently ignored (identical response to no filter). Filtering by position/team must be done client-side, or via the separate `rounds`/`athletes` sub-resources.
  - Summary: Returns metadata and $ref-linked sub-collections for a given NFL draft year (this is the Core API's version of the draft, distinct from the flatter Site API `draft` endpoint above — picks are not inlined here, they're behind the `rounds`/`athletes` $refs).
  - Returns: JSON object — `$ref` (str), `uid` (str), `year` (int), `numberOfRounds` (int, 7), `displayName` (str), `shortDisplayName` (str), `status` (dict, 1 key), `athletes` (dict — `$ref` link to `/draft/athletes` collection, 689 items when resolved), `rounds` (dict — `$ref` link to `/draft/rounds` collection, 7 items when resolved), `positions` (list, 16), `needs` (list, 32), `broadcasts` (list, 4), `links` (list, 1), `startDate` (str), `endDate` (str)
  - Not wired: adds nothing the Site API `draft` doesn't already give inline (picks are behind `$ref` sub-collections here instead of being inline), and its position/team filter params are broken (404 / silently ignored) — Site API `draft` is wired instead, see above.

- [ ] `GET /seasons/{year}/freeagents`
  - Method ID: `getFreeAgents`
  - Params: `{year}` (accepted without error, but has no observed effect — see below)
  - Summary: Intended to return real NFL free agents for a given year, but live-tested against 2026, 2025, 2024, 2023, and 2022 it returns zero items for every year tried — endpoint appears unpopulated/non-functional on the public API.
  - Returns: JSON object — `count` (int, always 0 in testing), `pageIndex` (int), `pageSize` (int, 25), `pageCount` (int, 0), `items` (list, always empty `[]`)
  - Not wired: always 0 items across every year tested — no data to expose.

- [ ] `GET /media`
  - Method ID: `getMedia`
  - Params: `limit` (page size, confirmed working, e.g. `limit=5`). No year/team/athlete scoping observed or needed.
  - Summary: Not news media/video content as the name suggests — this is a paginated directory of TV/radio broadcast outlets and affiliate stations (e.g. "ABC", "3TV", "ABC BALTIMORE") used elsewhere to label game broadcasts.
  - Returns: Top level — JSON object with `count` (int, 1310), `pageIndex` (int), `pageSize` (int, 25), `pageCount` (int, 53), `items` (list of `{"$ref": ...}` links, one per outlet). Each resolved item (e.g. `/media/0`) is an object — `$ref` (str), `id` (str), `threeLetterAbbreviation` (str), `name` (str), `shortName` (str), `slug` (str).
  - Not wired: broadcast-station directory, not news content — no standalone chat value.
