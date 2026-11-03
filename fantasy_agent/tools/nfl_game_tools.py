"""Real-NFL data scoped to one specific game: result, key plays, odds,
broadcast info, officiating crew, and stat leaders (ESPN's public API),
not fantasy matchups - see fantasy_matchup_tools.py for that.
Resolves team+week into a game id, then pulls CDN/Core API game data."""
from langchain_core.tools import tool

from ..clients.espn_nfl_client import CDN_API, CORE_API, get_json, resolve_event

MAX_TEAMS_PER_CALL = 32


def _dedupe(team_names: list[str]) -> list[str]:
    """Unique team names, order preserved, capped so a bad call can't fan out unbounded."""
    return list(dict.fromkeys(team_names))[:MAX_TEAMS_PER_CALL]


def _game_result_one(team_name: str, week: int) -> str:
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CDN_API}/boxscore", xhr=1, gameId=event_id)
    pkg = data.get("gamepackageJSON", data)
    comp = pkg["header"]["competitions"][0]
    status = comp["status"]["type"]["shortDetail"]
    score_line = ", ".join(
        f"{c['team']['abbreviation']} {c['score']}" for c in comp["competitors"]
    )

    lines = [f"{score_line} ({status})"]
    for team in pkg.get("boxscore", {}).get("teams", []):
        stats = ", ".join(
            f"{s['label']}: {s['displayValue']}" for s in team["statistics"][:5]
        )
        lines.append(f"{team['team']['abbreviation']} - {stats}")
    return "\n".join(lines)


@tool
def get_game_result(team_names: list[str], week: int = 0) -> str:
    """Get the real-NFL score, status, and top team stats for one or more
    teams' games in a given week (defaults to current week). Pass every
    team you need in one call, e.g. team_names=['Cowboys', 'DAL']."""
    return "\n\n".join(_game_result_one(t, week) for t in _dedupe(team_names))


def _game_key_plays_one(team_name: str, week: int) -> str:
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CDN_API}/playbyplay", xhr=1, gameId=event_id)
    pkg = data.get("gamepackageJSON", data)
    plays = pkg.get("scoringPlays", [])
    if not plays:
        return f"No scoring plays yet for '{team_name}'."

    lines = [
        f"Q{p['period']['number']} {p['clock']['displayValue']} - "
        f"{p['team']['displayName']} {p['scoringType']['displayName']}: {p['text']}"
        for p in plays
    ]
    return f"{team_name}:\n" + "\n".join(lines)


@tool
def get_game_key_plays(team_names: list[str], week: int = 0) -> str:
    """Get the scoring plays (touchdowns, field goals, etc.) from one or
    more teams' games in a given week (defaults to current week). Pass
    every team you need in one call, e.g. team_names=['Cowboys', 'DAL']."""
    return "\n\n".join(_game_key_plays_one(t, week) for t in _dedupe(team_names))


def _game_odds_one(team_name: str, week: int) -> str:
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/odds")
    items = data.get("items", [])
    if not items:
        return f"No odds available for '{team_name}''s game."

    lines = [
        f"{o['provider']['name']}: {o['details']}, O/U {o['overUnder']}"
        for o in items
    ]
    return f"{team_name} odds:\n" + "\n".join(lines)


@tool
def get_game_odds(team_names: list[str], week: int = 0) -> str:
    """Get the betting odds (spread, moneyline, over/under) for one or more
    teams' games in a given week (defaults to current week). Pass every
    team you need in one call, e.g. team_names=['Cowboys', 'DAL']."""
    return "\n\n".join(_game_odds_one(t, week) for t in _dedupe(team_names))


def _game_broadcast_one(team_name: str, week: int) -> str:
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/broadcasts")
    items = data.get("items", [])
    if not items:
        return f"No broadcast info available for '{team_name}''s game."

    lines = [
        f"{b.get('station') or b.get('media', {}).get('name', 'Unknown')} "
        f"({b['type']['longName']}, {b['market']['type']})"
        for b in items
    ]
    return f"{team_name} broadcasts:\n" + "\n".join(lines)


@tool
def get_game_broadcast(team_names: list[str], week: int = 0) -> str:
    """Get the TV/streaming broadcast info (network, market) for one or
    more teams' games in a given week (defaults to current week). Pass
    every team you need in one call, e.g. team_names=['Cowboys', 'DAL']."""
    return "\n\n".join(_game_broadcast_one(t, week) for t in _dedupe(team_names))


def _game_officials_one(team_name: str, week: int) -> str:
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/officials")
    items = sorted(data.get("items", []), key=lambda o: o.get("order", 0))
    if not items:
        return f"No officiating crew info available for '{team_name}''s game."

    lines = [f"{o['position']['displayName']}: {o['fullName']}" for o in items]
    return f"{team_name} officials:\n" + "\n".join(lines)


@tool
def get_game_officials(team_names: list[str], week: int = 0) -> str:
    """Get the officiating crew (referee, umpire, etc.) assigned to one or
    more teams' games in a given week (defaults to current week). Pass
    every team you need in one call, e.g. team_names=['Cowboys', 'DAL']."""
    return "\n\n".join(_game_officials_one(t, week) for t in _dedupe(team_names))


def _game_leaders_one(team_name: str, week: int) -> str:
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CDN_API}/matchup", xhr=1, gameId=event_id)
    pkg = data.get("gamepackageJSON", data)
    team_leaders = pkg.get("leaders", [])
    if not team_leaders:
        return f"No leader stats available for '{team_name}''s game."

    lines = []
    for entry in team_leaders:
        lines.append(f"{entry.get('team', {}).get('displayName', 'Unknown')}:")
        for cat in entry.get("leaders", []):
            leader = (cat.get("leaders") or [{}])[0]
            athlete = leader.get("athlete", {}).get("displayName", "Unknown")
            lines.append(f"  {cat['displayName']}: {athlete} - {leader.get('displayValue', '')}")
    return "\n".join(lines)


@tool
def get_game_leaders(team_names: list[str], week: int = 0) -> str:
    """Get each team's statistical leaders (passing/rushing/receiving
    yards, sacks, tackles) for one or more teams' games in a given week
    (defaults to current week). Pass every team you need in one call, e.g.
    team_names=['Cowboys', 'DAL']."""
    return "\n\n".join(_game_leaders_one(t, week) for t in _dedupe(team_names))


TOOLS = [
    get_game_result,
    get_game_key_plays,
    get_game_odds,
    get_game_broadcast,
    get_game_officials,
    get_game_leaders,
]
