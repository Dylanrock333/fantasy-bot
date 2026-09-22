"""Real-NFL data: league news headlines, transactions, and the draft
(ESPN's public API)."""
from langchain_core.tools import tool

from ..clients.espn_nfl_client import ATHLETE_API, SITE_API, best_link, get_json, resolve_athlete


@tool
def get_nfl_news(limit: int = 5) -> str:
    """Get the latest real-NFL headlines."""
    news = get_json(f"{SITE_API}/news")
    articles = news.get("articles", [])[:limit]
    if not articles:
        return "No news found."
    lines = [
        f"{a['headline']}: {a.get('description', '')}".strip(": ")
        for a in articles
    ]
    top_link = best_link(articles)
    text = "\n".join(lines)
    if top_link:
        text += f"\n\n{top_link}"
    return text


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


@tool
def get_player_news(player_name: str, pro_team: str, limit: int = 3) -> str:
    """Get the latest real-NFL news headlines specifically about one player
    (injuries, roles, outlook), not general league news. pro_team is that
    player's real NFL team abbreviation or name (e.g. 'DAL' or 'Cowboys') -
    get it from the player's proTeam field in a fantasy roster tool result
    first; this tool cannot search by name alone. Use get_nfl_news instead
    for general league-wide headlines."""
    athlete = resolve_athlete(pro_team, player_name)
    if athlete is None:
        return f"No NFL player matched '{player_name}' on team '{pro_team}'."

    overview = get_json(f"{ATHLETE_API}/athletes/{athlete['id']}/overview")
    articles = overview.get("news", [])[:limit]
    if not articles:
        return f"No recent news found for {athlete['fullName']}."

    lines = [
        f"{a['headline']}: {a.get('description', '')}".strip(": ")
        for a in articles
    ]
    top_link = best_link(articles)
    text = f"News for {athlete['fullName']}:\n" + "\n".join(lines)
    if top_link:
        text += f"\n\n{top_link}"
    return text


TOOLS = [get_nfl_news, get_player_news, get_nfl_transactions, get_nfl_draft]
