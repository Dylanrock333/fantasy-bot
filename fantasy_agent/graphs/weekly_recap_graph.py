"""Weekly recap LangGraph flow: pull the week's box scores + standings, one
LLM call writes a league-wide summary paragraph plus a ranked list of every
team with an award-style tag, then a Nano Banana image call turns those
rankings + this week's matchups into a poster-style recap graphic.

  START -> get_matchups -> league_summary -> power_ranking_image -> END

Standalone from graph.py's chat agent - this doesn't classify a user message
or call tools mid-conversation, it pulls box scores/standings directly and
writes straight to an LLM.
"""
import time
from typing import List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from fantasy_agent.clients.espn_fantasy_client import league_singleton, nfl_game_week
from fantasy_agent.graphs.graph import invoke_llm, MODEL
from fantasy_agent.logging.trace import emit
from fantasy_agent.utils.openai_image_gen import generate_image


class WeeklyRecapState(TypedDict):
    week: int
    matchups: List[dict]
    league_summary: str
    power_rankings: List[dict]
    power_ranking_image: Optional[bytes]


def get_matchups_node(state: WeeklyRecapState):
    week = state.get("week") or nfl_game_week()
    league = league_singleton()
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
        description="A punchy 2-4 word award-style title, Title Case, no "
        "emoji, no parenthetical stats or explanations - this gets "
        "rendered as a compact badge in a graphic. As unhinged and "
        "genuinely funny as possible, never basic or safe - avoid "
        "reaching for the obvious register every time (crime/warrant/ "
        "hazmat/medical is overused, pick something else more often "
        "than not). Pull from a wide, random-feeling grab bag: reality "
        "TV drama, cult/conspiracy energy, corporate-jargon absurdity, "
        "cryptids, fast food, celebrity scandal, weather disasters, "
        "government bureaucracy, whatever's genuinely surprising for "
        "that specific team - no two teams in the same list should draw "
        "from the same category. No guardrails, no PG-rated version, no "
        "hedging - this is a private group chat that roasts each other "
        "hard, so write it exactly that unfiltered: crude, dark, "
        "offensive-to-a-stranger levels of mean is the target, not a "
        "cute pun. If it reads like something a brand's Twitter account "
        "could post, it's too safe - throw it out and go further. This "
        "should get a genuine shocked laugh, not a smile. Vary both the "
        "wording and the sentence structure week to week based on what's "
        "actually happening for this team - don't reuse the same tag or "
        "phrasing pattern every time."
    )


class WeeklySummaryOutput(BaseModel):
    league_summary: str = Field(
        description="The week's recap broken into 3-5 short beats "
        "separated by a blank line (double newline) - NOT one dense "
        "paragraph. Each beat is 1-2 punchy sentences on a single "
        "storyline: standings movement, who's playing well, who's "
        "cratering, anything notable this week. One storyline per beat, "
        "don't stack multiple unrelated facts into the same sentence "
        "with commas. Every fact must come from the data given."
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
        "1. league_summary: standings movement, who is playing well "
        "overall, who is cratering, and anything notable across the "
        "week's results - broken into 3-5 short beats separated by a "
        "blank line (double newline), one storyline per beat, NOT one "
        "dense paragraph. Max "
        "unhinged - no filter, no restraint, borderline deranged. Roast "
        "people mercilessly, reach for the most chaotic and unhinged "
        "comparison you can think of for every result (crime scenes, "
        "natural disasters, medical emergencies, felonies - whatever fits), "
        "and don't soften a single sentence for politeness. Every fact "
        "still has to come from the data, but the tone should read like "
        "it was written by the most feral, chronically-online person in "
        "the group chat at 1am, not a recap. Wrap every team name in "
        "markdown bold (**Team Name**) each time it appears.\n\n"
        "2. power_rankings: a funny power ranking of EVERY team, ordered #1 "
        "(best) to last (worst), blending this week's result with overall "
        "standings. Give each team a short, punchy award-style tag in the "
        "voice of a group-chat power-rankings post - max unhinged: no "
        "filter, chaotic, deranged, not generic sports-cliche titles. Higher ranks get "
        "flattering/badass tags, middle ranks get 'meh/surviving' tags, "
        "bottom ranks get brutal ones. Ground every tag in a real detail "
        "from the data (record, this week's score/margin, points against, "
        "a streak implied by the standings) - never invent a stat, but "
        "don't spell the stat out in the tag itself, just let it inform "
        "the joke."
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
        "power_rankings": [
            {"rank": i, "team": pr.team, "tag": pr.tag}
            for i, pr in enumerate(result.power_rankings, start=1)
        ],
    }


