"""Real-NFL data: team identity, rosters, schedules, records, injuries,
depth charts, season offensive/defensive statistics (points, yards, sacks,
takeaways, etc.), and league conference/division structure (public
espn_nfl_public/ API, not your fantasy rosters - see fantasy_roster_tools.py
for that)."""
from langchain_core.tools import tool

from ..clients.nfl_client import SITE_API, get_json, resolve_team


@tool
def get_nfl_teams() -> str:
    """List all 32 real-world NFL teams with their abbreviation, e.g. to look up which abbreviation to use for another tool's pro_team/team_name arg."""
    data = get_json(f"{SITE_API}/teams")
    teams = data["sports"][0]["leagues"][0]["teams"]
    if not teams:
        return "No NFL teams found."
    lines = [f"{t['team']['displayName']} ({t['team']['abbreviation']})" for t in teams]
    return "NFL teams:\n" + "\n".join(lines)


@tool
def get_team_info(team_name: str) -> str:
    """Get a real-NFL team's profile: current record, conference/division, and franchise info, e.g. team_name='Cowboys' or 'DAL'."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    data = get_json(f"{SITE_API}/teams/{team['id']}")
    t = data["team"]
    totals = next(
        (r for r in t.get("record", {}).get("items", []) if r.get("type") == "total"),
        None,
    )
    record_str = totals["summary"] if totals else "no record available"
    venue = t.get("franchise", {}).get("venue", {}).get("fullName", "unknown venue")
    return (
        f"{t['displayName']} ({t['abbreviation']}): record {record_str}, "
        f"based in {t['location']}, home venue {venue}."
    )


@tool
def get_team_stats(team_name: str) -> str:
    """Get a real-NFL team's season offensive and defensive statistics -
    points scored, total/passing/rushing yards on offense, and defensive
    production (sacks, tackles for loss, interceptions, passes defended,
    forced/recovered fumbles). Use this (not get_team_info, which is
    record/venue only) to compare two teams' offense or defense, e.g.
    team_name='Cowboys' or 'DAL'."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    data = get_json(f"{SITE_API}/teams/{team['id']}/statistics")
    categories = {
        c["name"]: c
        for c in data.get("results", {}).get("stats", {}).get("categories", [])
    }
    if not categories:
        return f"No statistics available for {team['displayName']}."

    def stat(cat_name: str, stat_name: str) -> str | None:
        for s in categories.get(cat_name, {}).get("stats", []):
            if s["name"] == stat_name:
                return s["displayValue"]
        return None

    offense = {
        "Points scored": stat("scoring", "totalPoints"),
        "Total yards": stat("rushing", "totalYards"),
        "Passing yards": stat("passing", "netPassingYards"),
        "Rushing yards": stat("rushing", "rushingYards"),
        "Passing TDs": stat("passing", "passingTouchdowns"),
        "Rushing TDs": stat("rushing", "rushingTouchdowns"),
    }
    defense = {
        "Sacks": stat("defensive", "sacks"),
        "Tackles for loss": stat("defensive", "tacklesForLoss"),
        "Interceptions": stat("defensiveInterceptions", "interceptions"),
        "Passes defended": stat("defensive", "passesDefended"),
        "Fumbles forced": stat("general", "fumblesForced"),
        "Fumbles recovered": stat("general", "fumblesRecovered"),
    }
    off_str = ", ".join(f"{k}: {v}" for k, v in offense.items() if v is not None)
    def_str = ", ".join(f"{k}: {v}" for k, v in defense.items() if v is not None)
    return (
        f"{team['displayName']} season stats\n"
        f"Offense: {off_str}\n"
        f"Defense (production, not points/yards allowed): {def_str}"
    )


