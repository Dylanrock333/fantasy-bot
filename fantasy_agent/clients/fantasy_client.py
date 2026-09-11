"""League clients shared across category tool modules, cached per league_id."""
from fantasy_espn.espn_client import current_league_id, get_league

_leagues: dict[int, object] = {}


def league_singleton():
    league_id = current_league_id.get()
    if league_id not in _leagues:
        _leagues[league_id] = get_league(league_id)
    return _leagues[league_id]
