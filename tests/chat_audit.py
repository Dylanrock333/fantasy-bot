"""Manual audit tool: runs a fixed list of prompts through the LangGraph
agent (in-process, no server needed) and writes each run's full trace
(supervisor reasoning, tool calls/results, final reply) to one report file
under tests/audit_output/<timestamp>/, with any chart JSON rendered to a
PNG and embedded - open report.md's Preview in VS Code to see it inline.

Add/edit prompts below as you find bugs worth re-checking, then:
    python tests/chat_audit.py
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from langchain_core.messages import HumanMessage

from fantasy_agent import trace
from fantasy_agent.chart_render import render_chart_png
from fantasy_agent.graph import build_graph

PROMPTS = [
    "Who has the better defense, Vikings or Jaguars?",
    "Should I start my RB2 this week?",
    "What's Justin Jefferson's stat line this season?",
    "What games are on today?",
    "Show me a chart comparing the Vikings and Jaguars defenses.",
    "Haha nice, thanks!",
]

CHART_RE = re.compile(r"```chart\s*\n([\s\S]*?)```")


def run_one(graph, index: int, prompt: str, run_dir: Path) -> str:
    events = []
    original_emit = trace.emit

    def capture(event_type, **data):
        events.append({"type": event_type, **data})
        original_emit(event_type, **data)

    trace.emit = capture
    try:
        result = graph.invoke({"messages": [HumanMessage(content=prompt)]})
    finally:
        trace.emit = original_emit

    reply = result["messages"][-1].text

    lines = [f"## {prompt}", ""]
    for e in events:
        if e["type"] == "node_end" and e.get("node") == "supervisor":
            lines.append(f"- categories: {e.get('categories')}")
            lines.append(f"- reasoning: {e.get('reasoning')}")
        elif e["type"] == "tool_call":
            lines.append(f"- tool_call [{e.get('category')}] {e.get('name')}({e.get('args')})")
        elif e["type"] == "tool_result":
            lines.append(f"- tool_result [{e.get('category')}] {e.get('name')}: {e.get('result')}")

    flags = []
    if "https://" in reply or "http://" in reply:
        flags.append("url/image link")

    match = CHART_RE.search(reply)
    if match:
        flags.append("chart")
    if flags:
        lines.append(f"- contains: {', '.join(flags)}")

    lines += ["", "**Reply:**", reply]

    if match:
        try:
            chart = json.loads(match.group(1))
            png_bytes = render_chart_png(chart)
            if png_bytes:
                png_path = run_dir / f"{index:02d}_chart.png"
                png_path.write_bytes(png_bytes)
                lines += ["", f"![chart]({png_path.name})"]
        except json.JSONDecodeError as err:
            lines += ["", f"(chart JSON failed to parse: {err})"]

    lines.append("")
    return "\n".join(lines)


def main():
    base_dir = Path(__file__).resolve().parent / "audit_output"
    run_dir = base_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    graph = build_graph()
    reports = [run_one(graph, i, p, run_dir) for i, p in enumerate(PROMPTS, 1)]
    report_path = run_dir / "report.md"
    report_path.write_text("\n---\n\n".join(reports))
    print(f"\nWrote {len(PROMPTS)} runs to {report_path}")


if __name__ == "__main__":
    main()
