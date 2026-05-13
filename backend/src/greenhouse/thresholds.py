"""Threshold evaluation logic — pure functions, no I/O."""

from __future__ import annotations

from typing import TypedDict


class EvaluationResult(TypedDict):
    """Outcome of evaluating one reading against its threshold band."""

    side: str  # "below" | "above"
    severity: str  # "warning" | "critical"
    message: str


# A breach is "critical" when the distance past the band is more than
# CRITICAL_DISTANCE_RATIO times the band width. Below that, it is "warning".
CRITICAL_DISTANCE_RATIO = 0.25


def evaluate(value: float, min_value: float, max_value: float) -> EvaluationResult | None:
    """Decide whether ``value`` breaches the band [min_value, max_value].

    Returns ``None`` when the value is inside the band (inclusive on both
    ends). Otherwise returns a dict describing the breach.
    """
    if min_value <= value <= max_value:
        return None

    band_width = max_value - min_value
    if band_width <= 0:
        band_width = 1.0  # safety net; should be caught at threshold update time

    if value < min_value:
        side = "below"
        distance = min_value - value
        message = f"Value {value} is below minimum {min_value}"
    else:
        side = "above"
        distance = value - max_value
        message = f"Value {value} is above maximum {max_value}"

    severity = "critical" if (distance / band_width) > CRITICAL_DISTANCE_RATIO else "warning"
    return EvaluationResult(side=side, severity=severity, message=message)