@tool
def get_team_coach(team_name: str) -> str:
    """Get a real-NFL team's current head coach, e.g. team_name='Cowboys' or 'DAL'. Use this instead of assuming/recalling a coach's name from memory - coaching staffs change year to year."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    data = get_json(f"{SITE_API}/teams/{team['id']}/roster", enable="coach")
    coaches = data.get("coach", [])
    if not coaches:
        return f"No head coach on file for the {team['displayName']}."
    names = ", ".join(f"{c['firstName']} {c['lastName']}" for c in coaches)
    return f"{team['displayName']} head coach: {names}."


@tool
def get_nfl_team_roster(team_name: str) -> str:
    """Get a real-NFL team's full active roster grouped by position, e.g. team_name='Cowboys' or 'DAL'."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    data = get_json(f"{SITE_API}/teams/{team['id']}/roster")
    groups = data.get("athletes", [])
    if not groups:
        return f"No roster available for the {team['displayName']}."
    lines = []
    for group in groups:
        names = ", ".join(p["fullName"] for p in group["items"])
        lines.append(f"{group['position']}: {names}")
    return f"{team['displayName']} roster:\n" + "\n".join(lines)


@tool
def get_team_schedule(team_name: str) -> str:
    """Get a real-NFL team's season schedule (past results and upcoming games), e.g. team_name='Cowboys' or 'DAL'."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    data = get_json(f"{SITE_API}/teams/{team['id']}/schedule")
    events = data.get("events", [])
    if not events:
        return f"No schedule available for the {team['displayName']}."
    lines = [f"{e['date'][:10]} - {e['shortName']}" for e in events]
    return f"{team['displayName']} schedule:\n" + "\n".join(lines)


@tool
def get_nfl_divisions() -> str:
    """List the NFL's conferences and divisions with their member teams, e.g. to answer 'what division is a team in' or 'who's in the AFC East'."""
    data = get_json(f"{SITE_API}/groups")
    groups = data.get("groups", [])
    if not groups:
        return "No conference/division structure available."
    lines = []
    for conf in groups:
        for div in conf.get("children", []):
            names = ", ".join(t["displayName"] for t in div.get("teams", []))
            lines.append(f"{div['name']}: {names}")
    return "NFL conferences and divisions:\n" + "\n".join(lines)


@tool
def get_league_injury_report() -> str:
    """Get the current real-NFL injury report across all 32 teams in one call - use this instead of get_team_injuries, whose per-team endpoint is currently dead and always empty."""
    report = get_json(f"{SITE_API}/injuries")
    teams = report.get("injuries", [])
    if not teams:
        return "No injury report available."
    lines = []
    for team in teams:
        entries = team.get("injuries", [])
        if not entries:
            continue
        names = ", ".join(
            f"{e.get('athlete', {}).get('displayName', 'Unknown')} ({e.get('status', '?')})"
            for e in entries
        )
        lines.append(f"{team.get('displayName', team.get('id'))}: {names}")
    if not lines:
        return "No reported injuries league-wide."
    return "NFL injury report:\n" + "\n".join(lines)


@tool
def get_team_injuries(team_name: str) -> str:
    """Get the real-NFL injury report for one team, e.g. 'Cowboys' or 'DAL'."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    report = get_json(f"{SITE_API}/teams/{team['id']}/injuries")
    items = report.get("items", report.get("injuries", []))
    if not items:
        return f"No reported injuries for the {team['displayName']}."
    return f"{team['displayName']} injuries: {len(items)} entries — {items}"


@tool
def get_team_depth_chart(team_name: str) -> str:
    """Get the real-NFL depth chart (starters by position) for one team."""
    team = resolve_team(team_name)
    if team is None:
        return f"No NFL team matched '{team_name}'."
    depth = get_json(f"{SITE_API}/teams/{team['id']}/depthcharts")
    formations = depth.get("depthchart", [])
    if not formations:
        return f"No depth chart available for the {team['displayName']}."
    sections = []
    for formation in formations:
        lines = [f"{slot}: {info['athletes'][0]['displayName']}"
                 for slot, info in formation["positions"].items() if info.get("athletes")]
        if lines:
            sections.append(f"{formation['name']}:\n" + "\n".join(lines))
    return f"{team['displayName']} depth chart:\n\n" + "\n\n".join(sections)


TOOLS = [
    get_nfl_teams,
    get_team_info,
    get_team_stats,
    get_team_coach,
    get_nfl_team_roster,
    get_team_schedule,
    get_nfl_divisions,
    get_league_injury_report,
    get_team_injuries,
    get_team_depth_chart,
]
