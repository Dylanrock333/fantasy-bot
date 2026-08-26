"""Shared HTTP helper for ESPN's public (unauthenticated) NFL data API.

Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/football.md
No API key, espn_s2, or SWID required — contrast with fantasy_espn/espn_client.py,
which authenticates against your private fantasy league.
"""
import requests

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
    match), e.g. 'cowboys', 'DAL', 'dallas'. Caches the team list for the
    process lifetime since it's static within a season."""
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
    return None
