"""장애인콜택시 시간대별 예상 대기시간 산출.

TODO: notebooks_lye/5-1_plan_시간대별평균대기시간.ipynb, notebooks/06_wait_time_processing_analysis.ipynb
결과를 시간대별 lookup 테이블(또는 모델)로 옮겨와 실제 값을 채운다.
지금은 백엔드가 이 모듈을 어떤 시그니처로 호출할지 확정하기 위한 최소 인터페이스만 제공한다.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WaitingTimeEstimate:
    expected_minutes: float
    hour_of_day: int


def estimate_waiting_minutes(hour_of_day: int) -> WaitingTimeEstimate:
    """주어진 시간대(0~23시)의 예상 대기시간(분)을 반환한다.

    TODO: 실제 시간대별 평균 대기시간 데이터로 대체. 지금은 자리표시용 고정값.
    """
    if not 0 <= hour_of_day <= 23:
        raise ValueError("hour_of_day는 0~23 사이여야 합니다")

    return WaitingTimeEstimate(expected_minutes=30.0, hour_of_day=hour_of_day)
