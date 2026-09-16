"""Manual trigger for the weekly recap graph, no HTTP server needed.

Usage:
  python scripts/run_weekly_recap.py --league-id 1992397255 [--week 3]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from fantasy_agent.weekly_recap_graph import build_weekly_recap_graph
from fantasy_agent.clients.espn_fantasy_client import current_league_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", type=int, required=True)
    parser.add_argument("--week", type=int, default=0)
    args = parser.parse_args()

    current_league_id.set(args.league_id)
    graph = build_weekly_recap_graph()
    result = graph.invoke({"week": args.week})

    print(f"\n=== Week {result['week']} League Summary ===\n")
    print(result["league_summary"])

    print("\n=== Power Rankings ===\n")
    for i, r in enumerate(result["power_rankings"], start=1):
        print(f"#{i} {r['tag']} — {r['team']}")
        print(f"    {r['blurb']}")


if __name__ == "__main__":
    main()
