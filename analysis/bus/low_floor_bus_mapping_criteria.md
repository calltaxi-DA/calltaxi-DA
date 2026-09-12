# 저상버스 데이터 연결 기준

상태: 확정 (2026-09-12)  
목적: 현재 확보한 저상버스 노선·정류장·승하차 데이터를 재생성하지 않고 확인해, 후속 ODsay 버스 경로와 저상버스 접근성 정보를 연결하기 위한 **노선 단위 canonical key와 활용 범위**를 정리한다.

## 이번 Phase 범위

이번 Phase는 분석 결과를 서비스가 사용할 수 있게 정리하는 analysis Phase다. backend API client, ODsay 실제 버스 경로 호출, frontend 표시, 추천 정렬은 구현하지 않는다.

## 확인한 출처

| 출처 | 확인 목적 |
|---|---|
| `data/raw/bus/all_bus_routes.json` | 서울 버스 노선번호, 내부 노선 ID, 노선 유형, 기종점, 인가대수, 저상버스대수, 저상버스비율, 정류장 순서 확인 |
| `data/processed/bus/버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv` | 저상버스가 있는 노선의 시간대·정류장별 추정 재차인원과 혼잡 보조지표 확인 |
| `data/processed/bus/버스_노선별_시간대별_승하차인원_정제_2025.csv` | 2025년 전체 버스 노선번호 범위와 저상버스 정보 결합 상태 확인 |
| `data/processed/bus/버스_노선정류장별_총승하차인원_정제_2025.csv` | 노선·정류장 단위 승하차 수요와 정류장 key 후보 확인 |
| `data/processed/bus/버스_정류장별_시간대별_승하차인원_정제_2025.csv` | 정류장 단위 시간대별 수요와 정류장 위치 정보 확인 |
| `data/processed/bus/버스_승하차인원_원본월별요약_2025.csv` | 원본 승하차 데이터의 월별 범위와 노선/정류장 규모 확인 |

## 현재 데이터 규모

| 데이터 | 행/건수 | 주요 확인 내용 |
|---|---:|---|
| `all_bus_routes.json` | 364개 노선 | 노선번호 364개 모두 unique |
| `버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv` | 896,304행 | 320개 저상버스 노선이 `all_bus_routes.json` 노선번호와 매칭 |
| `버스_노선별_시간대별_승하차인원_정제_2025.csv` | 17,208행 | 671개 노선번호, 이 중 343개가 `all_bus_routes.json` 노선번호와 매칭 |
| `버스_노선정류장별_총승하차인원_정제_2025.csv` | 52,337행 | 노선·정류장 단위 연간 총승하차 수요 |
| `버스_정류장별_시간대별_승하차인원_정제_2025.csv` | 1,112,424행 | 정류장·시간대 단위 연간 승하차 수요 |
| `버스_승하차인원_원본월별요약_2025.csv` | 12행 | 2025-01~2025-12, 월별 노선수 657~662개 |

중요: 전체 승하차 데이터의 노선 범위와 `all_bus_routes.json`의 저상버스/노선 상세 범위는 다르다. 따라서 모든 승하차 노선에 저상버스 접근성 정보를 제공할 수 있다고 해석하지 않는다.

## 저상버스 노선 현황

`all_bus_routes.json` 기준 저상버스 노선 현황은 다음과 같다.

| 항목 | 값 |
|---|---:|
| 전체 노선 수 | 364 |
| 노선번호 unique 수 | 364 |
| `노선번호 정규화` 중복 수 | 0 |
| 저상버스 1대 이상 보유 노선 | 322 |
| 저상버스 0대 노선 | 40 |
| 저상버스 정보 미확인 노선 | 2 |
| 평균 저상버스 비율 | 약 0.6872 |
| 저상버스 비율 100% 노선 | 96 |
| 정류장 순서 보유 노선 | 362 |
| 정류장 순서 미보유 노선 | 2 |

저상버스 정보가 미확인된 노선은 `1155`, `8553`이다. 이 두 노선은 `id`, `type`, `endpoints`, `authorized`, `low_count`, `low_rate`, `stops`가 비어 있어 서비스에서는 `unknown` 상태로 처리해야 한다.

## 노선번호 정규화 기준

