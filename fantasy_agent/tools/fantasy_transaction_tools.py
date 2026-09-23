"""Fantasy league data: transactions and activity (adds/drops/trades/waivers
in your private league via clients/espn_fantasy_client.py, not real-NFL transactions)."""
from langchain_core.tools import tool

from ..clients.espn_fantasy_client import league_singleton


@tool
def get_recent_activity(size: int = 10) -> str:
    """Get recent fantasy league activity: adds, drops, trades, waiver claims."""
    league = league_singleton()
    lines = []
    for act in league.recent_activity(size=size):
        for team, action, player, bid in act.actions:
            lines.append(f"[{act.date}] {team} {action} {player} (bid={bid})")
    return "\n".join(lines) or "No recent activity."


TOOLS = [get_recent_activity]
