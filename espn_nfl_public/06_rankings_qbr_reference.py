"""Rankings, QBR & Static Reference Data
Covers: core rankings, venues, franchises, providers, media, current season,
season/weekly QBR

Run: python 06_rankings_qbr_reference.py
"""
from nfl_client import CORE_API, get_json

YEAR = 2025  # most recently completed regular season as of 2026 preseason
WEEK = 1


def main():
    print("=" * 60)
    print("RANKINGS - GET core/.../rankings")
    print("=" * 60)
    rankings = get_json(f"{CORE_API}/rankings")
    print(f"count={rankings.get('count')} (often 0 outside in-season AP poll weeks)")

    print()
    print("=" * 60)
    print("VENUES - GET core/.../venues (static/cacheable)")
    print("=" * 60)
    venues = get_json(f"{CORE_API}/venues", limit=3)
    print(f"count={venues['count']}, showing {len(venues['items'])} refs")

    print()
    print("=" * 60)
    print("FRANCHISES - GET core/.../franchises")
    print("=" * 60)
    franchises = get_json(f"{CORE_API}/franchises", limit=3)
    print(f"count={franchises.get('count')}, showing {len(franchises.get('items', []))} refs")

    print()
    print("=" * 60)
    print("PROVIDERS - GET core/.../providers (odds providers)")
    print("=" * 60)
    providers = get_json(f"{CORE_API}/providers", limit=5)
    print(f"count={providers.get('count')}, showing {len(providers.get('items', []))} refs")

    print()
    print("=" * 60)
    print("MEDIA - GET core/.../media")
    print("=" * 60)
    try:
        media = get_json(f"{CORE_API}/media", limit=3)
        print(f"count={media.get('count')}, showing {len(media.get('items', []))} refs")
    except Exception as e:
        print(f"media lookup failed: {e}")

    print()
    print("=" * 60)
    print("CURRENT SEASON - GET core/.../season")
    print("=" * 60)
    season = get_json(f"{CORE_API}/season")
    print(f"year={season.get('year')}, displayName={season.get('displayName')}")

    print()
    print("=" * 60)
    print(f"SEASON QBR TOTALS - GET core/.../seasons/{YEAR}/types/2/groups/1/qbr/0")
    print("=" * 60)
    try:
        qbr_season = get_json(f"{CORE_API}/seasons/{YEAR}/types/2/groups/1/qbr/0")
        print(f"count={qbr_season.get('count')}")
    except Exception as e:
        print(f"season QBR lookup failed: {e}")

    print()
    print("=" * 60)
    print(f"WEEKLY QBR - GET core/.../seasons/{YEAR}/types/2/weeks/{WEEK}/qbr/0")
    print("=" * 60)
    try:
        qbr_week = get_json(f"{CORE_API}/seasons/{YEAR}/types/2/weeks/{WEEK}/qbr/0")
        print(f"count={qbr_week.get('count')}")
    except Exception as e:
        print(f"weekly QBR lookup failed: {e}")
    print("(/qbr/0 = totals, /qbr/1 = home only, /qbr/2 = away only)")


if __name__ == "__main__":
    main()
