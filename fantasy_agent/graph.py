"""Supervisor + category-node LangGraph agent:

  supervisor  - classifies the user's latest message into 0+ categories
                (standings, roster, nfl_team, ...) via structured output.
                Never calls tools itself, never talks to the user.
  run_category - one instance per chosen category, dispatched in parallel via
                Send. Only sees that category's own (small) tool list, and
                loops tool-calls <-> itself until it has enough data.
  personality - the only node that talks to the user. Writes the final,
                short, in-character reply from every category's gathered data.

    START -> supervisor -> Send(run_category) x N (parallel, or none) -> personality -> END
"""
import os
import time
from datetime import datetime
from typing import List

from google.genai.errors import APIError as GoogleAPIError
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Send
from pydantic import BaseModel, Field

from fantasy_agent.tools import CATEGORY_DESCRIPTIONS, CATEGORY_REGISTRY
from fantasy_agent.trace import emit

TRACE_TRUNCATE = 800

MODEL = os.environ.get("FANTASY_AGENT_MODEL", "gemini-3.5-flash")
# 6, not 4: a "rank every WR on this team" question needs one round per named
# player plus a round or two for the roster/depth-chart lookup that names
# them - 4 left no room once a round got spent on an unhelpful tool call.
MAX_TOOL_ROUNDS = 6

PRIMARY_KEY = os.environ.get("GOOGLE_API_KEY")
BACKUP_KEY = os.environ.get("GOOGLE_API_KEY_BACKUP")


def _is_exhausted(err: Exception) -> bool:
    """True for errors a backup account/key could plausibly fix."""
    if isinstance(err, GoogleAPIError):
        if err.code == 429:  # rate limited or quota exceeded
            return True
        msg = str(err).lower()
        return "credit balance" in msg or "quota" in msg
    return False


def invoke_with_fallback(build_llm, *args, **kwargs):
    """Call build_llm(api_key).invoke(*args, **kwargs), retrying once against
    GOOGLE_API_KEY_BACKUP if the primary key is rate-limited or out of credits.
    """
    try:
        return build_llm(PRIMARY_KEY).invoke(*args, **kwargs)
    except Exception as err:
        if not BACKUP_KEY or not _is_exhausted(err):
            raise
        print(f"[fallback] primary Gemini key failed ({err}); retrying with backup key")
        return build_llm(BACKUP_KEY).invoke(*args, **kwargs)


_CATEGORY_LIST = "\n".join(
    f"- {name}: {desc}" for name, desc in CATEGORY_DESCRIPTIONS.items()
)


def _today() -> str:
    return datetime.now().strftime("%A, %Y-%m-%d")


def _supervisor_system() -> SystemMessage:
    return SystemMessage(content=(
        f"Today's date is {_today()}. Use it to judge what 'today', 'this "
        "week', 'tonight', or 'currently' mean in the message, and factor that "
        "into your reasoning (e.g. 'today' needs that specific date's games, "
        "not just the general schedule).\n\n"
        "You classify a fantasy football chat bot's incoming message into zero "
        "or more data categories. Categories prefixed 'fantasy_' are the user's "
        "private fantasy league; categories prefixed 'nfl_' are real-world NFL "
        "data. Available categories:\n" + _CATEGORY_LIST + "\n\n"
        "First write `reasoning`: think concretely about what would actually "
        "prove an answer - which specific stats, which teams/players, what "
        "angle (season totals? a single matchup? recent form?) - not just "
        "which topic the message is about. A comparison needs comparable data "
        "for both sides; a recommendation needs the factors that would change "
        "the recommendation. Then pick every category needed to gather that "
        "data, and skip any category that wouldn't add anything. Pick no "
        "categories for greetings, opinions, or follow-up chat that needs no "
        "new data.\n\n"
        "Examples:\n"
        "Q: \"Who has the better defense, Vikings or Jaguars?\"\n"
        "reasoning: A defense comparison needs actual defensive production for "
        "both teams - sacks, takeaways, tackles for loss, passes defended - "
        "not just win-loss record or injuries. Team season stats settle the "
        "core question; standout defensive players add supporting detail.\n"
        "categories: [nfl_team, nfl_player]\n\n"
        "Q: \"Should I start my RB2 this week?\"\n"
        "reasoning: A start/sit call depends on three things at once: whether "
        "the player is actually mine and healthy, his recent real-world form, "
        "and how tough the opponent he's facing is. That's my roster, his "
        "player stats, and the opposing team's data - missing any one makes "
        "the recommendation a guess.\n"
        "categories: [fantasy_roster, nfl_player, nfl_team]\n\n"
        "Note: fantasy team names (e.g. \"Hurts Cooks with Lamb\") are "
        "user-chosen nicknames, often punning on player surnames - they "
        "are not player names or actual rosters. Whenever a question "
        "names specific fantasy teams and needs to know who's on them, "
        "include fantasy_roster so the real roster is fetched instead of "
        "guessed from the team name.\n\n"
        "Q: \"What's Justin Jefferson's stat line this season?\"\n"
        "reasoning: A single player's own season numbers - no comparison, no "
        "team context, no fantasy-league angle needed.\n"
        "categories: [nfl_player]\n\n"
        "Q: \"Haha nice, thanks!\"\n"
        "reasoning: Acknowledgment/follow-up chat with no factual claim behind "
        "it - there's nothing to fetch.\n"
        "categories: []"
    ))


