"""Singletons shared across category tool modules."""
from fantasy_espn.espn_client import get_league

_league = None


def league_singleton():
    global _league
    if _league is None:
        _league = get_league()
    return _league
