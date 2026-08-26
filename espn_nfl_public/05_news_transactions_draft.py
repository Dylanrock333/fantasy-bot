"""News, Transactions & Draft
Covers: league news, team news, athlete news, real-NFL transactions,
draft board (site + core), core free agents

Run: python 05_news_transactions_draft.py
"""
from nfl_client import SITE_API, CORE_API, get_json

TEAM_ID = 6  # Dallas Cowboys
ATHLETE_ID = 3918298
DRAFT_YEAR = 2025  # most recently completed draft as of 2026 preseason


def main():
    print("=" * 60)
    print("LEAGUE NEWS - GET /news")
    print("=" * 60)
    news = get_json(f"{SITE_API}/news")
    for article in news.get("articles", [])[:5]:
        print(f"  {article['headline']}")

    print()
    print("=" * 60)
    print(f"TEAM NEWS - GET /teams/{TEAM_ID}/news")
    print("=" * 60)
    team_news = get_json(f"{SITE_API}/teams/{TEAM_ID}/news")
    for article in team_news.get("articles", [])[:5]:
        print(f"  {article['headline']}")

    print()
    print("=" * 60)
    print(f"ATHLETE NEWS - GET /athletes/{ATHLETE_ID}/news")
    print("=" * 60)
    try:
        athlete_news = get_json(f"{SITE_API}/athletes/{ATHLETE_ID}/news")
        for article in athlete_news.get("articles", [])[:5]:
            print(f"  {article['headline']}")
    except Exception as e:
        print(f"no athlete news for id {ATHLETE_ID}: {e}")

    print()
    print("=" * 60)
    print("TRANSACTIONS - GET /transactions (real NFL, not fantasy)")
    print("=" * 60)
    transactions = get_json(f"{SITE_API}/transactions")
    print(f"count={transactions.get('count')}")
    for t in transactions.get("transactions", [])[:5]:
        print(f"  [{t['date']}] {t['team']['location']}: {t['description']}")

    print()
    print("=" * 60)
    print("DRAFT (site API) - GET /draft")
    print("=" * 60)
    try:
        draft = get_json(f"{SITE_API}/draft")
        print(f"Top-level keys: {list(draft.keys())[:6]}")
    except Exception as e:
        print(f"site draft lookup failed: {e}")

    print()
    print("=" * 60)
    print(f"DRAFT (core API) - GET core/.../seasons/{DRAFT_YEAR}/draft")
    print("=" * 60)
    draft_core = get_json(f"{CORE_API}/seasons/{DRAFT_YEAR}/draft")
    print(f"{draft_core.get('displayName')}: {draft_core.get('numberOfRounds')} rounds")

    print()
    print("=" * 60)
    print(f"FREE AGENTS (core API, real NFL) - GET core/.../seasons/{DRAFT_YEAR}/freeagents")
    print("=" * 60)
    free_agents = get_json(f"{CORE_API}/seasons/{DRAFT_YEAR}/freeagents", limit=5)
    print(f"count={free_agents.get('count')}, showing {len(free_agents.get('items', []))} refs")


if __name__ == "__main__":
    main()
