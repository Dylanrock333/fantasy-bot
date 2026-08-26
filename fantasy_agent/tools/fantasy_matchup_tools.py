"""Fantasy league data: matchups, box scores, and week/period info (private
league via fantasy_espn/, not real-NFL games)."""
from langchain_core.tools import tool

from ..clients.fantasy_client import league_singleton


@tool
def get_matchup_scoreboard(week: int = 0) -> str:
    """Get this fantasy league's matchup scores for a given week (defaults
    to the current week)."""
    league = league_singleton()
    week = week or league.current_week or 1
    matchups = league.scoreboard(week=week)
    if not matchups:
        return f"No matchups found for week {week}."
    lines = [f"{m.home_team} {m.home_score} - {m.away_score} {m.away_team}"
             for m in matchups]
    return f"Week {week} matchups:\n" + "\n".join(lines)


@tool
def get_box_scores(week: int = 0) -> str:
    """Get full box scores for a given week (defaults to the current week),
    including both teams' complete starting lineups (plus bench/IR) with
    each player's scored and projected points."""
    league = league_singleton()
    week = week or league.current_week or 1
    try:
        box_scores = league.box_scores(week=week)
    except KeyError:
        return (f"No box scores available yet for week {week} — the league "
                "hasn't drafted, so ESPN has no roster data.")
    if not box_scores:
        return f"No box scores found for week {week}."
    lines = [f"{b.home_team} {b.home_score} ({b.home_projected} proj) - "
             f"{b.away_score} ({b.away_projected} proj) {b.away_team}"
             for b in box_scores]
    return f"Week {week} box scores:\n" + "\n".join(lines)


@tool
def get_current_week() -> str:
    """Get this fantasy league's current-week info: the fantasy matchup
    period, ESPN's live scoring period, the library's clamped default week,
    and the real-world NFL's latest scoring period. Useful for checking
    whether the season/league has started before calling other matchup
    tools (all four read 0 during the preseason, before any games)."""
    league = league_singleton()
    return (f"Fantasy matchup period: {league.currentMatchupPeriod}, "
            f"ESPN scoring period: {league.scoringPeriodId}, "
            f"league current week: {league.current_week}, "
            f"NFL latest week: {league.nfl_week}.")


@tool
def get_top_scored_week() -> str:
    """Get the single highest-scoring team/week combo so far this season,
    looking across every team's per-week score history through the current
    week."""
    league = league_singleton()
    try:
        team, score = league.top_scored_week()
    except ValueError:
        return "No top scored week available yet — no weeks have been played this season."
    return f"Top scored week so far: {team} with {score} points."


TOOLS = [get_matchup_scoreboard, get_box_scores, get_current_week, get_top_scored_week]
