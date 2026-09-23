"""Greppable structured trace logging for graph nodes and tool calls."""
from typing import Any


def emit(event_type: str, **data: Any) -> None:
    """Print one `[trace] <event> {data}` line."""
    print(f"[trace] {event_type} {data}")
