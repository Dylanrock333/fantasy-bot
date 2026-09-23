"""Matchup preview graph: projected matchups + lineup-change flags -> LLM preview -> scoreboard image.

  START -> get_matchup_data -> flag_lineup_changes -> matchup_preview -> matchup_image -> END
"""
import time
from typing import List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from fantasy_agent.clients.espn_fantasy_client import league_singleton
from fantasy_agent.graphs.graph import invoke_llm, MODEL
from fantasy_agent.logging.trace import emit
from fantasy_agent.utils.openai_image_gen import generate_image

# Lineup slots that do not count as starting.
BENCH_SLOTS = ("BE", "IR")


# State carried through the preview graph.
class MatchupPreviewState(TypedDict):
    week: int
    previous_recap_context: Optional[str]
    matchups: List[dict]
    lineup_flags: dict
    league_preview: str
    matchup_image: Optional[bytes]


def get_matchup_data_node(state: MatchupPreviewState):
    """Collect each matchup's projections, records, projected winner and margin."""
    league = league_singleton()
    week = state.get("week") or league.current_week
    box_scores = league.box_scores(week=week)
    records = {
        t.team_name: f"{t.wins}-{t.losses}-{t.ties}" for t in league.standings()
    }

    matchups = []
    for b in box_scores:
        home, away = str(b.home_team), str(b.away_team)
        proj_home, proj_away = round(b.home_projected, 2), round(b.away_projected, 2)
        margin = round(abs(proj_home - proj_away), 2)
        winner = home if proj_home >= proj_away else away
        matchups.append({
            "team_a": home, "proj_a": proj_home, "record_a": records.get(home, ""),
            "team_b": away, "proj_b": proj_away, "record_b": records.get(away, ""),
            "winner": winner, "margin": margin,
        })

    return {"week": week, "matchups": matchups}


def flag_lineup_changes_node(state: MatchupPreviewState):
    """Flag last week's zero-point starters (non-bye) and whether they were benched or dropped."""
    week = state["week"]
    last_week = week - 1
    if last_week < 1:
        return {"lineup_flags": {}}

    league = league_singleton()
    last_box_scores = league.box_scores(week=last_week)
    this_box_scores = league.box_scores(week=week)

    # Starters who scored zero last week, by team.
    duds_by_team: dict[str, list] = {}
    for b in last_box_scores:
        for team, lineup in ((b.home_team, b.home_lineup), (b.away_team, b.away_lineup)):
            duds = [
                p for p in lineup
                if p.slot_position not in BENCH_SLOTS
                and not p.on_bye_week
                and p.points == 0
            ]
            if duds:
                duds_by_team.setdefault(str(team), []).extend(duds)

    # This week's full roster and starters, by team.
    roster_by_team, starting_by_team = {}, {}
    for b in this_box_scores:
        for team, lineup in ((b.home_team, b.home_lineup), (b.away_team, b.away_lineup)):
            roster_by_team[str(team)] = {p.name for p in lineup}
            starting_by_team[str(team)] = {
                p.name for p in lineup if p.slot_position not in BENCH_SLOTS
            }

    flags: dict[str, list[dict]] = {}
    for team, duds in duds_by_team.items():
        team_flags = []
        for player in duds:
            if player.name not in roster_by_team.get(team, set()):
                status = "dropped/traded away"
            elif player.name not in starting_by_team.get(team, set()):
                status = "benched"
            else:
                status = "still starting despite the zero"
            flag = {"player": player.name, "status": status}
            injury = getattr(player, "injuryStatus", None)
            if injury and injury not in ("ACTIVE", "NORMAL"):
                flag["injury_status"] = injury
            team_flags.append(flag)
        flags[team] = team_flags

    return {"lineup_flags": flags}


# Structured LLM output for the preview (field description is sent to the LLM).
class MatchupPreviewOutput(BaseModel):
    league_preview: str = Field(
        description="A look ahead to this week, with one beat per matchup "
        "given - every matchup gets a beat, no exceptions, so every team "
        "name appears at least once. Each beat is exactly one punchy, "
        "unhinged joke sentence naming both teams in that matchup, "
        "separated from the next beat by a blank line (double newline) - "
        "NOT one dense paragraph. Go for the hardest, most surprising "
        "joke available (projection gap, records, a flagged player who "
        "scored a donut/got hurt/got benched/got dropped last week) "
        "rather than a safe factual recap with an insult tacked on - "
        "don't force a player mention into a beat if there's no flagged "
        "player for that matchup, a good projection-gap or record roast "
        "works fine on its own. Max unhinged, no filter, borderline "
        "deranged, same voice as the weekly recap. Wrap every team name "
        "in markdown bold (**Team Name**) each time it appears. Every "
        "fact must come from the data given, never invented."
    )


