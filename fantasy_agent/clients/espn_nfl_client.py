"""HTTP helpers and team/athlete/game lookups for ESPN's public, unauthenticated NFL API.

Endpoint reference: docs/NFL_PUBLIC_API.md
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
    """GET a URL and return its JSON body; raises on non-2xx."""
    resp = requests.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def follow_ref(ref: dict) -> dict:
    """Resolve a Core API {'$ref': url} stub into the full object."""
    return get_json(ref["$ref"])


# All 32 teams, fetched once per process.
_team_cache: list[dict] | None = None


def resolve_team(query: str) -> dict | None:
    """Find a team by abbreviation, then name substring, then fuzzy match (e.g. 'DAL', 'cowboys', 'dalas')."""
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


# Lazily cached rosters for teams actually looked up, instead of prefetching every athlete.
_roster_cache: dict[str, list[dict]] = {}


def resolve_athlete(pro_team: str, player_name: str) -> dict | None:
    """Find a public-API athlete on a team's roster by name (substring, then fuzzy match).

    Bridges fantasy players to public athlete ids, which use a different id space."""
    team = resolve_team(pro_team)
    if team is None:
        return None

    team_id = team["id"]
    if team_id not in _roster_cache:
        roster = get_json(f"{SITE_API}/teams/{team_id}/roster")
        _roster_cache[team_id] = [
            p for group in roster.get("athletes", []) for p in group["items"]
        ]

    q = player_name.strip().lower()
    for p in _roster_cache[team_id]:
        if q == p["fullName"].lower() or q in p["fullName"].lower():
            return p
    names = [p["fullName"].lower() for p in _roster_cache[team_id]]
    match = process.extractOne(q, names, scorer=fuzz.WRatio, score_cutoff=80)
    return _roster_cache[team_id][match[2]] if match else None


def resolve_event(pro_team: str, week: int = 0) -> str | None:
    """Find a team's game id for a week (default current) from the live, uncached scoreboard."""
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
