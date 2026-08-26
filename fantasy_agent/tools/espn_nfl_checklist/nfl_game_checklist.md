# ESPN NFL Public API Checklist — Game

Part of a 5-way split of
[`NFL_PUBLIC_API_CHECKLIST.md`](../NFL_PUBLIC_API_CHECKLIST.md), clustered to match
[`nfl_game_tools.py`](../nfl_game_tools.py). See the main checklist for the full
Placeholders table and Notes/gotchas (not duplicated here). 12 of 72 total checklist items.

Scope: everything scoped to **one specific game/event** — summary, competition sub-resources
(odds, officials, broadcasts, per-team, per-play personnel), and CDN game internals
(boxscore, play-by-play, matchup page). Split out from Scores, which is general/league-wide.

---

## Site API — `site.api.espn.com`

Base: `https://site.api.espn.com/apis/site/v2/sports/football/nfl/{resource}`

- [ ] `GET summary?event={event}`
  - Params: `event` (required, numeric event/game ID)
  - Summary: Returns the full "gamecast" page payload for one NFL game — boxscore, drives, scoring plays, win probability, pickcenter odds, injuries, and news — the same data ESPN's own game page uses. Verified with `event=401873286` (Raiders @ Texans, final).
  - Returns: `{boxscore: dict, format: dict, gameInfo: dict, drives: dict, leaders: list[dict], injuries: list[dict], broadcasts: list[dict], pickcenter: list[dict], odds: list[dict], againstTheSpread: list[dict], scoringPlays: list[dict], news: dict, winprobability: list[dict], header: dict, article: dict, videos: list[dict], wallclockAvailable: bool, meta: dict, standings: dict}`. `broadcasts`/`odds`/`videos` were empty lists for the tested game (can vary by game/network).
  - Not wired: redundant kitchen-sink bundle — its boxscore is already `get_game_result`, its scoring plays are already `get_game_key_plays`, and its odds/broadcasts/injuries are each better served by a dedicated Core API tool (`get_game_odds`, `get_game_broadcast`, existing `nfl_team_tools.get_team_injuries`) with a cleaner single-purpose shape.

## Core API v2 — `sports.core.api.espn.com`

Base: `https://sports.core.api.espn.com/v2/sports/football/leagues/nfl<sub-path>`

- [ ] `GET /events/{event}`
  - Method ID: `getEvent`
  - Params: `{event}` (numeric event ID, in the URL path)
  - Summary: Returns the core-API "event" resource for one game — mostly identity fields (name/date/season/week) plus a nested `competitions` list and `$ref` links out to venue, league, and related resources; it's a much thinner object than the site-API `summary` endpoint (no boxscore/plays inline).
  - Returns: `{$ref: str, id: str, uid: str, date: str, name: str, shortName: str, season: dict, seasonType: dict, week: dict, timeValid: bool, competitions: list[dict], links: list[dict], venues: list[dict], league: dict}`
  - Not wired: pure identity metadata (id/date/season/week) with no boxscore/stats/odds content — no standalone chat question this answers that isn't already answered by `resolve_event`'s internal lookup or the richer wired endpoints.

- [ ] `GET /events/{event}/competitions/{competition}`
  - Method ID: `getCompetition`
  - Params: `{event}`, `{competition}` (same ID as event for NFL) — confirmed both required and that `{competition}` equal to `{event}` works
  - Summary: Returns the full "competition" object for one game — status, attendance, embedded `competitors` (with per-team score/roster/stats sub-refs), a large set of `*Available` capability flags, and `$ref` pointers out to broadcasts/odds/officials/drives/leaders/situation/venue sub-resources rather than embedding them inline.
  - Returns: `{$ref: str, id: str, uid: str, date: str, attendance: int, guid: str, competitors: list[dict] (len 2, each has id/uid/homeAway/winner/order plus $ref links for team/score/linescores/roster/statistics/leaders/record), status: {$ref}, situation: {$ref}, venue: {$ref}, broadcasts: {$ref}, odds: {$ref}, officials: {$ref}, drives: {$ref}, leaders: {$ref}, probabilities: {$ref}, details: {$ref}, relevancy: {$ref}, format: dict, type: dict, gameSource: dict, statsSource: dict, linescoreSource: dict, playByPlaySource: dict, boxscoreSource: dict, links: list[dict], notes: list, neutralSite/conferenceCompetition/divisionCompetition/recent/onWatchESPN/dateValid/timeValid: bool, boxscoreAvailable/playByPlayAvailable/pickcenterAvailable/gamecastAvailable/summaryAvailable/liveAvailable/lineupAvailable/highlightsAvailable/recapAvailable/previewAvailable/shotChartAvailable/ticketsAvailable/wallclockAvailable/bracketAvailable/commentaryAvailable/conversationAvailable/possessionArrowAvailable/timeoutsAvailable/hasDefensiveStats: bool}`
  - Not wired: almost entirely `$ref` pointers and boolean capability flags, nothing embedded inline worth surfacing in chat — every sub-resource it points to (broadcasts/odds/officials) is already reachable directly and wired below.

