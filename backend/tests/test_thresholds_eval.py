"""Unit tests for the pure threshold-evaluation logic."""

from __future__ import annotations

from greenhouse.thresholds import evaluate


def test_inside_band_returns_none() -> None:
    assert evaluate(22.5, 15.0, 32.0) is None


def test_inclusive_lower_bound() -> None:
    assert evaluate(15.0, 15.0, 32.0) is None


def test_inclusive_upper_bound() -> None:
    assert evaluate(32.0, 15.0, 32.0) is None


def test_just_below_warning() -> None:
    # Band width 17.0, 1.0 below = 5.9% past => warning.
    result = evaluate(14.0, 15.0, 32.0)
    assert result is not None
    assert result["severity"] == "warning"
    assert result["side"] == "below"


def test_far_below_critical() -> None:
    result = evaluate(0.0, 15.0, 32.0)
    assert result is not None
    assert result["severity"] == "critical"


def test_just_above_warning() -> None:
    result = evaluate(33.0, 15.0, 32.0)
    assert result is not None
    assert result["severity"] == "warning"
    assert result["side"] == "above"


def test_far_above_critical() -> None:
    result = evaluate(60.0, 15.0, 32.0)
    assert result is not None
    assert result["severity"] == "critical"


def test_zero_width_band_safe() -> None:
    # Defensive: should not blow up even if persisted state is bad.
    result = evaluate(5.0, 10.0, 10.0)
    assert result is not None
    assert "below" in result["message"].lower()
