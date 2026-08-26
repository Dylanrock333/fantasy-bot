"""Read a list of NFL player names and print only the ones who are rookies
(Year 1) or Year 2 players, based on real-NFL draft data.

Put player names (one per line, or a CSV with a 'name' column) in
scripts/player_lists/players.txt or players.csv, then run:

    python scripts/find_rookies.py
    python scripts/find_rookies.py path/to/other_list.csv

Data source: ESPN's public NFL API (no auth required) - the same client
used by fantasy_agent/tools/nfl_player_tools.py. Each team roster is
searched to resolve a name to ESPN's athlete id, then that athlete's full
record is fetched for its "draft": {"year": N} field. current_season -
draft_year == 0 means the player was drafted this year (Rookie / Year 1);
== 1 means Year 2. Undrafted players fall back to the roster's
"experience": {"years": 0} flag, which reliably marks true first-year
players but can't distinguish a Year 2 UDFA from a veteran.
"""
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fantasy_agent.clients.nfl_client import CORE_API, SITE_API, get_json  # noqa: E402

DEFAULT_INPUT = ROOT / "scripts" / "player_lists" / "players.txt"

# Fantasy-relevant positions first, in typical draft-board order; anything
# else (e.g. OL/DL/LB) sorts alphabetically after these.
POSITION_ORDER = ["QB", "RB", "WR", "TE", "K", "DST", "DEF"]


def normalize(name: str) -> str:
    """Lowercase and strip punctuation/suffixes so 'A.J. Brown' and
    'Michael Pittman Jr.' match ESPN's fullName formatting reliably."""
    name = name.strip().lower()
    name = re.sub(r"[.'’]", "", name)
    name = re.sub(r"\s+(jr|sr|ii|iii|iv)$", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def load_names(path: Path) -> list[str]:
    if not path.exists():
        sys.exit(f"Input file not found: {path}")

    if path.suffix.lower() == ".csv":
        with path.open(newline="") as f:
            reader = csv.reader(f)
            rows = [row for row in reader if row and row[0].strip()]
        if rows and rows[0][0].strip().lower() == "name":
            rows = rows[1:]
        return [row[0].strip() for row in rows]

    with path.open() as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def build_player_index() -> dict[str, dict]:
    """Fetch every team's roster once and index athletes by normalized
    full name -> (athlete dict, team abbreviation)."""
    teams_data = get_json(f"{SITE_API}/teams", limit=50)
    teams = [t["team"] for t in teams_data["sports"][0]["leagues"][0]["teams"]]

    index: dict[str, dict] = {}
    for team in teams:
        roster = get_json(f"{SITE_API}/teams/{team['id']}/roster")
        athletes = [p for group in roster.get("athletes", []) for p in group["items"]]
        for athlete in athletes:
            key = normalize(athlete["fullName"])
            index[key] = {"athlete": athlete, "team": team["abbreviation"]}
    return index


def classify(athlete_id: str, current_season: int) -> str | None:
    """Return 'Rookie (Year 1)' / 'Year 2' if the athlete qualifies, else
    None. Prefers draft year (unambiguous); falls back to the roster's
    experience.years==0 flag for undrafted rookies."""
    data = get_json(f"{CORE_API}/athletes/{athlete_id}")
    draft = data.get("draft")
    if draft and "year" in draft:
        diff = current_season - draft["year"]
        if diff == 0:
            return "Rookie (Year 1)"
        if diff == 1:
            return "Year 2"
        return None

    exp_years = data.get("experience", {}).get("years")
    if exp_years == 0:
        return "Rookie (Year 1)"
    return None


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    names = load_names(input_path)
    if not names:
        sys.exit(f"No player names found in {input_path}")

    current_season = datetime.now().year
    print(f"Looking up {len(names)} player(s)...", file=sys.stderr)
    index = build_player_index()

    results = []
    for raw_name in names:
        key = normalize(raw_name)
        match = index.get(key)

        if match is None:
            # fall back to a substring match for minor name variations
            candidates = [v for k, v in index.items() if key in k or k in key]
            if len(candidates) == 1:
                match = candidates[0]
            elif len(candidates) > 1:
                print(f"Ambiguous match for '{raw_name}', skipping.", file=sys.stderr)
                continue

        if match is None:
            print(f"No match found for '{raw_name}'.", file=sys.stderr)
            continue

        athlete = match["athlete"]
        position = athlete.get("position", {}).get("abbreviation", "UNK")
        label = classify(athlete["id"], current_season)
        if label:
            print(
                f"{athlete['fullName']} ({match['team']}, {position}) -> {label}",
                file=sys.stderr,
            )
            results.append(
                {
                    "name": athlete["fullName"],
                    "team": match["team"],
                    "position": position,
                    "label": label,
                }
            )

    print_by_position(results)


def print_by_position(results: list[dict]) -> None:
    """Print results grouped by position (fantasy-relevant positions first),
    with rookies listed above year-2 players within each group."""
    positions = sorted(
        {r["position"] for r in results},
        key=lambda p: (
            POSITION_ORDER.index(p) if p in POSITION_ORDER else len(POSITION_ORDER),
            p,
        ),
    )

    for position in positions:
        group = [r for r in results if r["position"] == position]
        rookies = [r for r in group if r["label"] == "Rookie (Year 1)"]
        year_twos = [r for r in group if r["label"] == "Year 2"]

        print(f"\n{position} ({len(rookies)} rookie(s), {len(year_twos)} year 2)")
        for r in rookies:
            print(f"  {r['name']} ({r['team']}) - {r['label']}")
        for r in year_twos:
            print(f"  {r['name']} ({r['team']}) - {r['label']}")


if __name__ == "__main__":
    main()
