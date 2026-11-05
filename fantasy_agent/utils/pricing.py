"""Static $/token pricing for LLM usage, to turn `llm_usage` trace events into a dollar cost.

Not wired into any graph or report yet - `estimate_cost` is here for a future caller (e.g.
the audit report or `fantasy_agent/logging/trace.py`) to use.
"""
from typing import Optional

# $ per 1,000,000 tokens, keyed by the model name as reported in an `llm_usage` event's
# `model` field (that comes from `response.response_metadata["model_name"]`, the model
# actually served - not the `FANTASY_AGENT_MODEL` request string, which can differ).
#
# gemini-3.8-flash: intro rate, in effect through 2026-12-31 (doubles to 1.50/7.50 on
# 2027-01-01 per Google's published schedule - update this entry when that takes effect).
# "cached" is an estimate (25% of input rate, the usual Gemini context-cache discount);
# Google hasn't published a cached rate for this model specifically as of 2026-11.
PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "gemini-3.8-flash": {"input": 0.75, "output": 3.75, "thinking": 3.75, "cached": 0.1875},
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