def _personality_system() -> SystemMessage:
    return SystemMessage(content=(
        f"Today's date is {_today()}. You are the voice of a fantasy football "
        "chat bot: sharp, confident, a little witty, but never rambling.\n\n"
        "HARD RULE: every fact, name, number, or claim in your reply must "
        "come from the tool results gathered earlier in this conversation. "
        "This includes things that feel like stable background knowledge - "
        "head coaches, coordinators, depth charts, injury status, records, "
        "rookies vs. veterans, anything roster- or season-specific. Rosters, "
        "coaching staffs, and depth charts change constantly and your "
        "training data is not live - if a detail isn't in the tool results, "
        "you do not know it right now. Never fill a gap from memory, "
        "assumption, or 'usually.' If the gathered data doesn't cover part "
        "of the question, say so explicitly (e.g. 'no coach data was "
        "pulled for this') rather than guessing.\n\n"
        "Keep replies SHORT: 2-5 sentences of framing text by default. "
        "Whenever the answer has two or more comparable rows of data - "
        "standings, rosters, multi-player stat lines, matchup comparisons - "
        "default to a single table (see TABLES below) instead of prose or "
        "bullets. No filler, no restating the question, no disclaimers beyond flagging "
        "genuinely missing data. Label every bare number with a short unit "
        "so it's never ambiguous - e.g. '364.9 pts' not '(364.9)', '75 rec "
        "/ 1,077 yds / 3 TD' not '75/1,077/3', '6 playoff teams'. "
        "Abbreviations are fine (pts, yds, rec, TD), just never leave a "
        "number floating with no label.\n\n"
        "You must always write a reply, even when no tool data was "
        "gathered - greetings, thanks, opinions, meta questions about the "
        "conversation, and non-football questions all still get a short, "
        "in-character response using only the conversation itself. Never "
        "produce an empty or whitespace-only reply.\n\n"
        "TABLES: whenever your reply has two or more comparable rows of "
        "data - not just when the user asks for a 'chart' or 'table' - "
        "default to presenting it as a single table. Emit exactly one "
        "fenced code block labeled `chart` (```chart ... ```) containing a "
        "single JSON object and nothing else inside the fence; never "
        "hand-write a markdown or bulleted table instead, and never split "
        "one answer's data across more than one such block. Two shapes "
        "are supported:\n"
        "- Comparing two or more things across several differently-scaled "
        "metrics (e.g. two teams' full stat lines): "
        '{"type": "comparison", "title": "...", "series": ["Name A", '
        '"Name B"], "rows": [{"label": "Points Scored", "unit": "pts", '
        '"values": [344, 474]}, ...]}. Each row is scaled to its own max, '
        "so wildly different units (points vs. sacks) both stay readable.\n"
        "- One metric across several categories, all in the same unit "
        '(e.g. targets per WR): {"type": "bar", "title": "...", "unit": '
        '"tgt", "categories": ["Name A", "Name B"], "series": [{"name": '
        '"Targets", "values": [141, 98]}]}. All values share one scale, '
        "and `series` may hold more than one line for a grouped chart.\n"
        "Values must be raw numbers (no commas or unit text baked in) - "
        "put the unit in the `unit` field. You may add one short sentence "
        "of framing text before the code block, but never restate the "
        "chart's numbers again in prose below it. Skip the table entirely "
        "only when the reply is a single fact, a one-line answer, or "
        "non-data chat (greetings, opinions, follow-up banter)."
    ))


class CategoryChoice(BaseModel):
    reasoning: str = Field(
        description="One or two sentences on what data would actually "
        "answer this well - which stats/teams/players and what angle - "
        "decided before picking categories.",
    )
    categories: List[str] = Field(
        default_factory=list,
        description="Subset of the available category names needed to answer.",
    )


class AgentState(MessagesState):
    categories: List[str]
    category: str
    reasoning: str


def supervisor_node(state: AgentState):
    emit("node_start", node="supervisor")
    t0 = time.monotonic()
    choice = invoke_with_fallback(
        lambda key: ChatGoogleGenerativeAI(model=MODEL, google_api_key=key).with_structured_output(CategoryChoice),
        [_supervisor_system()] + state["messages"],
    )
    valid = [c for c in choice.categories if c in CATEGORY_REGISTRY]
    emit(
        "node_end",
        node="supervisor",
        duration_ms=int((time.monotonic() - t0) * 1000),
        categories=valid,
        reasoning=choice.reasoning,
    )
    return {"categories": valid, "reasoning": choice.reasoning}


def route_to_categories(state: AgentState):
    if not state["categories"]:
        return "personality"
    return [
        Send("run_category", {
            "messages": state["messages"],
            "category": c,
            "reasoning": state["reasoning"],
        })
        for c in state["categories"]
    ]


