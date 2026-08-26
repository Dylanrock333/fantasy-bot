"""Teams & Rosters
Covers: league.teams, Team attributes, team.roster, team.schedule/scores/
outcomes/mov, get_team_data(), team.get_player_name(), load_roster_week()

Run: python 02_teams_and_rosters.py
"""
from fantasy_espn.espn_client import get_league


def main():
    league = get_league()

    print("=" * 60)
    print("ALL TEAMS - league.teams")
    print("=" * 60)
    for team in league.teams:
        print(f"{team.team_id}: {team.team_name} ({team.team_abbrev}) "
              f"- Division: {team.division_name}")

    print()
    print("=" * 60)
    print("TEAM DETAIL (first team) - Team attributes")
    print("=" * 60)
    team = league.teams[0]
    print(f"team_name: {team.team_name}")
    print(f"team_abbrev: {team.team_abbrev}")
    print(f"division_id / division_name: {team.division_id} / {team.division_name}")
    print(f"record: {team.wins}-{team.losses}-{team.ties}")
    print(f"points_for / points_against: {team.points_for} / {team.points_against}")
    print(f"standing / final_standing: {team.standing} / {team.final_standing}")
    print(f"streak: {team.streak_type} x{team.streak_length}")
    print(f"waiver_rank: {team.waiver_rank}")
    print(f"acquisitions/drops/trades/move_to_ir: "
          f"{team.acquisitions}/{team.drops}/{team.trades}/{team.move_to_ir}")
    print(f"acquisition_budget_spent: {team.acquisition_budget_spent}")
    print(f"playoff_pct: {team.playoff_pct}")
    print(f"draft_projected_rank: {team.draft_projected_rank}")
    print(f"logo_url: {team.logo_url}")
    print(f"owners: {team.owners}")
    print(f"stats (subset): {dict(list(team.stats.items())[:5])}")

    print()
    print("=" * 60)
    print("ROSTER - team.roster")
    print("=" * 60)
    for player in team.roster:
        print(f"  {player.lineupSlot:>6} | {player.name} ({player.position}, {player.proTeam}) "
              f"- {player.total_points} pts, proj {player.projected_total_points}")

    print()
    print("=" * 60)
    print("SCHEDULE / SCORES / OUTCOMES / MOV - team.schedule / .scores / .outcomes / .mov")
    print("=" * 60)
    for week, (opp, score, outcome, mov) in enumerate(
        zip(team.schedule, team.scores, team.outcomes, team.mov), start=1
    ):
        print(f"Week {week}: vs {opp.team_name} | {score} pts | {outcome} | MOV {mov}")

    print()
    print("=" * 60)
    print("GET_TEAM_DATA - league.get_team_data(team_id)")
    print("=" * 60)
    found = league.get_team_data(team.team_id)
    print(f"Looked up team_id {team.team_id}: {found}")

    print()
    print("=" * 60)
    print("GET_PLAYER_NAME - team.get_player_name(playerId)")
    print("=" * 60)
    if team.roster:
        pid = team.roster[0].playerId
        print(f"Player name for id {pid}: {team.get_player_name(pid)}")
    else:
        print("Roster is empty, nothing to look up.")

    print()
    print("=" * 60)
    print(f"LOAD_ROSTER_WEEK - league.load_roster_week({league.current_week})")
    print("=" * 60)
    league.load_roster_week(league.current_week)
    print("Roster reloaded for current week; team.roster mutated in place.")


if __name__ == "__main__":
    main()
