"""Transactions, Activity & Messages
Covers: league.recent_activity(), league.transactions(), league.message_board()

Run: python 05_transactions_and_activity.py
"""
from fantasy_espn.espn_client import get_league


def main():
    league = get_league()

    print("=" * 60)
    print("RECENT ACTIVITY - league.recent_activity(size=10)")
    print("=" * 60)
    for act in league.recent_activity(size=10):
        for team, action, player, bid in act.actions:
            print(f"[{act.date}] {team} {action} {player} (bid={bid})")

    print()
    print("=" * 60)
    print("RECENT ACTIVITY FILTERED - league.recent_activity(size=5, msg_type='WAIVER')")
    print("=" * 60)
    for act in league.recent_activity(size=5, msg_type="WAIVER"):
        for team, action, player, bid in act.actions:
            print(f"[{act.date}] {team} {action} {player} (bid={bid})")

    print()
    print("=" * 60)
    print("TRANSACTIONS - league.transactions()")
    print("=" * 60)
    try:
        for t in league.transactions():
            print(f"{t.team} | {t.type} | {t.status} | {t.items}")
    except Exception as e:
        print(f"No transactions found: {e}")

    print()
    print("=" * 60)
    print("MESSAGE BOARD - league.message_board()")
    print("=" * 60)
    messages = league.message_board()
    print(f"{len(messages)} messages found")
    for msg in messages[:5]:
        print(msg)


if __name__ == "__main__":
    main()
