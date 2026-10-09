"""Model price table for the spend estimate.

KEEP THIS IN STEP WITH ANTHROPIC PRICING. Values are US dollars per million
tokens ``(input, output)``. They are deliberately conservative (high): the
daily spend cap is a safety net, so over-estimating is the safe direction.
Unknown models are priced at ``FALLBACK_PRICE`` (also high). Override without
a code change by setting ``UPDATES_MODEL_PRICES`` to a JSON object such as
``{"claude-sonnet-5-5": [3.0, 15.0]}`` (entries merge over these defaults).
"""

from __future__ import annotations

import json
from typing import Mapping

#: model id -> (input $/MTok, output $/MTok)
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5-5": (3.0, 15.0),
}

#: Used for any model not in the table (high on purpose).
FALLBACK_PRICE: tuple[float, float] = (15.0, 75.0)

#: Fake clients used in tests/dev cost nothing.
FREE_MODELS = frozenset({"fake-guard", "fake-agent"})


def parse_price_overrides(raw: str | None) -> dict[str, tuple[float, float]]:
    if not (raw or "").strip():
        return {}
    try:
        data = json.loads(raw)
        return {str(k): (float(v[0]), float(v[1])) for k, v in data.items()}
    except (ValueError, TypeError, IndexError, AttributeError):
        raise ValueError(
            "UPDATES_MODEL_PRICES must be JSON like {\"model\": [input, output]}"
        ) from None


def cost_usd(
    usage: list[Mapping[str, object]],
    prices: Mapping[str, tuple[float, float]] | None = None,
) -> float:
    """Estimated dollar cost of usage dicts (``model``/``input_tokens``/``output_tokens``)."""
    table = {**MODEL_PRICES, **(prices or {})}
    total = 0.0
    for u in usage:
        model = str(u.get("model", ""))
        if model in FREE_MODELS:
            continue
        p_in, p_out = table.get(model, FALLBACK_PRICE)
        total += (int(u.get("input_tokens", 0) or 0) * p_in
                  + int(u.get("output_tokens", 0) or 0) * p_out) / 1_000_000
    return total
