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
    if match is None:
        return None
    candidate = _roster_cache[team_id][match[2]]
    # WRatio can score two different people highly if they share a last name
    # (e.g. "A.J. Brown" vs "Hollywood Brown") - require the first-name
    # initial to agree too, or treat it as no match.
    if q[0] != candidate["fullName"].strip().lower()[0]:
        return None
    return candidate


def _ensure_all_rosters() -> None:
    """Fill _roster_cache for every team (idempotent)."""
    global _team_cache
    if _team_cache is None:
        resolve_team("")  # populates _team_cache as a side effect
    for team in _team_cache:
        team_id = team["id"]
        if team_id not in _roster_cache:
            roster = get_json(f"{SITE_API}/teams/{team_id}/roster")
            _roster_cache[team_id] = [
                p for group in roster.get("athletes", []) for p in group["items"]
            ]


def resolve_players_anywhere(
    player_names: list[str],
) -> dict[str, tuple[dict, dict] | list[tuple[dict, dict]] | None]:
    """Find each name's athlete + team across all 32 rosters in one pass, no team needed.

    A handful of real players share an exact full name across two teams
    (e.g. two NFL players named "Justin Jefferson") - silently picking one
    would risk returning the wrong person's stats, so an exact name with
    more than one roster hit is returned as a list instead of guessing."""
    _ensure_all_rosters()
    all_players = [
        (p, team)
        for team in _team_cache
        for p in _roster_cache[team["id"]]
    ]
    all_names = [p["fullName"].lower() for p, _ in all_players]

    results: dict[str, tuple[dict, dict] | list[tuple[dict, dict]] | None] = {}
    for name in player_names:
        q = name.strip().lower()
        exact = [pair for pair, n in zip(all_players, all_names) if q == n]
        if len(exact) > 1:
            results[name] = exact
            continue
        hit = exact[0] if exact else next(
            (pair for pair, n in zip(all_players, all_names) if q in n), None
        )
        if hit is None:
            match = process.extractOne(q, all_names, scorer=fuzz.WRatio, score_cutoff=80)
            if match and q[0] == all_names[match[2]][0]:
                hit = all_players[match[2]]
        results[name] = hit
    return results


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
