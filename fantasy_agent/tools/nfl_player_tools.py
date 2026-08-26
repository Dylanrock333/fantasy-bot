"""Real-NFL data: individual athlete stats, career/game-log/split detail,
league-wide statistical leaders, and QBR rankings (public espn_nfl_public/
API, not fantasy players/points - see fantasy_player_tools.py for that).
Cross-refs a fantasy roster player against real-world performance, e.g. for
"who should I start" or "compare my roster to theirs" questions."""
from datetime import datetime

from langchain_core.tools import tool

from ..clients.nfl_client import (
    ATHLETE_API,
    CORE_API,
    SITE_API,
    follow_ref,
    get_json,
    resolve_athlete,
)


@tool
def get_nfl_player_summary(player_name: str, pro_team: str) -> str:
    """Get a real-NFL player's season stats summary. pro_team is that
    player's real NFL team abbreviation or name (e.g. 'DAL' or 'Cowboys') -
    get it from the player's proTeam field in a fantasy roster tool result
    first; this tool cannot search by name alone."""
    athlete = resolve_athlete(pro_team, player_name)
    if athlete is None:
        return f"No NFL player matched '{player_name}' on team '{pro_team}'."

    overview = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/overview")
    stats = overview.get("statistics", {})
    names = stats.get("displayNames", [])
    splits = stats.get("splits", [])
    season = next((s for s in splits if s["displayName"] == "Regular Season"), None)
    if not season:
        return f"{athlete['fullName']} ({pro_team}): no season stats available yet."

    lines = [f"{n}: {v}" for n, v in list(zip(names, season["stats"]))[:8]]
    return f"{athlete['fullName']} ({pro_team}) season stats:\n" + "\n".join(lines)


@tool
def get_nfl_player_career_stats(player_name: str, pro_team: str) -> str:
    """Get a real-NFL player's career statistics broken out by category
    (passing, rushing, receiving, etc.), most recent season first. pro_team
    is that player's real NFL team abbreviation or name (e.g. 'DAL' or
    'Cowboys') - get it from the player's proTeam field in a fantasy roster
    tool result first; this tool cannot search by name alone."""
    athlete = resolve_athlete(pro_team, player_name)
    if athlete is None:
        return f"No NFL player matched '{player_name}' on team '{pro_team}'."

    data = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/stats")
    categories = data.get("categories", [])
    lines = []
    for cat in categories:
        stints = cat.get("statistics", [])
        if not stints:
            continue
        latest = stints[-1]
        year = latest.get("season", {}).get("year", "?")
        pairs = list(zip(cat.get("labels", []), latest.get("stats", [])))[:6]
        stat_str = ", ".join(f"{k}: {v}" for k, v in pairs)
        lines.append(f"{cat['displayName']} ({year}): {stat_str}")
    if not lines:
        return f"No career stats available for {athlete['fullName']}."
    return f"{athlete['fullName']} ({pro_team}) career stats by category:\n" + "\n".join(lines)


@tool
def get_nfl_player_gamelog(player_name: str, pro_team: str, num_games: int = 5) -> str:
    """Get a real-NFL player's game-by-game stat log for their most recent
    games this season, most recent first. pro_team is that player's real NFL
    team abbreviation or name (e.g. 'DAL' or 'Cowboys') - get it from the
    player's proTeam field in a fantasy roster tool result first; this tool
    cannot search by name alone."""
    athlete = resolve_athlete(pro_team, player_name)
    if athlete is None:
        return f"No NFL player matched '{player_name}' on team '{pro_team}'."

    data = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/gamelog")
    season_types = data.get("seasonTypes", [])
    events_map = data.get("events", {})
    display_names = data.get("displayNames", [])
    game_entries = []
    for st in season_types:
        for cat in st.get("categories", []):
            game_entries.extend(cat.get("events", []))

    if not game_entries:
        return f"No game log available for {athlete['fullName']} this season."

    lines = []
    for entry in game_entries[:num_games]:
        ev = events_map.get(entry["eventId"], {})
        opp = ev.get("opponent", {}).get("abbreviation", "?")
        at_vs = ev.get("atVs", "vs")
        week = ev.get("week", "?")
        result = ev.get("gameResult", "")
        score = ev.get("score", "")
        pairs = list(zip(display_names, entry.get("stats", [])))[:5]
        stat_str = ", ".join(f"{n}: {v}" for n, v in pairs)
        lines.append(f"Week {week} {at_vs}{opp} ({result} {score}): {stat_str}")
    return f"{athlete['fullName']} ({pro_team}) recent games:\n" + "\n".join(lines)


