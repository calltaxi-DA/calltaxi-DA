# ADR 0004: 경로 지표 가용 상태와 추천 계약

- 상태: 결정됨 (2026-09-12)
- 관련: [ADR 0002](./0002-ai-as-adapter-only.md), [`analysis/transport_comparison_criteria.md`](../../analysis/transport_comparison_criteria.md)

## 배경

기존 `RouteResult`는 `available` 경로의 시간·거리·비용·도보거리·도보시간을 모두 필수로 요구했다. 그러나 장애인 콜택시는 검증된 승하차 접근 도보 데이터가 없어, 대기시간과 차량 이동시간이 준비되어도 도보값을 근거 없이 0으로 넣지 않고서는 `available` 경로를 표현할 수 없었다.

Backend Phase 7은 세 이동수단을 사용자 우선순위로 정렬해야 한다. 누락 지표를 0으로 대체하지 않으면서 부분적으로 계산 가능한 경로를 표현하고, 접근성 미확인을 정상 접근성으로 해석하지 않도록 계약 변경이 필요하다.

## 결정

1. `RouteResult`에 numeric field별 `available`/`not_available` 상태인 `metric_availability`를 추가한다.
2. `available` metric은 값이 필수이고, `not_available` metric은 반드시 `null`이어야 한다.
3. 경로 자체가 `unavailable`이면 모든 numeric metric은 `null/not_available`이며 기존처럼 `unavailable_reason`이 필수다.
4. 접근성은 경로 상태와 분리해 `verified_available`, `verified_unavailable`, `not_verified`로 표현한다.
5. 공개 추천 요청은 출발지·목적지와 `time`, `cost`, `walk`의 중복 없는 우선순위만 받는다. 클라이언트가 제출한 `RouteResult`는 추천 입력으로 받지 않는다.
6. 추천 라우터는 Backend 소유 `RecommendationRouteProvider`에서 세 이동수단 결과를 생성한 뒤 정렬 서비스에 전달한다. 통합 provider가 준비되지 않은 운영 상태에서는 가짜 경로를 만들지 않고 `503`으로 fail-closed한다.
7. 1순위 metric이 `not_available`인 경로와 `verified_unavailable` 경로는 추천 후보에서 제외하고 사유를 반환한다.
8. 2·3순위 metric이 없는 후보는 앞선 지표가 동률일 때 해당 metric이 있는 후보보다 뒤에 둔다. 수치 대체값은 만들지 않는다.
9. 모든 우선순위 값이 같으면 `calltaxi`, `subway`, `low_floor_bus` 순서의 고정 tie-breaker를 사용해 응답 재현성을 보장한다. 이 순서는 선호 점수가 아니라 완전 동률 해소 규칙이다.
10. 추천 정렬은 `backend/`의 순수 서비스에 두고 HTTP 라우터는 Backend provider 호출과 요청·응답 변환만 담당한다.

## 영향

- 시간·비용 1순위이고 해당 지표가 준비된 세 경로는 TOP 3을 반환할 수 있다.
- 콜택시 도보 metric이 `not_available`인 동안 도보 1순위 추천은 지하철·저상버스만 반환하고 콜택시 제외 사유를 함께 반환한다.
- 기존 지하철·저상버스 API는 numeric metric을 모두 제공하므로 생략된 `metric_availability`가 모두 `available`로 해석된다.
- 기존 응답에는 `metric_availability`, `accessibility_status` 필드가 추가된다. 필드 추가를 반영하는 Frontend 연동은 별도 Phase에서 진행한다.
- `POST /routes/recommendations` 요청에는 `routes`가 존재하지 않으며 추가 필드도 거부한다. 서로 다른 출발지·목적지의 결과를 클라이언트가 조합하거나 지표를 조작할 수 없다.
- 현재 대기시간 모델이 없어 운영용 통합 provider는 연결하지 않았다. dependency override 기반으로 Backend provider→통합→정렬 경계를 검증했지만 기본 endpoint는 `503`을 반환한다.
- 따라서 Backend Phase 7 전체는 완료가 아니며, 이번 산출물은 Phase 7-1 추천 계약·정렬 엔진 및 Backend-owned orchestration 경계까지만 완료한 것이다.