- [x] `GET /events/{event}/competitions/{competition}/broadcasts`
  - Method ID: `getBroadcasts`
  - Params: `{event}`, `{competition}` — confirmed working
  - Summary: Returns the paginated list of TV/streaming broadcasters (network, channel, region, language) carrying the game.
  - Returns: `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`; each item: `{type: dict, market: str, media: dict, lang: str, region: str, station: str?, channel: str?, priority: int, slug: str, partnered: bool}`. Tested game had `count: 3`.
  - Wired: `nfl_game_tools.get_game_broadcast`

- [ ] `GET /events/{event}/competitions/{competition}/competitors/{competitor}`
  - Method ID: `getCompetitor`
  - Params: `{event}`, `{competition}`, `{competitor}` (team ID as it appears in this game's `competitors` list, e.g. `34`/`13`, not the global team ID lookup path) — confirmed working
  - Summary: Returns one team's participation record for this specific game — home/away, win/loss, and `$ref` pointers to that team's score/linescores/roster/statistics/leaders/record for the game (no stats embedded inline; must be dereferenced separately).
  - Returns: `{$ref: str, id: str, uid: str, type: str, order: int, homeAway: str, winner: bool, team: {$ref}, score: {$ref}, linescores: {$ref}, roster: {$ref}, statistics: {$ref}, leaders: {$ref}, record: {$ref}}`
  - Not wired: entirely `$ref` pointers, nothing embedded inline — same "pure metadata" case as `getEvent`/`getCompetition` above; every sub-resource it points to (score/roster/statistics/leaders/record) would need a separate dereference call, and the ones worth surfacing standalone are already wired via other endpoints.

- [x] `GET /events/{event}/competitions/{competition}/odds`
  - Method ID: `getCompetitionOdds`
  - Params: `{event}`, `{competition}` — confirmed working
  - Summary: Returns the paginated list of betting-market odds (spread, moneyline, over/under, prop bets) for the game, one item per provider (e.g. ESPN BET).
  - Returns: `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`; each item: `{$ref: str, provider: dict, details: str, overUnder: float, spread: float, overOdds/underOdds: float, moneylineWinner: bool, spreadWinner: bool, awayTeamOdds: dict, homeTeamOdds: dict, open: dict, close: dict, current: dict, propBets: list}`. Tested game had `count: 1`.
  - Wired: `nfl_game_tools.get_game_odds`

- [x] `GET /events/{event}/competitions/{competition}/officials`
  - Method ID: `getOfficials`
  - Params: `{event}`, `{competition}` — confirmed working
  - Summary: Returns the paginated list of the game's officiating crew (referee, umpire, etc.) with names and their assigned position/role.
  - Returns: `{count: int, pageIndex: int, pageSize: int, pageCount: int, items: list[dict]}`; each item: `{$ref: str, id: str, order: int, firstName: str, lastName: str, fullName: str, displayName: str, position: dict}`. Tested game had `count: 7`.
  - Wired: `nfl_game_tools.get_game_officials`

- [ ] `GET /events/{event}/competitions/{competition}/plays/{play}/personnel`
  - Method ID: `getPersonnel`
  - Params: `{event}`, `{competition}`, `{play}` (real play IDs pulled from the CDN playbyplay `drives.previous[].plays[].id`)
  - Summary: Intended to return on-field personnel for a specific play, but the endpoint is currently broken — it consistently returns a server error, so it cannot be relied on.
  - Returns: **Fails.** Tested with 6+ distinct real play IDs across two different completed games (`401873286` preseason 2026, `401772830` regular-season 2025) and every call returned `HTTP 500` with body `{"error": {"message": "application error", "code": 500}}`. By contrast, `GET .../plays/{play}` (no `/personnel` suffix) works fine and returns a play object with a `participants: list[dict]` field (athlete/position/order/type refs) that already covers most "who was involved" needs — that may be the intended substitute.
  - Not wired: confirmed broken (HTTP 500 on every play tried, prior research) — pre-emptive skip, not re-attempted.

## CDN Game Data — `cdn.espn.com`

All endpoints require `?xhr=1`. Payload lives under `gamepackageJSON`.

- [ ] `GET core/nfl/game?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId` — confirmed both required
  - Summary: Returns ESPN's full server-rendered "gamecast" page data bundle for the game (the same JSON that hydrates the web page), with the actual game data nested under `gamepackageJSON`.
  - Returns: top level `{__gamepackage__: dict, ads: dict, analytics: dict, content: dict, customNav: dict, customStyleSheet: dict, gameId: str, gamepackageJSON: dict, meta: dict, nowFeedSupported: bool, sport: str, targeting: dict, tier2Nav: dict, type: str}`. `gamepackageJSON` (the useful payload) = `{article: dict, boxscore: dict, broadcasts: list[dict], drives: dict, gameInfo: dict, header: dict, leaders: list[dict], news: dict, pickcenter: list[dict], scoringPlays: list[dict], standings: dict, videos: list[dict], winprobability: list[dict]}` — this is the broadest of the four CDN variants (includes `drives`, `gameInfo`, `leaders`, `article`, `pickcenter`, `scoringPlays` that `boxscore`/`matchup` variants omit).
  - Not wired: kitchen-sink superset with no unique content — `boxscore` is already `get_game_result`, `drives`/`scoringPlays` are already `get_game_key_plays` (via `playbyplay`), and `leaders` is already `get_game_leaders` (via `matchup`); nothing here justifies a 4th CDN game variant.

- [x] `GET core/nfl/boxscore?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId` — confirmed both required
  - Summary: Returns a trimmed version of the gamecast page bundle focused on the final/current boxscore, header, and standings, dropping the play-by-play/drives/leaders/article content the `game` variant includes.
  - Returns: top level same envelope as `core/nfl/game` (`{__gamepackage__, ads, analytics, content, customNav, customStyleSheet, gameId, gamepackageJSON, meta, nowFeedSupported, sport, targeting, tier2Nav, type}`). `gamepackageJSON` = `{boxscore: dict, broadcasts: list[dict], header: dict, news: dict, standings: dict, videos: list[dict], winprobability: list[dict]}`.
  - Wired: `nfl_game_tools.get_game_result`

- [x] `GET core/nfl/playbyplay?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId` — confirmed both required
  - Summary: Returns the gamecast bundle with the full drive-by-drive play-by-play included; each drive contains an ordered list of individual plays (with clock, down/distance-ish text, participants, and a numeric play `id` usable for other per-play calls).
  - Returns: top level same envelope as `core/nfl/game`. `gamepackageJSON` = `{boxscore: dict, broadcasts: list[dict], drives: dict, header: dict, news: dict, scoringPlays: list[dict], standings: dict, videos: list[dict], winprobability: list[dict]}`. `drives` = `{previous: list[dict]}` where each drive dict has `{id, description, displayResult, shortDisplayResult, result, isScore: bool, team: dict, start: dict, end: dict, timeElapsed: dict, yards: int, offensivePlays: int, plays: list[dict]}`, and each play dict has `{id: str, sequenceNumber: str, type: dict, text: str, awayScore/homeScore: int, period: int, clock: dict, scoringPlay: bool, statYardage: int, isPenalty: bool, isTurnover: bool, teamParticipants: list[dict], start/end: dict, wallclock: str, modified: str, priority: bool}`. Verified game had 25 drives / 180 plays total; `nfl_game_tools` currently only extracts scoring plays from this, but the full drive/play detail is present.
  - Wired: `nfl_game_tools.get_game_key_plays`

- [x] `GET core/nfl/matchup?xhr=1&gameId={event}`
  - Params: `xhr=1`, `gameId` — confirmed both required; works even for a completed game (not exclusively pre-game), returning the same boxscore/header data as the other variants
  - Summary: Returns the gamecast bundle trimmed to the matchup/preview-style view — team leaders, betting pickcenter, and game info, but (unlike `playbyplay`/`game`) no `drives` or `scoringPlays`.
  - Returns: top level same envelope as `core/nfl/game`. `gamepackageJSON` = `{boxscore: dict, broadcasts: list[dict], gameInfo: dict, header: dict, leaders: list[dict], news: dict, pickcenter: list[dict], standings: dict, winprobability: list[dict]}`.
  - Wired: `nfl_game_tools.get_game_leaders`
