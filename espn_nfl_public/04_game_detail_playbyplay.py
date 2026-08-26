"""Game Detail & Play-by-Play
Covers: game summary/boxscore, core event/competition sub-resources
(broadcasts, odds, officials), CDN game package (boxscore, play-by-play,
matchup, live scoreboard)

Run: python 04_game_detail_playbyplay.py
"""
from nfl_client import SITE_API, CORE_API, CDN_API, get_json


def get_a_live_event_id() -> str:
    """Pull the first event id off today's scoreboard so this script works
    without a hardcoded, quickly-stale game id."""
    sb = get_json(f"{SITE_API}/scoreboard")
    return sb["events"][0]["id"]


def main():
    event_id = get_a_live_event_id()
    print(f"Using event id {event_id} from current scoreboard\n")

    print("=" * 60)
    print(f"GAME SUMMARY - GET /summary?event={event_id}")
    print("=" * 60)
    summary = get_json(f"{SITE_API}/summary", event=event_id)
    box_teams = summary.get("boxscore", {}).get("teams", [])
    for t in box_teams:
        print(f"  {t['team']['displayName']}: {len(t.get('statistics', []))} stat groups")

    print()
    print("=" * 60)
    print(f"COMPETITION - GET core/.../events/{event_id}/competitions/{event_id}")
    print("=" * 60)
    try:
        competition = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}")
        print(f"venue ref: {competition.get('venue', {}).get('$ref', 'n/a')}")
    except Exception as e:
        print(f"competition lookup failed: {e}")

    print()
    print("=" * 60)
    print(f"BROADCASTS - GET core/.../competitions/{event_id}/broadcasts")
    print("=" * 60)
    try:
        broadcasts = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/broadcasts")
        print(f"{len(broadcasts.get('items', []))} broadcast entries")
    except Exception as e:
        print(f"broadcasts lookup failed: {e}")

    print()
    print("=" * 60)
    print(f"ODDS - GET core/.../competitions/{event_id}/odds")
    print("=" * 60)
    try:
        odds = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/odds")
        print(f"{len(odds.get('items', []))} odds provider entries")
    except Exception as e:
        print(f"odds lookup failed (often empty pre-week): {e}")

    print()
    print("=" * 60)
    print(f"OFFICIALS - GET core/.../competitions/{event_id}/officials")
    print("=" * 60)
    try:
        officials = get_json(f"{CORE_API}/events/{event_id}/competitions/{event_id}/officials")
        print(f"{len(officials.get('items', []))} officiating crew entries")
    except Exception as e:
        print(f"officials lookup failed (usually empty until kickoff): {e}")

    print()
    print("=" * 60)
    print(f"CDN GAME PACKAGE - GET cdn.espn.com/core/nfl/game?xhr=1&gameId={event_id}")
    print("=" * 60)
    game = get_json(f"{CDN_API}/game", xhr=1, gameId=event_id)
    print(f"Top-level keys under gamepackageJSON: "
          f"{list(game.get('gamepackageJSON', {}).keys())[:8]}")

    print()
    print("=" * 60)
    print(f"CDN BOXSCORE - GET cdn.espn.com/core/nfl/boxscore?xhr=1&gameId={event_id}")
    print("=" * 60)
    boxscore = get_json(f"{CDN_API}/boxscore", xhr=1, gameId=event_id)
    print(f"gameId echoed back: {boxscore.get('gameId')}")

    print()
    print("=" * 60)
    print(f"CDN PLAY-BY-PLAY - GET cdn.espn.com/core/nfl/playbyplay?xhr=1&gameId={event_id}")
    print("=" * 60)
    pbp = get_json(f"{CDN_API}/playbyplay", xhr=1, gameId=event_id)
    drives = pbp.get("gamepackageJSON", {}).get("drives", {})
    print(f"Drive data present: {bool(drives)}")

    print()
    print("=" * 60)
    print("CDN LIVE SCOREBOARD - GET cdn.espn.com/core/nfl/scoreboard?xhr=1")
    print("=" * 60)
    live = get_json(f"{CDN_API}/scoreboard", xhr=1)
    print(f"Top-level keys: {list(live.keys())[:6]}")


if __name__ == "__main__":
    main()
