# analysis/

`ai/`(AI Adapter)가 실제로 호출·서빙하는 **장애인 콜택시 통합 대기시간 Prediction 모델과 그 산출물의 발행처(export 대상)**. `data/`, `notebooks*/`, `src/`(탐색적 분석, 원본/중간 산출물, 팀 작업 공간)와는 구분된다 — 이 폴더에는 "서비스가 그대로 가져다 쓰기로 확정된" 모델/결과만 둔다.

## 규칙

- 노트북/스크립트가 직접 여기 쓰지 않는다. 모델 학습/검증이 끝나고 결과가 안정화되면, 사람이 검토해서 필요한 파일만 이곳에 export한다.
- `ai/`는 `data/`나 `notebooks*/`의 원본 파일을 직접 열지 않고, 이 폴더의 산출물만 참조한다(`docs/architecture.md` "대기시간 예측 흐름", "데이터 소유권" 참고).
- 파일 하나하나에 출처(어떤 노트북/분석에서 나왔는지)와 갱신 방법을 주석 또는 같은 이름의 `.md`로 남긴다.

## 현재 상태

아직 이곳으로 export된 Prediction 모델 파일이나 lookup table은 없다 — `ai/waiting_time/estimator.py`는 그래서 지금 `NotImplementedError`를 발생시킨다.

다만 통합 대기시간 Prediction 모델과 서비스 개발에서 사용할 데이터 기준은 [`waiting_time/data_criteria.md`](waiting_time/data_criteria.md)에 정리했다. 이 문서는 기존 전처리 Notebook을 재실행하지 않고, 임차택시·특장차 대기시간 전처리 기준, 당일/전일 접수 구분, 서비스 목표값(`접수_승차_분`)과 운영 KPI(`접수_배차_분`)의 차이를 확정하기 위한 기준 문서다. 실제 모델 파일이나 분석 산출물을 export할 때는 이 기준을 따른다.

기존 이용패턴 분석 결과 중 통합 대기시간 Prediction 모델의 입력 해석과 결과 검증에 활용할 근거는 [`waiting_time/usage_pattern_evidence.md`](waiting_time/usage_pattern_evidence.md)에 정리했다. 이 문서는 시간대·요일·차량유형·이동유형별 대기시간 분포, 수요 proxy, 장시간 대기율 proxy, leakage 방지 기준을 기존 Notebook output 기준으로 확인한 문서다. 단, 실시간 접수 stream/API/DB가 필요한 rolling 수요량 feature는 현재 1차 production feature에서 제외하고 offline 실험 근거로만 유지한다.

지하철 경로와 접근성 데이터를 연결하기 위한 기준은 [`subway/accessibility_mapping_criteria.md`](subway/accessibility_mapping_criteria.md)에 정리했다. 이 문서는 기존 지하철 전처리 결과, 월별 이용량 데이터와 station accessibility master 분리 기준, 역명·호선 canonical key, 엘리베이터·휠체어리프트·안전발판 등 접근성 시설 연결 기준, ODsay 지하철역 정보와 연결할 매핑 전략을 정리한 문서다. Backend Phase 5-1에서 사용할 검토 완료 접근성 lookup은 [`subway/station_accessibility_master.csv`](subway/station_accessibility_master.csv)에 export했다. 아직 ODsay stationID 매핑 테이블은 없으므로 backend는 현재 `노선명 + 역명정규화` canonical key로 연결한다. 환승 내부 동선까지 포함한 실제 총 도보거리·총 도보시간은 Backend Phase 5-2에서 별도 데이터 또는 실제 ODsay 응답 검증 후 확정한다.

저상버스 경로와 접근성 데이터를 연결하기 위한 기준은 [`bus/low_floor_bus_mapping_criteria.md`](bus/low_floor_bus_mapping_criteria.md)에 정리했다. 이 문서는 현재 확보한 저상버스 노선 metadata, 2025년 버스 승하차/혼잡 대체지표, 노선번호 정규화 기준, ODsay 버스 경로와 연결할 후보 route mapping 전략을 정리한 문서다. 후속 버스 API 연동 Phase에서 사용할 검토 완료 route master는 [`bus/low_floor_bus_route_master.csv`](bus/low_floor_bus_route_master.csv)에 export했다. 아직 ODsay busID/노선번호 실제 응답 검증은 없으므로 이번 산출물은 Analysis Phase 5-1의 route master와 후보 key 정리로 한정한다. 실제 ODsay 버스 경로와의 매핑 성공률 검증은 Phase 5-2에서 진행한다.

저상버스 추천과 혼잡도 분석에 추가로 활용할 수 있는 버스 데이터 후보는 [`bus/bus_additional_data_discovery.md`](bus/bus_additional_data_discovery.md)에 정리했다. 이 문서는 Analysis Phase 6-1 산출물로, 시간대별 승하차 인원, 버스 혼잡도, 재차인원, 배차간격, 실시간 위치·도착정보, 차량별 저상버스 여부의 현재 확보 상태와 공식 API 후보를 구분한 문서다. 현재 서비스에 바로 사용할 수 있는 범위는 노선 단위 저상버스 접근성 및 2025년 집계 기반 혼잡 위험 보조지표까지이며, 실시간 저상버스 도착·차량별 혼잡도·실시간 배차간격은 Phase 6-2에서 실제 API 호출과 필드 의미 검증 이후 확장한다.

버스 공식 API 실제 검증 기준과 현재 blocker는 [`bus/bus_api_validation_criteria.md`](bus/bus_api_validation_criteria.md)에 정리했다. 현재 저장소에는 서울 버스 API 전용 키가 명확히 준비되어 있지 않고, 일부 후보 endpoint가 평문 HTTP를 사용하므로 기존 `MOBILITY_API_KEY`를 임의 전송하지 않았다. 따라서 Phase 6-2는 아직 완료가 아니라 키 준비와 실제 응답 확보가 필요한 상태다.

요금/시간/도보 우선순위 추천 로직은 이 폴더·`ai/`가 아니라 `backend/`가 담당한다(Backend Phase 7 예정).
