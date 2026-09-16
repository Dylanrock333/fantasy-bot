"""Category -> tool-list registry consumed by graph.py's supervisor/category
nodes. Add a new category by adding a module here (with a TOOLS list) and
registering it below - no graph changes needed.

Category names are prefixed to keep the two data sources unambiguous to the
supervisor LLM: "fantasy_*" = your private league (via clients/espn_fantasy_client.py),
"nfl_*" = real-world NFL data (ESPN's public API, see docs/NFL_PUBLIC_API.md).
"""
import sys
from pathlib import Path

# Let this package be imported regardless of the process's cwd, since
# fantasy_agent isn't an installed package.
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

CATEGORY_REGISTRY = {name: mod.TOOLS for name, mod in _MODULES.items()}

# Each module's docstring is its category description - the supervisor reads
# these to tell similarly-named categories apart (e.g. nfl_scores vs
# nfl_game), so keep each module's docstring a clear one-liner on its scope.
CATEGORY_DESCRIPTIONS = {name: mod.__doc__.strip() for name, mod in _MODULES.items()}
