# ESPN Public NFL API — Runnable Representations

Source: [pseudo-r/Public-ESPN-API — football.md](https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md)
(community-documented, unofficial, undocumented ESPN endpoints — **no API key,
`espn_s2`, or `SWID` required**).

**Different from [`fantasy_espn/`](../fantasy_espn):** that folder wraps the `espn_api`
Python package against *your private fantasy league* (rosters, matchups, waivers — needs
auth). This folder hits ESPN's *public sports-data* API directly over HTTP — real NFL
scores, rosters, injuries, stats, news — useful to enrich fantasy decisions with data the
private fantasy API doesn't expose. For the full endpoint catalogue this folder was built
from, see [`fantasy_espn/NFL_PUBLIC_API_REFERENCE.md`](../fantasy_espn/NFL_PUBLIC_API_REFERENCE.md).

Each script below is a runnable, categorized tour of one cluster of endpoints — same
pattern as `fantasy_espn/01_*.py` through `05_*.py`, but for the public API instead of the
authenticated league API.

| Script | Covers |
|---|---|
| `nfl_client.py` | Shared `get_json()` / `follow_ref()` HTTP helpers + base API URLs (not runnable on its own) |
| `01_scores_schedule_standings.py` | Scoreboard (live/week/date), standings, calendar, seasons, events |
| `02_teams_rosters_depthcharts.py` | Teams, team detail, roster, schedule, leaders, depth charts, injuries (team + league-wide) |
| `03_players_athletes_stats.py` | Athletes list, positions, athlete overview/stats/gamelog/splits, stat leaderboard |
| `04_game_detail_playbyplay.py` | Game summary/boxscore, broadcasts, odds, officials, CDN play-by-play & win probability |
| `05_news_transactions_draft.py` | League/team/athlete news, real-NFL transactions, draft board, free agents |
| `06_rankings_qbr_reference.py` | Rankings, venues, franchises, providers, media, current season, season/weekly QBR |

Run any script directly:

```bash
cd espn_nfl_public
python3 01_scores_schedule_standings.py
```

## Notes / gotchas

- No auth needed anywhere in this folder — all public.
- These are **undocumented** ESPN endpoints (community-reverse-engineered) — no
  uptime/schema guarantee. Scripts print `count=`/key summaries defensively rather than
  assuming every field exists, since payloads vary by time of year (e.g. `qbr`, `rankings`,
  and `odds` are often empty outside the relevant in-season window).
- The Core API (`sports.core.api.espn.com`) list endpoints return `{"$ref": url}` stubs, not
  full objects — use `follow_ref()` from `nfl_client.py` to resolve one when you need the
  full payload.
- Event ID and Competition ID are the same number for NFL games (no multi-competition
  events).
- Rate limiting is undocumented; cache static data (`teams`, `venues`, `positions`) instead
  of re-fetching per request.
