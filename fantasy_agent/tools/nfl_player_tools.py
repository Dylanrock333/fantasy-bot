"""Real-NFL data: individual athlete stats, career/game-log/split detail,
league-wide statistical leaders, and QBR rankings (ESPN's public API,
not fantasy players/points - see fantasy_player_tools.py for that).
Cross-refs a fantasy roster player against real-world performance, e.g. for
"who should I start" or "compare my roster to theirs" questions."""
from datetime import datetime

from langchain_core.tools import tool

from ..clients.espn_nfl_client import (
    ATHLETE_API,
    CORE_API,
    SITE_API,
    follow_ref,
    get_json,
    resolve_athlete,
)


def _view_summary(athlete: dict, pro_team: str, num_games: int) -> str:
    overview = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/overview")
    stats = overview.get("statistics", {})
    names = stats.get("displayNames", [])
    splits = stats.get("splits", [])
    season = next((s for s in splits if s["displayName"] == "Regular Season"), None)
    if not season:
        return f"{athlete['fullName']} ({pro_team}): no season stats available yet."

    lines = [f"{n}: {v}" for n, v in list(zip(names, season["stats"]))[:8]]
    return f"{athlete['fullName']} ({pro_team}) season stats:\n" + "\n".join(lines)


def _view_career(athlete: dict, pro_team: str, num_games: int) -> str:
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


def _view_gamelog(athlete: dict, pro_team: str, num_games: int) -> str:
    data = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/gamelog")
    season_types = data.get("seasonTypes", [])
    events_map = data.get("events", {})
    display_names = data.get("displayNames", [])
    # Flatten per-game stat rows across every season type and category.
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


def _view_splits(athlete: dict, pro_team: str, num_games: int) -> str:
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


_VIEWS = {
    "summary": _view_summary,
    "career": _view_career,
    "gamelog": _view_gamelog,
    "splits": _view_splits,
}


@tool
def get_nfl_player_stats(
    player_name: str, pro_team: str = "", view: str = "summary", num_games: int = 5
) -> str:
    """Get a real-NFL player's stats. pro_team is optional - pass the
    player's real NFL team abbreviation or name (e.g. 'DAL' or 'Cowboys')
    if you already know it, for a faster exact lookup; leave it blank to
    search by name alone. view selects what to return: 'summary' (season
    stat totals, default), 'career' (career stats by category, most recent
    season first), 'gamelog' (last num_games games, most recent first), or
    'splits' (season splits, e.g. All/Home/Away)."""
    athlete = resolve_athlete(pro_team, player_name)
    if athlete is None:
        suffix = f" on team '{pro_team}'" if pro_team else ""
        return f"No NFL player matched '{player_name}'{suffix}."
    team_label = athlete.get("proTeam") or pro_team or "?"
    fn = _VIEWS.get(view, _view_summary)
    return fn(athlete, team_label, num_games)


# Stat categories relevant to each position, for the position= filter below.
# ESPN's public leaders feed has no kicking (FG) category at all - not fixable
# without a per-team roster + per-player overview call for all 32 teams.
_POSITION_CATEGORIES = {
    "QB": ["passingYards", "passingTouchdowns", "quarterbackRating", "interceptions"],
    "RB": ["rushingYards", "rushingTouchdowns"],
    "WR": ["receivingYards", "receptions", "receivingTouchdowns"],
    "TE": ["receivingYards", "receptions", "receivingTouchdowns"],
    "DEF": ["totalTackles", "sacks", "interceptions", "passesDefended"],
    "ST": ["kickoffYards", "puntYards"],
}


@tool
def get_nfl_stat_leaders(category: str = "", position: str = "", limit: int = 1) -> str:
    """Get real-NFL statistical leaders for the current season, top `limit`
    player(s) per stat category (default 1 - raise it for a top-N list).
    category optionally filters to one stat by name/abbreviation, e.g.
    'passing yards' or 'rushingYards'. position optionally filters to every
    category relevant to one position instead (QB, RB, WR, TE, DEF, or ST),
    e.g. position='RB' for rushing yards/TD leaders - use at most one of
    category/position. Leave both blank to list leaders across all
    categories. Note: this feed has no kicking (FG) stat category."""
    data = get_json(f"{SITE_API}/statistics")
    categories = data.get("stats", {}).get("categories", [])

    if position:
        wanted = _POSITION_CATEGORIES.get(position.strip().upper())
        if not wanted:
            return (
                f"No leader categories for position '{position}'. "
                f"Supported: {', '.join(_POSITION_CATEGORIES)}."
            )
        categories = [c for c in categories if c["name"] in wanted]
    elif category:
        q = category.strip().lower()
        categories = [
            c for c in categories
            if q in c["name"].lower() or q in c["displayName"].lower()
        ]
    if not categories:
        return f"No stat category matched '{category or position}'."

    lines = []
    for cat in categories:
        leaders = cat.get("leaders", [])[: max(limit, 1)]
        for entry in leaders:
            athlete = entry["athlete"]
            team = athlete.get("team", {}).get("abbreviation", "?")
            lines.append(
                f"{cat['displayName']}: {athlete['displayName']} ({team}) - {entry['displayValue']}"
            )
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

    # Rank by QBR value, then resolve only the top 10 athlete refs (one request each).
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
    get_nfl_player_stats,
    get_nfl_stat_leaders,
    get_nfl_qbr_leaders,
]
