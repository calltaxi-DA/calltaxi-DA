"""요금/시간/도보 우선순위에 따른 Rule-based 경로 정렬.

기획서(§8 기본 추천 로직) 기준:
- 요금 우선: 비용 → 시간 → 도보거리
- 시간 우선: 총 이동시간 → 비용 → 도보거리
- 도보 최소: 도보거리 → 비용 → 총 이동시간
"""

from dataclasses import dataclass
from typing import Literal

PriorityMode = Literal["cost", "time", "walk"]

_SORT_KEYS: dict[PriorityMode, tuple[str, ...]] = {
    "cost": ("cost", "total_minutes", "walk_meters"),
    "time": ("total_minutes", "cost", "walk_meters"),
    "walk": ("walk_meters", "cost", "total_minutes"),
}


@dataclass(frozen=True)
class RouteCandidate:
    mode: str
    cost: float
    total_minutes: float
    walk_meters: float


def rank_routes(
    candidates: list[RouteCandidate], priority: PriorityMode
) -> list[RouteCandidate]:
    """우선순위 기준으로 정렬된 경로 후보 목록을 반환한다.

    TODO: 접근성 필터링(엘리베이터/저상버스 여부 등)은 후보 생성 단계에서 처리하고
    이 함수는 이미 필터링된 후보만 받는다고 가정한다.
    """
    if priority not in _SORT_KEYS:
        raise ValueError(f"알 수 없는 priority: {priority}")

    keys = _SORT_KEYS[priority]
    return sorted(candidates, key=lambda c: tuple(getattr(c, key) for key in keys))
