import os

from dotenv import load_dotenv
from espn_api.football import League

load_dotenv()

LEAGUE_ID = 1992397255
YEAR = 2026


def get_league() -> League:
    return League(
        league_id=LEAGUE_ID,
        year=YEAR,
        espn_s2=os.environ["ESPN_S2"],
        swid=os.environ["SWID"],
    )
