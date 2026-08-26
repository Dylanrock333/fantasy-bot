import os

from dotenv import load_dotenv
from espn_api.football import League

load_dotenv()

# Init
league = League(
    league_id=1992397255,
    year=2026,
    espn_s2=os.environ["ESPN_S2"],
    swid=os.environ["SWID"],
)

print(league)
print(league.teams)