ODsay 버스 경로와 내부 저상버스 데이터를 연결할 1차 canonical key는 다음이다.

```text
route_number_normalized
```

정규화 규칙:

1. 문자열로 변환
2. 앞뒤 공백 제거
3. 내부 공백 제거
4. 영문 대문자화
5. 선행 0은 제거하지 않음

예시:

| 원본 | 정규화 |
|---|---|
| `01A` | `01A` |
| `0017` | `0017` |
| ` 7016 ` | `7016` |

선행 0은 의미가 있는 노선번호일 수 있으므로 유지한다. 예를 들어 `0017`과 `17`은 자동으로 같은 노선으로 합치지 않는다.

## ODsay 버스 경로 연결 기준

아직 이 저장소에서는 ODsay 버스 실제 응답 샘플을 확보하지 않았다. 따라서 ODsay의 `busID`와 서울시/내부 `seoul_route_id`가 동일하다고 가정하지 않는다.

후속 ODsay 버스 연동 Phase에서는 다음 순서로 매핑한다.

| 우선순위 | key | 설명 |
|---:|---|---|
| 1 | ODsay busID ↔ 검토 완료 route mapping table | 실제 ODsay 응답 샘플로 busID 의미를 확인한 뒤 사용 |
| 2 | `route_number_normalized` + ODsay 버스 유형 | 노선번호가 unique인 현재 route master의 1차 fallback |
| 3 | `route_number_normalized` 단독 | 현재 `analysis/bus/low_floor_bus_route_master.csv`에서는 unique지만, 타 지역/동명이 노선 확장 시 진단용으로 제한 |

현재 서울 저상버스 route master에서는 `route_number_normalized`가 364개 모두 unique다. 따라서 MVP의 서울 버스 범위에서는 ODsay가 노선번호를 안정적으로 제공할 경우 이 key로 저상버스 접근성 정보를 연결할 수 있다.

다만 ODsay 실제 응답에서 다음 항목을 반드시 확인해야 한다.

- 버스 구간의 노선번호 필드명과 표기 방식
- ODsay `busID`가 서울시 노선 ID와 같은지 여부
- 순환/지선/간선/마을 등 버스 유형 표기 방식
- 같은 노선번호가 지역/유형 차이로 중복될 가능성

## 접근성 판단 기준

서비스에서 노선별 저상버스 접근성은 다음처럼 해석한다.

| 조건 | 상태 | 서비스 해석 |
|---|---|---|
| `low_floor_bus_count > 0` | `available` | 해당 노선에 저상버스 운행 정보가 있음 |
| `low_floor_bus_count = 0` | `unavailable` | 현재 확보 데이터 기준 저상버스 운행 정보가 없음 |
| `low_floor_bus_count` 결측 | `unknown` | 저상버스 정보 미확인, 상세 확인 필요 |

주의: 노선에 저상버스가 있다는 것은 “사용자가 탑승하려는 특정 시간·정류장에 저상버스가 곧 도착한다”는 뜻이 아니다. 현재 데이터는 노선 단위 보유/운행 정보이며, 실시간 차량 위치·배차·저상버스 도착정보는 포함하지 않는다.

## 혼잡도 보조 지표 활용 기준

`버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv`의 `저상버스1대당_추정재차인원`은 연간 승하차 집계와 정류장 순서 누적 방식으로 만든 혼잡 대체지표다.

따라서 이 값은 다음 용도로만 사용한다.

- 노선별·시간대별 혼잡 위험 비교
- 저상버스 접근성은 있으나 혼잡 주의가 필요한 노선 식별
- 후속 추천 로직 검증용 보조 지표

다음 용도로 사용하지 않는다.

- 실시간 재차인원
- 특정 차량의 실제 혼잡도
- 특정 시간에 반드시 탑승 가능한지 판단하는 값

## 데이터 기준일 관리

| 항목 | 기준 |
|---|---|
| 승하차/혼잡 대체지표 | 2025년 1월~12월 연간 집계 |
| 저상버스 노선 metadata | `data/raw/bus/all_bus_routes.json` 확보본 기준 |
| route master export | `analysis/bus/low_floor_bus_route_master.csv` |
| ODsay mapping 검증 | 아직 실제 응답 샘플 미확보 |

