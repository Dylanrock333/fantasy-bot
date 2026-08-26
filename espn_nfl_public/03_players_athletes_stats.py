"""Players & Athletes
Covers: core athletes list, positions reference, athlete overview/stats/
gamelog/splits, league-wide statistical leaderboard

Run: python 03_players_athletes_stats.py
"""
from nfl_client import CORE_API, ATHLETE_API, get_json, follow_ref

ATHLETE_ID = 3918298  # example athlete id (per Public-ESPN-API docs)


def main():
    print("=" * 60)
    print("ATHLETES - GET core/.../athletes (paginated $ref list)")
    print("=" * 60)
    athletes = get_json(f"{CORE_API}/athletes", limit=3, active="true")
    print(f"count={athletes['count']}, showing {len(athletes['items'])} refs")
    if athletes["items"]:
        resolved = follow_ref(athletes["items"][0])
        print(f"  Resolved: {resolved.get('fullName')} ({resolved.get('position', {}).get('abbreviation', '?')})")

    print()
    print("=" * 60)
    print("POSITIONS - GET core/.../positions")
    print("=" * 60)
    positions = get_json(f"{CORE_API}/positions", limit=5)
    print(f"count={positions['count']}, showing {len(positions['items'])} refs")

    print()
    print("=" * 60)
    print(f"ATHLETE OVERVIEW - GET athletes/{ATHLETE_ID}/overview")
    print("=" * 60)
    try:
        overview = get_json(f"{ATHLETE_API}/athletes/{ATHLETE_ID}/overview")
        stats = overview.get("statistics", {})
        print(f"Statistics: {stats.get('displayName')}")
        for cat in stats.get("categories", [])[:3]:
            print(f"  {cat['displayName']}: {cat['count']} fields")
    except Exception as e:
        print(f"overview lookup failed for id {ATHLETE_ID}: {e}")

    print()
    print("=" * 60)
    print(f"ATHLETE SEASON STATS - GET athletes/{ATHLETE_ID}/stats")
    print("=" * 60)
    try:
        stats = get_json(f"{ATHLETE_API}/athletes/{ATHLETE_ID}/stats")
        print(f"Top-level keys: {list(stats.keys())[:6]}")
    except Exception as e:
        print(f"stats lookup failed: {e}")

    print()
    print("=" * 60)
    print(f"ATHLETE GAME LOG - GET athletes/{ATHLETE_ID}/gamelog")
    print("=" * 60)
    try:
        gamelog = get_json(f"{ATHLETE_API}/athletes/{ATHLETE_ID}/gamelog")
        print(f"Top-level keys: {list(gamelog.keys())[:6]}")
    except Exception as e:
        print(f"gamelog lookup failed: {e}")

    print()
    print("=" * 60)
    print(f"ATHLETE SPLITS - GET athletes/{ATHLETE_ID}/splits")
    print("=" * 60)
    try:
        splits = get_json(f"{ATHLETE_API}/athletes/{ATHLETE_ID}/splits")
        print(f"Top-level keys: {list(splits.keys())[:6]}")
    except Exception as e:
        print(f"splits lookup failed: {e}")

    print()
    print("=" * 60)
    print("LEAGUE-WIDE STAT LEADERS - GET statistics/byathlete")
    print("=" * 60)
    leaders = get_json(f"{ATHLETE_API}/statistics/byathlete")
    print(f"pagination: page {leaders['pagination']['page']}/{leaders['pagination']['pages']}, "
          f"count={leaders['pagination']['count']}")


if __name__ == "__main__":
    main()
