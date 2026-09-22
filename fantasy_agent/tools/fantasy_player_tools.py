"""Fantasy league data: free agents, single-player lookup by name, ownership/points
(private league via clients/espn_fantasy_client.py - for real-NFL athlete stats see nfl_player_tools.py)."""
from langchain_core.tools import tool

from ..clients.espn_fantasy_client import league_singleton


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


SORT_KEYS = {
    "points": lambda p: p.total_points,
    "avg_points": lambda p: p.avg_points,
    "projected_points": lambda p: p.projected_total_points,
    "percent_owned": lambda p: p.percent_owned,
}


def get_player_leaderboard(position: str, size: int = 15, sort_by: str = "points") -> list[dict]:
    """Return the top `size` fantasy players at `position` (e.g. 'QB', 'RB',
    'WR', 'TE', 'D/ST', 'K') ranked by `sort_by` (one of SORT_KEYS above,
    defaulting to season total points), across both rostered and
    free-agent players. `owner_team_name` is None for players nobody in the
    league owns. Plain data helper for the REST API - not registered as an
    LLM tool."""
    league = league_singleton()
    position = position.upper()
    sort_key = SORT_KEYS.get(sort_by, SORT_KEYS["points"])

    rostered = [
        (player, team.team_name)
        for team in league.teams
        for player in team.roster
        if player.position == position
    ]
    free_agents = [(player, None) for player in league.free_agents(size=1000, position=position)]

    ranked = sorted(rostered + free_agents, key=lambda pair: sort_key(pair[0]), reverse=True)[:size]

    return [
        {
            "rank": i + 1,
            "name": player.name,
            "pro_team": player.proTeam,
            "total_points": player.total_points,
            "avg_points": player.avg_points,
            "projected_total_points": player.projected_total_points,
            "percent_owned": player.percent_owned,
            "owner_team_name": owner_team_name,
        }
        for i, (player, owner_team_name) in enumerate(ranked)
    ]
