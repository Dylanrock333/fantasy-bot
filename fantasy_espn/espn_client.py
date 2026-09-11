import os
from contextvars import ContextVar

from dotenv import load_dotenv
from espn_api.football import League

load_dotenv()

YEAR = 2026

# Set once per request (in api/server.py) so tool calls deep in the graph
# know which league to fetch, without threading league_id through every
# tool signature - those are dictated by the LLM, not the app.
current_league_id: ContextVar[int] = ContextVar("current_league_id")


def get_league(league_id: int) -> League:
    return League(
        league_id=league_id,
        year=YEAR,
        espn_s2=os.environ["ESPN_S2"],
        swid=os.environ["SWID"],
    )
