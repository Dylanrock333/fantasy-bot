"""Static $/token pricing for LLM usage, to turn `llm_usage` trace events into a dollar cost.

Not wired into any graph or report yet - `PRICING_PER_MILLION_TOKENS` is empty until real
rates for the model(s) in `FANTASY_AGENT_MODEL` are confirmed. `estimate_cost` is here for a
future caller (e.g. the audit report or `fantasy_agent/logging/trace.py`) to use once it is.
"""
from typing import Optional

# $ per 1,000,000 tokens, keyed by the model name as reported in an `llm_usage` event's
# `model` field (that comes from `response.response_metadata["model_name"]`, the model
# actually served - not the `FANTASY_AGENT_MODEL` request string, which can differ).
PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    # "gemini-3.7-flash": {"input": 0.0, "output": 0.0, "thinking": 0.0, "cached": 0.0},
}


def estimate_cost(
    model: Optional[str],
    input_tokens: int = 0,
    output_tokens: int = 0,
    thinking_tokens: int = 0,
    cached_tokens: int = 0,
) -> Optional[float]:
    """Return the dollar cost of one LLM call, or None if `model` has no rate entry.

    `output_tokens` is expected to already include `thinking_tokens` (as Gemini's
    usage_metadata reports it), so thinking tokens are priced here and not double-counted.
    """
    rates = PRICING_PER_MILLION_TOKENS.get(model)
    if rates is None:
        return None
    billed_input = max(input_tokens - cached_tokens, 0)
    billed_output = max(output_tokens - thinking_tokens, 0)
    return (
        billed_input * rates["input"]
        + billed_output * rates["output"]
        + thinking_tokens * rates["thinking"]
        + cached_tokens * rates["cached"]
    ) / 1_000_000
