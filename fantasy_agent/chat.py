#!/usr/bin/env python3
"""CLI chat loop for the fantasy football agent.

Run: python3 fantasy_agent/chat.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from fantasy_agent.graph import build_graph  # noqa: E402  (after load_dotenv)


def main():
    if not (ROOT / ".env").exists() or "ANTHROPIC_API_KEY" not in (ROOT / ".env").read_text():
        print("Warning: ANTHROPIC_API_KEY not found in .env - set it before chatting.\n")

    graph = build_graph()
    messages = []

    print("Fantasy football agent - type 'exit' to quit.\n")
    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        messages.append(HumanMessage(content=user_input))
        try:
            result = graph.invoke({"messages": messages})
        except Exception as err:
            print(f"bot> (error, message not saved) {err}\n")
            messages.pop()
            continue
        messages = result["messages"]

        reply = messages[-1]
        print(f"bot> {reply.text}\n")


if __name__ == "__main__":
    main()
