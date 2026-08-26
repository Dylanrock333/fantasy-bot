"""Fantasy league data: standings (current or as-of a given week), top/bottom
scorers, points against, power rankings, and lowest single-week score (your
private ESPN fantasy league via fantasy_espn/, not real-NFL data)."""
from langchain_core.tools import tool

from ..clients.fantasy_client import league_singleton


@tool
def get_standings(week: int = 0) -> str:
    """Get fantasy league standings (record, points for/against), sorted by rank. Pass week (e.g. 3) to get standings as of that week; omit or pass 0 for current standings. Before any matchup period has completed (preseason), both forms return the same unresolved list."""
    league = league_singleton()
    teams = league.standings_weekly(week) if week else league.standings()
    lines = []
    for i, team in enumerate(teams, start=1):
        lines.append(
            f"{i}. {team.team_name} ({team.wins}-{team.losses}-{team.ties}) "
            f"PF:{team.points_for} PA:{team.points_against}"
        )
    return "\n".join(lines) or "No standings available yet."


@tool
def get_top_scorer() -> str:
    """Get the fantasy team with the most total points scored this season. Preseason, all teams are tied at 0.0 points, so the result is arbitrary until games are played."""
    league = league_singleton()
    team = league.top_scorer()
    return f"Top scorer: {team.team_name} with {team.points_for} points for."


@tool
def get_least_scorer() -> str:
    """Get the fantasy team with the fewest total points scored this season. Preseason, all teams are tied at 0.0 points, so the result is arbitrary until games are played."""
    league = league_singleton()
    team = league.least_scorer()
    return f"Lowest scorer: {team.team_name} with {team.points_for} points for."


@tool
def get_most_points_against() -> str:
    """Get the fantasy team that has had the most total points scored against it this season. Preseason, all teams are tied at 0.0 points against, so the result is arbitrary until games are played."""
    league = league_singleton()
    team = league.most_points_against()
    return f"Most points against: {team.team_name} with {team.points_against} points against."


@tool
def get_power_rankings() -> str:
    """Get the fantasy league's power rankings for the current week, blending head-to-head dominance, average score, and average margin of victory into one ranked list. Preseason (no games played), every team scores '0.00' and the order is not meaningful."""
    league = league_singleton()
    rankings = league.power_rankings()
    lines = [
        f"{i}. {team.team_name} (power score: {score})"
        for i, (score, team) in enumerate(rankings, start=1)
    ]
    return "\n".join(lines) or "No power rankings available yet."


@tool
def get_least_scored_week() -> str:
    """Get the fantasy team and week with the single lowest weekly score so far this season."""
    league = league_singleton()
    try:
        team, score = league.least_scored_week()
    except ValueError:
        return "No weekly low score yet — season hasn't started."
    return f"Lowest single-week score: {team.team_name} with {score} points."


TOOLS = [
    get_standings,
    get_top_scorer,
    get_least_scorer,
    get_most_points_against,
    get_power_rankings,
    get_least_scored_week,
]