@tool
def get_nfl_player_splits(player_name: str, pro_team: str) -> str:
    """Get a real-NFL player's season stat splits (e.g. All/Home/Away), one
    line per split. pro_team is that player's real NFL team abbreviation or
    name (e.g. 'DAL' or 'Cowboys') - get it from the player's proTeam field
    in a fantasy roster tool result first; this tool cannot search by name
    alone."""
    athlete = resolve_athlete(pro_team, player_name)
    if athlete is None:
        return f"No NFL player matched '{player_name}' on team '{pro_team}'."

    data = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/splits")
    split_categories = data.get("splitCategories", [])
    if not split_categories:
        return f"No split stats available for {athlete['fullName']}."

    display_names = data.get("displayNames", [])
    splits = split_categories[0].get("splits", [])
    if not splits:
        return f"No split stats available for {athlete['fullName']}."

    lines = []
    for s in splits:
        pairs = list(zip(display_names, s.get("stats", [])))[:5]
        stat_str = ", ".join(f"{n}: {v}" for n, v in pairs)
        lines.append(f"{s['displayName']}: {stat_str}")
    label = data.get("displayName", "Season")
    return f"{athlete['fullName']} ({pro_team}) {label} splits:\n" + "\n".join(lines)


@tool
def get_nfl_stat_leaders(category: str = "") -> str:
    """Get real-NFL statistical leaders for the current season (top player
    per stat category, e.g. passing yards, rushing yards, receiving yards).
    category optionally filters to one stat by name/abbreviation, e.g.
    'passing yards' or 'rushingYards' - leave blank to list leaders across
    all categories."""
    data = get_json(f"{SITE_API}/statistics")
    categories = data.get("stats", {}).get("categories", [])
    if category:
        q = category.strip().lower()
        categories = [
            c for c in categories
            if q in c["name"].lower() or q in c["displayName"].lower()
        ]
    if not categories:
        return f"No stat category matched '{category}'."

    lines = []
    for cat in categories:
        leaders = cat.get("leaders", [])
        if not leaders:
            continue
        top = leaders[0]
        lines.append(f"{cat['displayName']}: {top['athlete']['displayName']} ({top['displayValue']})")
    if not lines:
        return "No statistical leaders available."
    return "NFL statistical leaders:\n" + "\n".join(lines)


@tool
def get_nfl_qbr_leaders(week: int = 0) -> str:
    """Get real-NFL QBR (ESPN's Total QBR advanced metric) rankings for
    qualified quarterbacks, highest first. week=0 (default) returns
    full-season rankings; pass a week number (e.g. 1-18) for that single
    week's rankings instead."""
    year = datetime.now().year
    if week:
        url = f"{CORE_API}/seasons/{year}/types/2/weeks/{week}/qbr/0"
        scope = f"week {week}"
    else:
        url = f"{CORE_API}/seasons/{year}/types/2/groups/1/qbr/0"
        scope = "season"

    data = get_json(url)
    items = data.get("items", [])
    if not items:
        return f"No QBR data available for {scope} ({year}) yet."

    ranked = []
    for item in items:
        stats = {s["name"]: s for cat in item["splits"]["categories"] for s in cat["stats"]}
        qbr = stats.get("qbr")
        if qbr is None:
            continue
        ranked.append((qbr["value"], qbr["displayValue"], item["athlete"]))
    ranked.sort(key=lambda t: t[0], reverse=True)

    lines = []
    for _, display_value, athlete_ref in ranked[:10]:
        athlete = follow_ref(athlete_ref)
        lines.append(f"{athlete.get('displayName', '?')}: QBR {display_value}")
    if not lines:
        return f"No QBR data available for {scope} ({year}) yet."
    return f"NFL QBR leaders ({scope}, {year}):\n" + "\n".join(lines)


TOOLS = [
    get_nfl_player_summary,
    get_nfl_player_career_stats,
    get_nfl_player_gamelog,
    get_nfl_player_splits,
    get_nfl_stat_leaders,
    get_nfl_qbr_leaders,
]
