"""Authenticated ESPN fantasy-league client with a per-league_id League cache."""
import os
import time
from contextvars import ContextVar
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from espn_api.football import League

from fantasy_agent.logging.trace import emit

load_dotenv()

YEAR = 2026
# Thursday of NFL week 1 - update alongside YEAR each season.
SEASON_KICKOFF = date(2026, 9, 10)
TTL_SECONDS = 30 * 60  # League cache lifetime (30 min).

# Set per request by server.py so tools know which league to fetch without a league_id arg
# (tool signatures are exposed to the LLM).
current_league_id: ContextVar[int] = ContextVar("current_league_id")

_leagues: dict[int, tuple[League, float]] = {}


def get_league(league_id: int) -> League:
    """Build a fresh authenticated League for this season."""
    return League(
        league_id=league_id,
        year=YEAR,
        espn_s2=os.environ["ESPN_S2"],
        swid=os.environ["SWID"],
    )


def league_singleton() -> League:
    """Return the current request's League, refetching when missing or older than TTL_SECONDS."""
    league_id = current_league_id.get()
    cached = _leagues.get(league_id)
    if cached is None or time.time() - cached[1] > TTL_SECONDS:
        emit("league_cache_refresh", league_id=league_id, reason="expired" if cached else "first_fetch")
        cached = (get_league(league_id), time.time())
        _leagues[league_id] = cached
    return cached[0]


def nfl_game_week() -> int:
    """The NFL week that is live or just finished; rolls over Wednesday 00:00 ET.

    ESPN's current_week jumps ahead right after MNF, so it can't be used here."""
    today = datetime.now(ZoneInfo("America/New_York")).date()
    # Days since the Wednesday before kickoff, so each week starts on a Wednesday.
    days = (today - SEASON_KICKOFF).days + 1
    week = days // 7 + 1
    return max(1, min(week, league_singleton().finalScoringPeriod))
