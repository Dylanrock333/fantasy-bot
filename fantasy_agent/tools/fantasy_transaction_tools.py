"""Fantasy league data: transactions and activity (adds/drops/trades/waivers
in your private league via fantasy_espn/, not real-NFL transactions)."""
from langchain_core.tools import tool

from ..clients.fantasy_client import league_singleton


@tool
def get_recent_activity(size: int = 10) -> str:
    """Get recent fantasy league activity: adds, drops, trades, waiver claims."""
    league = league_singleton()
    lines = []
    for act in league.recent_activity(size=size):
        for team, action, player, bid in act.actions:
            lines.append(f"[{act.date}] {team} {action} {player} (bid={bid})")
    return "\n".join(lines) or "No recent activity."


@tool
def get_transactions(scoring_period: int = 0) -> str:
    """Get fantasy league transactions (waiver claims, free-agent adds/drops) for a scoring period. Use scoring_period=0 (default) for the current/latest period, or pass a specific week number to check a past period."""
    league = league_singleton()
    try:
        transactions = league.transactions(scoring_period=scoring_period or None)
    except Exception as e:
        if "No transactions found" in str(e):
            return "No transactions found for this scoring period."
        raise
    lines = []
    for t in transactions:
        items = ", ".join(f"{i.type} {i.player}" for i in t.items)
        lines.append(f"[{t.date}] {t.team} {t.type} ({t.status}): {items}")
    return "Transactions:\n" + "\n".join(lines)


TOOLS = [get_recent_activity, get_transactions]
