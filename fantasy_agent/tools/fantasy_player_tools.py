"""Fantasy league data: free agents, single-player lookup by name, ownership/points
(private league via fantasy_espn/ - for real-NFL athlete stats see nfl_player_tools.py)."""
from langchain_core.tools import tool

from ..clients.fantasy_client import league_singleton


@tool
def get_free_agents(position: str = "", size: int = 10) -> str:
    """List top available fantasy free agents, optionally filtered by
    position (e.g. 'QB', 'RB', 'WR', 'TE', 'D/ST', 'K')."""
    league = league_singleton()
    kwargs = {"size": size}
    if position:
        kwargs["position"] = position.upper()
    players = league.free_agents(**kwargs)
    if not players:
        return "No free agents found."
    lines = [f"{p.name} ({p.position}, {p.proTeam}) - owned {p.percent_owned}%, "
             f"proj {p.projected_points}" for p in players]
    return "\n".join(lines)


@tool
def get_player_info(name: str) -> str:
    """Look up a single NFL player's fantasy status by name, e.g. 'Jahmyr Gibbs' or
    "Ja'Marr Chase". Use this for a question about one named player rather than a list."""
    league = league_singleton()
    player = league.player_info(name=name)
    if player is None:
        return f"No player found matching '{name}'."
    return (f"{player.name} ({player.position}, {player.proTeam}) - "
            f"owned {player.percent_owned}%, started {player.percent_started}%, "
            f"proj {player.projected_total_points}, total {player.total_points}, "
            f"injury status {player.injuryStatus}")


TOOLS = [get_free_agents, get_player_info]
