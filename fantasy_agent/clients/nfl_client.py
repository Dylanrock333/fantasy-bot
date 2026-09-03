"""Shared HTTP helper for ESPN's public (unauthenticated) NFL data API.

Vendored from espn_nfl_public/nfl_client.py so fantasy_agent/ has no
cross-package import and can be deployed standalone (e.g. as a Discord bot)
without the espn_nfl_public/ reference scripts. Mirror changes there if the
upstream client changes.

Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md
No API key, espn_s2, or SWID required — contrast with fantasy_espn/espn_client.py,
which authenticates against your private fantasy league.
"""
import requests
from rapidfuzz import fuzz, process

SITE_API = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
SITE_API_STANDINGS = "https://site.api.espn.com/apis/v2/sports/football/nfl"
CORE_API = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
ATHLETE_API = "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl"
CDN_API = "https://cdn.espn.com/core/nfl"

TIMEOUT = 10


def get_json(url: str, **params) -> dict:
    """GET a URL and return the parsed JSON body. Raises on non-2xx."""
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def follow_ref(ref: dict) -> dict:
    """Core API list endpoints return {'$ref': url} stubs instead of full
    objects. Resolve one by re-fetching its $ref."""
    return get_json(ref["$ref"])


_team_cache: list[dict] | None = None


def resolve_team(query: str) -> dict | None:
    """Look up a team by name/city/abbreviation (case-insensitive substring
    match, falling back to fuzzy matching for typos), e.g. 'cowboys', 'DAL',
    'dallas', or a misspelling like 'dalas'. Caches the team list for the
    process lifetime since it's static within a season (32 teams total)."""
    global _team_cache
    if _team_cache is None:
        teams = get_json(f"{SITE_API}/teams")
        _team_cache = [t["team"] for t in teams["sports"][0]["leagues"][0]["teams"]]

    q = query.strip().lower()
    for team in _team_cache:
        if q == team["abbreviation"].lower():
            return team
    for team in _team_cache:
        if q in team["displayName"].lower():
            return team
    names = [team["displayName"].lower() for team in _team_cache]
    match = process.extractOne(q, names, scorer=fuzz.WRatio, score_cutoff=70)
    return _team_cache[match[2]] if match else None


# Per-team roster cache, populated lazily (only for teams actually looked
# up) rather than prefetching the full ~1700-athlete player pool. Fantasy
# roster tools already return each player's proTeam, so resolving one
# player only ever requires fetching that one team's ~53-man roster.
_roster_cache: dict[str, list[dict]] = {}


def _roster_from_depth_chart(team_id: str) -> list[dict]:
    """Fallback for teams whose /roster endpoint 404s on ESPN's side (seen
    live for the Cardinals, team id 22) - the depth chart lists the same
    athletes with the same public ids under a separate, working endpoint."""
    depth = get_json(f"{SITE_API}/teams/{team_id}/depthcharts")
    seen: dict[str, dict] = {}
    for formation in depth.get("depthchart", []):
        for info in formation.get("positions", {}).values():
            for a in info.get("athletes", []):
                seen[a["id"]] = {"id": a["id"], "fullName": a.get("displayName", "")}
    return list(seen.values())


def resolve_athlete(pro_team: str, player_name: str) -> dict | None:
    """Look up a real-NFL athlete's public-API id by team + name (substring
    match, falling back to fuzzy matching for typos), e.g. pro_team='DAL',
    player_name='Dak Prescott' or a misspelling like 'Dak Prescot'. The
    public athlete id is a different id space than the fantasy playerId
    from espn_api - this is the only reliable way to bridge the two
    without a full player cache."""
    team = resolve_team(pro_team)
    if team is None:
        return None

    team_id = team["id"]
    if team_id not in _roster_cache:
        try:
            roster = get_json(f"{SITE_API}/teams/{team_id}/roster")
            _roster_cache[team_id] = [
                p for group in roster.get("athletes", []) for p in group["items"]
            ]
        except requests.exceptions.HTTPError:
            _roster_cache[team_id] = _roster_from_depth_chart(team_id)

    q = player_name.strip().lower()
    for p in _roster_cache[team_id]:
        if q == p["fullName"].lower() or q in p["fullName"].lower():
            return p
    names = [p["fullName"].lower() for p in _roster_cache[team_id]]
    match = process.extractOne(q, names, scorer=fuzz.WRatio, score_cutoff=80)
    return _roster_cache[team_id][match[2]] if match else None


def resolve_event(pro_team: str, week: int = 0) -> str | None:
    """Look up a real-NFL game id for one team's game in a given week
    (defaults to current week). Not cached - scores/status change live
    during a game, unlike the mostly-static team/roster lookups above."""
    team = resolve_team(pro_team)
    if team is None:
        return None

    params = {"week": week} if week else {}
    sb = get_json(f"{SITE_API}/scoreboard", **params)
    for event in sb.get("events", []):
        comp = event["competitions"][0]
        if any(c["team"]["id"] == team["id"] for c in comp["competitors"]):
            return event["id"]
    return None
