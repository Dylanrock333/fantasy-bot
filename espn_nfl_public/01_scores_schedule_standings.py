"""Scores, Schedule & Standings
Covers: scoreboard (current/week/date), standings, calendar, seasons, events

Run: python 01_scores_schedule_standings.py
"""
from nfl_client import SITE_API, SITE_API_STANDINGS, CORE_API, get_json


def main():
    print("=" * 60)
    print("SCOREBOARD (current) - GET /scoreboard")
    print("=" * 60)
    sb = get_json(f"{SITE_API}/scoreboard")
    for event in sb.get("events", []):
        comp = event["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        status = comp["status"]["type"]["shortDetail"]
        print(f"{away['team']['displayName']} {away['score']} @ "
              f"{home['team']['displayName']} {home['score']} | {status}")

    print()
    print("=" * 60)
    print("SCOREBOARD BY WEEK - GET /scoreboard?week=1&seasontype=2")
    print("=" * 60)
    sb_week = get_json(f"{SITE_API}/scoreboard", week=1, seasontype=2)
    print(f"{len(sb_week.get('events', []))} games found for week 1, regular season")

    print()
    print("=" * 60)
    print("STANDINGS - GET apis/v2/.../standings (note: site v2 API, not apis/site/v2)")
    print("=" * 60)
    standings = get_json(f"{SITE_API_STANDINGS}/standings")
    for conf in standings.get("children", []):
        entries = conf.get("standings", {}).get("entries", [])
        print(f"{conf['abbreviation']}: {len(entries)} teams")
        for entry in entries[:3]:
            wins = next((s["displayValue"] for s in entry["stats"] if s["name"] == "wins"), "?")
            losses = next((s["displayValue"] for s in entry["stats"] if s["name"] == "losses"), "?")
            print(f"  {entry['team']['displayName']}: {wins}-{losses}")

    print()
    print("=" * 60)
    print("CALENDAR - GET core/.../calendar")
    print("=" * 60)
    calendar = get_json(f"{CORE_API}/calendar")
    print(f"Calendar entries: {len(calendar) if isinstance(calendar, list) else 'n/a (dict shape)'}")

    print()
    print("=" * 60)
    print("SEASONS - GET core/.../seasons")
    print("=" * 60)
    seasons = get_json(f"{CORE_API}/seasons", limit=5)
    print(f"count={seasons.get('count')}, showing {len(seasons.get('items', []))} refs")

    print()
    print("=" * 60)
    print("EVENTS - GET core/.../events")
    print("=" * 60)
    events = get_json(f"{CORE_API}/events", limit=5)
    print(f"count={events.get('count')}, showing {len(events.get('items', []))} refs")
    if events.get("items"):
        first_id = events["items"][0]["$ref"].split("/events/")[1].split("?")[0]
        print(f"EVENTS/{{event}} - GET core/.../events/{first_id}")
        single = get_json(f"{CORE_API}/events/{first_id}")
        print(f"  name: {single.get('name')}, date: {single.get('date')}")


if __name__ == "__main__":
    main()
