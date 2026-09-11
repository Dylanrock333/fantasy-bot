"""Structured event logging for graph.py's nodes.

Every node/tool-call in graph.py calls emit(event_type, **data) instead of
print(), so trace output has a consistent, greppable shape.
"""
from typing import Any


def emit(event_type: str, **data: Any) -> None:
    print(f"[trace] {event_type} {data}")
