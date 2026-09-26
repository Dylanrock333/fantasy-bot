"""Manual audit: run PROMPTS through the chat graph and write traces to tests/audit_output/.

Usage: python tests/chat_audit.py
"""
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
from fantasy_agent.graphs.graph import build_graph

PROMPTS = [
    "Who has the better defense, Vikings or Jaguars?",
    "Should I start my RB2 this week?",
    "What's Justin Jefferson's stat line this season?",
    "What games are on today?",
    "Haha nice, thanks!",
]


def run_one(graph, prompt: str) -> str:
    """Run one prompt, capturing trace events, and return its markdown report section."""
    events = []
    original_emit = trace.emit

    def capture(event_type, **data):
        events.append({"type": event_type, **data})
        original_emit(event_type, **data)

    # Temporarily swap in the capturing emit for this run.
    trace.emit = capture
    try:
        result = graph.invoke({"messages": [HumanMessage(content=prompt)]})
    finally:
        trace.emit = original_emit

    reply = result["messages"][-1].text

    # Summarize supervisor decisions and tool traffic from the captured events.
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
