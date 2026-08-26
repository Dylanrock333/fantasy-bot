"""Real-NFL data scoped to one specific game: result, key plays, odds,
broadcast info, officiating crew, and stat leaders (public espn_nfl_public/
API), not fantasy matchups - see fantasy_matchup_tools.py for that.
Resolves team+week into a game id, then pulls CDN/Core API game data."""
from langchain_core.tools import tool

from ..clients.nfl_client import CDN_API, CORE_API, get_json, resolve_event


@tool
def get_game_result(team_name: str, week: int = 0) -> str:
    """Get the real-NFL score, status, and top team stats for one team's
    game in a given week (defaults to current week). team_name e.g.
    'Cowboys' or 'DAL'."""
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
def get_game_key_plays(team_name: str, week: int = 0) -> str:
    """Get the scoring plays (touchdowns, field goals, etc.) from one
    team's game in a given week (defaults to current week). team_name e.g.
    'Cowboys' or 'DAL'."""
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CDN_API}/playbyplay", xhr=1, gameId=event_id)
    pkg = data.get("gamepackageJSON", data)
    plays = pkg.get("scoringPlays", [])
    if not plays:
        return "No scoring plays yet."

    lines = [
        f"Q{p['period']['number']} {p['clock']['displayValue']} - "
        f"{p['team']['displayName']} {p['scoringType']['displayName']}: {p['text']}"
        for p in plays
    ]
    return "\n".join(lines)


@tool
def get_game_odds(team_name: str, week: int = 0) -> str:
    """Get the betting odds (spread, moneyline, over/under) for one team's
    game in a given week (defaults to current week). team_name e.g.
    'Cowboys' or 'DAL'."""
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/odds")
    items = data.get("items", [])
    if not items:
        return "No odds available for this game."

    lines = [
        f"{o['provider']['name']}: {o['details']}, O/U {o['overUnder']}"
        for o in items
    ]
    return "Odds:\n" + "\n".join(lines)


@tool
def get_game_broadcast(team_name: str, week: int = 0) -> str:
    """Get the TV/streaming broadcast info (network, market) for one team's
    game in a given week (defaults to current week). team_name e.g.
    'Cowboys' or 'DAL'."""
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/broadcasts")
    items = data.get("items", [])
    if not items:
        return "No broadcast info available for this game."

    lines = [
        f"{b.get('station') or b.get('media', {}).get('name', 'Unknown')} "
        f"({b['type']['longName']}, {b['market']['type']})"
        for b in items
    ]
    return "Broadcasts:\n" + "\n".join(lines)


@tool
def get_game_officials(team_name: str, week: int = 0) -> str:
    """Get the officiating crew (referee, umpire, etc.) assigned to one
    team's game in a given week (defaults to current week). team_name e.g.
    'Cowboys' or 'DAL'."""
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/officials")
    items = sorted(data.get("items", []), key=lambda o: o.get("order", 0))
    if not items:
        return "No officiating crew info available for this game."

    lines = [f"{o['position']['displayName']}: {o['fullName']}" for o in items]
    return "Officials:\n" + "\n".join(lines)


@tool
def get_game_leaders(team_name: str, week: int = 0) -> str:
    """Get each team's statistical leaders (passing/rushing/receiving
    yards, sacks, tackles) for one team's game in a given week (defaults to
    current week). team_name e.g. 'Cowboys' or 'DAL'."""
    event_id = resolve_event(team_name, week)
    if event_id is None:
        return f"No game found for '{team_name}'" + (f" in week {week}." if week else ".")

    data = get_json(f"{CDN_API}/matchup", xhr=1, gameId=event_id)
    pkg = data.get("gamepackageJSON", data)
    team_leaders = pkg.get("leaders", [])
    if not team_leaders:
        return "No leader stats available for this game."

    lines = []
    for entry in team_leaders:
        lines.append(f"{entry.get('team', {}).get('displayName', 'Unknown')}:")
        for cat in entry.get("leaders", []):
            leader = (cat.get("leaders") or [{}])[0]
            athlete = leader.get("athlete", {}).get("displayName", "Unknown")
            lines.append(f"  {cat['displayName']}: {athlete} - {leader.get('displayValue', '')}")
    return "\n".join(lines)


TOOLS = [
    get_game_result,
    get_game_key_plays,
    get_game_odds,
    get_game_broadcast,
    get_game_officials,
    get_game_leaders,
]
