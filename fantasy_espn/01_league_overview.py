"""League Overview & Standings
Covers: league.settings, standings(), standings_weekly(), top_scorer(),
least_scorer(), most_points_against(), top_scored_week(), least_scored_week(),
power_rankings(), refresh()

Run: python 01_league_overview.py
"""
from fantasy_espn.espn_client import get_league


def main():
    league = get_league()

    print("=" * 60)
    print("LEAGUE SETTINGS - league.settings")
    print("=" * 60)
    s = league.settings
    print(f"Name: {s.name}")
    print(f"Team count: {s.team_count}")
    print(f"Regular season weeks: {s.reg_season_count}")
    print(f"Playoff teams: {s.playoff_team_count}")
    print(f"Playoff matchup length: {s.playoff_matchup_period_length}")
    print(f"Veto votes required: {s.veto_votes_required}")
    print(f"Keeper count: {s.keeper_count}")
    print(f"Trade deadline (epoch ms): {s.trade_deadline}")
    print(f"Division map: {s.division_map}")
    print(f"Tie rule: {s.tie_rule}")
    print(f"Playoff tie rule: {s.playoff_tie_rule}")
    print(f"Playoff seed tie rule: {s.playoff_seed_tie_rule}")
    print(f"Scoring type: {s.scoring_type}")
    print(f"Median scoring enabled: {s.median_scoring}")
    print(f"FAAB enabled: {s.faab}")
    print(f"Acquisition budget: {s.acquisition_budget}")
    print(f"Position slot counts: {s.position_slot_counts}")
    print(f"Scoring format (first 5): {s.scoring_format[:5]}")

    print()
    print("=" * 60)
    print("LEAGUE STATE")
    print("=" * 60)
    print(f"Current matchup period: {league.currentMatchupPeriod}")
    print(f"Current scoring period: {league.scoringPeriodId}")
    print(f"Current week: {league.current_week}")
    print(f"NFL week: {league.nfl_week}")
    print(f"First/final scoring period: {league.firstScoringPeriod} / {league.finalScoringPeriod}")
    print(f"Previous seasons: {league.previousSeasons}")

    print()
    print("=" * 60)
    print("STANDINGS - league.standings()")
    print("=" * 60)
    for i, team in enumerate(league.standings(), start=1):
        print(f"{i}. {team.team_name} ({team.wins}-{team.losses}-{team.ties}) "
              f"PF:{team.points_for} PA:{team.points_against}")

    print()
    print("=" * 60)
    print(f"STANDINGS AS OF WEEK {league.current_week} - league.standings_weekly(week)")
    print("=" * 60)
    for i, team in enumerate(league.standings_weekly(league.current_week), start=1):
        print(f"{i}. {team.team_name}")

    print()
    print("=" * 60)
    print("LEAGUE LEADERS")
    print("=" * 60)
    print(f"Top scorer (top_scorer()): {league.top_scorer()}")
    print(f"Least scorer (least_scorer()): {league.least_scorer()}")
    print(f"Most points against (most_points_against()): {league.most_points_against()}")

    try:
        top_team, top_score = league.top_scored_week()
        print(f"Top scored week (top_scored_week()): {top_team} - {top_score} pts")

        least_team, least_score = league.least_scored_week()
        print(f"Least scored week (least_scored_week()): {least_team} - {least_score} pts")
    except ValueError:
        print("top_scored_week()/least_scored_week() need at least one completed "
              "week of scores - season hasn't started yet.")

    print()
    print("=" * 60)
    print("POWER RANKINGS - league.power_rankings()")
    print("=" * 60)
    for rank, team in league.power_rankings():
        print(f"{rank}: {team}")

    print()
    print("=" * 60)
    print("REFRESH - league.refresh()")
    print("=" * 60)
    league.refresh()
    print("League data refreshed successfully.")


if __name__ == "__main__":
    main()
