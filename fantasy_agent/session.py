"""Per-conversation message history, keyed by caller-supplied id (e.g. a
Discord channel or thread id). chat.py's CLI loop gets away with one
in-memory `messages` list because it only ever has one conversation; a bot
serving many channels at once needs one history per channel instead.
"""
_sessions: dict[str, list] = {}


def get_history(conversation_id: str) -> list:
    return _sessions.setdefault(conversation_id, [])


def set_history(conversation_id: str, messages: list) -> None:
    _sessions[conversation_id] = messages
