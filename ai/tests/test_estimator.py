import pytest

from ai.waiting_time.estimator import estimate_waiting_minutes


def test_estimate_waiting_minutes_raises_when_model_not_connected() -> None:
    """모델 연결 전까지는 가짜 값 대신 NotImplementedError로 명확히 실패해야 한다."""
    with pytest.raises(NotImplementedError):
        estimate_waiting_minutes(9)


def test_estimate_waiting_minutes_rejects_invalid_hour() -> None:
    with pytest.raises(ValueError):
        estimate_waiting_minutes(24)
