"""Category -> tool-list registry for the chat graph ("fantasy_*" = private league, "nfl_*" = real NFL).

Add a category by adding a module with a TOOLS list and registering it in _MODULES.
"""
import sys
from pathlib import Path

# fantasy_agent isn't installed, so make the repo root importable from any cwd.
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from . import (
    fantasy_matchup_tools,
    fantasy_player_tools,
    fantasy_roster_tools,
    fantasy_standings_tools,
    fantasy_transaction_tools,
    nfl_game_tools,
    nfl_news_tools,
    nfl_player_tools,
    nfl_scores_tools,
    nfl_team_tools,
)

_MODULES = {
    "fantasy_standings": fantasy_standings_tools,
    "fantasy_roster": fantasy_roster_tools,
    "fantasy_matchup": fantasy_matchup_tools,
    "fantasy_player": fantasy_player_tools,
    "fantasy_transaction": fantasy_transaction_tools,
    "nfl_scores": nfl_scores_tools,
    "nfl_team": nfl_team_tools,
    "nfl_player": nfl_player_tools,
    "nfl_news": nfl_news_tools,
    "nfl_game": nfl_game_tools,
}

CATEGORY_REGISTRY = {}
CATEGORY_DESCRIPTIONS = {}
for name, mod in _MODULES.items():
    CATEGORY_REGISTRY[name] = mod.TOOLS
    # Sent to the supervisor as the category description, so keep docstrings
    CATEGORY_DESCRIPTIONS[name] = mod.__doc__.strip()
