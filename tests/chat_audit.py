"""Manual audit: run PROMPTS through the chat graph and write traces to tests/audit_output/.

Usage: python tests/chat_audit.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# Make the repo root importable and load .env before importing project modules.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from langchain_core.messages import HumanMessage

from fantasy_agent.logging import trace
from fantasy_agent.graphs import graph as graph_module
from fantasy_agent.graphs.graph import build_graph
from fantasy_agent.clients.espn_fantasy_client import current_league_id, current_team_context

current_league_id.set(int(os.environ["LEAGUE_ID"]))
current_team_context.set(os.environ["TEAM_CONTEXT"])

PROMPTS = [
    "Who has the better defense, Vikings or Jaguars?",
    "Should I start my RB2 this week?",
    "What's Justin Jefferson's stat line this season?",
    "What games are on today?",
    "Haha nice, thanks!",
    "As of right now which flex player has the most points this week",
    "Okay between Flok, Bass, pinero, Boswell, and McLaughlin who is going to have the best chance of having the most points. This week based off the team how often they make it to field goal range and how accurate the kicker is",
    "What is the best player i can trade Jordan love to for a RB2 and WR2",
    "What do you think about this trade AJ Brown and Cook for olave and tuten",
    "who should i pick up off waivers this week at wr",
    "is anyone on my team on a bye this week",
    "where do i stand in the standings rn, am i making the playoffs",
    "jaylen warren or rachaad white this week, who do i start",
    "give me a recap of how my matchup went last week"
]


def _call_summary(e: dict) -> str:
    """One line of model/token/finish-reason detail for an `llm_usage` event."""
    return (
        f"call summary: model={e.get('model')}, in={e.get('input_tokens')}, "
        f"out={e.get('output_tokens')} (thinking={e.get('thinking_tokens')}), "
        f"cached={e.get('cached_tokens')}, finish={e.get('finish_reason')}"
    )


def run_one(graph, prompt: str) -> str:
    """Run one prompt, capturing trace events, and return its markdown report section."""
    events = []
    original_emit = trace.emit

    def capture(event_type, **data):
        events.append({"type": event_type, **data})
        original_emit(event_type, **data)

    # graph.py did `from ...trace import emit`, so it holds its own local
    # name bound to the function object - patching trace.emit alone never
    # reaches it. Patch the name graph.py actually calls instead.
    graph_module.emit = capture
    try:
        result = graph.invoke({"messages": [HumanMessage(content=prompt)]})
    finally:
        graph_module.emit = original_emit

    reply = result["messages"][-1].text

    # Summarize the full node-by-node flow from the captured events.
    # run_category instances for one supervisor round execute in parallel, so their tool_call/
    # tool_result events arrive interleaved across categories - buffer them by category and round,
    # then flush as grouped blocks once that round's categories all finish (at the personality step).
    lines = [f"## {prompt}", ""]
    supervisor_round = 0
    category_order = []
    category_rounds = {}  # category -> {round: [line, ...]}
    category_done = {}  # category -> done summary line

    def flush_categories():
        for cat in category_order:
            lines.append(f"**[{cat}]**")
            for rnd in sorted(category_rounds[cat]):
                lines.append(f"- **round {rnd}:**")
                lines.extend(f"  - {l}" for l in category_rounds[cat][rnd])
            if cat in category_done:
                lines.append(f"- {category_done[cat]}")
        category_order.clear()
        category_rounds.clear()
        category_done.clear()

    # llm_usage fires right before the node_end of the node it belongs to, except inside
    # run_category where it fires once per tool round - buffer the rest by node name.
    pending_usage = {}
    for e in events:
        node = e.get("node")
        if e["type"] == "llm_usage":
            if node == "run_category":
                cat = e.get("category")
                if cat not in category_rounds:
                    category_order.append(cat)
                    category_rounds[cat] = {}
                category_rounds[cat].setdefault(e.get("round", 0), []).append(_call_summary(e))
            else:
                pending_usage[node] = e
            continue
        if e["type"] == "node_end" and node == "supervisor":
            supervisor_round += 1
            lines.append(f"**[supervisor round {supervisor_round}]** ({e.get('duration_ms') / 1000:.1f}s)")
            lines.append(f"- categories: {e.get('categories')}")
            lines.append(f"- reasoning: {e.get('reasoning')}")
            if "supervisor" in pending_usage:
                lines.append(f"- {_call_summary(pending_usage.pop('supervisor'))}")
        elif e["type"] in ("tool_call", "tool_result"):
            cat = e.get("category")
            if cat not in category_rounds:
                category_order.append(cat)
                category_rounds[cat] = {}
            rnd = e.get("round", 0)
            if e["type"] == "tool_call":
                line = f"tool_call {e.get('name')}({e.get('args')})"
            else:
                line = f"tool_result {e.get('name')}: {e.get('result')}"
            category_rounds[cat].setdefault(rnd, []).append(line)
        elif e["type"] == "node_end" and node == "run_category":
            cat = e.get("category")
            category_done[cat] = (
                f"done in {e.get('duration_ms') / 1000:.1f}s, {e.get('tool_rounds')} tool round(s)"
            )
        elif e["type"] == "node_end" and node == "personality":
            flush_categories()
            lines.append(f"**[personality]** ({e.get('duration_ms') / 1000:.1f}s)")
            if "personality" in pending_usage:
                lines.append(f"- {_call_summary(pending_usage.pop('personality'))}")
        # critique node disabled in graph.py, so this never fires currently.
        # elif e["type"] == "node_end" and node == "critique":
        #     verdict = "satisfied" if e.get("satisfied") else "NOT satisfied -> looping back to supervisor"
        #     lines.append(f"**[critique]** ({e.get('duration_ms')}ms) {verdict}")
        #     if e.get("missing"):
        #         lines.append(f"- missing: {e.get('missing')}")

    flags = []
    if "https://" in reply or "http://" in reply:
        flags.append("url/image link")

    if flags:
        lines.append(f"- contains: {', '.join(flags)}")

    lines += ["", "**Reply:**", reply]

    lines.append("")
    return "\n".join(lines)


def main():
    """Run every prompt and write report.md into a timestamped folder."""
    base_dir = Path(__file__).resolve().parent / "audit_output"
    run_dir = base_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    graph = build_graph()
    reports = [run_one(graph, p) for p in PROMPTS]
    report_path = run_dir / "report.md"
    report_path.write_text("\n---\n\n".join(reports))
    print(f"\nWrote {len(PROMPTS)} runs to {report_path}")


if __name__ == "__main__":
    main()
