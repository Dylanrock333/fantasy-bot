"""Players, Free Agents & Draft
Covers: league.free_agents(), league.player_info() (by name and by id),
league.draft, league.refresh_draft()

Run: python 04_players_free_agents_draft.py
"""
from fantasy_espn.espn_client import get_league


def main():
    league = get_league()

    print("=" * 60)
    print("FREE AGENTS - league.free_agents(size=10)")
    print("=" * 60)
    free_agents = league.free_agents(size=10)
    for p in free_agents:
        print(f"{p.name} ({p.position}, {p.proTeam}) - owned {p.percent_owned}% "
              f"| proj {p.projected_points}")

    print()
    print("=" * 60)
    print("FREE AGENTS BY POSITION - league.free_agents(position='RB', size=5)")
    print("=" * 60)
    for p in league.free_agents(position="RB", size=5):
        print(f"{p.name} ({p.proTeam}) - owned {p.percent_owned}%")

    sample_player = free_agents[0] if free_agents else None

    print()
    print("=" * 60)
    print("PLAYER_INFO BY NAME - league.player_info(name=...)")
    print("=" * 60)
    if sample_player:
        player = league.player_info(name=sample_player.name)
        print(f"{player.name}: total_points={player.total_points}, "
              f"position={player.position}, proTeam={player.proTeam}")
    else:
        print("No free agents available to sample from.")

    print()
    print("=" * 60)
    print("PLAYER_INFO BY ID - league.player_info(playerId=...)")
    print("=" * 60)
    if sample_player:
        player = league.player_info(playerId=sample_player.playerId)
        print(f"{player.name}: injuryStatus={player.injuryStatus}, "
              f"eligibleSlots={player.eligibleSlots}")
    else:
        print("No free agents available to sample from.")

    print()
    print("=" * 60)
    print("DRAFT - league.draft")
    print("=" * 60)
    if league.draft:
        for pick in league.draft[:10]:
            print(f"R{pick.round_num} P{pick.round_pick}: {pick.team} selects "
                  f"{pick.playerName} (bid={pick.bid_amount}, keeper={pick.keeper_status})")
    else:
        print("No draft data yet (league hasn't drafted this season).")

    print()
    print("=" * 60)
    print("REFRESH_DRAFT - league.refresh_draft()")
    print("=" * 60)
    league.refresh_draft()
    print(f"Draft refreshed. Picks so far: {len(league.draft)}")


if __name__ == "__main__":
    main()
