"""Teams, Rosters & Depth Charts
Covers: teams list, team detail, roster, schedule, record, leaders,
depth charts, injuries (team + league-wide)

Run: python 02_teams_rosters_depthcharts.py
"""
from nfl_client import SITE_API, CORE_API, get_json, follow_ref

TEAM_ID = 6  # Dallas Cowboys


def main():
    print("=" * 60)
    print("ALL TEAMS - GET /teams")
    print("=" * 60)
    teams = get_json(f"{SITE_API}/teams")
    sports = teams["sports"][0]["leagues"][0]["teams"]
    print(f"{len(sports)} teams")
    for t in sports[:5]:
        team = t["team"]
        print(f"  {team['id']}: {team['displayName']} ({team['abbreviation']})")

    print()
    print("=" * 60)
    print(f"TEAM DETAIL - GET /teams/{TEAM_ID}")
    print("=" * 60)
    team = get_json(f"{SITE_API}/teams/{TEAM_ID}")["team"]
    print(f"displayName: {team['displayName']}")
    print(f"record: {team.get('record', {}).get('items', [{}])[0].get('summary', 'n/a')}")

    print()
    print("=" * 60)
    print(f"ROSTER - GET /teams/{TEAM_ID}/roster")
    print("=" * 60)
    roster = get_json(f"{SITE_API}/teams/{TEAM_ID}/roster")
    for group in roster.get("athletes", []):
        print(f"{group['position']}: {len(group['items'])} players")
        for player in group["items"][:2]:
            pos = player.get("position", {}).get("abbreviation", "?")
            print(f"    #{player.get('jersey', '-')} {player['fullName']} ({pos})")

    print()
    print("=" * 60)
    print(f"SCHEDULE - GET /teams/{TEAM_ID}/schedule")
    print("=" * 60)
    schedule = get_json(f"{SITE_API}/teams/{TEAM_ID}/schedule")
    for event in schedule.get("events", [])[:5]:
        print(f"  Week {event.get('week', {}).get('number', '?')}: {event['name']}")

    print()
    print("=" * 60)
    print(f"TEAM LEADERS - GET /teams/{TEAM_ID}/leaders")
    print("=" * 60)
    leaders = get_json(f"{SITE_API}/teams/{TEAM_ID}/leaders")
    for category in leaders.get("leaders", [])[:3]:
        top = category["leaders"][0] if category.get("leaders") else None
        athlete = top["athlete"]["displayName"] if top else "n/a"
        print(f"  {category['displayName']}: {athlete}")

    print()
    print("=" * 60)
    print(f"DEPTH CHART - GET /teams/{TEAM_ID}/depthcharts")
    print("=" * 60)
    depth = get_json(f"{SITE_API}/teams/{TEAM_ID}/depthcharts")
    formations = depth.get("depthchart", [])
    print(f"{len(formations)} formations (e.g. Base 3-4, Nickel, ...)")
    if formations:
        positions = formations[0]["positions"]
        for slot, info in list(positions.items())[:3]:
            starter = info["athletes"][0]["displayName"] if info.get("athletes") else "n/a"
            print(f"  {slot}: {starter}")

    print()
    print("=" * 60)
    print(f"TEAM INJURIES - GET /teams/{TEAM_ID}/injuries")
    print("=" * 60)
    try:
        injuries = get_json(f"{SITE_API}/teams/{TEAM_ID}/injuries")
        print(f"Injury groups: {len(injuries.get('items', injuries.get('injuries', [])))}")
    except Exception as e:
        print(f"No team-level injuries payload: {e}")

    print()
    print("=" * 60)
    print("LEAGUE-WIDE INJURIES - GET /injuries")
    print("=" * 60)
    league_injuries = get_json(f"{SITE_API}/injuries")
    print(f"{len(league_injuries.get('injuries', []))} teams reporting injuries")
    if league_injuries.get("injuries"):
        team_report = league_injuries["injuries"][0]
        print(f"  {team_report['displayName']}: {len(team_report['injuries'])} players listed")

    print()
    print("=" * 60)
    print("CORE API TEAMS - GET core/.../teams (paginated $ref list)")
    print("=" * 60)
    core_teams = get_json(f"{CORE_API}/teams", limit=3)
    print(f"count={core_teams['count']}, resolving first ref...")
    resolved = follow_ref(core_teams["items"][0])
    print(f"  Resolved: {resolved.get('displayName')}")


if __name__ == "__main__":
    main()