def run_category_node(state: AgentState):
    category = state["category"]
    tools = CATEGORY_REGISTRY[category]
    tool_node = ToolNode(tools, handle_tool_errors=True)
    system = SystemMessage(content=(
        f"Today's date is {_today()}. You retrieve data for the "
        f"'{category}' category using only the tools provided. The "
        f"supervisor's plan for this question: \"{state['reasoning']}\"\n"
        "Fantasy team/league names (e.g. \"Hurts Cooks with Lamb\") are "
        "arbitrary nicknames the user picked, often puns on player "
        "surnames - never infer a real player's identity from a substring "
        "of a team name, and never treat a team name as a player or user "
        "name. Only trust players confirmed via fantasy_roster or "
        "matchup/box-score tool output.\n"
        "When the question already names specific players, or asks you to "
        "rank/compare every player in a specific group (e.g. a team's "
        "WRs), call each named player's own stat tool directly (e.g. "
        "get_nfl_player_summary once per player) rather than starting "
        "with a league-wide leaderboard tool - those rarely include the "
        "exact players you need and each call still costs a full round.\n"
        "Call whatever tools serve that plan, then stop - never write a "
        "summary or answer yourself."
    ))

    emit("node_start", node="run_category", category=category)
    t0 = time.monotonic()
    local = []
    rounds = 0
    for _ in range(MAX_TOOL_ROUNDS):
        rounds += 1
        response = invoke_with_fallback(
            lambda key: ChatGoogleGenerativeAI(model=MODEL, google_api_key=key).bind_tools(tools),
            [system] + state["messages"] + local,
        )
        local.append(response)
        if not response.tool_calls:
            break
        for tc in response.tool_calls:
            emit("tool_call", category=category, name=tc["name"], args=tc["args"], round=rounds)
            tc_t0 = time.monotonic()
            results = tool_node.invoke(
                {"messages": [AIMessage(content="", tool_calls=[tc])]}
            )["messages"]
            tc_duration_ms = int((time.monotonic() - tc_t0) * 1000)
            for m in results:
                content = str(m.content)
                emit(
                    "tool_result",
                    category=category,
                    name=getattr(m, "name", None),
                    result=content[:TRACE_TRUNCATE],
                    truncated=len(content) > TRACE_TRUNCATE,
                    duration_ms=tc_duration_ms,
                    round=rounds,
                )
            local.extend(results)
    emit(
        "node_end",
        node="run_category",
        category=category,
        duration_ms=int((time.monotonic() - t0) * 1000),
        tool_rounds=rounds,
    )
    return {"messages": local}


def _chunk_text(chunk) -> str:
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def personality_node(state: AgentState):
    # The last turn before this is always an assistant message (tool call or
    # plain reply), and this model rejects a request that doesn't end on a
    # user turn - so cap the context with a synthetic cue instead of raw history.
    context = (
        [_personality_system()]
        + state["messages"]
        + [HumanMessage(content="Reply now, per your instructions.")]
    )

    def _llm(key):
        # reasoning_effort="low": this node only writes a short, in-character
        # reply from data already gathered - it doesn't need to burn a large
        # reasoning budget, and doing so on ambiguous/off-topic turns has been
        # seen to consume the entire output budget on "thinking" and leave no
        # text behind, i.e. an empty reply.
        return ChatGoogleGenerativeAI(model=MODEL, google_api_key=key, reasoning_effort="low")

    def _stream(key):
        # Build the reply as a plain string rather than merging raw
        # AIMessageChunks, to avoid re-sending provider-specific chunk
        # artifacts back as conversation history.
        parts = []
        for chunk in _llm(key).stream(context):
            text = _chunk_text(chunk)
            if text:
                parts.append(text)
                emit("token", text=text)
        return "".join(parts)

    emit("node_start", node="personality")
    t0 = time.monotonic()
    try:
        full_text = _stream(PRIMARY_KEY)
    except Exception as err:
        if not BACKUP_KEY or not _is_exhausted(err):
            raise
        emit("node_warning", node="personality", message=f"primary key failed, retrying with backup: {err}")
        full_text = _stream(BACKUP_KEY)

    if not full_text.strip():
        # Streaming occasionally yields no text block at all (e.g. the model
        # spent its whole turn on non-text/thinking content) even though a
        # plain, non-streamed call for the same context reliably returns one -
        # retry once before ever showing the user a blank reply.
        emit("node_warning", node="personality", message="stream produced no text, retrying with a plain call")
        full_text = _chunk_text(invoke_with_fallback(_llm, context))

    if not full_text.strip():
        full_text = "Sorry, I didn't quite catch that - could you rephrase?"

    response = AIMessage(content=full_text)
    emit(
        "node_end",
        node="personality",
        duration_ms=int((time.monotonic() - t0) * 1000),
        text=full_text,
    )
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("run_category", run_category_node)
    graph.add_node("personality", personality_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor", route_to_categories, ["run_category", "personality"]
    )
    graph.add_edge("run_category", "personality")
    graph.add_edge("personality", END)

    return graph.compile()
