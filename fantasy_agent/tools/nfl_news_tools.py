"""Real-NFL data: league news headlines, transactions, and the draft (public
espn_nfl_public/ API)."""
from langchain_core.tools import tool

from ..clients.nfl_client import SITE_API, get_json


@tool
def get_nfl_news(limit: int = 5) -> str:
    """Get the latest real-NFL headlines."""
    news = get_json(f"{SITE_API}/news")
    headlines = [a["headline"] for a in news.get("articles", [])[:limit]]
    return "\n".join(headlines) or "No news found."


@tool
def get_nfl_transactions(limit: int = 10) -> str:
    """Get the most recent real-NFL roster transactions (signings, trades,
    waivers, IR moves) league-wide, newest first. limit caps how many to
    return."""
    data = get_json(f"{SITE_API}/transactions", limit=limit)
    txns = data.get("transactions", [])
    if not txns:
        return "No recent NFL transactions found."
    lines = [f"{t['date']} ({t['team']['abbreviation']}): {t['description']}"
              for t in txns]
    return "Recent NFL transactions:\n" + "\n".join(lines)


@tool
def get_nfl_draft(limit: int = 32) -> str:
    """Get the current real-NFL draft board - picks in order with prospect,
    college, position, and drafting team. limit caps how many picks to
    return, e.g. limit=32 for just round 1 (257 total picks across 7
    rounds)."""
    data = get_json(f"{SITE_API}/draft")
    picks = data.get("picks", [])
    if not picks:
        return "No draft picks found."
    team_abbrs = {t["id"]: t["abbreviation"] for t in data.get("teams", [])}
    lines = [
        f"Pick {p['pick']} (Rd {p['round']}): {p['athlete']['displayName']} "
        f"({p['athlete'].get('team', {}).get('abbreviation', '?')}) -> "
        f"{team_abbrs.get(p['teamId'], p['teamId'])}"
        for p in picks[:limit]
    ]
    return f"{data.get('displayName', 'NFL Draft')}:\n" + "\n".join(lines)


TOOLS = [get_nfl_news, get_nfl_transactions, get_nfl_draft]
