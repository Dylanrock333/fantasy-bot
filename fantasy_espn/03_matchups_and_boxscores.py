"""Matchups & Box Scores
Covers: league.scoreboard(), league.box_scores(), BoxScore lineup detail

Run: python 03_matchups_and_boxscores.py
"""
from fantasy_espn.espn_client import get_league


def main():
    league = get_league()
    # current_week is 0 before the season starts; box_scores/scoreboard
    # need a real week number, so fall back to week 1.
    week = league.current_week or 1

    print("=" * 60)
    print(f"SCOREBOARD - league.scoreboard(week={week})")
    print("=" * 60)
    for m in league.scoreboard(week=week):
        print(f"{m.home_team} {m.home_score} - {m.away_score} {m.away_team} "
              f"| playoff={m.is_playoff} ({m.matchup_type})")

    print()
    print("=" * 60)
    print(f"BOX SCORES - league.box_scores(week={week})")
    print("=" * 60)
    box_scores = []
    try:
        box_scores = league.box_scores(week=week)
        for bs in box_scores:
            print(f"{bs.home_team} {bs.home_score} (proj {bs.home_projected}) vs "
                  f"{bs.away_team} {bs.away_score} (proj {bs.away_projected})")
    except KeyError:
        print("box_scores() needs rosters to exist for the week - this league "
              "hasn't drafted yet, so ESPN has no roster data to return.")

    if box_scores and box_scores[0].home_lineup:
        print()
        print("=" * 60)
        print("BOX SCORE LINEUP DETAIL (first matchup, home lineup) - bs.home_lineup")
        print("=" * 60)
        for player in box_scores[0].home_lineup:
            print(f"  {player.slot_position:>4} | {player.name} - {player.points} pts "
                  f"(proj {player.projected_points}) vs {player.pro_opponent} "
                  f"| bye={player.on_bye_week}")
    else:
        print("\nNo lineup data yet for this matchup period.")


if __name__ == "__main__":
    main()
