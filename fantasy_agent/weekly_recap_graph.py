"""Weekly recap LangGraph flow: one funny recap per matchup (fanned out in
parallel via Send), then one league-wide summary once every recap is in.

  START -> get_matchups -> Send(recap_matchup) x N -> league_summary -> END

Standalone from graph.py's chat agent - this doesn't classify a user message
or call tools mid-conversation, it pulls box scores/standings directly and
writes straight to an LLM per matchup.
"""
import operator
import time
from typing import Annotated, List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from fantasy_agent.clients.fantasy_client import league_singleton
from fantasy_agent.graph import invoke_with_fallback, MODEL
from fantasy_agent.trace import emit
from langchain_google_genai import ChatGoogleGenerativeAI


class MatchupRecap(TypedDict):
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    winner: str
    recap: str


class WeeklyRecapState(TypedDict):
    week: int
    matchups: List[dict]
    matchup_recaps: Annotated[List[MatchupRecap], operator.add]
    league_summary: str


class _MatchupState(TypedDict):
    week: int
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    lineup_summary: str


def _format_lineup(team_name: str, lineup) -> str:
    lines = [f"{team_name}:"]
    for p in lineup:
        tag = "BENCH" if p.slot_position == "BE" else p.slot_position
        lines.append(
            f"  [{tag}] {p.name} - {p.points} pts (proj {p.projected_points})"
        )
    return "\n".join(lines)


def get_matchups_node(state: WeeklyRecapState):
    week = state["week"]
    league = league_singleton()
    week = week or league.current_week or 1
    box_scores = league.box_scores(week=week)

    matchups = []
    for b in box_scores:
        lineup_summary = (
            _format_lineup(b.home_team, b.home_lineup)
            + "\n\n"
            + _format_lineup(b.away_team, b.away_lineup)
        )
        matchups.append({
            "week": week,
            "home_team": str(b.home_team),
            "away_team": str(b.away_team),
            "home_score": b.home_score,
            "away_score": b.away_score,
            "lineup_summary": lineup_summary,
        })
    return {"week": week, "matchups": matchups}


def route_to_matchups(state: WeeklyRecapState):
    if not state["matchups"]:
        return "league_summary"
    return [Send("recap_matchup", m) for m in state["matchups"]]


def recap_matchup_node(state: _MatchupState):
    emit("node_start", node="recap_matchup", home=state["home_team"], away=state["away_team"])
    t0 = time.monotonic()

    system = SystemMessage(content=(
        "You are the foul-mouthed, brutally honest voice of a fantasy "
        "football league's weekly recap channel. Write a SHORT (3-5 "
        "sentence) recap of one matchup. Actually be funny, not "
        "generic-hype-with-an-exclamation-point funny - mean, blunt, "
        "and profane is encouraged. Cussing is allowed and welcome.\n\n"
        "HARD RULE: every player name, stat, and score you mention must come "
        "from the box score data given below - never invent or assume a stat.\n\n"
        "Cover whatever actually stands out in the data, e.g.: the top "
        "performer, a notable bust (started, low points vs projection - "
        "roast them for it in your own words), a 'clutch' player who beat "
        "their projection and mattered to the margin, and - importantly - "
        "check whether a benched player scored more than the starter in "
        "their same position group; if so, roast the manager for that call. "
        "Only mention what the data actually shows; skip anything that "
        "doesn't apply to this matchup rather than forcing it in.\n\n"
        "Don't hedge the insults - commit to them, but vary your language "
        "and angle of attack each time. Don't lean on the same stock "
        "phrases or jokes recap after recap. End with who won and the "
        "final score.\n\n"
        "Formatting: this is posted to Discord. Wrap every team name in "
        "double asterisks for bold (e.g. **Team Name**) every time it "
        "appears, since these are custom user-chosen names and otherwise "
        "blend into the text. Don't bold player names."
    ))
    prompt = HumanMessage(content=(
        f"Week {state['week']} matchup: {state['home_team']} {state['home_score']} "
        f"- {state['away_score']} {state['away_team']}\n\n"
        f"Full lineups (starters and bench) with points and projections:\n"
        f"{state['lineup_summary']}"
    ))

    def _llm(key):
        return ChatGoogleGenerativeAI(model=MODEL, google_api_key=key, reasoning_effort="high")

    text = invoke_with_fallback(_llm, [system, prompt]).text
    winner = state["home_team"] if state["home_score"] >= state["away_score"] else state["away_team"]

    emit("node_end", node="recap_matchup", duration_ms=int((time.monotonic() - t0) * 1000))
    return {"matchup_recaps": [{
        "home_team": state["home_team"],
        "away_team": state["away_team"],
        "home_score": state["home_score"],
        "away_score": state["away_score"],
        "winner": winner,
        "recap": text.strip(),
    }]}


