"""Refreshes stale cached fantasy-league state. Meant to be called on a
timer (~15 min) - the timer/scheduler itself isn't wired up yet.

Per FANTASY_ESPN_API_CHECKLIST.md, league.refresh() is the only call needed:
it's the sole method that overwrites the league.teams/settings/draft
snapshot that the "cached"-network methods (standings, top_scorer,
least_scorer, most_points_against, top_scored_week, least_scored_week,
standings_weekly, get_team_data) read from. Every other method already hits
ESPN live on every call, so there's nothing else that goes stale.
"""
from .fantasy_client import league_singleton


def refresh_all() -> None:
    league_singleton().refresh()
