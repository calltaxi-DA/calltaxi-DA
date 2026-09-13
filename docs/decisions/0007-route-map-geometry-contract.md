# ADR 0007: RouteResult 지도 표시 geometry 계약

- 상태: 결정됨 (2026-09-14)
- 관련: [ADR 0003](./0003-frontend-map-sdk-exception.md), [ADR 0004](./0004-route-metric-availability-and-recommendation-contract.md)

## 배경

Frontend는 Kakao Maps JavaScript SDK로 지도와 마커를 렌더링할 수 있지만, 실제 경로 계산과 추천 판단은 Backend 책임이다. 추천 결과를 지도 polyline으로 표시하려면 Frontend가 외부 경로 API를 직접 호출하거나 경로를 재구성하지 않고, Backend가 계산한 `RouteResult` 안에 표시 가능한 좌표 구간을 함께 내려줘야 한다.

ODsay 대중교통 경로 응답은 일부 구간에 `graph`, `passStopList.stations`, `startX/startY/endX/endY` 좌표를 제공한다. 다만 모든 구간의 상세 보행로 또는 환승 내부 무장애 동선을 보장하지 않으므로, 좌표가 없는 구간을 임의 추정해 만들면 안 된다.

## 결정

1. `RouteResult`에 optional `route_map_segments`를 추가한다.
2. 각 구간은 `segment_type`, `label`, 2개 이상의 WGS84 좌표 `points`를 가진다.
3. `segment_type`은 `walk`, `subway`, `bus`, `vehicle`로 제한한다.
4. Backend는 외부 API 응답에서 확인 가능한 좌표만 `route_map_segments`에 포함한다.
5. 좌표가 없거나 불완전한 구간은 geometry에서 제외하되, 기존 시간·거리·요금 metric 계산을 실패시키지 않는다.
6. `unavailable` 경로에는 `route_map_segments`를 포함하지 않는다.
7. Frontend는 후속 Phase에서 이 계약을 Kakao Map polyline 렌더링에 사용할 수 있지만, 경로 계산이나 좌표 보정은 수행하지 않는다.

## 영향

- `/routes/subway`, `/routes/bus`, `/routes/recommendations`의 `RouteResult` 응답에 지도 표시용 선택 필드가 추가된다.
- 기존 클라이언트는 필드를 무시할 수 있으므로 수치 추천 계약과 정렬 정책은 변경하지 않는다.
- 지하철과 저상버스는 ODsay 응답의 `graph`, `passStopList.stations`, endpoint 좌표를 순서대로 사용한다.
- 콜택시 차량 상세 geometry는 TMAP 응답 필드 검증이 필요하므로 이번 결정에서는 계약 타입만 열어두고 실제 `vehicle` 구간 생성은 후속 Phase로 남긴다.
- 환승 내부 무장애 동선이나 실측 보행 경로를 좌표로 보완하려면 검토 완료 데이터 또는 별도 외부 API 계약을 확정한 뒤 추가 Phase에서 구현한다.
