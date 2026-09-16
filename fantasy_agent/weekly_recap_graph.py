"""Weekly recap LangGraph flow: pull the week's box scores + standings, then
one LLM call writes a league-wide summary paragraph plus a roast-y power
ranking of every team.

  START -> get_matchups -> league_summary -> END

Standalone from graph.py's chat agent - this doesn't classify a user message
or call tools mid-conversation, it pulls box scores/standings directly and
writes straight to an LLM.
"""
import time
from typing import List, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from fantasy_agent.clients.espn_fantasy_client import league_singleton
from fantasy_agent.graph import invoke_llm, MODEL
from fantasy_agent.trace import emit


class WeeklyRecapState(TypedDict):
    week: int
    matchups: List[dict]
    league_summary: str
    power_rankings: List[dict]


def get_matchups_node(state: WeeklyRecapState):
    week = state["week"]
    league = league_singleton()
    week = week or league.current_week or 1
    box_scores = league.box_scores(week=week)

    matchups = [
        {
            "home_team": str(b.home_team),
            "away_team": str(b.away_team),
            "home_score": b.home_score,
            "away_score": b.away_score,
        }
        for b in box_scores
    ]
    return {"week": week, "matchups": matchups}


class PowerRankingEntry(BaseModel):
    team: str = Field(description="Exact team name as given in the standings data.")
    tag: str = Field(
        description="A short award-style title with one emoji, e.g. "
        "'👑 King for the Week' or '🗑️ Dumpster Fire'. Vary the wording and "
        "emoji week to week based on what's actually happening for this "
        "team - don't reuse the same tag every time."
    )
    blurb: str = Field(
        description="One short, punchy sentence roasting or hyping this "
        "team, citing a real detail from the data given (record, this "
        "week's score/margin, points against, an implied win/lose streak). "
        "Never invent a stat that isn't in the data."
    )


class WeeklySummaryOutput(BaseModel):
    league_summary: str = Field(
        description="One tight paragraph (4-6 sentences): standings "
        "movement, who's playing well, who's cratering, anything notable "
        "this week. Every fact must come from the data given."
    )
    power_rankings: List[PowerRankingEntry] = Field(
        description="Every team in the league, ordered #1 (best) to last "
        "(worst), blending this week's result with overall standings."
    )


def league_summary_node(state: WeeklyRecapState):
    emit("node_start", node="league_summary")
    t0 = time.monotonic()

    league = league_singleton()
    standings = league.standings()
    standings_lines = [
        f"{i}. {t.team_name} ({t.wins}-{t.losses}-{t.ties}) PF:{t.points_for} PA:{t.points_against}"
        for i, t in enumerate(standings, start=1)
    ]
    matchup_lines = [
        f"{m['home_team']} {m['home_score']} - {m['away_score']} {m['away_team']}"
        for m in state["matchups"]
    ]

    system = SystemMessage(content=(
        "You are the voice of a fantasy football league's weekly recap "
        "channel, written for a rowdy, joke-heavy group chat. Produce two "
        "things from the data below - every fact must come from that data, "
        "never invented:\n\n"
        "1. league_summary: one tight paragraph (4-6 sentences) covering "
        "standings movement, who is playing well overall, who is "
        "cratering, and anything notable across the week's results.\n\n"
        "2. power_rankings: a funny, roast-y power ranking of EVERY team, "
        "ordered #1 (best) to last (worst), blending this week's result "
        "with overall standings. Higher ranks get flattering/badass tags, "
        "middle ranks get 'meh/surviving' tags, bottom ranks get brutal "
        "ones. Ground every blurb in a real detail from the data (record, "
        "this week's score/margin, points against, a streak implied by the "
        "standings) - never invent a stat."
    ))
    prompt = HumanMessage(content=(
        f"Week {state['week']} results:\n" + "\n".join(matchup_lines) +
        "\n\nCurrent standings:\n" + "\n".join(standings_lines)
    ))

    def _llm(key):
        return ChatGoogleGenerativeAI(
            model=MODEL, google_api_key=key, reasoning_effort="high"
        ).with_structured_output(WeeklySummaryOutput)

    result = invoke_llm(_llm, [system, prompt])

    emit("node_end", node="league_summary", duration_ms=int((time.monotonic() - t0) * 1000))
    return {
        "league_summary": result.league_summary.strip(),
        "power_rankings": [pr.model_dump() for pr in result.power_rankings],
    }


def build_weekly_recap_graph():
    graph = StateGraph(WeeklyRecapState)
    graph.add_node("get_matchups", get_matchups_node)
    graph.add_node("league_summary", league_summary_node)

    graph.add_edge(START, "get_matchups")
    graph.add_edge("get_matchups", "league_summary")
    graph.add_edge("league_summary", END)

    return graph.compile()
