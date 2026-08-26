"""Real-NFL data: scores, schedule, standings (public espn_nfl_public/ API,
not your fantasy league - see fantasy_matchup_tools.py for that)."""
from langchain_core.tools import tool

from ..clients.nfl_client import SITE_API, SITE_API_STANDINGS, get_json


@tool
def get_nfl_scoreboard(week: int = 0, seasontype: int = 0, dates: str = "") -> str:
    """Get real-NFL scores across the league (not fantasy). With no args, returns
    whatever week ESPN currently considers live. Pass week (e.g. 1) and seasontype
    (1=preseason, 2=regular season, 3=postseason) together to pin one specific week
    of the current season, or dates e.g. '20250907' (format YYYYMMDD) to get the
    week containing that calendar date."""
    params = {}
    if week:
        params["week"] = week
    if seasontype:
        params["seasontype"] = seasontype
    if dates:
        params["dates"] = dates
    sb = get_json(f"{SITE_API}/scoreboard", **params)
    lines = []
    for event in sb.get("events", []):
        comp = event["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        status = comp["status"]["type"]["shortDetail"]
        lines.append(f"{away['team']['displayName']} {away['score']} @ "
                      f"{home['team']['displayName']} {home['score']} | {status}")
    return "\n".join(lines) or "No games found."


@tool
def get_nfl_standings() -> str:
    """Get current real-NFL league standings (win-loss record, win percentage, and
    point differential) for both conferences, not fantasy standings."""
    data = get_json(f"{SITE_API_STANDINGS}/standings")
    lines = []
    for conf in data.get("children", []):
        entries = conf.get("standings", {}).get("entries", [])
        if not entries:
            continue
        lines.append(f"{conf['name']}:")
        for entry in entries:
            team = entry["team"]
            stats = {s["name"]: s["displayValue"] for s in entry.get("stats", [])}
            lines.append(
                f"  {team['displayName']} ({stats.get('wins', '?')}-{stats.get('losses', '?')}) "
                f"win%: {stats.get('winPercent', '?')} diff: {stats.get('differential', '?')}"
            )
    if not lines:
        return "No NFL standings available."
    return "\n".join(lines)


TOOLS = [get_nfl_scoreboard, get_nfl_standings]
