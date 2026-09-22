"""Step 1 of the one-off full player report: pull every NFL team's raw,
unfiltered roster from ESPN's public API and dump it to a temp file per
team. Nothing is filtered here - that happens in build_report.py. Run once:

    python3 scripts/player_report/fetch_rosters.py
"""
import json
from collections import Counter
from pathlib import Path

from fantasy_agent.clients.espn_nfl_client import SITE_API, get_json

RAW_DIR = Path(__file__).resolve().parent / "raw"

# The roster groups ESPN returns per team - used only for logging labels.
ALL_GROUPS = ["offense", "defense", "specialTeam", "injuredReserveOrOut", "practiceSquad", "suspended"]


def fetch_all_teams() -> list[dict]:
    data = get_json(f"{SITE_API}/teams")
    return [t["team"] for t in data["sports"][0]["leagues"][0]["teams"]]


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    teams = fetch_all_teams()

    position_totals = Counter()
    group_totals = Counter()
    grand_total = 0
    failed_teams = []

    for team in teams:
        abbr = team["abbreviation"]
        try:
            roster = get_json(f"{SITE_API}/teams/{team['id']}/roster")
        except Exception as err:
            print(f"[fetch_rosters] FAILED to fetch roster for {abbr}: {err}")
            failed_teams.append(abbr)
            continue

        groups = roster.get("athletes", [])
        if not groups:
            print(f"[fetch_rosters] WARNING: empty roster for {abbr}")
            failed_teams.append(abbr)
            continue

        (RAW_DIR / f"{abbr}.json").write_text(json.dumps(roster))

        team_position_counts = Counter()
        team_group_counts = Counter()
        for group in groups:
            group_name = group.get("position", "?")
            team_group_counts[group_name] += len(group["items"])
            for p in group["items"]:
                pos = p.get("position", {}).get("abbreviation", "?")
                team_position_counts[pos] += 1

        team_total = sum(team_position_counts.values())
        grand_total += team_total
        position_totals.update(team_position_counts)
        group_totals.update(team_group_counts)

        pos_str = ", ".join(f"{pos}:{n}" for pos, n in team_position_counts.most_common())
        group_str = ", ".join(f"{g}:{team_group_counts.get(g, 0)}" for g in ALL_GROUPS)
        print(f"[fetch_rosters] {abbr}: {team_total} players | by position: {pos_str} | by group: {group_str}")

    print("\n=== fetch_rosters summary ===")
    print(f"Teams fetched: {len(teams) - len(failed_teams)}/{len(teams)}")
    if failed_teams:
        print(f"Failed/empty teams: {failed_teams}")
    print(f"Grand total players (raw, unfiltered): {grand_total}")
    print("League-wide totals by position:")
    for pos, n in position_totals.most_common():
        print(f"  {pos}: {n}")
    print("League-wide totals by roster group:")
    for g in ALL_GROUPS:
        print(f"  {g}: {group_totals.get(g, 0)}")


if __name__ == "__main__":
    main()
