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
from fantasy_espn.espn_client import current_league_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", type=int, required=True)
    parser.add_argument("--week", type=int, default=0)
    args = parser.parse_args()

    current_league_id.set(args.league_id)
    graph = build_weekly_recap_graph()
    result = graph.invoke({"week": args.week})

    print(f"\n=== Week {result['week']} recaps ===\n")
    for r in result["matchup_recaps"]:
        print(f"-- {r['home_team']} vs {r['away_team']} (winner: {r['winner']}) --")
        print(r["recap"])
        print()

    print("=== League summary ===\n")
    print(result["league_summary"])


if __name__ == "__main__":
    main()
