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

import anthropic
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.types import Send
from pydantic import BaseModel, Field

from fantasy_agent.tools import CATEGORY_DESCRIPTIONS, CATEGORY_REGISTRY
from fantasy_agent.trace import emit

TRACE_TRUNCATE = 800

MODEL = os.environ.get("FANTASY_AGENT_MODEL", "claude-haiku-4-5")
MAX_TOOL_ROUNDS = 4

PRIMARY_KEY = os.environ.get("ANTHROPIC_API_KEY")
BACKUP_KEY = os.environ.get("ANTHROPIC_API_KEY_BACKUP")


def _is_exhausted(err: Exception) -> bool:
    """True for errors a backup account/key could plausibly fix."""
    if isinstance(err, anthropic.RateLimitError):
        return True
    if isinstance(err, anthropic.BadRequestError):
        msg = str(err).lower()
        return "credit balance" in msg or "quota" in msg
    return False


def invoke_with_fallback(build_llm, *args, **kwargs):
    """Call build_llm(api_key).invoke(*args, **kwargs), retrying once against
    ANTHROPIC_API_KEY_BACKUP if the primary key is rate-limited or out of credits.
    """
    try:
        return build_llm(PRIMARY_KEY).invoke(*args, **kwargs)
    except Exception as err:
        if not BACKUP_KEY or not _is_exhausted(err):
            raise
        print(f"[fallback] primary Anthropic key failed ({err}); retrying with backup key")
        return build_llm(BACKUP_KEY).invoke(*args, **kwargs)


_CATEGORY_LIST = "\n".join(
    f"- {name}: {desc}" for name, desc in CATEGORY_DESCRIPTIONS.items()
)

SUPERVISOR_SYSTEM = SystemMessage(content=(
    "You classify a fantasy football chat bot's incoming message into zero "
    "or more data categories. Categories prefixed 'fantasy_' are the user's "
    "private fantasy league; categories prefixed 'nfl_' are real-world NFL "
    "data. Available categories:\n" + _CATEGORY_LIST + "\n\n"
    "Pick every category needed to answer (e.g. a roster + injury question "
    "needs both 'fantasy_roster' and 'nfl_team'). Pick none for greetings, "
    "opinions, or follow-up chat that needs no new data."
))

def _personality_system() -> SystemMessage:
    today = datetime.now().strftime("%Y-%m-%d")
    return SystemMessage(content=(
        f"Today's date is {today}. You are the voice of a fantasy football "
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
        "Keep replies SHORT: 1-4 sentences by default, and never more than "
        "a tight bulleted list for things like standings or rosters. No "
        "filler, no restating the question, no disclaimers beyond flagging "
        "genuinely missing data. Label every bare number with a short unit "
        "so it's never ambiguous - e.g. '364.9 pts' not '(364.9)', '75 rec "
        "/ 1,077 yds / 3 TD' not '75/1,077/3', '6 playoff teams'. "
        "Abbreviations are fine (pts, yds, rec, TD), just never leave a "
        "number floating with no label."
    ))


class CategoryChoice(BaseModel):
    categories: List[str] = Field(
        default_factory=list,
        description="Subset of the available category names needed to answer.",
    )


class AgentState(MessagesState):
    categories: List[str]
    category: str


def supervisor_node(state: AgentState):
    emit("node_start", node="supervisor")
    t0 = time.monotonic()
    choice = invoke_with_fallback(
        lambda key: ChatAnthropic(model=MODEL, api_key=key).with_structured_output(CategoryChoice),
        [SUPERVISOR_SYSTEM] + state["messages"],
    )
    valid = [c for c in choice.categories if c in CATEGORY_REGISTRY]
    emit(
        "node_end",
        node="supervisor",
        duration_ms=int((time.monotonic() - t0) * 1000),
        categories=valid,
    )
    return {"categories": valid}


def route_to_categories(state: AgentState):
    if not state["categories"]:
        return "personality"
    return [
        Send("run_category", {"messages": state["messages"], "category": c})
        for c in state["categories"]
    ]


def run_category_node(state: AgentState):
    category = state["category"]
    tools = CATEGORY_REGISTRY[category]
    tool_node = ToolNode(tools, handle_tool_errors=True)
    system = SystemMessage(content=(
        f"You retrieve data for the '{category}' category using only the "
        "tools provided. Call whatever tools are needed, then stop - never "
        "write a summary or answer yourself."
    ))

    emit("node_start", node="run_category", category=category)
    t0 = time.monotonic()
    local = []
    rounds = 0
    for _ in range(MAX_TOOL_ROUNDS):
        rounds += 1
        response = invoke_with_fallback(
            lambda key: ChatAnthropic(model=MODEL, api_key=key).bind_tools(tools),
            [system] + state["messages"] + local,
        )
        local.append(response)
        if not response.tool_calls:
            break
        for tc in response.tool_calls:
            emit("tool_call", category=category, name=tc["name"], args=tc["args"])
        results = tool_node.invoke({"messages": [response]})["messages"]
        for m in results:
            emit(
                "tool_result",
                category=category,
                name=getattr(m, "name", None),
                result=str(m.content)[:TRACE_TRUNCATE],
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

    def _stream(key):
        # Build the reply as a plain string rather than merging raw
        # AIMessageChunks: Anthropic's streaming deltas can merge into a
        # message with a stray empty text content block, which the API then
        # rejects ("text content blocks must be non-empty") the next time
        # this stored message is resent as conversation history.
        parts = []
        for chunk in ChatAnthropic(model=MODEL, api_key=key).stream(context):
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
