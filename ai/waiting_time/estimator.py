"""AI Adapter: 장애인 콜택시 통합 대기시간 Prediction 모델 연동 지점.

이 모듈은 예측 모델 자체가 아니라, backend가 예측 모델을 호출하기 위해 쓰는 어댑터다.
아직 실제 모델이 연결되지 않았으므로 호출 시 NotImplementedError를 발생시킨다 —
연결 전까지 가짜 값을 반환해 문제를 숨기지 않는다.

TODO: 장애인 콜택시 통합 대기시간 Prediction 모델이 준비되면 이 함수 내부에서 모델을 호출하도록 구현한다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WaitingTimeEstimate:
    expected_minutes: float
    hour_of_day: int


def estimate_waiting_minutes(hour_of_day: int) -> WaitingTimeEstimate:
    """주어진 시간대(0~23시)의 예상 대기시간(분)을 반환한다.

    모델이 연결되기 전까지는 항상 NotImplementedError를 발생시킨다.
    호출하는 쪽(backend)은 이 예외를 잡아 "대기시간 예측 불가" 상태로 처리해야 한다.
    """
    if not 0 <= hour_of_day <= 23:
        raise ValueError("hour_of_day는 0~23 사이여야 합니다")

    raise NotImplementedError(
        "장애인 콜택시 통합 대기시간 Prediction 모델이 아직 연결되지 않았습니다."
    )