def power_ranking_image_node(state: WeeklyRecapState):
    emit("node_start", node="power_ranking_image")
    t0 = time.monotonic()

    league_name = league_singleton().settings.name

    rank_by_team = {pr["team"]: pr for pr in state["power_rankings"]}
    matchup_lines = []
    for m in state["matchups"]:
        home = rank_by_team.get(m["home_team"])
        away = rank_by_team.get(m["away_team"])
        matchup_lines.append(
            f"- \"#{home['rank']} {home['tag']}\" {m['home_team']} "
            f"({m['home_score']} pts) vs \"#{away['rank']} {away['tag']}\" "
            f"{m['away_team']} ({m['away_score']} pts)"
            if home and away else
            f"- {m['home_team']} ({m['home_score']} pts) vs "
            f"{m['away_team']} ({m['away_score']} pts)"
        )

    prompt = (
        "Design a bold, poster-style graphic recapping this fantasy "
        f"football league's Week {state['week']} results. Wide landscape "
        "layout. Dark background, punchy sports-broadcast typography, a "
        "grid of matchup cards (two teams per card, 'VS' between them). "
        "Each team's card shows: its team name printed as plain readable "
        "text exactly as spelled below, the way a real sports broadcast "
        "graphic prints a team name - nothing else attached to it, no "
        "field labels, no surrounding punctuation or symbols beyond "
        "what's in the name itself; its score for the week; a colored "
        "badge; and a bold mascot-style icon illustration. THE "
        "BADGE TEXT MUST BE THE EXACT QUOTED STRING GIVEN BELOW FOR THAT "
        "TEAM, verbatim including the rank number and emoji - do not "
        "shorten it, translate it into a generic word like "
        "'WINNER'/'LOSER'/'TOP TIER', or invent your own label. If a "
        "badge's full text doesn't fit, shrink the font, don't change "
        "the wording. For the mascot icon, find a literal or punny "
        "reading of that team's own NAME (not its tag) - an animal, "
        "weapon, object, person, or place the name references or sounds "
        "like - and illustrate that, the way a fantasy-sports meme "
        "graphic would (e.g. a team named after an animal gets that "
        "animal, a name that's a pun on an object gets that object). "
        "Never draw a real NFL team's actual logo/mascot even if a name "
        "overlaps with one - invent your own illustration instead. Keep "
        "every mascot icon in the same bold flat-illustration style "
        "across the whole poster so it reads as one consistent set. "
        f"Put the league name, \"{league_name}\", as the main header in "
        "large, bold, stylized lettering at the top of the poster. At "
        "the bottom, in noticeably smaller text, print "
        f"'WEEK {state['week']} RECAP'.\n\n"
        "Matchups (badge text for each team is in quotes):\n" +
        "\n".join(matchup_lines)
    )

    image_bytes = None
    try:
        image_bytes = generate_image(prompt, size="1536x1024")
    except Exception as err:
        emit("node_error", node="power_ranking_image", error=str(err))

    emit("node_end", node="power_ranking_image", duration_ms=int((time.monotonic() - t0) * 1000))
    return {"power_ranking_image": image_bytes}


def build_weekly_recap_graph():
    graph = StateGraph(WeeklyRecapState)
    graph.add_node("get_matchups", get_matchups_node)
    graph.add_node("league_summary", league_summary_node)
    graph.add_node("power_ranking_image", power_ranking_image_node)

    graph.add_edge(START, "get_matchups")
    graph.add_edge("get_matchups", "league_summary")
    graph.add_edge("league_summary", "power_ranking_image")
    graph.add_edge("power_ranking_image", END)

    return graph.compile()
