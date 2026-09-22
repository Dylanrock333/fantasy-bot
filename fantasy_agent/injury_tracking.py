"""NFL-wide injury alert diffing: fetches every team's full roster, diffs
it against the last-seen snapshot on disk, and returns alerts for players
who crossed the Active <-> Out/Injured-Reserve line since the last check.

Pulls full team rosters rather than ESPN's public /injuries feed, which
caps out at 25 entries/team mixed across every position - that cap was
crowding out real fantasy-relevant players (confirmed live: e.g. only 8
fantasy-relevant players showed for one team on a given day vs. 17 for
another). The roster endpoint has no such cap and already carries each
athlete's status/injuries fields directly, so no separate lookup is
needed. Team defenses (D/ST) aren't individual athletes, so each team gets
one synthetic "DST_{abbr}" row instead.

Players are matched across checks by ESPN's shared numeric athlete id
(present directly on roster entries here - not by name+team, which is
ambiguous: ESPN has multiple real players sharing the same display name,
e.g. two different "Justin Jefferson"s).

Not a LangChain @tool or LangGraph flow - this is pure diff logic with no
LLM step, called directly from server.py.
"""
import json
import os
from pathlib import Path

from .clients.espn_nfl_client import ATHLETE_API, SITE_API, FANTASY_POSITIONS, best_link, flatten_roster_groups, get_json

ALERT_STATUSES = {"Out", "Injured Reserve"}
ROSTER_GROUPS = {"offense", "defense", "specialTeam", "injuredReserveOrOut"}

STATE_FILE = Path(__file__).resolve().parent / "data" / "injury_state.json"


def _derive_status(athlete: dict) -> str:
    """Read injury status straight off the roster data already fetched -
    no separate API call. Prefers the injuries[] array (how IR/Out show up)
    over the coarser top-level status object."""
    injuries = athlete.get("injuries") or []
    if injuries:
        latest = max(injuries, key=lambda i: i.get("date", ""))
        return latest.get("status", "Active")
    status_name = athlete.get("status", {}).get("name")
    if status_name and status_name != "Active":
        return status_name
    return "Active"


def _fetch_injury_report() -> dict[int | str, dict]:
    """Pull every NFL team's full roster and flatten it into
    fantasy-relevant rows keyed by athlete id - real players get their
    numeric ESPN id, team defenses get a synthetic "DST_{abbr}" key."""
    teams = get_json(f"{SITE_API}/teams")["sports"][0]["leagues"][0]["teams"]
    rows: dict[int | str, dict] = {}
    for entry in teams:
        team = entry["team"]
        abbr = team["abbreviation"]
        try:
            roster = get_json(f"{SITE_API}/teams/{team['id']}/roster")
        except Exception as err:
            print(f"[injury_tracking] failed to fetch roster for {abbr}: {err}")
            continue

        for athlete in flatten_roster_groups(roster, groups=ROSTER_GROUPS):
            position = athlete.get("position", {}).get("abbreviation")
            if position not in FANTASY_POSITIONS:
                continue
            rows[int(athlete["id"])] = {
                "team": team["displayName"],
                "name": athlete.get("fullName"),
                "position": position,
                "status": _derive_status(athlete),
            }

        rows[f"DST_{abbr}"] = {
            "team": team["displayName"],
            "name": f"{team['displayName']} D/ST",
            "position": "D/ST",
            "status": "Active",
        }
    return rows


def _crossed_alert_line(previous_status: str | None, current_status: str) -> bool:
    """A row alerts on entering ALERT_STATUSES (Active/Questionable/Doubtful
    -> Out/IR) or leaving it back to Active (a recovery alert). Churn
    between Questionable and Doubtful, or any change not crossing that
    Active/Out-IR line, doesn't alert."""
    was_alert = previous_status in ALERT_STATUSES
    is_alert = current_status in ALERT_STATUSES
    if not was_alert and is_alert:
        return True
    if was_alert and current_status == "Active":
        return True
    return False


def _build_alert(athlete_id: int | str, row: dict, previous_status: str | None) -> dict | None:
    news_link = None
    # D/ST entries use a synthetic "DST_{abbr}" id - no individual overview
    # page exists for a team defense, and D/ST's status is always "Active"
    # anyway (never in ALERT_STATUSES), so this only ever runs for real
    # numeric athlete ids.
    if row["status"] in ALERT_STATUSES and isinstance(athlete_id, int):
        try:
            overview = get_json(f"{ATHLETE_API}/athletes/{athlete_id}/overview")
            news_link = best_link(overview.get("news", []))
        except Exception:
            news_link = None

    return {
        "name": row["name"],
        "pro_team": row["team"],
        "status": row["status"],
        "previous_status": previous_status,
        "news_link": news_link,
    }


def _load_state() -> dict[int | str, dict]:
    try:
        raw = json.loads(STATE_FILE.read_text())
        # Real athlete ids round-trip through JSON as digit strings and get
        # cast back to int; D/ST's "DST_{abbr}" keys stay strings as-is.
        return {(int(k) if k.isdigit() else k): v for k, v in raw.items()}
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        # ValueError also covers a pre-migration state file whose keys/values
        # are the old "Team|Name": status shape rather than
        # id: {injury_status, name, position, team} - treat it as no prior
        # state rather than crashing.
        return {}


def _save_state(state: dict[int | str, dict]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_FILE.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state))
    os.replace(tmp_path, STATE_FILE)


def check_injuries() -> list[dict]:
    """Fetch the current injury report, diff it against the last-seen
    snapshot, and return alerts for players who crossed the Active <->
    Out/IR line since the last check. Players are matched across checks by
    ESPN's shared numeric athlete id (see module docstring). The on-disk
    state stores each player's full row (name/position/team/injury_status),
    not just status, so the file is self-describing when inspected."""
    previous_state = _load_state()
    report = _fetch_injury_report()

    new_state = {
        athlete_id: {
            "injury_status": row["status"],
            "name": row["name"],
            "position": row["position"],
            "team": row["team"],
        }
        for athlete_id, row in report.items()
    }
    _save_state(new_state)

    alerts = []
    for athlete_id, row in report.items():
        prev_entry = previous_state.get(athlete_id)
        # isinstance guard tolerates a not-yet-migrated entry from the old
        # id: status (str) shape - treated as no prior state, same as the
        # ValueError case in _load_state above.
        previous_status = prev_entry["injury_status"] if isinstance(prev_entry, dict) else None
        if not _crossed_alert_line(previous_status, row["status"]):
            continue
        alert = _build_alert(athlete_id, row, previous_status)
        if alert is not None:
            alerts.append(alert)

    return alerts
