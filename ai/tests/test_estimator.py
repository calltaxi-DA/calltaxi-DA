import pytest

from ai.waiting_time.estimator import estimate_waiting_minutes


def test_estimate_waiting_minutes_returns_hour() -> None:
    result = estimate_waiting_minutes(9)

    assert result.hour_of_day == 9
    assert result.expected_minutes > 0


def test_estimate_waiting_minutes_rejects_invalid_hour() -> None:
    with pytest.raises(ValueError):
        estimate_waiting_minutes(24)
