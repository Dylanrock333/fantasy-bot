"""Step 2 of the one-off full player report: read the raw roster files
fetch_rosters.py wrote, filter down to fantasy-relevant positions, and fill
in each player's real injury status using data already present in those
raw files (no new HTTP calls). Run once, after fetch_rosters.py:

    python3 scripts/player_report/build_report.py
"""
import json
from collections import Counter
from pathlib import Path

from fantasy_agent.clients.espn_nfl_client import FANTASY_POSITIONS, flatten_roster_groups

RAW_DIR = Path(__file__).resolve().parent / "raw"
OUTPUT_FILE = Path(__file__).resolve().parent / "player_report.json"

ROSTER_GROUPS = {"offense", "defense", "specialTeam", "injuredReserveOrOut"}

# Status vocabulary this script already knows how to expect - anything else
# encountered gets logged rather than silently passed through, per the plan.
KNOWN_STATUSES = {"Active", "Questionable", "Doubtful", "Out", "Injured Reserve", "Day-To-Day", "Suspended"}


def derive_status(athlete: dict) -> str:
    """Read injury status directly from the roster data already fetched -
    no new API calls. Prefers the injuries[] array (how IR shows up) over
    the coarser top-level status object."""
    injuries = athlete.get("injuries") or []
    if injuries:
        latest = max(injuries, key=lambda i: i.get("date", ""))
        return latest.get("status", "Active")
    status_name = athlete.get("status", {}).get("name")
    if status_name and status_name != "Active":
        return status_name
    return "Active"


def main():
    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        print(f"[build_report] No raw files found in {RAW_DIR} - run fetch_rosters.py first.")
        return

    report: dict[int, dict] = {}
    position_totals = Counter()
    dropped_total = 0
    status_totals = Counter()
    unexpected_statuses = set()

    for raw_file in raw_files:
        abbr = raw_file.stem
        raw = json.loads(raw_file.read_text())
        team_name = raw.get("team", {}).get("displayName", abbr)

        all_players = flatten_roster_groups(raw, groups=ROSTER_GROUPS)
        team_kept = Counter()

        for p in all_players:
            pos = p.get("position", {}).get("abbreviation")
            if pos not in FANTASY_POSITIONS:
                dropped_total += 1
                continue

            status = derive_status(p)
            if status not in KNOWN_STATUSES:
                unexpected_statuses.add(status)

            report[int(p["id"])] = {
                "name": p.get("fullName"),
                "position": pos,
                "team": team_name,
                "injury_status": status,
            }
            team_kept[pos] += 1
            status_totals[status] += 1

        # One synthetic D/ST entry per team - not an individual athlete, so
        # it doesn't come from the roster endpoint at all.
        report[f"DST_{abbr}"] = {
            "name": f"{team_name} D/ST",
            "position": "D/ST",
            "team": team_name,
            "injury_status": "Active",
        }
        team_kept["D/ST"] += 1

        team_total_kept = sum(team_kept.values())
        team_dropped = len(all_players) - (team_total_kept - 1)  # -1 for the synthetic D/ST
        position_totals.update(team_kept)
        pos_str = ", ".join(f"{pos}:{n}" for pos, n in team_kept.most_common())
        print(f"[build_report] {abbr}: kept {team_total_kept} ({pos_str}) | dropped {team_dropped}")

    OUTPUT_FILE.write_text(json.dumps(report, indent=2))

    non_active = sum(n for status, n in status_totals.items() if status != "Active")
    print("\n=== build_report summary ===")
    print(f"Total entries in report: {len(report)}")
    print("League-wide totals by position:")
    for pos, n in position_totals.most_common():
        print(f"  {pos}: {n}")
    print(f"Total dropped (non-fantasy positions): {dropped_total}")
    print(f"Status breakdown: {status_totals.get('Active', 0)} Active, {non_active} non-Active")
    for status, n in status_totals.most_common():
        if status != "Active":
            print(f"  {status}: {n}")
    if unexpected_statuses:
        print(f"Unexpected status values encountered (not in KNOWN_STATUSES): {sorted(unexpected_statuses)}")
    print(f"\nWrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