`all_bus_routes.json` 자체에는 명시적인 기준일 컬럼이 없다. 따라서 현재 export에는 `기준연도=2025`를 두되, 노선 metadata의 실제 기준일은 “원본 확보본 기준”으로 관리한다. 후속 데이터 갱신 시에는 원본 수집일 또는 공공데이터 기준일을 별도 컬럼으로 추가해야 한다.

## Backend/서비스에서 사용할 export

이번 Phase에서 서비스 연결 후보로 검토한 route master는 다음이다.

```text
analysis/bus/low_floor_bus_route_master.csv
```

주요 컬럼:

| 컬럼 | 설명 |
|---|---|
| `기준연도` | 승하차/혼잡 대체지표 기준 연도 |
| `route_number` | 원본 노선번호 |
| `route_number_normalized` | ODsay 연결용 1차 canonical key |
| `seoul_route_id` | `all_bus_routes.json`의 내부 노선 ID. ODsay busID와 동일하다고 가정하지 않음 |
| `route_type_code` | 원본 노선 유형 코드 |
| `endpoints` | 기종점 |
| `authorized_bus_count` | 인가대수 |
| `low_floor_bus_count` | 저상버스대수 |
| `low_floor_bus_rate` | 저상버스비율 |
| `has_low_floor_bus` | 저상버스 1대 이상 여부 |
| `accessibility_status` | `available`, `unavailable`, `unknown` |
| `stop_count` | 노선 정류장 수 |
| `has_stop_sequence` | 정류장 순서 보유 여부 |
| `congestion_data_available` | 저상버스 혼잡 대체지표 존재 여부 |
| `max_low_floor_bus_load_per_bus` | 노선 내 최대 저상버스 1대당 추정 재차인원 |
| `p95_low_floor_bus_load_per_bus` | 노선 내 95분위 저상버스 1대당 추정 재차인원 |
| `peak_load_hour` | 최대 혼잡 대체지표 발생 시간대 |
| `peak_load_stop_name` | 최대 혼잡 대체지표 발생 정류장 |
| `peak_load_direction` | 최대 혼잡 대체지표 발생 방향 |
| `has_top25_low_floor_congestion` | 상위 25% 혼잡 구간 보유 여부 |

검증 결과:

| 검증 항목 | 결과 |
|---|---:|
| export 행 수 | 364 |
| `route_number_normalized` unique 수 | 364 |
| `route_number_normalized` 중복 수 | 0 |
| 혼잡 대체지표 매칭 노선 수 | 320 |
| 저상버스 접근성 `available` | 322 |
| 저상버스 접근성 `unavailable` | 40 |
| 저상버스 접근성 `unknown` | 2 |

## 이번 Phase에서 확정한 활용 대상

1. 저상버스 route master의 1차 canonical key는 `route_number_normalized`로 둔다.
2. ODsay `busID`와 서울시/내부 `seoul_route_id`는 동일하다고 가정하지 않는다.
3. 후속 ODsay 버스 연동 Phase에서 실제 응답 샘플을 확보해 `busID`, 노선번호, 버스유형의 매핑 성공률을 검증한다.
4. 노선별 저상버스 접근성 상태는 `available`, `unavailable`, `unknown`으로 구분한다.
5. 혼잡도 관련 값은 실시간 혼잡이 아니라 연간 집계 기반 대체지표로만 사용한다.
6. 서비스 코드는 `data/raw`나 `data/processed`를 직접 읽지 않고, 검토 완료된 `analysis/bus/low_floor_bus_route_master.csv`만 사용한다.

## 후속 Phase가 해야 할 일

- ODsay 버스 경로 실제 응답 샘플을 확보해 노선번호, busID, 버스 유형 필드를 확인한다.
- ODsay busID와 `analysis/bus/low_floor_bus_route_master.csv`의 매핑 성공률, 미매핑 노선, 다중 매칭 노선을 기록한다.
- 실시간 저상버스 도착정보가 필요하면 별도 API/데이터 소스를 확보한다.
- 저상버스 혼잡도는 실시간 값이 아니므로 추천 로직에 직접 반영하기 전에 별도 검증 기준을 둔다.
