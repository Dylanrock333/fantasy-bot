"""Fantasy league data: your teams' rosters, league rules/settings, and
draft results (private league via fantasy_espn/, not real-NFL rosters/depth
charts)."""
from datetime import datetime

from langchain_core.tools import tool

from ..clients.fantasy_client import league_singleton


@tool
def get_team_roster(team_name: str) -> str:
    """Get the fantasy roster for one of your league's teams. team_name can
    be a partial match, e.g. 'Cowboys' or part of the manager's team name."""
    league = league_singleton()
    q = team_name.strip().lower()
    team = next((t for t in league.teams if q in t.team_name.lower()), None)
    if team is None:
        names = ", ".join(t.team_name for t in league.teams)
        return f"No fantasy team matched '{team_name}'. Known teams: {names}"
    if not team.roster:
        return f"{team.team_name} has no players on its roster yet."
    lines = [f"{p.name} ({p.position}, {p.proTeam}) - {p.total_points} pts, "
             f"proj {p.projected_total_points}, status={p.injuryStatus}"
             for p in team.roster]
    return f"{team.team_name} roster:\n" + "\n".join(lines)


@tool
def get_league_settings() -> str:
    """Get this fantasy league's rules: name, size, scoring type, playoff
    format, and starting roster slot counts (e.g. how many RB/WR/FLEX
    starters). Use this for "how does this league work" style questions."""
    league = league_singleton()
    s = league.settings
    starters = ", ".join(
        f"{count} {slot}" for slot, count in s.position_slot_counts.items()
        if count and slot not in ("BE", "IR")
    )
    bench = s.position_slot_counts.get("BE", 0)
    ir = s.position_slot_counts.get("IR", 0)
    deadline = datetime.fromtimestamp(s.trade_deadline / 1000).strftime("%Y-%m-%d")
    return (
        f"{s.name}: {s.team_count} teams, {s.scoring_type} scoring, "
        f"{s.playoff_team_count} playoff teams over {s.reg_season_count} "
        f"regular season weeks.\nStarters: {starters}. Bench: {bench}, IR: {ir}.\n"
        f"Trade deadline: {deadline}."
    )


@tool
def get_draft_results() -> str:
    """Get the results of this league's draft (who picked which player,
    round/pick number). Returns a friendly message if the draft hasn't
    happened yet."""
    league = league_singleton()
    picks = league.draft
    if not picks:
        return "This league's draft hasn't happened yet."
    lines = [f"Round {p.round_num}, Pick {p.round_pick}: {p.team.team_name} "
              f"selected {p.playerName}" for p in picks]
    return "Draft results:\n" + "\n".join(lines)


TOOLS = [get_team_roster, get_league_settings, get_draft_results]
