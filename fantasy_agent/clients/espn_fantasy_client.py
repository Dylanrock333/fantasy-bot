"""ESPN private fantasy-league client: authenticates and builds a League
object, cached per league_id.
"""
import os
import time
from contextvars import ContextVar

from dotenv import load_dotenv
from espn_api.football import League

from fantasy_agent.trace import emit

load_dotenv()

YEAR = 2026
TTL_SECONDS = 30 * 60 #Every well

# Set once per request (in fantasy_agent/server.py) so tool calls deep in the graph
# know which league to fetch, without threading league_id through every
# tool signature - those are dictated by the LLM, not the app.
current_league_id: ContextVar[int] = ContextVar("current_league_id")

_leagues: dict[int, tuple[League, float]] = {}


def get_league(league_id: int) -> League:
    return League(
        league_id=league_id,
        year=YEAR,
        espn_s2=os.environ["ESPN_S2"],
        swid=os.environ["SWID"],
    )


def league_singleton() -> League:
    league_id = current_league_id.get()
    cached = _leagues.get(league_id)
    if cached is None or time.time() - cached[1] > TTL_SECONDS:
        emit("league_cache_refresh", league_id=league_id, reason="expired" if cached else "first_fetch")
        cached = (get_league(league_id), time.time())
        _leagues[league_id] = cached
    return cached[0]
