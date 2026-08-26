"""Structured event emission for graph.py's nodes.

Every node/tool-call in graph.py calls emit(event_type, **data) instead of
print(). With no sink bound, emit() just prints (identical to the old CLI
behavior). webapp/server.py binds a sink for the duration of one graph.invoke
call so it can forward every event to that request's browser tab as it
happens, without graph.py knowing anything about HTTP/SSE.
"""
import contextlib
import contextvars
import time
from typing import Any, Optional

_sink: contextvars.ContextVar = contextvars.ContextVar("trace_sink", default=None)


@contextlib.contextmanager
def bind(loop, queue):
    """Route emit() calls made in this context (and threads spawned from it
    via asyncio.to_thread, which copies the context) to `queue`, delivered
    thread-safely via `loop.call_soon_threadsafe`.
    """
    token = _sink.set((loop, queue))
    try:
        yield
    finally:
        _sink.reset(token)


def emit(event_type: str, **data: Any) -> None:
    print(f"[trace] {event_type} {data}")
    sink = _sink.get()
    if sink is None:
        return
    loop, queue = sink
    event = {"type": event_type, "ts": time.time(), **data}
    loop.call_soon_threadsafe(queue.put_nowait, event)