def league_summary_node(state: WeeklyRecapState):
    emit("node_start", node="league_summary")
    t0 = time.monotonic()

    league = league_singleton()
    standings = league.standings()
    standings_lines = [
        f"{i}. {t.team_name} ({t.wins}-{t.losses}-{t.ties}) PF:{t.points_for} PA:{t.points_against}"
        for i, t in enumerate(standings, start=1)
    ]
    recap_lines = [
        f"{r['home_team']} {r['home_score']} - {r['away_score']} {r['away_team']}: "
        f"winner {r['winner']}"
        for r in state["matchup_recaps"]
    ]

    system = SystemMessage(content=(
        "You are the foul-mouthed, brutally honest voice of a fantasy "
        "football league's weekly recap channel. Write a short (4-6 "
        "sentence) league-wide wrap-up for this week: standings movement, "
        "who is playing well overall, who is cratering, and anything "
        "notable across the week's results. Actually be funny, not "
        "generic-hype funny - mean, blunt, and profane is encouraged.\n\n"
        "Every team should get at least a brief mention. As a baseline, give "
        "teams that won this week a little bit of props, and give teams "
        "that lost a bit of shit for it - nothing elaborate needed there, "
        "just a quick line. Save the real roasting (or real praise) for "
        "whichever results actually stand out - use your own judgment on "
        "which teams earned that versus which ones just get the baseline "
        "line.\n\n"
        "Look across this week's matchup scores (given below) to find "
        "whoever scored the most and least points in the whole league this "
        "week - this is independent of who won their own matchup, since a "
        "high scorer can still lose and a low scorer can still win. That's "
        "usually worth calling out. Also call out standings movement when "
        "something actually moved, like a big jump/drop or a tightening "
        "race. Every fact must come from the data given - never invent a "
        "stat.\n\n"
        "Formatting: this is posted to Discord. Wrap every team name in "
        "double asterisks for bold (e.g. **Team Name**) every time it "
        "appears, since these are custom user-chosen names and otherwise "
        "blend into the text."
    ))
    prompt = HumanMessage(content=(
        f"Week {state['week']} results:\n" + "\n".join(recap_lines) +
        "\n\nCurrent standings:\n" + "\n".join(standings_lines)
    ))

    def _llm(key):
        return ChatGoogleGenerativeAI(model=MODEL, google_api_key=key, reasoning_effort="high")

    text = invoke_with_fallback(_llm, [system, prompt]).text

    emit("node_end", node="league_summary", duration_ms=int((time.monotonic() - t0) * 1000))
    return {"league_summary": text.strip()}


def build_weekly_recap_graph():
    graph = StateGraph(WeeklyRecapState)
    graph.add_node("get_matchups", get_matchups_node)
    graph.add_node("recap_matchup", recap_matchup_node)
    graph.add_node("league_summary", league_summary_node)

    graph.add_edge(START, "get_matchups")
    graph.add_conditional_edges(
        "get_matchups", route_to_matchups, ["recap_matchup", "league_summary"]
    )
    graph.add_edge("recap_matchup", "league_summary")
    graph.add_edge("league_summary", END)

    return graph.compile()