def matchup_preview_node(state: MatchupPreviewState):
    """Write one joke beat per matchup, optionally calling back to last week's recap."""
    emit("node_start", node="matchup_preview")
    t0 = time.monotonic()

    matchup_lines = []
    for m in state["matchups"]:
        line = (
            f"- {m['team_a']} ({m['record_a']}) proj {m['proj_a']} vs "
            f"{m['team_b']} ({m['record_b']}) proj {m['proj_b']} - "
            f"projected winner {m['winner']} by {m['margin']}"
        )
        for team in (m["team_a"], m["team_b"]):
            for flag in state["lineup_flags"].get(team, []):
                injury = f", injury status {flag['injury_status']}" if flag.get("injury_status") else ""
                line += f"; {team} - {flag['player']} scored 0 last week{injury}, now {flag['status']}"
        matchup_lines.append(line)

    system = SystemMessage(content=(
        "You are the voice of a fantasy football league's Thursday "
        "matchup-preview channel, written for the same rowdy, joke-heavy "
        "group chat as the weekly recap - but looking ahead to this "
        "week's games instead of back at last week's results. Every "
        "fact must come from the data below, never invented:\n\n"
        "league_preview: one joke beat per matchup given, covering every "
        "matchup so every team gets named - close matchups, projected "
        "blowouts, records worth noting, and any panic roster moves "
        "after a zero last week. Max unhinged, no filter, borderline "
        "deranged, same voice as the recap.\n\n"
        "If last week's recap is provided below, use it as color - "
        "callback a player, storyline, or team from it where it's "
        "actually relevant to this week's matchup, don't force it into "
        "every line."
    ))
    prompt_text = ""
    if state.get("previous_recap_context"):
        prompt_text += state["previous_recap_context"] + "\n\n"
    prompt_text += (
        f"Week {state['week']} projected matchups:\n" + "\n".join(matchup_lines)
    )
    prompt = HumanMessage(content=prompt_text)

    def _llm(key):
        return ChatGoogleGenerativeAI(
            model=MODEL, google_api_key=key, reasoning_effort="high"
        ).with_structured_output(MatchupPreviewOutput)

    result = invoke_llm(_llm, [system, prompt])

    emit("node_end", node="matchup_preview", duration_ms=int((time.monotonic() - t0) * 1000))
    return {
        "league_preview": result.league_preview.strip(),
        "matchups": state["matchups"],
    }


def matchup_image_node(state: MatchupPreviewState):
    """Generate the scoreboard graphic; leaves the image as None if generation fails."""
    emit("node_start", node="matchup_image")
    t0 = time.monotonic()

    league_name = league_singleton().settings.name

    rows = []
    for i, m in enumerate(state["matchups"], start=1):
        rows.append(
            f"{i}. {m['team_a']} ({m['record_a']}), projected {m['proj_a']} "
            f"points, versus {m['team_b']} ({m['record_b']}), projected "
            f"{m['proj_b']} points. {m['winner']} is favored by {m['margin']} "
            "points."
        )

    prompt = (
        "Design a bold, eye-catching scoreboard-style graphic previewing "
        f"this fantasy football league's Week {state['week']} matchups. "
        "Dark background with punchy, high-contrast sports-broadcast "
        "energy - think ESPN/ticker graphics, ESPN Fantasy scoreboard, or "
        "a hype sports betting odds board: bold condensed headline type, "
        "sharp angled dividers or diagonal accent shapes, glowing or "
        "neon-edged accent colors, subtle gradients or light streaks "
        "behind the title. A single table with one row per matchup and "
        "columns for Matchup #, Team A, Record, Proj, Team B, Record, "
        "Proj, Margin - no separate Winner column, the higher projected "
        "score already shows who's favored. Print each team's name in "
        "the table exactly as spelled in the matchup description below, "
        "as plain readable text, the same way a real broadcast graphic "
        "prints a team name - nothing else attached to it, no field "
        "labels, no surrounding punctuation or symbols beyond what's in "
        "the name itself. Copy every number (projection, margin, "
        "record) exactly as given, never invented or rounded "
        "differently. Give the projected winner's score in each row the "
        "higher of the two projections - more visual weight "
        "(bolder/brighter) than the loser's so the table reads at a "
        "glance. No illustrated mascot characters, but a small bold "
        "flat-icon team badge per row is welcome if it fits. Put the "
        f"league name, \"{league_name}\", as the main header in large, "
        "bold, stylized lettering at the top of the graphic. At the "
        "bottom, in noticeably smaller text, print "
        f"'WEEK {state['week']} FANTASY PROJECTIONS'.\n\n"
        "Matchups:\n" + "\n".join(rows)
    )

    image_bytes = None
    try:
        image_bytes = generate_image(prompt, size="1536x1024")
    except Exception as err:
        emit("node_error", node="matchup_image", error=str(err))

    emit("node_end", node="matchup_image", duration_ms=int((time.monotonic() - t0) * 1000))
    return {"matchup_image": image_bytes}


def build_matchup_preview_graph():
    """Wire and compile the linear matchup preview graph."""
    graph = StateGraph(MatchupPreviewState)
    graph.add_node("get_matchup_data", get_matchup_data_node)
    graph.add_node("flag_lineup_changes", flag_lineup_changes_node)
    graph.add_node("matchup_preview", matchup_preview_node)
    graph.add_node("matchup_image", matchup_image_node)

    graph.add_edge(START, "get_matchup_data")
    graph.add_edge("get_matchup_data", "flag_lineup_changes")
    graph.add_edge("flag_lineup_changes", "matchup_preview")
    graph.add_edge("matchup_preview", "matchup_image")
    graph.add_edge("matchup_image", END)

    return graph.compile()
