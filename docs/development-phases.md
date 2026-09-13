# 개발 단계 추적

## 작성 기준

- Phase는 완료된 뒤에 기록한다(계획 단계에서 미리 여러 Phase를 만들어두지 않는다).
- 각 Phase 항목: 날짜, 한 일, 만들어진 산출물(파일/브랜치/PR), 다음 Phase가 이어받을 것.
- 화면/API 설계처럼 아직 확정되지 않은 것은 "다음 Phase 산출물"에만 적고, 앞당겨 구현하지 않는다.

## Phase 0 — 모노레포 초기 스캐폴딩 (2026-09-10)

- 브랜치: `feat/service-bootstrap` (base: `dev`)
- 한 일: `backend/`(FastAPI), `ai/`(AI Adapter 골격), `frontend/`(Vite+React+TS)를 기존 데이터분석 구조와 분리해 추가. `analysis/`를 분석→서비스 경계(Prediction 모델 export 전용 공간)로 추가. 이후 `ai/`에서 추천 정렬(`recommendation/`)을 제거하고 예측 모델 어댑터 역할로 좁힘(ADR 0002), `estimator.py`가 모델 미연결 시 `NotImplementedError`를 던지도록 변경. `docs/`, `AGENTS.md`, 루트 `README.md` 정비.
- 산출물:
  - `GET /health` 동작(200 확인), `pytest`(backend+ai) 5개 통과, `npm run build`/`npm test`(frontend) 통과
  - `docs/architecture.md`(폴더 책임/데이터 소유권/대기시간 예측 흐름), `docs/decisions/0001-monorepo-and-stack.md`, `docs/decisions/0002-ai-as-adapter-only.md`
  - `analysis/README.md` — export 규칙만 정의, 아직 실제 export된 Prediction 모델은 없음
- 다음 Phase가 이어받을 것:
  - 화면 1(MAP) → 화면 2(경로 비교) → 화면 3(교통비 캘린더) 구체 설계 — 원 기획서에서 이미 다음 단계로 지정된 작업
  - 특장차/임차택시 Prediction 모델을 `analysis/`로 export하고, `ai/waiting_time/estimator.py`가 그 모델을 실제로 호출하도록 구현(현재는 `NotImplementedError`)
  - **Backend Phase 7**: 요금/시간/도보 우선순위 추천 정렬(Rule-based)을 `backend/`에 구현 — `ai/`가 아니라 `backend/`가 담당(ADR 0002)

## Phase 0 — Backend 프로젝트 기반 보강 (2026-09-11)

- 브랜치: `feat/service-bootstrap`에 직접 반영 후 `backend/phase1-api-contract` PR(base: `dev`)에 포함
- 한 일: FastAPI 백엔드 기본 골격에서 누락되어 있던 공통 예외 처리 레이어를 추가. 예상하지 못한 서버 예외는 상세 내용을 응답에 노출하지 않고 `500 {"detail": "Internal Server Error"}`로 변환하도록 했다. 기존 `/health`, 설정 로딩, JSON 로깅, 테스트 구조는 유지했다.
- 산출물:
  - `backend/app/core/exceptions.py` — 공통 500 예외 핸들러
  - `backend/app/main.py` — 전역 예외 핸들러 등록
  - `backend/tests/test_health.py` — `/health` 성공 응답과 안전한 500 응답 테스트
- 검증 결과:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 4개 통과
  - `uvicorn app.main:app --host 127.0.0.1 --port 8010` 실행 후 `GET /health` — 200, `{"status":"ok"}` 확인
- 다음 Phase가 이어받을 것:
  - 화면/API 계약이 확정되기 전까지 경로 추천, 지도 API 연동, 대기시간 모델 연결은 구현하지 않는다.
  - 새로운 백엔드 라우트가 추가되면 `backend/app/api/`에 라우터와 요청/응답 스키마를 두고 `backend/tests/`에 TestClient 기반 테스트를 함께 추가한다.

## Backend Phase 1 — 공통 데이터 구조 및 API Contract (2026-09-11)

- 브랜치: `backend/phase1-api-contract` (base: `dev`, Phase 0 Backend 보강 커밋 포함)
- 한 일: 장애인 콜택시, 지하철, 저상버스를 같은 응답 구조로 다루기 위한 공통 API 계약을 정의했다. 위치(`Location`), 이동수단(`TransportType`), 경로 상태(`RouteStatus`), 경로 결과(`RouteResult`), 경로 비교 응답(`RouteComparisonResponse`)을 Pydantic 모델로 추가하고, 시간·거리·비용 단위를 각각 초/미터/원으로 명시했다. 도보거리(`walking_distance_meters`)와 도보시간(`walking_time_seconds`)은 이용 가능한 모든 이동수단 경로 결과에 포함되도록 했다. 외부 API 실패·경로 없음·운행 없음은 가짜 0값 대신 `unavailable` 상태와 `unavailable_reason`으로 표현한다.
- 산출물:
  - `backend/app/api/contracts.py` — 공통 계약 모델
  - `backend/app/api/routes.py` — `APP_ENABLE_SAMPLE_ROUTES=true`일 때만 등록되는 계약 확인용 샘플 라우터
  - `backend/app/core/config.py`, `backend/.env.example` — 샘플 라우터를 기본 비활성화하는 fail-closed 설정
  - `backend/tests/test_route_contracts.py` — 도보거리·도보시간 포함 여부, 음수 단위 거부, 이용불가 상태, 정확히 3개 이동수단·중복 금지, 좌표 범위 검증
  - `.github/workflows/backend-tests.yml` — PR/push 시 backend+ai pytest 자동 실행
- 검증 결과:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 26개 통과
  - `APP_ENABLE_SAMPLE_ROUTES=true uvicorn app.main:app --host 127.0.0.1 --port 8011` 실행 후 `GET /routes/sample` — 200, `calltaxi`, `subway`, `low_floor_bus` 3개 이동수단과 도보거리·도보시간 필드 포함 확인
  - 기본 설정으로 `uvicorn app.main:app --host 127.0.0.1 --port 8011` 실행 시 `GET /routes/sample` — 404 확인
  - `create_app()` 기본 설정과 `create_app(include_sample_routes=False)` 기준 `/routes/sample` — 404 확인
  - `create_app(include_sample_routes=True)` 기준 `/routes/sample` — 200 확인
- 다음 Phase가 이어받을 것:
  - 실제 카카오/티맵/ODSAY 등 외부 경로 API 호출은 이번 Phase 범위가 아니므로 이후 Backend Phase에서 구현한다.
  - 추천 정렬, 경로 점수화, 대기시간 모델 연결은 아직 구현하지 않는다.

## Frontend Phase 1 — 기본 화면 및 사용자 입력 UI (2026-09-11)

- 브랜치: `frontend/phase1-basic-input-ui` (base: `dev`)
- 한 일: 사용자가 경로 검색에 필요한 조건을 입력할 수 있는 기본 화면을 구성했다. 출발지·목적지 입력창, 장애인 콜택시·지하철·저상버스 선택, 시간·비용·도보 기준의 1순위·2순위·3순위 선택, 경로검색 버튼과 입력 조건 요약 영역을 추가했다. 실제 경로 검색 API 호출과 지도 표시는 이후 Phase로 남겼다.
- 산출물:
  - `frontend/src/App.tsx` — 기본 입력 UI와 로컬 입력 상태
  - `frontend/src/index.css` — 반응형 기본 스타일
  - `frontend/src/__tests__/App.test.tsx` — 입력 UI 렌더링과 조건 입력/제출 테스트
  - `.github/workflows/frontend-tests.yml` — PR/push 시 frontend test/build 자동 실행
- 검증 결과:
  - `npm test` — 5개 통과
  - `npm run build` — TypeScript 빌드 및 Vite production build 통과
- 다음 Phase가 이어받을 것:
  - 지도 SDK, 실제 위치 검색, backend API client 연결은 아직 구현하지 않는다.
  - 경로 결과 표시와 추천 정렬 UI는 backend 계약과 API가 준비된 뒤 진행한다.

## Frontend Phase 2 — Kakao Map 및 장소검색 연동 (2026-09-11)

- 브랜치: `frontend/phase2-kakao-map-search` (base: `dev`)
- 한 일: 사용자가 Kakao 장소검색으로 실제 출발지·목적지를 검색하고 지도에서 선택 위치를 확인할 수 있게 했다. Kakao Maps JavaScript SDK를 루트 `.env`의 `KAKAO_JS_KEY` 환경변수 기반으로 동적 로드하고, 장소검색 결과 선택 시 입력값·좌표를 저장하며 지도 중심 이동과 Marker 표시가 이루어지도록 했다. 이후 화면을 일반 폼 중심이 아니라 지도 앱처럼 전체 지도 위에 검색 패널이 떠 있는 구조로 정리했다. 입력값 수정 시 이전 Marker와 선택 좌표를 함께 무효화하고, 오래된 장소검색 응답이 최신 결과를 덮어쓰지 않도록 role별 request id를 적용했다. 경로검색은 출발지·목적지 좌표가 모두 선택된 경우에만 가능하다. 실제 경로 검색 API 호출은 아직 연결하지 않고, 검색 조건 요약에 선택 좌표만 포함했다.
- 산출물:
  - `frontend/src/App.tsx` — Kakao Maps SDK 로딩, 장소검색, 출발지·목적지 좌표 상태, Marker 표시
  - `frontend/src/index.css` — 지도 카드, 장소검색 결과, 선택 위치 표시 스타일
  - `frontend/src/__tests__/App.test.tsx` — 지도/장소검색 UI 렌더링, SDK 미준비 상태 안내, SDK namespace 누락 실패 처리, 장소검색→위치 선택→Marker 생성, 입력 수정 시 Marker 제거, stale 검색 응답 무시, 장소 선택 후 pending 검색 응답 무시, 장소검색 오류 구분, 좌표 선택 전 경로검색 비활성화 테스트
  - `.env.example`, `frontend/.env.example`, `frontend/vite.config.ts` — 프론트 내부 Kakao env를 제거하고 루트 `.env`의 `KAKAO_JS_KEY`만 사용하도록 설정
  - `docs/decisions/0003-frontend-map-sdk-exception.md` — Kakao Maps JavaScript SDK 브라우저 직접 사용 예외 기록
- 검증 결과:
  - `npm test` — 13개 통과
  - `npm run build` — TypeScript 빌드 및 Vite production build 통과
  - `npm run lint` — oxlint 통과
  - 실제 Kakao 앱키가 필요한 브라우저 smoke test는 루트 `.env`의 `KAKAO_JS_KEY`와 Kakao Developers의 localhost 도메인 등록이 필요하므로, merge 전 사람이 `서울시청`/`서울역` 검색과 Marker 표시를 수동 확인한다.
- 다음 Phase가 이어받을 것:
  - 실제 경로검색 backend API 연결과 RouteResult 표시 UI는 아직 구현하지 않는다.
  - Kakao REST API, TMAP/대중교통 경로 API, 추천 정렬은 이후 Backend/API 연동 Phase에서 구현한다.
  - 지도에서 직접 클릭해 출발지·목적지를 지정하는 기능은 이번 Phase 범위에 포함하지 않았다.

## Backend Phase 2 — 장애인 콜택시 경로 및 요금 (2026-09-12)

- 브랜치: `backend/phase2-calltaxi-tmap-route` (base: `dev`)
- 한 일: TMAP 자동차 경로안내 API를 이용해 출발지·목적지 좌표 기반 장애인 콜택시 차량 이동거리와 차량 이동시간을 계산하는 백엔드 경로를 추가했다. `/routes/calltaxi`는 `RouteRequest`의 출발지·목적지 좌표를 받아 `CalltaxiRouteResponse` 형식으로 차량 이동거리(`vehicle_distance_meters`), 차량 이동시간(`vehicle_time_seconds`), 거리 기반 예상요금(`estimated_fare_won`)을 반환한다. 기존 `RouteResult.total_time_seconds`는 대기시간을 포함한 총 소요시간 계약이므로 이번 Phase에서는 차량시간의 별칭으로 사용하지 않는다. 예상요금은 서울 장애인콜택시 공식 거리요금 기준(5km까지 1,500원, 5km 초과 10km까지 km당 280원, 10km 초과 km당 70원, 100원 미만 절사)으로 산출하고, 통행료·주차료 등 추가 비용 제외 안내를 `warnings`에 포함한다. TMAP 키가 없으면 `503`, TMAP 호출/응답 실패는 `502`로 명시한다.
- 산출물:
  - `backend/app/api/contracts.py` — 출발지·목적지 단일 경로 계산 요청 `RouteRequest`, 장애인 콜택시 차량경로 전용 응답 `CalltaxiRouteResponse` 추가
  - `backend/app/api/calltaxi.py` — `POST /routes/calltaxi` 라우터 추가
  - `backend/app/services/calltaxi.py` — TMAP 자동차 경로안내 클라이언트, `totalDistance`·`totalTime` 파싱, 서울 장애인콜택시 예상요금 계산
  - `backend/app/main.py` — 장애인 콜택시 라우터 등록
  - `backend/app/core/config.py`, `backend/.env.example` — `APP_TMAP_APP_KEY` 설정 추가, 로컬 호환을 위해 `TMAP_APP_KEY`도 읽도록 지원
  - `backend/tests/test_calltaxi_routes.py` — 라우터 응답, 좌표 검증, 키 누락, TMAP 실패·invalid JSON 처리 테스트
  - `backend/tests/test_calltaxi_service.py` — 요금 계산, TMAP 응답 파싱, outbound 요청 URL·헤더·payload 검증 테스트
  - `backend/tests/test_config.py` — `APP_TMAP_APP_KEY`와 `TMAP_APP_KEY` alias 설정 로딩 테스트
  - `docs/troubleshooting.md` — 실제 TMAP smoke test `403 Forbidden` 이슈 기록
- 검증 결과:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 46개 통과
  - 로컬 `APP_TMAP_APP_KEY` 또는 `TMAP_APP_KEY` 존재 확인 — 키 값은 출력하지 않고 존재 여부만 확인
  - 실제 TMAP 자동차 경로안내 smoke test — `403 Forbidden`으로 실패. 코드 요청/응답 처리 검증은 완료됐지만, 실제 키의 자동차 경로안내 API 상품 권한 또는 제한 설정 확인이 필요하다.
- 다음 Phase가 이어받을 것:
  - TMAP 개발자 콘솔에서 App Key가 자동차 경로안내 API를 사용할 수 있는지 확인하고 실제 smoke test를 재실행한다.
  - 프론트엔드 경로검색 버튼과 `/routes/calltaxi` 연결은 이번 Phase 범위가 아니므로 이후 Frontend/API 연동 Phase에서 진행한다.
  - 장애인 콜택시 대기시간 예측 모델 연결과 총 이동시간에 대기시간을 합산하는 작업은 AI Adapter/대기시간 Phase에서 진행한다.
  - 지하철·저상버스 경로 API와 추천 정렬은 별도 Backend Phase에서 구현한다.

## Analysis Phase — 통합 대기시간 Prediction 데이터 기준 확정 (2026-09-12)

- 브랜치: `analysis/waiting-time-data-criteria` (base: `dev`)
- 한 일: 이미 작성된 장애인 콜택시 대기시간 전처리 Notebook과 특장차 전처리 스크립트를 재실행하지 않고 확인해, 통합 대기시간 Prediction 모델과 서비스 개발에서 사용할 데이터 기준을 문서화했다. 임차택시와 특장차의 차량구분 기준, 결측치·이상치 처리, 날짜·시간 파생 변수, 전일접수·당일접수·심야시간 사전예약 기준, 서비스 대기시간 목표값과 운영 KPI의 차이를 하나의 기준 문서로 확정했다. 현재 저장소에는 공통 정제 탑승내역은 존재하지만 대기시간 전처리 산출 CSV는 존재하지 않으므로, 실제 모델 export 전 사람이 이 기준에 맞는 산출물을 검토해 `analysis/`에 export해야 함을 명시했다.
- 산출물:
  - `analysis/waiting_time/data_criteria.md` — 통합 대기시간 Prediction 데이터 기준 문서
  - `analysis/README.md` — 대기시간 기준 문서 위치와 현재 export 상태 갱신
- 검증 결과:
  - 기존 Notebook/스크립트 읽기 확인: `notebooks_waiting_time/01_rental_wait_time_data_preprocessing.ipynb`, `notebooks_waiting_time/03_wait_time_data_preprocessing.ipynb`, `notebooks_waiting_time/04_special_vehicle_wait_time_analysis.ipynb`, `src/waiting_time/special_vehicle_preprocessing.py`
  - 현재 존재 파일 확인: `data/processed/서울시설공단_장애인콜택시 탑승내역_정제_20251231.csv` 존재 및 필수 컬럼 샘플 확인
  - 현재 미존재 파일 확인: `data/processed/임차택시_대기시간_전처리.csv`, `data/processed/특장차_대기시간_전처리.csv`, `data/processed/특장차_대기시간_전처리_접수유형분류.csv`
  - 데이터 재생성, Notebook 수정, `data/` 파일 변경 없음
- 확정 기준 요약:
  - 1차 통합 서비스 Prediction 모델은 하나로 가져가되, 학습 대상은 임차택시 바로콜과 특장차 바로콜 후보로 제한한다.
  - 서비스 1차 target은 사용자가 실제로 차량에 타기 전까지의 체감 대기시간인 `접수_승차_분`으로 둔다.
  - `접수_승차_분` 학습에는 `접수일시`와 `승차일시`가 존재하고 `접수_승차_분 >= 0`인 건을 사용하며, `배차일시`는 필수 조건으로 두지 않는다.
  - `접수_배차_분`은 차량 배정까지의 운영 병목을 설명하는 KPI와 보조 target으로 유지한다.
  - 임차택시는 예약 목적이 아니고 `접수_승차_분`이 0~250분인 건을 offline 정제·평가용 바로콜 기준으로 본다.
  - 특장차 바로콜은 전일접수·심야시간 사전예약 후보를 제외하고, 당일 접수·당일 승차 또는 자정 넘김 0~200분 이내 건을 offline 정제·평가용 기준으로 본다.
  - 실제 inference 시점의 feature와 세그먼트는 `승차일시`, `배차일시`, `하차일시`, 실제 `승차거리`, 실제 `요금`, target 파생값을 쓰지 않고 접수 순간에 존재하는 값만 사용한다.
  - 전일접수·심야시간 사전예약은 1차 모델에서 제외하고, `예정일시` 기준 Prediction은 후속 Phase에서 별도로 정의한다.
- 다음 Phase가 이어받을 것:
  - 기준에 맞는 대기시간 전처리 산출 CSV 또는 모델/lookup 산출물을 사람이 검토해 `analysis/`에 export한다.
  - `ai/waiting_time/estimator.py`는 export 산출물이 준비된 뒤에만 실제 모델 호출로 대체한다.
  - 서비스 연결 Phase에서는 예측 실패/미연결 상태를 명시적으로 처리한다.

## Analysis Phase 2 — 장애인 콜택시 이용패턴 분석 근거 정리 (2026-09-12)

- 브랜치: `analysis/phase2-usage-pattern-evidence` (base: `dev`)
- 한 일: 기존에 완료된 장애인 콜택시 이용패턴 분석 Notebook을 재실행하지 않고 확인해, 통합 대기시간 Prediction 모델의 입력 해석과 결과 검증에 활용할 분석 근거를 문서화했다. 임차택시·특장차 바로콜의 대기시간 분포, 시간대·요일별 이용패턴, 전일접수 포함 시 시간대 평균이 왜곡되는 현상, 취소 패턴, 수요 proxy와 장시간 대기율 proxy의 성능 개선 근거, leakage 방지 기준을 정리했다.
- 산출물:
  - `analysis/waiting_time/usage_pattern_evidence.md` — 이용패턴 분석 근거와 모델 검증 활용 기준
  - `analysis/README.md` — 이용패턴 근거 문서 위치 추가
- 검증 결과:
  - 기존 Notebook/output 읽기 확인: `notebooks_waiting_time/02_rental_wait_time_analysis.ipynb`, `notebooks_waiting_time/04_special_vehicle_wait_time_analysis.ipynb`, `notebooks_lye/5-1_plan_시간대별평균대기시간.ipynb`, `notebooks_waiting_time/05_calltaxi_wait_time_modeling.ipynb`, `notebooks_waiting_time/06_calltaxi_wait_time_feature_experiments.ipynb`, `notebooks_waiting_time/07_calltaxi_wait_time_hgb_modeling.ipynb`, `notebooks_waiting_time/08_calltaxi_wait_time_feature_set_v2.ipynb`, `notebooks_waiting_time/corr_original.ipynb`
  - 데이터 재생성, Notebook 수정, `data/` 파일 변경 없음
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 46개 통과
- 확정 기준 요약:
  - 모델 검증은 전체 평균만 보지 않고 `model_group`, 시간대, 요일, 세부이동유형별 분포와 오차를 함께 확인한다.
  - 서비스 target은 `접수_승차_분`이며, 장시간 대기 위험 기준은 train set의 `접수_승차_분` 90분위수 기준으로 평가한다.
  - 새벽 02~06시는 제거 대상이 아니라 별도 위험 시간대 또는 segment 검증 대상으로 유지한다.
  - 전일접수·심야시간 사전예약은 1차 바로콜 모델에서 제외하고, 시간대 평균 분석에서도 왜곡 요인으로 분리한다.
  - 직전 30분/60분 rolling 수요량 proxy는 현재 실시간 전체 접수 stream/API/DB가 없으므로 1차 production feature에서는 제외하고 offline 실험 근거로만 유지한다.
  - 장시간 대기율 proxy는 train 기준 통계 또는 out-of-fold 방식으로만 생성하며, production 사용은 `analysis/` lookup export와 inference-safe key 재정의 이후 판단한다.
  - 기존 Notebook의 `model_group`은 offline evaluation segment로만 사용하고, production feature에는 inference 시점에 안전하게 알 수 있는 `차량구분`을 사용한다.
- 다음 Phase가 이어받을 것:
  - 학습용 바로콜 dataset export 시 row count, target 결측/음수 제외 건수, `model_group`별 건수, 시간대별 건수, 취소 제외 건수를 함께 기록한다.
  - 모델 학습 Phase에서는 전체 MAE/RMSE뿐 아니라 `model_group`·시간대·요일·이동유형별 성능표와 장시간 대기 Precision/Recall/F1을 함께 남긴다.
  - production feature set 확정 전, 각 feature가 inference 시점에 생성 가능한지와 데이터 출처가 무엇인지 다시 검증한다.
  - `analysis/`에 실제 모델/lookup 산출물을 export하기 전까지 `ai/waiting_time/estimator.py`는 미연결 상태를 유지한다.

## Analysis Phase 3 — 병원 이동 이용패턴 서비스 활용 기준 (2026-09-13)

- 브랜치: `analysis/phase3-hospital-usage-pattern` (base: `dev`)
- 한 일: 기존 병원·의료목적 이동 Notebook과 저장된 output을 재실행하지 않고 확인해 Backend와 Frontend에서 제공할 의료 목적지 분석정보를 확정했다. 의료목적콜의 목적지 자치구·행정동별 이용량, 같은구·다른구 이동, 5km 거리 커버리지, 자치구 순유입·순유출을 제공 대상으로 선정했다. 개별 탑승건과 병원 식별자가 연결되지 않는 데이터 한계를 확인해 Phase 요구사항의 `병원별 이용량`은 **데이터 제약으로 미충족** 처리하고, 제공 단위를 `의료목적콜 도착 지역별 이용량`으로 제한했다. 병원 이동 전용 시간대 및 특장차·임차택시 비교는 기존 분석 결과가 없음을 확인하고 전체콜·전체 바로콜 결과로 대체하지 않도록 명시했다.
- 산출물:
  - `analysis/hospital/hospital_destination_insights.md` — 의료목적콜 정의, 모집단, 확정 결과, 표·그래프 선정, Backend/Frontend 인계와 제공 금지 기준
  - `analysis/README.md` — 병원 이동 분석 기준 문서 링크와 현재 제공 범위 추가
- 확정 기준:
  - 서비스의 병원 목적지 분석정보는 개별 병원 단위가 아니라 의료목적으로 기록된 이동의 목적지 자치구·행정동 단위 집계다.
  - 목적지 서울 기준 126,705건, 서울 내부 OD 기준 126,566건, 100km 초과 이상치 제외 거리 분석 기준 126,561건을 서로 다른 모집단으로 구분한다.
  - 네 서비스 제공 분석 ID의 `source_period`는 모두 `2025-01-01 ~ 2025-12-31`(접수일시 기준, `Asia/Seoul`)로 확정한다. 기간 경계에서 승차·하차가 2026년 1월 1일로 넘어간 건은 2025년 12월 31일 접수 건에 포함한다.
  - 목적지 이용량 상위 자치구·행정동, 같은구 41.8%·다른구 58.2%, 전체 5km 이내 55.9%, 자치구 순유입·순유출을 서비스 제공 후보로 확정한다.
  - 의료기관 수·병원급 규모·재활의학과와 콜 건수의 관계는 탐색적 참고정보로만 유지하며 추천 점수·병원 평가·인과 설명에 사용하지 않는다.
  - 기존 전체콜 시간대·요일 결과를 병원 이동 시간대 결과로 표시하지 않는다.
  - 기존 임차택시·특장차 바로콜 대기시간 비교를 병원 이동 차량유형 비교로 표시하지 않는다. 병원 이동 전용 차량유형 분석은 현재 미확정이다.
  - 특장차·임차택시 기존 비교 결과의 존재와 수치는 확인했으나 병원 이동 전용 결과가 아니므로 서비스 재사용 불가로 확정한다.
  - 서비스 코드가 Notebook 또는 `data/processed`를 직접 읽지 않는다. 실제 구현 전에 선택 집계를 `analysis/hospital/`로 수동 export해야 한다.
- 검증 결과:
  - 관련 Notebook 7개와 기존 이용패턴 기준 문서의 저장된 셀·output을 읽고, Notebook 재실행 및 `data/` 변경이 없음을 확인
  - 문서에 목적지 이용량, 지역 간 이동, 거리, 시간대 결과의 범위, 특장차·임차택시 비교 상태, 선정 표·그래프, Backend/Frontend 인계가 모두 포함됨을 확인
  - 기존 산출물 경로와 선정 이미지 4개의 존재 여부 확인
  - `git diff --check` 통과
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 147개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건 외 실패 없음
  - `cd frontend && npm test -- --run` — 18개 통과
- 다음 Phase가 이어받을 것:
  - Backend 분석정보 API 범위가 확정되면 필요한 집계 파일만 출처·생성일·갱신 방법과 함께 `analysis/hospital/`로 수동 export하고, Backend는 해당 export만 읽는다.
  - Frontend는 `의료목적콜 도착 지역`이라는 표현과 모집단·한계를 함께 표시하고 Backend 값을 재계산하지 않는다.
  - 개별 병원별 이용량을 제공하려면 병원 식별자·좌표와 탑승 목적지를 검증 가능하게 연결하는 데이터가 먼저 필요하다.
  - 병원 이동 전용 시간대 및 특장차·임차택시 비교가 필요하면 기존 결과 활용 범위를 넘어서는 별도 분석으로 승인받아 수행한다.

## Analysis Phase 4 — 지하철 접근성 데이터 분석 기준 정리 (2026-09-12)

- 브랜치: `analysis/phase4-subway-accessibility` (base: `dev`)
- 한 일: 기존에 완료된 지하철 데이터 전처리와 지하철·콜택시 비교 분석 Notebook을 재실행하지 않고 확인해, ODsay 지하철 경로와 접근성 시설 데이터를 연결하기 위한 내부 canonical key와 매핑 전략을 문서화했다. 월별 승하차 데이터와 station accessibility master 분리 기준, 역명·호선 매핑 기준, 엘리베이터 설치정보·위치·운행구간, 휠체어리프트·안전발판·장애인화장실 보조 정보, 서울 25개 구 기준 지하철·콜택시 비교 분석 활용 범위를 정리했다.
- 산출물:
  - `analysis/subway/accessibility_mapping_criteria.md` — 지하철 접근성 데이터 연결 기준, station master 분리 기준, ODsay 매핑 전략
  - `analysis/README.md` — 지하철 접근성 기준 문서 위치 추가
- 검증 결과:
  - 기존 Notebook 읽기 확인: `parkchansik/10_subway_data_preprocessing.ipynb`, `parkchansik/11_subway_calltaxi_comparison_analysis.ipynb`
  - 현재 존재 파일 확인: `data/processed/서울교통공사_장애인_지하철_승하차인원_정제_20251231.csv`, `data/raw/교통약자이용정보_엘리베이터.csv`, `data/raw/교통약자이용정보_휠체어리프트.csv`, `data/raw/교통약자이용정보_안전발판보유현황.csv`, `data/raw/교통약자이용정보_장애인화장실.csv`, `data/raw/교통약자이용정보_휠체어급속충전기.csv`
  - key 중복 확인: 월별 processed CSV는 `노선명+역명정규화` 160개 key가 최대 12개월씩 반복되며, 최신월 기준 station master로 분리하면 158행·중복 0건으로 확인
  - 데이터 재생성, Notebook 수정, `data/` 파일 변경 없음
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 46개 통과
- 확정 기준 요약:
  - 월별 승하차 데이터와 station accessibility master를 분리한다.
  - station accessibility master의 내부 canonical key는 `노선명 + 역명 정규화`로 둔다.
  - `고유역번호(외부역코드)`는 서울교통공사 원본 검증용 보조 key이며, ODsay stationID와 동일하다고 가정하지 않는다.
  - ODsay stationID 매핑 테이블과 실제 응답 샘플 검증은 아직 없으므로, 이번 Phase는 ODsay 최종 key 검증 완료가 아니라 후속 연결을 위한 내부 canonical key와 매핑 전략 확정으로 본다.
  - 1차 접근성 판단은 `운행엘리베이터보유여부`, `운행엘리베이터수`, `엘리베이터연결층`, `엘리베이터설치위치`를 우선 사용한다.
  - 접근성 평가는 출발역, 모든 환승역, 도착역에 대해 수행한다.
  - 휠체어리프트, 안전발판, 장애인화장실, 휠체어 급속충전기는 보조 접근성 정보로 사용한다.
  - 지하철·콜택시 비교 분석 결과는 추천 로직이 아니라 서비스 분석 근거와 검증 지표로 사용한다.
- 다음 Phase가 이어받을 것:
  - ODsay 지하철 경로 응답 샘플을 확보해 stationID, 역명, 노선명 필드를 확인한다.
  - ODsay stationID와 station accessibility master의 `노선명+역명정규화`를 연결하는 매핑 테이블을 만들고 매핑 성공률, 미매핑 역, 다중 매칭 역을 기록한다.
  - 환승 0회, 1회, 2회 경로 샘플에서 출발역·모든 환승역·도착역 접근성 lookup이 모두 검사되는지 검증한다.
  - 검토 완료된 지하철 접근성 lookup만 `analysis/`에 export한다.
  - backend/frontend는 `data/processed`를 직접 읽지 않고, 검토 완료된 `analysis/` 산출물만 사용한다.

## Backend Phase 5-1 — ODsay 지하철 경로 및 접근성 1차 연동 (2026-09-12)

- 브랜치: `backend/phase5-subway-accessibility-route` (base: `dev`)
- 범위 조정: 원래 Backend Phase 5 요구사항의 “환승 내부 동선까지 포함한 실제 총 도보거리·총 도보시간”은 현재 ODsay 제공값과 보유 데이터만으로 검증 완료할 수 없으므로 이번 PR의 범위를 **Phase 5-1**로 낮춘다. 이번 Phase는 “ODsay 제공 도보 subPath 기준 지하철 경로 + 접근성 lookup 1차 연동”까지만 완료 처리하고, 실제 총 도보거리·총 도보시간 확정은 **Backend Phase 5-2**로 분리한다.
- 한 일: ODsay 지하철 경로 응답을 backend에서 받아 공통 `RouteResult` 계약으로 반환하는 `/routes/subway` API를 추가했다. ODsay 요청에는 `SearchType=0`, `SearchPathType=1`을 넣어 지하철 전용 경로만 요청하고, 응답에서도 `pathType=1`이며 지하철/도보 subPath만 포함된 경로만 선택하도록 방어했다. ODsay 응답의 총 이동시간, 총 이동거리, 요금, ODsay가 제공한 도보 subPath 기준 도보거리·도보시간을 파싱한다. 환승역별 내부 무장애 동선 거리·시간에 대한 공식/실측 lookup이 아직 없으므로 근거 없는 임의 추정값은 `walking_time_seconds`나 `walking_distance_meters`에 섞지 않고, API warning에서 ODsay 제공 도보 subPath 기준임을 명시한다. 접근성 데이터는 `analysis/subway/station_accessibility_master.csv`로 export한 reviewed station master를 backend provider가 읽어 출발역·환승역·도착역 접근성을 검사한다.
- 산출물:
  - `backend/app/api/subway.py` — `POST /routes/subway` 라우터
  - `backend/app/services/subway.py` — ODsay 지하철 경로 클라이언트, 응답 파서, CSV 기반 접근성 lookup provider, 접근성 warning 생성
  - `backend/app/main.py` — 지하철 라우터 등록
  - `backend/app/core/config.py`, `backend/.env.example` — `APP_ODSAY_API_KEY` 설정 추가, 로컬 호환을 위해 `ODSAY_API_KEY`도 읽도록 지원
  - `analysis/subway/station_accessibility_master.csv` — 최신월 기준 검토 완료 station accessibility master export
  - `analysis/subway/accessibility_mapping_criteria.md`, `analysis/README.md` — station master export 상태와 ODsay 환승 도보시간 한계 반영
  - `backend/tests/test_subway_routes.py` — 라우터 응답, 좌표 검증, 키 누락, ODsay 실패 처리, 접근성 warning 테스트
  - `backend/tests/test_subway_service.py` — ODsay 응답 파싱, 도보거리·도보시간 합산, outbound 요청 검증, 혼합 버스+지하철 경로 제외, CSV 접근성 provider 로딩, 환승역 접근성 검사 테스트
  - `backend/tests/test_config.py` — ODsay API key alias 설정 로딩 테스트
- 검증 결과:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 62개 통과
  - Mock ODsay 응답 기준 `totalTime`, `totalDistance`, `payment`, ODsay 도보 subPath 기준 도보거리·도보시간 합산 확인
  - ODsay outbound 요청에 `SearchType=0`, `SearchPathType=1` 포함 확인
  - 응답 첫 번째 경로가 버스+지하철 혼합 경로여도 `/routes/subway`는 순수 지하철 경로만 선택하는지 확인
  - `analysis/subway/station_accessibility_master.csv` 로딩과 `노선명+역명정규화` lookup 확인
  - 환승 1회 경로에서 출발역, 환승역의 각 노선 구간, 도착역 접근성 lookup 호출 확인
  - 실제 ODsay smoke test는 수행하지 않았다. 운영 적용 전 backend용 ODsay Server Key/IP 등록, 실제 응답의 stationID/역명/노선명 형식, 환승 0회·1회·2회 경로의 도보 subPath 제공 여부 확인이 필요하다.
- 다음 Phase가 이어받을 것:
  - 실제 ODsay API 응답 샘플로 stationID, 역명, 노선명 필드를 확인하고 `analysis/subway/accessibility_mapping_criteria.md`의 canonical key와 매칭 성공률을 검증한다.
  - ODsay가 환승 내부 도보시간·도보거리를 실제로 제공하는지 환승 0회, 1회, 2회 실제 경로 샘플에서 검증한다.
  - ODsay 제공값만으로 실제 총 도보시간·총 도보거리를 충족하지 못하면, 환승역별 내부 무장애 동선 거리·시간 공식 데이터 또는 실측 기준을 확보해 `analysis/` lookup으로 export한 뒤 backend에서 보완한다.
  - 현재 Phase 5-1의 `walking_time_seconds`, `walking_distance_meters`는 ODsay 제공 도보 subPath 기준이며, 실제 환승 내부 동선까지 포함한 총 도보값으로 단정하지 않는다.
  - 지하철 접근성 결과를 frontend에 표시하는 작업은 별도 Frontend/API 연동 Phase에서 진행한다.

## Backend Phase 5-2 — 지하철 실제 총 도보거리·총 도보시간 보완 (다음 Phase)

- 상태: 미완료 / 후속 Phase로 분리
- 목표: 출발지→역, 환승역 내부 동선, 역→목적지 도보구간을 모두 포함한 실제 총 도보거리와 총 도보시간을 확정한다.
- 필요한 일:
  - ODsay 실제 응답 샘플에서 환승 0회·1회·2회 경로의 도보 subPath가 환승 내부 거리·시간을 포함하는지 검증
  - 포함하지 않는 경우 환승역별 무장애 내부 동선 거리·시간 공식 데이터 또는 실측 기준 확보
  - 검토 완료된 환승 동선 lookup을 `analysis/`에 export
  - backend가 ODsay 제공 도보 subPath와 환승 동선 lookup을 합산해 실제 총 도보거리·총 도보시간을 반환하도록 보완
- 주의: 이 Phase가 완료되기 전까지 `walking_time_seconds`, `walking_distance_meters`를 실제 환승 내부 동선까지 포함한 총 도보값으로 표시하지 않는다.

## Analysis Phase 5-1 — 저상버스 데이터 분석 및 route master 정리 (2026-09-12)

- 브랜치: `analysis/phase5-low-floor-bus` (base: `dev`)
- 범위 조정: 원래 Analysis Phase 5 요구사항의 “ODsay에서 조회한 버스 경로와 기존 저상버스 데이터를 연결하여 노선별 저상버스 접근성 정보를 제공할 수 있음”은 실제 ODsay 버스 응답 샘플 검증이 필요하다. 이번 PR은 **Analysis Phase 5-1**로 범위를 낮춰 저상버스 데이터 분석, 후보 route mapping key 정의, route master export까지만 완료 처리하고, 실제 ODsay 버스 응답 기반 매핑 성공률 검증은 **Phase 5-2**로 분리한다.
- 한 일: 현재 확보한 저상버스 노선 metadata와 2025년 버스 승하차/혼잡 대체지표를 재생성하지 않고 확인해, 후속 ODsay 버스 경로와 저상버스 접근성 데이터를 연결하기 위한 노선 단위 후보 canonical key와 route master를 정리했다. 노선번호 정규화 기준, 노선별 인가대수·저상버스대수·저상버스비율, 저상버스 접근성 상태, 혼잡 대체지표의 활용 한계, 데이터 기준일 관리 기준을 문서화했다.
- 산출물:
  - `analysis/bus/low_floor_bus_mapping_criteria.md` — 저상버스 데이터 연결 기준, 노선번호 정규화, ODsay 버스 경로 mapping 전략, 데이터 기준일 관리
  - `analysis/bus/low_floor_bus_route_master.csv` — 후속 서비스 연동 후보 route master
  - `analysis/README.md` — 저상버스 기준 문서와 route master 위치 추가
- 검증 결과:
  - 현재 존재 파일 확인: `data/raw/bus/all_bus_routes.json`, `data/processed/bus/버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv`, `data/processed/bus/버스_노선별_시간대별_승하차인원_정제_2025.csv`, `data/processed/bus/버스_노선정류장별_총승하차인원_정제_2025.csv`, `data/processed/bus/버스_정류장별_시간대별_승하차인원_정제_2025.csv`, `data/processed/bus/버스_승하차인원_원본월별요약_2025.csv`
  - `all_bus_routes.json` 기준 전체 364개 노선, `route_number_normalized` 364개 unique, 중복 0건 확인
  - 저상버스 1대 이상 보유 노선 322개, 저상버스 0대 노선 40개, 저상버스 정보 미확인 노선 2개 확인
  - 정류장 순서 보유 노선 362개, 정류장 순서 미보유 노선 2개 확인
  - `버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv`의 320개 노선이 route master 노선번호와 모두 매칭됨을 확인
  - `analysis/bus/low_floor_bus_route_master.csv` export 결과 364행, `route_number_normalized` 중복 0건, 혼잡 대체지표 매칭 노선 320개 확인
  - `ridership_basis_year=2025`, `route_metadata_as_of=unknown`으로 승하차/혼잡 지표 기준연도와 저상버스 노선 metadata 기준일을 분리
  - 데이터 재생성, Notebook 수정, `data/` 파일 변경 없음
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 62개 통과
- 확정 기준 요약:
  - 저상버스 route master의 1차 후보 canonical key는 `route_number_normalized`로 둔다.
  - ODsay `busID`와 서울시/내부 `seoul_route_id`는 동일하다고 가정하지 않는다.
  - 이번 Phase는 ODsay 실제 연결 검증 완료가 아니라 route master와 후보 key 정리 단계다.
  - 후속 ODsay 버스 연동 Phase 5-2에서 실제 응답 샘플을 확보해 `busID`, 노선번호, 버스유형의 매핑 성공률을 검증한다.
  - 노선별 저상버스 접근성 상태는 `available`, `unavailable`, `unknown`으로 구분한다.
  - `저상버스1대당_추정재차인원`은 2025년 연간 승하차 집계와 정류장 순서 누적 방식으로 만든 혼잡 대체지표이며, 실시간 재차인원으로 사용하지 않는다.
  - 서비스 코드는 `data/raw`나 `data/processed`를 직접 읽지 않고, 검토 완료된 `analysis/bus/low_floor_bus_route_master.csv`만 사용한다.
- 다음 Phase가 이어받을 것:
  - ODsay 버스 경로 실제 응답 샘플을 확보해 노선번호, busID, 버스 유형 필드를 확인한다.
  - ODsay busID와 `analysis/bus/low_floor_bus_route_master.csv`의 매핑 성공률, 미매핑 노선, 다중 매칭 노선을 기록한다.
  - `route_type_code`가 비어 있는 노선의 ODsay 매핑 처리 기준을 별도로 확정한다.
  - 실시간 저상버스 도착정보가 필요하면 별도 API/데이터 소스를 확보한다.
  - 저상버스 혼잡도는 실시간 값이 아니므로 추천 로직에 직접 반영하기 전에 별도 검증 기준을 둔다.

## Analysis Phase 5-2 — ODsay 버스 route mapping 실제 검증 (2026-09-12)

- 상태: 완료
- 한 일: 서울 내부 실제 버스 경로 요청 11건에서 고유 `busID/busNo/type` lane 조합 65개를 확인하고 서울 route master와 대조했다. 검토 완료된 51개(78.46%)만 명시적 매핑으로 export했으며, 경기·광역 유형 및 route master 미등록 14개(21.54%)는 제외했다.
- 산출물: `analysis/bus/odsay_seoul_bus_route_mapping.csv`
- 확정 기준: backend는 mapping export의 `busID`를 우선 조회하고 `busNo`와 `type`도 모두 일치할 때만 서울 노선으로 인정한다. 노선번호 단독 fallback은 사용하지 않는다.

## Analysis Phase 6-1 — 버스 추가 데이터 후보 탐색 및 서비스 적용 범위 정리 (2026-09-12)

- 브랜치: `analysis/phase6-bus-data-discovery` (base: `dev`)
- 범위 조정: 원래 Analysis Phase 6 요구사항의 “각 버스 데이터의 확보 가능 여부와 수집 방법 확정”은 실제 API 호출, 응답 필드 의미 검증, ID mapping 검증이 필요하다. 이번 PR은 **Analysis Phase 6-1**로 범위를 낮춰 현재 확보 데이터 확인, 공식 API 후보 탐색, 서비스 적용 가능 범위 분류까지만 완료 처리하고, 실제 API 호출·필드 검증·수집 방법 확정은 **Analysis Phase 6-2**로 분리한다.
- 한 일: 저상버스 이동 추천과 혼잡도 분석에 추가로 활용할 수 있는 버스 데이터 후보를 확인하고, 현재 확보 데이터·공식 API 후보·서비스 적용 가능 범위를 구분했다. 기존 `data/raw`, `data/processed`를 재생성하지 않고 컬럼과 규모만 확인했으며, 공식 데이터는 서울 버스위치정보조회, 버스도착정보조회, 정류소정보조회, T-DATA 정류장 정보, 교통카드 빅데이터 시스템, TOPIS Open API 안내를 우선 후보로 정리했다. 비공식 크롤링은 공식 API·CSV로 해결되지 않는 항목에 한해 약관·저작권·호출 제한 검토 후에만 고려하기로 했다.
- 산출물:
  - `analysis/bus/bus_additional_data_discovery.md` — 버스 추가 데이터 후보, 공식 API 후보, 서비스 적용 범위 정리
  - `analysis/README.md` — 버스 추가 데이터 탐색 기준 문서 위치 추가
- 검증 결과:
  - 현재 존재 파일 확인: `analysis/bus/low_floor_bus_route_master.csv`, `data/raw/bus/all_bus_routes.json`, `data/processed/bus/버스_저상노선_시간대별_추정재차인원_혼잡도_2025.csv`, `data/processed/bus/버스_노선별_시간대별_승하차인원_정제_2025.csv`, `data/processed/bus/버스_노선정류장별_총승하차인원_정제_2025.csv`, `data/processed/bus/버스_정류장별_시간대별_승하차인원_정제_2025.csv`, `data/processed/bus/버스_승하차인원_원본월별요약_2025.csv`
  - `analysis/bus/low_floor_bus_route_master.csv` 364행, `route_number_normalized` unique 364개, `route_type_code` 결측 34건 확인
  - 저상버스 접근성 상태: `available` 322개, `unavailable` 40개, `unknown` 2개 확인
  - 저상버스 혼잡 대체지표 896,304행, 노선별 시간대별 승하차 17,208행, 노선·정류장별 총승하차 52,337행, 정류장별 시간대별 승하차 1,112,424행 확인
  - 공식 API 후보 확인: 서울특별시_버스위치정보조회 서비스는 실시간 위치, 차량번호, 차량유형, 혼잡도 후보로 확인했고, 서울시 버스 특정차량 위치정보는 차량유형 후보로 확인했다. 정류장 정보와 교통카드 빅데이터의 재차인원/혼잡도 지표는 후속 키·권한 확인 대상으로 정리했다. 이 단계는 공식 API 후보 확인이며, 실제 API 호출 성공·필드 의미·서비스 적용 가능성은 아직 확정하지 않았다.
  - 데이터 재생성, Notebook 수정, `data/` 파일 변경 없음
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 62개 통과
- 확정 기준 요약:
  - 현재 서비스에 바로 사용할 수 있는 범위는 노선 단위 저상버스 접근성(`available`/`unavailable`/`unknown`)과 2025년 집계 기반 혼잡 위험 보조지표까지다.
  - 기존 혼잡 대체지표는 실시간 재차인원이나 특정 차량 혼잡도가 아니므로 “현재 혼잡”처럼 표시하지 않는다.
  - `low_floor_bus_count > 0`은 노선 단위 저상버스 운행 정보가 있다는 뜻이지, 사용자가 기다리는 정류장에 저상버스가 곧 도착한다는 뜻이 아니다.
  - 실시간 버스 위치·도착정보, 차량별 저상버스 여부, 실시간 혼잡도, 실시간 배차간격은 서울 공식 API 응답 필드와 ID mapping을 검증한 뒤에만 서비스 로직에 반영한다.
  - 배차간격은 아직 수집 방법이 확정되지 않았다. 후속 Phase에서 노선 운행정보 API의 계획/평균 배차간격 필드 또는 실시간 위치·도착정보 기반 headway 계산 가능성을 검증한다.
  - 비공식 크롤링은 공식 API·CSV로 해결되지 않는 항목에만 검토하며, 약관·저작권·호출 부하 확인 전에는 핵심 로직에 사용하지 않는다.
- 다음 Phase가 이어받을 것:
  - ODsay 인증 문제를 해결해 버스 경로 응답의 노선번호, `busID`, 버스 유형, 정류장 ID 필드를 확인한다.
  - 서울 버스위치정보조회 API 키를 준비하고 샘플 노선 10~20개에서 차량유형·혼잡도·저상 여부 필드 의미를 확인한다.
  - 서울 버스도착정보조회 API에서 정류장·노선별 도착예정정보를 확보하고 ODsay 정류장 ID와 서울 BIS/ARS ID mapping 가능성을 검증한다.
  - 차량별 저상 여부가 안정적으로 확인되면 “노선 단위 접근성”과 “실시간 차량 단위 접근성”을 분리해 `analysis/` 기준 문서를 갱신한다.
  - 필요한 경우 backend는 공식 API client를 구현하되, `data/raw`나 `data/processed`를 직접 읽지 않는다.

## Analysis Phase 6-2 — 버스 공식 API 호출 가능성 및 수집 방법 검증 (2026-09-12)

- 브랜치: `analysis/phase6-2-bus-api-validation-from-6-1` (base: `dev`)
- 한 일: 사용자가 확인한 서울 버스 위치·도착 API의 활용승인 상태와 공식 endpoint를 바탕으로, 키를 보내지 않은 HTTP 요청과 HTTPS 연결을 검증했다. 공식 endpoint는 HTTP로만 도달 가능하고 HTTPS는 timeout이 발생해 인증키를 전송하지 않았다. ODsay 버스 경로 API는 HTTPS로 실제 호출했으나 `[ApiKeyAuthFailed]`가 재현됐다. T-DATA 재차인원 파일·Open API의 제공 단위와 활용신청 조건을 확인해 각 후보를 `가능`, `조건부`, `불가`로 판정했다.
- 산출물:
  - `analysis/bus/bus_api_validation_criteria.md` — 실제 확인 결과, 보안·인증 blocker, 항목별 최종 판정과 재검토 조건
- 검증 결과:
  - `가능`: 노선 단위 저상버스 접근성, 2025년 집계 기반 혼잡 위험 보조지표
  - `조건부`: T-DATA 재차인원 오프라인 분석·검토 후 `analysis/` export, ODsay ↔ 서울 BIS/ARS ID mapping
  - `불가`: 현재 endpoint 기준 서울 실시간 위치·도착 직접 연동, 차량별 저상 여부, 실시간 혼잡도, 실시간 배차간격·headway
  - 서울 버스 API 키는 HTTP query로 전송하지 않았고, ODsay 키 값과 요청 query string은 기록하지 않았다.
- 다음 Phase가 이어받을 것:
  - 공식 HTTPS gateway가 제공되면 서울 버스 위치·도착 응답과 차량유형·혼잡도 코드를 재검증한다.
  - ODsay 서버 인증을 정상화한 뒤 실제 버스 경로 응답의 `busID`·정류장 ID 매핑률을 검증한다.
  - T-DATA 활용승인과 실제 데이터 시점·ID를 검증한 뒤 서비스에 필요한 집계만 사람이 `analysis/`로 export한다.

## Backend Phase 6 — 저상버스 경로 및 데이터 연동 (2026-09-12)

- 브랜치: `backend/phase6-low-floor-bus-routes` (base: `dev`)
- 한 일: `POST /routes/bus`를 추가해 ODsay 버스 전용 경로를 조회하고, 검토 완료된 `busID/busNo/type` 조합을 통해서만 서울 저상버스 route master와 연결한다. 모든 버스 구간에서 `available` 노선을 하나 이상 선택할 수 있는 첫 경로만 반환한다. ODsay의 모든 도보 `subPath`에서 `distance`와 `sectionTime`을 필수 검증한 뒤 출발·환승·도착 도보 합계를 반환하며, 누락·음수·NaN·무한대·비수치 값은 0으로 보정하지 않고 외부 응답 오류로 처리한다.
- 산출물:
  - `backend/app/services/bus.py` — ODsay 버스 경로 client·parser, route master provider, 저상버스 경로 선택과 도보 합산
  - `analysis/bus/odsay_seoul_bus_route_mapping.csv` — 검토 완료된 ODsay `busID/busNo/type` 51개 매핑
  - `backend/app/api/bus.py` — `POST /routes/bus`, 외부 API 오류·경로 없음 처리
  - `backend/tests/test_bus_service.py`, `backend/tests/test_bus_routes.py` — 파서·매칭·도보 합산·HTTP 응답 테스트
  - `backend/app/core/logging.py`, `backend/tests/test_logging.py` — HTTP client URL의 query API 키 로그 노출 방지
  - `docs/troubleshooting.md` — ODsay Web/Server Key 불일치와 query API 키 로그 노출의 재현·원인·해결 기록
- 검증 결과:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 118개 통과
  - 실제 ODsay lane 65개 중 51개 매핑(78.46%), 경기·광역 또는 route master 미등록 14개 fail-closed 확인
  - 실제 route master 로딩: `100`, `101`은 `available`, `1155`는 `unknown`으로 조회됨
  - OpenAPI schema에서 `POST /routes/bus` 등록 확인
  - 실제 ODsay 단일 버스 경로: 서울시청→강남역 `402`, 서울역→강남역 `402`, 홍대입구→잠실역 `N73`, 서울대입구→광화문 `501` 확인
  - 실제 ODsay 환승 경로: 노원역→구로디지털단지역에서 `1138 → 150`, 버스 2구간, 도보 3구간 확인
  - 환승 경로 합계: 총 6,240초, 총 30,992m, 도보 300초, 도보 357m 반환
  - 실제 smoke test에서 `httpx` 요청 URL과 ODsay API 키가 로그에 출력되지 않음을 확인
- 확정 기준:
  - 저상버스 접근성은 노선 단위 정보이며 특정 시간·정류장에 도착하는 차량이 저상버스임을 보장하지 않는다.
  - 총 도보거리·총 도보시간은 ODsay가 반환한 모든 도보 `subPath`의 합계이며 실제 보행로 실측값으로 단정하지 않는다. ODsay가 제공하지 않은 실제 보행경로나 임의 보정값은 추가하지 않는다.
  - 실시간 위치·도착·차량별 저상 여부·실시간 혼잡도는 Analysis Phase 6-2 판정에 따라 이번 API에 포함하지 않는다.
- 다음 Phase가 이어받을 것:
  - 새 ODsay 노선은 실제 응답 검토 후 명시적 mapping export에 추가하며, 미등록 lane은 계속 fail-closed 한다.
  - 고정 공인 IP 또는 배포 환경의 고정 egress IP를 ODsay Server 플랫폼에 등록한다.
  - Backend Phase 7에서 콜택시·지하철·저상버스 결과의 Rule-based 추천 정렬을 구현한다.

## Frontend Phase 5 — 지하철 경로 결과 UI (2026-09-12)

- 브랜치: `frontend/phase5-subway-route-ui` (base: `dev`)
- 한 일: 경로검색 시 선택한 출발지·목적지 좌표를 기존 `POST /routes/subway` 계약으로 보내고, 지하철 결과의 총 예상시간·예상비용·도보거리·도보시간·경로 요약·엘리베이터 접근성 경고를 한 카드에서 확인할 수 있도록 구현했다. 요청 중·실패·경로 없음 상태를 구분하며, 지하철을 선택하지 않은 경우에는 지하철 API를 호출하지 않는다. 이동수단 해제, 입력 변경, 새 장소 선택 시 진행 중 요청을 `AbortController`로 취소하고 request ID도 무효화해 이전 조건의 응답이 표시되지 않도록 했다. ODsay 도보 `subPath` 기준이라는 Backend warning을 그대로 표시하고 환승 내부 보행값을 프론트에서 추정하지 않는다.
- 산출물:
  - `frontend/src/api/subway.ts` — `RouteRequest`·`RouteResult`에 대응하는 타입과 지하철 API client
  - `frontend/src/components/SubwayRouteCard.tsx` — 시간·비용·도보 부담·접근성 결과 카드
  - `frontend/src/App.tsx`, `frontend/src/index.css` — 기존 장소선택 흐름과 API 호출·결과 영역·반응형 스타일 연결
  - `frontend/src/__tests__/App.test.tsx` — 실제 요청 body, loading, 성공·오류·unavailable 상태, 이동수단/장소 변경 및 역순 응답 경쟁 조건 검증
  - `frontend/vite.config.ts`, `frontend/.env.example` — 로컬 동일 출처 `/routes` 개발 프록시
  - `docs/troubleshooting.md` — 서로 다른 localhost origin의 CORS 차단과 개발 프록시 해결 기록
- 검증 결과:
  - `npm test` — 19개 통과
  - `npm run build` — TypeScript 및 Vite production build 통과
  - `npm run lint` — oxlint 통과
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests/test_subway_routes.py backend/tests/test_subway_service.py` — 14개 통과
  - 최신 Backend 실제 호출(서울시청→강남역): `200`, 총 2,340초, 1,650원, 도보 351m·660초, `을지로입구역 → 강남역 지하철 경로`와 접근성 경고 반환 확인
  - 개발 서버 HTML·React 모듈 응답 정상 확인. 자동 브라우저 도구는 현재 환경에 설치되지 않아 스크린샷 기반 시각 검증은 수행하지 못했으며, jsdom 렌더 테스트로 필수 표시 항목을 검증했다.
- 확정 기준:
  - 화면의 도보거리·도보시간은 Backend가 반환한 ODsay 도보 `subPath` 합계이며 지하철 환승 내부 도보 전체를 의미하지 않는다.
  - 접근성 경고는 Backend 소유 데이터로 보고 프론트에서 역 접근성을 재판정하지 않는다.
  - 로컬 개발은 Vite proxy를 사용한다. 분리 배포 시에는 Backend CORS allowlist 또는 같은 origin reverse proxy 설계가 추가로 필요하다.
- 다음 Phase가 이어받을 것:
  - 저상버스·장애인콜택시 결과 UI는 각각의 전용 Frontend Phase에서 연결한다.
  - Backend Phase 7 추천 정렬 계약이 확정된 뒤 세 이동수단 비교·추천 순서를 UI에 연결한다.
  - 지도 경로선과 실제 환승 내부 무장애 보행정보는 검증된 Backend 데이터가 마련된 뒤 별도 Phase에서 다룬다.

## Frontend Phase 6 — 저상버스 경로 결과 UI (2026-09-13)

- 브랜치: `frontend/phase6-low-floor-bus-route-ui` (base: `dev`)
- 한 일: 선택한 출발지·목적지를 기존 `POST /routes/bus` 계약으로 보내고, 저상버스 결과의 총 예상시간·예상비용·도보거리·도보시간·버스 경로 요약·노선 단위 접근성 경고를 한 카드에 표시했다. 지하철과 저상버스 요청의 로딩·오류·취소·최신 응답 상태를 독립적으로 관리하며, 저상버스를 선택하지 않았거나 입력 조건이 바뀌면 이전 요청과 결과를 무효화한다. 경로 없음은 수치 0으로 보정하지 않고 Backend의 `unavailable` 사유만 표시한다.
- 산출물:
  - `frontend/src/api/bus.ts` — 저상버스 경로 요청·응답 타입과 API client
  - `frontend/src/components/LowFloorBusRouteCard.tsx` — 시간·비용·도보 부담·경로·저상버스 접근성 결과 카드
  - `frontend/src/App.tsx`, `frontend/src/index.css` — 기존 장소선택 흐름과 독립 요청 상태·결과 영역 스타일 연결
  - `frontend/src/__tests__/App.test.tsx` — 요청 body, loading, 성공·오류·unavailable 상태와 필수 결과 표시 검증
- 검증 결과:
  - `npm test -- --run` — 22개 통과
  - `npm run build` — TypeScript 및 Vite production build 통과
  - `npm run lint` — oxlint 통과
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests/test_bus_routes.py backend/tests/test_bus_service.py` — 54개 통과(기존 Starlette deprecation warning 1건)
- 확정 기준:
  - 도보거리·도보시간과 저상버스 접근성 안내는 Backend 값을 그대로 표시하며 프론트에서 추정하거나 접근 가능 여부를 재판정하지 않는다.
  - 저상버스 정보는 노선 단위 정보이며 실제 도착 차량의 저상 여부를 보장하지 않는다는 Backend warning을 사용자에게 함께 표시한다.
  - 실제 도착정보·차량별 저상 여부·혼잡도와 지도 경로선은 이번 Phase 범위에 포함하지 않는다.
- 다음 Phase가 이어받을 것:
  - 장애인 콜택시 결과 UI와 세 이동수단 추천 결과 UI는 각각 계약과 데이터가 준비된 전용 Frontend Phase에서 연결한다.
  - 실제 차량 단위 저상 여부는 검증 가능한 Backend 데이터가 확보된 뒤 다룬다.

## Frontend Phase 7 — 교통수단 비교 및 추천 UI (2026-09-13)

- 브랜치: `frontend/phase7-transport-recommendation-ui` (base: `dev`)
- 한 일: 경로검색 시 공개 `POST /routes/recommendations`에 출발지·목적지, 사용자가 선택한 이동수단과 드래그·키보드 버튼으로 정한 시간·금액·도보 우선순위를 전송하고, Backend가 선택 후보 안에서 계산한 최대 TOP 3 순위를 그대로 표시한다. 추천 카드마다 총시간·비용·도보거리·도보시간·접근성 상태와 warning을 함께 보여주며, 지표가 `not_available`이면 0으로 보정하지 않고 `비교 불가`로 표시한다. Backend에서 제외한 이동수단은 추천 카드로 승격하지 않고 제외 사유를 별도 영역에 유지한다. 입력 장소·이동수단·우선순위가 변경되면 진행 중 요청을 취소하고 이전 결과를 무효화한다. 검색 조건과 추천 결과는 지도 위 하나의 세로 스크롤 패널에 통합했다.
- 산출물:
  - `frontend/src/api/recommendation.ts` — 추천 요청·응답, 공통 지표 가용성·접근성 타입과 API client
  - `frontend/src/components/RecommendationResults.tsx` — 순위, 이동수단별 네 지표, 접근성 상태·warning, 제외 사유 UI
  - `frontend/src/App.tsx`, `frontend/src/index.css` — Backend-owned 추천 요청과 통합 결과 영역·상태 스타일 연결
  - `frontend/src/__tests__/App.test.tsx` — 이동수단 선택, 드래그·키보드 우선순위, 요청 계약, TOP 3, 지표 누락, 접근성, 제외·오류·stale 응답, 장소검색·지도 회귀 검증
- 검증 결과:
  - `npm test -- --run` — 18개 통과
  - `npm run lint` — oxlint 통과
  - `npm run build` — TypeScript 및 Vite production build 통과
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 147개 통과(기존 Starlette deprecation warning 1건)
  - 명시적 로컬 Backend URL `http://127.0.0.1:8000/routes/recommendations`과 허용 Frontend origin CORS preflight 연결 검증
  - 로컬 Frontend proxy 실호출(서울시청→강남역, 시간 우선): HTTP 200, 저상버스 1위·지하철 2위와 각 경로 지표 반환 확인
  - 지하철만 선택한 로컬 Frontend proxy 실호출: HTTP 200, `transport_types=[subway]`, 지하철 1위만 반환되고 선택하지 않은 이동수단은 `excluded_routes`에도 포함되지 않음
  - 실제 콜택시는 Prediction 모델 미연결로 제외 사유가 반환됨을 확인하고, 검증된 세 경로 응답 fixture로 1~3위 및 콜택시 도보 `비교 불가` 표시를 검증
- 확정 기준:
  - 추천 순위와 제외 여부는 Frontend에서 재계산하지 않고 Backend 응답을 단일 신뢰 소스로 사용한다.
  - 사용자가 선택한 1~3개 이동수단만 Backend 추천 대상으로 전달하며, 선택하지 않은 이동수단은 provider를 호출하거나 제외 사유에 넣지 않는다. Frontend는 임의 경로 수치를 만들거나 추천 결과를 사후 필터링하지 않는다.
  - `not_verified`는 접근성 확인됨으로 승격하지 않고, `verified_unavailable` 및 `not_available`도 정상값이나 0으로 대체하지 않는다.
  - TOP 3은 조건을 만족하는 후보 중 최대 3개다. 모델·외부 API·접근성 조건으로 제외된 경로가 있으면 3개보다 적을 수 있다.
- 남은 한계와 다음 작업:
  - 실제 콜택시 포함 시간·금액 TOP 3은 검증된 대기시간 Prediction 모델을 AI Adapter에 연결한 뒤 운영 환경에서 재검증한다.
  - 콜택시 승하차 접근 도보 데이터가 없는 동안 최소 도보 1순위에서는 콜택시가 제외된다.
  - ODsay Server Key는 등록된 출구 IP에서만 실호출할 수 있으므로 배포 환경에서는 고정 egress IP가 필요하다.
  - 로컬은 `VITE_API_BASE_URL=http://127.0.0.1:8000`, 배포는 실제 Backend URL과 `APP_CORS_ALLOW_ORIGINS`의 실제 Frontend origin을 함께 설정한다.

## Analysis Phase 7 — 이동수단 비교 분석 (2026-09-12)

- 브랜치: `analysis/phase7-transport-comparison` (base: `dev`)
- 한 일: 기존 대기시간·지하철 접근성·저상버스 분석 기준, 공통 경로 계약, 이동수단별 현재 서비스 산출값과 기존 지하철·콜택시 비교 Notebook을 확인해 장애인 콜택시·지하철·저상버스의 공통 비교 기준을 확정했다. 총 이동시간·예상 비용·총 도보거리·총 도보시간은 초·원·미터 단위로 비교하고, 접근성 상태는 근거 없는 종합점수로 환산하지 않고 적격성 판단과 경고로 유지한다. 추천 정렬 입력, 표시·주의 정보, 오프라인 분석·검증 결과, 현재 사용 금지 항목을 분리했다.
- 산출물:
  - `analysis/transport_comparison_criteria.md` — 공통 지표 정의, 이동수단별 산정 기준, 데이터 한계, 추천/참고 활용 구분
  - `analysis/README.md` — Phase 7 비교 기준 문서 링크
- 확정 기준:
  - 장애인 콜택시 총 이동시간은 검증된 `예측 대기시간 + 차량 이동시간`이며, 모델 연결 전에는 차량시간만으로 다른 수단과 순위를 비교하지 않는다.
  - 예측 대기시간은 콜택시 총 이동시간의 전용 구성요소이며 세 이동수단 공통 정렬 지표로 직접 비교하지 않는다.
  - 콜택시 도보값 미확정과 현 `RouteResult`의 available numeric field 필수 계약은 충돌한다. Backend Phase 7에서 지표별 `available`/`not_available`을 표현하도록 계약을 변경하기 전에는 도보값을 0으로 채우거나 콜택시 공통 비교 결과를 완성 처리하지 않는다.
  - 접근성 공통 상태는 `verified_available`, `verified_unavailable`, `not_verified`로 구분한다. 콜택시는 현재 `not_verified`이며 이를 정상 접근성으로 해석하지 않는다.
  - 지하철·저상버스 도보값은 ODsay 도보 subPath 합계이고, 환승 내부 무장애 동선이나 실제 보행로 전체로 단정하지 않는다.
  - 지하철 접근성은 모든 이용역의 엘리베이터 조건을 핵심으로 보고, 저상버스 접근성은 노선 단위 정보로만 해석한다.
  - 기존 지역·월별 수요, 시설 부담, 집계 혼잡 분석은 추천 점수가 아니라 사후 검증과 분석 참고 자료로 사용한다.
  - 누락·이용불가 값은 0으로 대체하지 않으며 실시간으로 검증되지 않은 값은 추천 정렬에 사용하지 않는다.
- 검증 결과:
  - `analysis/transport_comparison_criteria.md`의 내부 경로 8개가 모두 존재함을 확인
  - 비교 문서가 세 이동수단과 5개 핵심 지표를 모두 명시하고, 추천 입력·표시/주의·오프라인 분석·사용 금지의 네 범주를 포함함을 확인
  - 후속 계약 예시에서 `calltaxi available + walking metrics null/not_available + accessibility not_verified` 상태를 손실 없이 표현하고, Backend Phase 7 필수 테스트 케이스로 지정
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 118개 통과, 기존 의존성의 `DeprecationWarning` 1건 외 실패 없음
- 다음 Phase가 이어받을 것:
  - Backend Phase 7에서 경로 상태와 별도로 지표별 가용 상태 및 접근성 상태를 표현하도록 공통 계약을 먼저 변경한다.
  - 통합 대기시간 Prediction 모델을 검증·export하고 `ai/` Adapter에 연결해 콜택시 총 이동시간을 완성한다.
  - Backend Phase 7에서 사용자 우선순위, 동률, 누락값, 접근성 적격성 규칙을 포함한 Rule-based 추천 정렬 계약과 테스트를 구현한다. `calltaxi available + walking unknown`, 세 이동수단 접근성 상태 혼합, 선택 지표 미확인 경로 제외를 반드시 검증한다.
  - 지하철 환승 내부 무장애 동선, 콜택시 승하차 접근 도보, 차량 단위 저상버스 실시간 정보는 검증된 데이터가 확보된 뒤 별도 Phase에서 확장한다.

## Backend Phase 7-1 — 추천 계약·정렬 엔진 및 통합 경계 (2026-09-12)

- 브랜치: `backend/phase7-transport-recommendation` (base: `dev`)
- 범위 조정: Backend Phase 7의 완료 조건은 Backend가 세 이동수단 결과를 직접 생성해 통합하고 최대 TOP 3을 반환하는 것이다. 현재 콜택시 대기시간 Prediction 모델이 없어 신뢰 가능한 콜택시 총 이동시간을 만들 수 없으므로 전체 Phase를 완료 처리하지 않는다. 이번 작업은 공개 요청에서 클라이언트 경로 결과를 받지 않는 Backend-owned orchestration 경계, 추천 계약과 정렬 엔진까지를 **Phase 7-1**로 완료한다.
- 한 일: 공개 `POST /routes/recommendations`가 출발지·목적지, 선택 이동수단과 시간·비용·도보 우선순위만 받고, Backend 소유 `RecommendationRouteProvider`가 선택된 `RouteResult`를 최대 3개까지 사전식 정렬하도록 구성했다. 운영 통합 provider는 가짜 값을 만들지 않고 이동수단별로 fail-closed하며, dependency override로 provider→통합→정렬 흐름을 검증했다. Analysis Phase 7의 콜택시 도보 미확정 문제를 해소하기 위해 경로 상태와 별도로 numeric field별 `available`/`not_available` 및 접근성 `verified_available`/`verified_unavailable`/`not_verified`를 표현하도록 공통 계약을 확장했다.
- 산출물:
  - `backend/app/api/contracts.py` — 지표 가용성, 접근성, 추천 우선순위 및 추천 요청·응답 계약
  - `backend/app/services/recommendation.py` — Backend route provider Protocol, Rule-based 우선순위 정렬, 입력 방어, 제외 및 안정적 동률 처리
  - `backend/app/api/recommendation.py`, `backend/app/main.py` — `POST /routes/recommendations` 등록
  - `backend/app/services/subway.py`, `backend/app/api/subway.py`, `backend/app/api/bus.py` — 지하철·저상버스 접근성 공통 상태 반환
  - `backend/tests/test_recommendation_service.py`, `backend/tests/test_recommendation_routes.py` — 시간·비용·도보 정렬과 HTTP 계약 검증
  - `backend/tests/test_route_contracts.py`, `backend/tests/test_subway_service.py`, `backend/tests/test_subway_routes.py`, `backend/tests/test_bus_routes.py` — 지표 가용성 및 접근성 회귀 검증
  - `docs/decisions/0004-route-metric-availability-and-recommendation-contract.md` — 계약 변경과 정렬 정책 결정
- 확정 기준:
  - 공개 추천 요청은 `origin`, `destination`, `priorities`만 받으며 클라이언트가 제출한 `routes` 추가 필드는 `422`로 거부한다.
  - 라우터는 Backend 소유 provider의 결과만 정렬 서비스에 전달한다. 통합 provider 미연결 상태는 `503`으로 명시한다.
  - 1순위 지표가 사용 가능한 경로만 후보로 삼고, 2·3순위 지표 누락은 앞선 지표가 동률일 때 후순위로 처리한다.
  - `unavailable` 경로, 1순위 지표 `not_available`, 접근성 `verified_unavailable`은 후보에서 제외하며 이유를 응답에 보존한다.
  - 접근성 `not_verified`는 정상으로 바꾸지 않고 warning과 상태를 유지한 채 후보에 포함한다.
  - 도보 우선은 거리, 시간 순서로 비교한다. 모든 우선순위가 같은 완전 동률은 이동수단 고정 순서로만 해소한다.
  - 콜택시 도보값을 0으로 만들지 않는다. 따라서 현재 도보 1순위에서는 콜택시를 제외하고 최대 2개를 반환한다.
- 검증 결과:
  - dependency override로 Backend provider 결과를 주입해 시간 우선 콜택시 → 지하철 → 저상버스 TOP 3 반환 확인
  - dependency override로 비용 우선 저상버스 → 지하철 → 콜택시 TOP 3 반환 확인
  - dependency override로 도보 우선 저상버스 → 지하철 반환 및 콜택시 제외 사유 확인
  - 세 이동수단 모두 도보 지표가 제공된 provider 샘플에서는 콜택시 → 저상버스 → 지하철 TOP 3 반환 확인
  - 클라이언트 제출 `routes`와 중복 우선순위 요청이 `422`를 반환하는지 확인
  - 운영 통합 provider 미연결 상태에서 `503` 반환 확인
  - `rank_routes()` 직접 호출 시 빈 우선순위와 세 이동수단 누락을 명확한 `ValueError`로 거부하는지 확인
  - 콜택시 `available + walking null/not_available + accessibility not_verified` 계약 검증
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 138개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건 외 실패 없음
  - `cd frontend && npm test -- --run` — 19개 통과
  - `cd frontend && npm run build` — TypeScript 및 Vite production build 통과
  - OpenAPI schema에서 `POST /routes/recommendations`의 200 응답 계약 등록 확인
- 다음 Phase가 이어받을 것:
  - **Backend Phase 7-2**에서 대기시간 Prediction 모델을 연결한 뒤 TMAP 콜택시, ODsay 지하철·저상버스 결과를 생성하는 운영 `RecommendationRouteProvider`를 구현한다.
  - 운영 provider와 함께 콜택시 `total_time_seconds`를 실제 통합 결과로 생성하고, 공개 endpoint에서 조건을 만족하는 최대 TOP 3 반환을 검증한 뒤 Backend Phase 7 전체를 완료 처리한다.
  - Frontend는 추가된 지표·접근성 상태와 추천·제외 결과를 별도 Phase에서 연결한다.
  - 검증된 콜택시 승하차 접근 도보 데이터가 확보되면 도보 1순위 TOP 3 가능 여부를 재검토한다.

## Backend Phase 7-2 — 운영 이동수단 통합 provider (2026-09-12)

- 브랜치: `backend/phase7-2-route-orchestration` (base: `dev`)
- 완료 범위: 공개 추천 API가 TMAP 콜택시, ODsay 지하철·저상버스와 AI Adapter를 Backend 내부에서 조합하는 운영 `RecommendationRouteProvider`를 사용하도록 연결했다. 개별 이동수단의 설정·외부 호출·접근성 lookup·대기시간 예측이 실패하면 해당 경로만 `unavailable`로 만들고 다른 이동수단은 계속 추천한다. 검증된 대기시간 모델이 연결된 주입 테스트에서는 콜택시 총 이동시간과 세 이동수단 통합을 확인했다.
- 전체 Phase 상태: **미완료**. 현재 `analysis/`에 Prediction 모델 artifact와 serving feature mapping은 export됐지만, `ai/waiting_time/estimator.py`의 실제 artifact 호출과 Backend feature 생성 흐름은 아직 연결되지 않았다. 따라서 실제 운영 요청에서 콜택시를 포함한 시간·비용 TOP 3을 안정적으로 반환할 수 없으며, 가짜 대기시간은 사용하지 않는다.
- 산출물:
  - `backend/app/services/route_orchestration.py` — 콜택시·지하철·저상버스 생성, 오류 격리, 대기시간 합산
  - `backend/app/api/recommendation.py` — 설정 기반 TMAP·ODsay client, 접근성 provider, AI Adapter 조합
  - `backend/tests/test_route_orchestration.py` — 모델 연결/미연결/잘못된 예측 결과의 통합 동작 검증
  - `backend/tests/test_recommendation_routes.py` — 설정 키가 없을 때 세 경로를 개별 이용불가로 반환하는 fail-closed 검증
- 확정 동작:
  - 콜택시: `predicted waiting seconds + TMAP vehicle seconds`를 총 이동시간으로 사용하고 도보는 `null/not_available`, 접근성은 `not_verified`로 유지한다.
  - 지하철: ODsay 경로와 모든 이용역의 accessibility lookup을 결합한다. lookup을 읽지 못하면 경로 수치는 유지하되 접근성은 `not_verified`다.
  - 저상버스: 검토된 route mapping을 사용하는 ODsay 저상버스 client 결과만 사용한다.
  - 대기시간 모델 미연결·예측값 NaN/음수/비수치, 외부 경로 실패, 키 누락은 임의 수치로 대체하지 않는다.
- 필수 선행조건:
  - 완료: `analysis/`에 검증 완료된 통합 대기시간 Prediction 모델 artifact, metadata, serving feature mapping export
  - 완료: 실제 모델의 inference 입력 계약 확정. 현재 Adapter의 `hour_of_day`만으로는 부족하며, 요청 시각·이용목적·구/동·세부이동유형·TMAP 차량거리·전일 차량운행·날씨 feature를 받는 구조로 확정
  - 남음: `ai/waiting_time/estimator.py`가 해당 export만 읽어 검증된 예측을 반환하도록 실제 artifact 호출 구현 및 AI 단위 테스트 추가
  - 남음: Backend가 주소 정규화, TMAP 차량거리, 전일 차량운행, 날씨 feature를 생성한 뒤 AI Adapter를 호출하도록 orchestration 순서 확장
  - 실호출 환경의 `APP_TMAP_APP_KEY`, `APP_ODSAY_API_KEY`와 ODsay Server Key 등록 IP 준비
- 검증 결과:
  - 예측 대기시간 30분 + 차량시간 1,800초 = 콜택시 총 3,600초 확인
  - 모델 미연결 시 콜택시만 `unavailable`, 지하철·저상버스는 `available` 유지 확인
  - NaN 예측값을 거부하고 콜택시 수치를 `null`로 유지하는지 확인
  - TMAP·ODsay 지하철·ODsay 버스 호출 실패를 각 경로의 `unavailable`로 격리하고 수치를 `null`로 유지하는지 확인
  - 키 미설정 추천 요청에서 200 응답과 추천 0개·제외 3개 사유 반환 확인
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 142개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건 외 실패 없음
  - `cd frontend && npm test -- --run` — 19개 통과
  - `cd frontend && npm run build` — TypeScript 및 Vite production build 통과
  - OpenAPI schema에서 `POST /routes/recommendations` 등록 확인
- 다음 작업:
  - 위 Prediction 선행조건을 충족한 뒤 실제 모델 입력으로 운영 provider smoke test를 수행한다.
  - 실제 콜택시·지하철·저상버스 결과가 준비된 시간·비용 기준에서 최대 TOP 3을 확인한 뒤 Backend Phase 7 전체를 완료 처리한다.

## Analysis Phase 8 — 서비스용 분석 데이터 생성 (2026-09-13)

- 브랜치: `analysis/phase8-service-data-exports` (base: `dev`)
- 한 일: Phase 3에서 확정한 병원 이동 집계 4개와 기존 그래프 2개를 `analysis/hospital/`의 reviewed JSON·PNG로 수동 export했다. 병원 데이터는 후속 검토를 위해 유지하되 현재 서비스의 Backend API와 Frontend UI에는 노출하지 않기로 범위를 조정했다. 기존 지하철 station accessibility master와 저상버스 route master·ODsay mapping은 Backend provider에 연결되어 있음을 확인하고, 실제 서비스 consumer가 있는 export와 현재 미노출 reviewed export를 manifest에서 분리했다.
- 산출물:
  - `analysis/service_data_manifest.json` — 지하철·저상버스 `service_exports`와 병원 `reviewed_analysis_exports` 구분
  - `analysis/hospital/hospital_analytics.json`, `analysis/hospital/figures/`, `analysis/hospital/README.md` — 병원 정적 집계·선정 그래프·출처 및 갱신 기준
  - `backend/tests/test_service_data_exports.py` — 서비스 export와 provider 기본 경로, 미노출 reviewed export 파일·그래프 참조 검증
  - `docs/troubleshooting.md` — 지하철·저상버스 export의 실행 디렉터리 의존 문제와 해결 기록
- 확정 범위:
  - 병원 분석은 개별 병원이 아니라 `의료목적으로 기록된 이동`의 목적지 지역 집계만 제공한다.
  - 병원 이동 전용 시간대·차량유형 비교, 실시간 진료·병상·무장애 시설 정보는 제공하지 않는다.
  - 병원 reviewed export는 현재 서비스 consumer가 없으며 Backend API와 Frontend UI에서 노출하지 않는다.
  - 지하철 접근성은 158행 station master, 저상버스는 364행 route master와 51행 ODsay mapping을 기존 provider가 사용한다. 실시간 고장·차량 도착·혼잡으로 해석하지 않는다.
  - 지하철·저상버스 provider는 프로세스 현재 디렉터리가 아니라 저장소 위치 기준으로 `analysis/` export를 읽는다.
  - Backend와 Frontend 환경설정은 저장소 루트 `.env` 한 곳에서 관리하며, Backend 실행 위치와 무관하게 같은 파일을 읽는다.
- 검증 결과:
  - 원격 fetch 후 Phase 브랜치 시작점과 최신 `origin/dev`가 동일한 커밋임을 확인
  - 병원 JSON 4개 `analysis_id`와 Phase 3 확정 수치·모집단·기간 대조
  - 선정 PNG 2개가 각각 949×699, 1187×504의 유효 PNG임을 확인
  - manifest의 `service_exports`에 지하철·저상버스만 존재하고 실제 provider 경로·consumer와 일치하는지 검증
  - 병원 JSON·PNG가 consumer 없는 `reviewed_not_served` 상태이며 JSON의 `asset_path`와 reviewed PNG 경로가 일치하는지 검증
  - 저장소 밖 임시 작업 디렉터리에서도 지하철·저상버스 reviewed export가 로드되는지 검증
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 150개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건 외 실패 없음
  - `cd frontend && npm test -- --run` — 18개 통과
  - `cd frontend && npm run build` — TypeScript 및 Vite production build 통과
  - `cd frontend && npm run lint` — oxlint 통과
  - 최초 `.venv/bin/uvicorn app.main:app` 실행은 `No module named 'ai'`로 실패했으며, `PYTHONPATH=..` 누락이 원인임을 확인해 실행 안내와 troubleshooting 문서를 수정
  - `backend/` 실행 조건에서도 루트 `.env`의 TMAP·ODsay 키가 인식됨을 확인하고, 서울시청→강남역 실제 추천 요청에서 지하철·저상버스 추천과 콜택시 모델 미연결 제외 사유 반환 확인
  - `git diff --check` 통과
- 다음 Phase가 이어받을 것:
  - 검증 완료된 통합 대기시간 Prediction 모델과 inference 계약을 별도 Phase에서 export·연결한다. Phase 8은 모델을 미리 구현하지 않는다.
  - 지하철 실시간 엘리베이터 상태, 차량 단위 저상버스 도착·혼잡·배차간격은 공식 HTTPS 데이터와 코드 정의가 확보된 뒤 별도 Phase에서 검토한다.
  - 병원별 통계가 필요하면 병원 식별자·좌표와 탑승 목적지를 검증 가능하게 연결하는 데이터가 선행되어야 한다.

## Backend/Frontend Phase 8 — 교통비 기록 및 분석 데이터 연결 (2026-09-13)

- 브랜치: `backend/phase8-transport-cost-records` (base: `dev`)
- 범위 조정: 병원 이동 분석 Mapping은 요청에 따라 제외했다. 병원 reviewed export, manifest, Backend/Frontend 노출 상태는 변경하지 않았다.
- 한 일: 추천 결과에서 실제 이용 날짜·이동수단·금액을 기록하고, Backend가 같은 출발지·목적지와 후보 이동수단을 비용 우선으로 다시 계산해 추천 비용과 절약 가능 금액을 저장하도록 구현했다. SQLite 저장소를 도입해 날짜별 원본 기록·합계와 월별 일자 집계·합계를 조회하고, Frontend가 Backend 응답을 그대로 표시하도록 연결했다.
- 산출물:
  - `backend/app/api/transport_costs.py`, `backend/app/api/contracts.py` — 생성·날짜별·월별 API와 요청/응답 계약
  - `backend/app/services/transport_costs.py` — SQLite 저장, 실제/추천 비용과 절약 가능 금액 집계
  - `frontend/src/api/transportCosts.ts`, `frontend/src/components/TransportCostTracker.tsx` — 실제 이용금액 입력과 월별 비교 UI
  - `backend/tests/test_transport_cost_routes.py`, `frontend/src/__tests__/TransportCostTracker.test.tsx` — API·저장·집계·렌더·요청 회귀 검증
  - `docs/decisions/0005-backend-owned-transport-cost-records.md` — 저장 소유권과 계산 경계 결정
- 확정 동작:
  - `POST /transport-cost-records`는 실제 금액과 경로 조건을 받고 Backend 계산 비용 우선 1위를 함께 저장한다.
  - `GET /transport-cost-records/daily?date=YYYY-MM-DD`는 해당 날짜의 기록과 실제·추천·절약 합계를 반환한다.
  - `GET /transport-cost-records/monthly?month=YYYY-MM`는 날짜별 집계와 월 합계를 반환한다.
  - 절약 가능 금액은 음수가 되지 않으며 Frontend에서 재계산하지 않는다.
  - 비용 추천이 불가능하면 임의 비용을 기록하지 않고 `503`으로 실패한다.
  - DB 기본 경로는 분석 폴더가 아닌 `backend/var/transport_costs.sqlite3`이고 루트 `.env`에서 변경할 수 있다.
- 검증 결과:
  - 생성 시 저상버스 1,400원 비용 우선 추천, 실제 2,000원, 절약 가능 600원 저장 확인
  - 날짜별 기록·합계, 월별 날짜 그룹·합계, 실제 금액이 추천보다 낮을 때 절약액 0 clamp 확인
  - 잘못된 날짜·월·선택 이동수단 `422`, 비용 추천 불가 `503` 및 미저장 확인
  - Frontend가 실제 금액과 기존 추천 조건을 전송하고 Backend 월별 합계를 그대로 렌더링하는지 확인
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 157개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건 외 실패 없음
  - `cd frontend && npm test -- --run` — 20개 통과
  - `cd frontend && npm run build` — TypeScript 및 Vite production build 통과
  - `cd frontend && npm run lint` — oxlint 통과
  - `git diff --check` 통과
- 남은 범위:
  - 인증·사용자별 소유권, 기록 수정·삭제, 결제/카드사 연동, 다중 Backend 인스턴스용 서버 DB는 후속 설계 대상이다.
  - 실제 외부 경로 API의 과거 요금이 아니라 기록 저장 시점의 예상 비용을 비교 기준으로 사용한다.
  - 병원 이동 분석 Mapping과 병원 서비스 노출은 이번 Phase에 포함하지 않는다.

## Frontend Phase 8-1 — 교통비 캘린더 UI 보강 (2026-09-13)

- 브랜치: `phase8-cost-calendar-analysis-ui` (base: `dev`)
- 범위 조정: 사용자 요청에 따라 병원 분석정보 표시는 제외했다. `analysis/hospital/` reviewed export와 manifest의 병원 `reviewed_not_served` 상태는 변경하지 않았다.
- 한 일: 기존 교통비 기록 API를 유지하면서 Frontend 교통비 UI를 월간 캘린더 형태로 보강했다. 월 누적 실제 이용금액·금액 우선 추천 비용·절약 가능 금액을 표시하고, 날짜별 칸에는 해당 일자의 실제 이용금액을 표시한다. 날짜를 선택하면 Backend의 날짜별 기록 API를 조회해 실제 이용수단, 실제 이용금액, 금액 우선 추천 이동수단·비용, 절약 가능 금액을 상세 표시한다.
- 산출물:
  - `frontend/src/api/transportCosts.ts` — 날짜별 교통비 조회 client와 응답 타입 추가
  - `frontend/src/components/TransportCostTracker.tsx` — 월간 캘린더, 선택 날짜 상세 기록, 응답 shape 방어 처리
  - `frontend/src/index.css` — 교통비 캘린더와 날짜별 상세 UI 스타일
  - `frontend/src/__tests__/TransportCostTracker.test.tsx` — 월 누적 합계, 캘린더 날짜 표시, 날짜별 상세 기록, 저장 후 월·일 상세 갱신, 저장 성공 후 상세 조회 실패 시 상태 분리 검증
- 확정 동작:
  - Frontend는 실제 금액·절약 가능 금액을 직접 재계산하지 않고 Backend 응답 값을 그대로 표시한다.
  - 월별 캘린더는 `GET /transport-cost-records/monthly`의 날짜별 집계를 사용한다.
  - 날짜별 상세는 `GET /transport-cost-records/daily`의 원본 기록과 합계를 사용한다.
  - 교통비 API 응답 shape가 예상과 다르면 화면을 깨뜨리지 않고 조회 오류 상태로 처리한다.
  - 병원 분석정보와 개별 병원 통계는 이번 UI에 표시하지 않는다.
- 검증 결과:
  - `cd frontend && npm test -- --run` — 21개 통과
  - `cd frontend && npm run lint` — oxlint 통과
  - `cd frontend && npm run build` — TypeScript 및 Vite production build 통과
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 157개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건 외 실패 없음
  - 최초 백엔드 테스트 실행은 새 worktree에 `backend/.venv`가 없어 실패했고, 시스템 Python 3.9로 재시도했을 때 FastAPI 미설치·`StrEnum` 미지원으로 수집 실패했다. 이후 Python 3.12 venv를 생성하고 `backend/requirements.txt`를 설치해 정상 검증했다.
- 남은 범위:
  - 인증·사용자별 교통비 기록 분리, 기록 수정·삭제, 결제/카드사 연동은 후속 설계 대상이다.
  - 병원 분석정보 서비스 노출은 이번 Phase에서 제외했으며, 노출하려면 `analysis/service_data_manifest.json`과 Backend/Frontend API 범위를 별도 Phase에서 갱신해야 한다.

## Analysis Phase 9 — 데이터 품질 및 최종 분석 검증 (2026-09-13)

- 상태: 현재 확정된 정적 export 및 미연결 경계에 대한 최종 검증 완료. 전체 실시간 데이터·Prediction 성능·전체 외부 mapping 검증 완료를 의미하지 않는다.
- 브랜치: `analysis/phase9-data-quality` (base: 최신 `origin/dev` `2c7b12b`). 원격 기본 `main`에는 서비스 코드가 없어 기존 Phase 통합 기준 `dev`를 사용했다. 기존 로컬 교통비·지도 미커밋 변경은 원래 worktree에 보존했다.
- 한 일:
  - `src/data_quality.py`에 읽기 전용 오프라인 검사 추가. export 행·키 중복, 컬럼별 결측, 숫자·접근성 상태, 매핑 참조·기준시점, 원본과 reviewed 결과의 일치를 검증한다. 오류는 종료 코드 1, 미검증 범위는 별도 warning/status로 출력한다.
  - `--check-report` 모드를 추가해 현재 커밋된 export snapshot이 `docs/validation/phase9-audit-2026-09-13.json`과 drift되면 CI가 실패하도록 했다. 로컬 원본 파일이 필요한 source comparison metrics는 CI 비교 범위에서 제외한다.
  - 원본 없는 CI에서도 버스 export 내부의 저상버스 count·flag·status와 혼잡 availability·row count·proxy 값의 상호 모순을 잡도록 검사를 강화했다.
  - 지하철·버스 전체 export를 실제 Backend provider와 대조하고, 미등록 역 및 버스 ID·번호·유형 불일치가 자동 매핑되지 않는지 검증했다.
  - 병원 집계 4개와 이미지 2개를 기존 CSV·노트북 저장 output에 대조하고 API/Frontend 미노출을 검증했다. 병원 서비스 연결은 추가하지 않았다.
  - Git 미추적 원본은 `--source-root`로 읽기 전용 대조하고, 없는 환경에서는 `not_verified_source_missing`을 명시한다. CI는 커밋된 자료만 검사한다.
- 산출물:
  - `src/data_quality.py`, `src/tests/test_data_quality.py`
  - `backend/tests/test_phase9_data_quality.py`
  - `.github/workflows/data-quality.yml`
  - [최종 검증 보고서](validation/phase9-data-quality.md), [수치·해시·결측·미매핑 목록](validation/phase9-audit-2026-09-13.json)
  - [문제·대안·해결·잔여 한계](troubleshooting/phase9-data-quality.md)
- 검증 결과:
  - 지하철 158행, 버스 364행, ODsay mapping 51행: 키·전체 행 중복 0. 지하철/mapping 빈 값 0, 버스 결측은 unknown·보조지표 미확보 범위로 기록.
  - 지하철 정제 1,896행의 최신월 158행과 export 일치. 버스 원본 364노선 일치(비율 소수 4자리 반올림 차이 168건 구분).
  - 혼잡 원본 896,304행/320노선: count/max/p95/존재 플래그 일치. 실시간 혼잡으로 해석하지 않는다.
  - 병원 구 25행·동 416행 합계 126,705, 상위지역 JSON 일치. 범위·거리·순유입은 서로 다른 모집단을 유지한 채 기존 output 일치.
  - `python3 -m src.data_quality --source-root /Users/pakrchansik/Desktop/calltaxi-DA`: 오류 0, 종료 코드 0, 알려진 범위 제한 warning 5건.
  - 원본 없는 `python3 -m src.data_quality`도 실행해 원본 3개의 미검증 상태를 확인. `python3 -m src.data_quality --check-report docs/validation/phase9-audit-2026-09-13.json`로 커밋된 export snapshot drift 없음 확인.
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest src/tests backend/tests ai/tests -q`: 181개 통과. 기존 Starlette/anyio DeprecationWarning 1건.
  - `npm test --prefix frontend`: 21개 통과. `npm run build --prefix frontend`, `npm run lint --prefix frontend`: 통과.
  - 최초 스키마·반올림 비교 실패와 LFS 권한 오류도 보고서/트러블슈팅에 기록하고 수정 후 재검증했다.
- 자체 리뷰:
  - API/이벤트 계약, 데이터 소유권, 기술 스택, 서비스 코드, 원본/processed/analysis export, 기존 ADR·README 변경 없음.
  - 검증 모듈은 오프라인 `src/`에만 위치하고 서비스 코드가 이를 import하지 않는다. CI에서 원본 부재를 원본 대조 성공으로 숨기지 않고, 커밋된 export 결과와 audit JSON의 drift는 별도 실패로 잡는다.
  - 미확정 시점과 일부 mapping만으로 최신성·전체 coverage를 주장하지 않는다. 기존 AI 미연결 동작을 유지한다.
- 다음에 이어받을 것:
  - 버스 metadata 기준일 364건 unknown, 저상 정보 2노선 unknown, 전체 master 중 ODsay 미매핑 313노선.
  - 지하철 stationID 매핑·전체 역 coverage·실시간 시설 상태·환승 내부 동선은 추가 근거 필요.
  - Prediction 산출물과 inference 계약·성능 검증은 별도 모델 연결 Phase에서 진행.
  - 병원 결과는 reviewed-only 유지. 실시간 버스 API와 신규 의료시설 자료는 별도 승인된 데이터 연결 범위에서 검토.

## AI Phase 0 — 대기시간 Prediction 연동 구조 정의 (2026-09-13)

- 브랜치: `ai/phase0-wait-time-contract` (base: 최신 `origin/dev` `15a0b23`). 기존 로컬 작업은 원래 worktree에 보존하고, Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 통합 장애인 콜택시 대기시간 Prediction 모델 1개를 Backend에서 사용할 수 있도록 입력·출력 형식, feature 정의, 단위, 호출 방식, 오류 처리 구조를 확정했다.
- 한 일:
  - `ai/waiting_time/estimator.py`에 `WaitingTimePredictionInput` dataclass를 추가해 Backend가 AI Adapter에 넘길 입력 계약을 정의했다.
  - 학습 feature 이름과 단위를 유지하는 `to_model_features()` 변환을 추가했다. `승차거리`는 TMAP 차량거리 미터 단위이며 `승차거리_km`로 변환하지 않는다.
  - 예측 목표값을 `접수→승차 대기시간`, 모델 출력 단위를 minutes로 확정했다. Backend 총 소요시간에는 후속 연결 Phase에서 seconds로 변환해 반영한다.
  - `02:00~06:59`, 미지원 이용목적, 미지원 이동유형, 미지원 `model_group`, 주소 정규화 실패에 해당하는 빈 구/동, 유효하지 않은 numeric feature를 prediction unavailable 조건으로 고정했다.
  - 기존 `estimate_waiting_minutes(hour_of_day)`는 Backend placeholder 호환을 위해 유지하고, 실제 artifact 호출 전까지 계속 `NotImplementedError`를 발생시킨다.
  - `docs/decisions/0006-wait-time-prediction-contract.md`에 Backend 호출 순서, feature source, 오류 응답 원칙, 후속 작업 범위를 ADR로 기록했다.
  - `analysis/README.md`의 대기시간 모델 export 상태를 최신화했다.
- 산출물:
  - `ai/waiting_time/estimator.py`
  - `ai/tests/test_estimator.py`
  - `docs/decisions/0006-wait-time-prediction-contract.md`
  - `analysis/README.md`
  - `docs/development-phases.md`
- 확정 동작:
  - `ai/`는 FastAPI/HTTP를 import하지 않고 순수 Python dataclass 계약만 제공한다.
  - `ai/`와 `backend/`는 `data/raw`, `data/processed`, `notebooks*/`를 직접 참조하지 않는다.
  - 서비스 transport type은 계속 `calltaxi`이며, `model_group`은 모델 feature로만 사용한다.
  - 실제 차량유형이 확정되지 않은 MVP에서는 후속 연결 Phase에서 `임차택시_바로콜`, `특장차_바로콜`을 모두 예측하고 보수적으로 큰 값을 사용하는 정책을 따른다.
  - 모델 artifact 미연결 상태에서는 가짜 대기시간을 반환하지 않는다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests -q` — 12개 통과
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests backend/tests/test_route_orchestration.py backend/tests/test_recommendation_routes.py -q` — 26개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 170개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `git diff --check` — 통과
- 자체 리뷰:
  - 확정된 폴더 책임과 데이터 소유권을 변경하지 않았다.
  - 실제 모델 로딩, 전일 차량운행 lookup, 날씨 lookup/API, Backend API 입력 확장은 후속 Phase로 남겼다.
  - `analysis/waiting_time/*.joblib` artifact는 수정하지 않았다.
- 다음에 이어받을 것:
  - Backend route orchestration 순서를 TMAP 차량거리 확보 후 AI Adapter 호출로 변경한다.
  - 추천 요청/API에 이용목적과 필요한 주소 metadata를 전달할지, Backend reverse geocoding으로 보완할지 확정한다.
  - 전일 차량운행과 시간별 날씨 feature provider를 `analysis/` export 또는 운영 API로 연결한다.
  - AI Adapter가 `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib`을 lazy-load하고 예측값 검증·경고를 반환하도록 구현한다.

## AI Phase 1 — 특장차 Prediction Feature Mapping 연동 (2026-09-13)

- 브랜치: `ai/phase1-special-vehicle-feature-mapping` (base: 최신 `origin/dev` `22d0e84`). 기존 로컬 문서 변경은 원래 worktree에 보존하고, Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 통합 장애인 콜택시 대기시간 Prediction 모델에 필요한 입력값 중 특장차 예측에 사용할 Backend feature mapping을 서비스 구조에 연결했다. 실제 모델 artifact 호출은 하지 않고, Backend 입력값이 AI Adapter 입력 계약으로 정상 변환되는지 검증했다.
- 한 일:
  - `backend/app/services/waiting_time_features.py`를 추가해 Backend 입력값을 `WaitingTimePredictionInput`으로 변환하는 순수 service를 구현했다.
  - 특장차 Phase 범위에 맞춰 `model_group`은 `특장차_바로콜`로 고정했다.
  - `requested_at`은 AI Adapter가 Asia/Seoul 기준으로 정규화하도록 전달하고, TMAP 차량거리는 `승차거리` feature에 미터 단위 그대로 전달한다.
  - 출발구·목적구 기준으로 `세부이동유형`을 `구 내 이동`, `구 간 이동`, `서울→서울 외`, `서울 외→서울` 중 하나로 파생한다. 서울 외↔서울 외 이동은 모델 대상이 아니므로 mapping error로 처리한다.
  - 날씨 feature에서 `is_bad_weather`를 학습 당시 rule과 동일하게 파생한다. 강수, 적설, 3시간 신적설, -5도 이하, 풍속 5m/s 이상을 악천후 조건으로 본다.
  - 필수 위치값 누락, `None` 위치값, 음수 강수·풍속·적설·신적설, 비숫자 날씨값을 명시적으로 거부한다.
  - AI Adapter validation에서 발생한 `ValueError`를 Backend feature mapping 경계의 `WaitingTimeFeatureMappingError`로 감싸 후속 route orchestration에서 일관되게 처리할 수 있게 했다.
- 산출물:
  - `backend/app/services/waiting_time_features.py`
  - `backend/tests/test_waiting_time_features.py`
  - `docs/development-phases.md`
- 확정 동작:
  - Backend feature mapper는 모델 artifact를 읽지 않고, `data/raw`, `data/processed`, `notebooks*/`도 직접 참조하지 않는다.
  - Backend feature mapper는 AI Adapter의 순수 Python dataclass인 `WaitingTimePredictionInput`만 생성한다.
  - 현재 Phase에서는 API 요청 schema, Frontend UI, reverse geocoding, 전일 차량운행 lookup, 날씨 lookup/API, 실제 모델 inference를 구현하지 않는다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests/test_waiting_time_features.py ai/tests/test_estimator.py -q` — 41개 통과
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 199개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `git diff --check` — 통과
- 자체 리뷰:
  - 기존 API/이벤트 계약과 추천 정렬 로직을 변경하지 않았다.
  - `analysis/waiting_time/*.joblib` 및 metadata/export 문서는 수정하지 않았다.
  - 특장차 feature mapping만 구현했고, 임차택시·양쪽 `model_group` 보수적 max 정책의 실제 호출은 후속 모델 연결 Phase에 남겼다.
- 다음에 이어받을 것:
  - 추천 요청/API에서 이용목적과 주소 metadata를 어떻게 받을지 확정한다.
  - 주소 metadata가 부족할 때 사용할 reverse geocoding provider를 연결하고, Backend feature mapper에는 서울 25개 구 canonical name처럼 정규화 완료된 구/동만 전달되도록 검증한다.
  - 전일 차량운행과 시간별 날씨 provider를 운영 데이터 또는 `analysis/` export 기준으로 연결한다.
  - `BackendRecommendationRouteProvider`에서 TMAP 차량거리 계산 후 `build_special_vehicle_waiting_time_input()`을 호출하도록 순서를 확장한다.

## AI Phase 2 — Prediction 출력 구조 연결 (2026-09-13)

- 브랜치: `ai/phase2-prediction-output-mapping` (base: 최신 `origin/dev` `8861702`). 기존 로컬 문서 변경은 원래 worktree에 보존하고, Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 통합 장애인 콜택시 대기시간 Prediction 모델의 raw output을 Backend에서 사용할 수 있는 `waitingTime` 형식으로 변환하는 출력 mapping을 AI Adapter 경계에 추가했다.
- 한 일:
  - `ai/waiting_time/estimator.py`에 `map_prediction_output_to_waiting_time()`을 추가해 모델 예측 raw output을 `WaitingTimeEstimate`로 변환한다.
  - scikit-learn 계열 `predict()` 결과에서 흔한 scalar, 단일 list/tuple, array-like 단일 output을 1건 예측값으로 해석한다.
  - 모델 출력 단위는 기존 계약대로 minutes로 고정하고, Backend 연결용 출력 dict에는 `waitingTime`과 `unit=minutes`를 명시한다.
  - `NaN`, `inf`, non-numeric, bool, 음수, 빈 컨테이너, 다건 output은 예측 불가로 처리할 수 있도록 `ValueError`로 거부한다.
  - 학습 target domain인 130분을 초과하는 예측값은 clamp하지 않고 그대로 반환하되 `out_of_training_target_range` warning을 추가한다.
  - 기존 `expected_minutes` 기반 Backend placeholder 계약은 유지하면서, 서비스 응답 계약에 맞춘 `waitingTime` alias와 `to_backend_output()`을 추가했다.
- 산출물:
  - `ai/waiting_time/estimator.py`
  - `ai/tests/test_estimator.py`
  - `docs/development-phases.md`
- 확정 동작:
  - 출력 mapping은 순수 Python AI Adapter 내부 로직이며 FastAPI/HTTP, Backend schema, 추천 정렬 로직을 import하지 않는다.
  - 실제 joblib artifact 로딩과 추론 호출은 아직 구현하지 않는다. 모델 미연결 상태에서는 기존처럼 `NotImplementedError`를 유지한다.
  - `data/raw`, `data/processed`, `notebooks*/` 경로는 참조하지 않는다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py backend/tests/test_route_orchestration.py -q` — 32개 통과
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 214개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `git diff --check` — 통과
- 자체 리뷰:
  - Backend orchestration, API request schema, Frontend UI, 전일 차량운행 provider, 날씨 provider, 실제 모델 lazy-load는 이번 Phase 범위에서 제외했다.
  - `analysis/waiting_time/*.joblib` 및 metadata/export 산출물은 수정하지 않았다.
- 다음에 이어받을 것:
  - 실제 artifact 연결 Phase에서 모델 `predict()` 결과를 `map_prediction_output_to_waiting_time()`에 통과시켜 출력 검증을 일원화한다.
  - 임차택시·특장차 양쪽 `model_group` 예측을 수행하고 보수적 max 정책과 warning 병합 정책을 구현한다.
  - Backend route orchestration에서 `expected_minutes` 또는 `waitingTime`을 seconds로 변환해 차량 이동시간과 합산한다.

## AI Phase 3 — Prediction Adapter 구현 (2026-09-13)

- 브랜치: `ai/phase3-prediction-adapter` (base: 최신 `origin/dev` `3df65bc`). 기존 로컬 문서 변경은 원래 worktree에 보존하고, Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 통합 장애인 콜택시 대기시간 Prediction 모델 artifact를 Backend에서 직접 사용할 수 있도록 AI Adapter의 모델 호출 구조를 구현했다.
- 한 일:
  - `ai/waiting_time/estimator.py`에 `WaitingTimePredictionAdapter`를 추가했다.
  - Adapter는 `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib`을 lazy-load하고, `WaitingTimePredictionInput.to_model_features()` 결과를 학습 feature 순서의 pandas DataFrame으로 변환해 모델 `predict()`에 전달한다.
  - 모델 raw output은 Phase 2의 `map_prediction_output_to_waiting_time()`을 통해 `WaitingTimeEstimate`와 `waitingTime` minutes 형식으로 변환한다.
  - `estimate_waiting_minutes_for_input()`은 더 이상 `NotImplementedError`를 발생시키지 않고 기본 Adapter를 호출한다.
  - public entrypoint가 요청마다 1.48GB 모델을 다시 로딩하지 않도록 모듈 레벨 기본 Adapter를 재사용한다. 테스트에서는 명시적 Adapter 주입 또는 test-only setter로 교체할 수 있게 했다.
  - 모델 파일 없음, Git LFS pointer 상태, pandas/joblib 누락, 모델 로딩 실패, 모델 호출 실패를 명시적 Prediction error로 분리했다.
  - backend 서비스용 ML 추론 의존성으로 `joblib`, `pandas`, `scikit-learn`을 `backend/requirements.txt`에 추가했다.
  - 모델 artifact LFS pointer와 ML 의존성 누락 이슈를 `docs/troubleshooting/phase3-wait-time-prediction-adapter.md`에 기록했다.
  - `analysis/README.md`를 Adapter 실제 artifact 호출 상태와 남은 Backend orchestration 연결 범위에 맞게 갱신했다.
- 산출물:
  - `ai/waiting_time/estimator.py`
  - `ai/tests/test_estimator.py`
  - `backend/requirements.txt`
  - `analysis/README.md`
  - `docs/troubleshooting/phase3-wait-time-prediction-adapter.md`
  - `docs/development-phases.md`
- 확정 동작:
  - AI Adapter는 FastAPI/HTTP나 Backend schema를 import하지 않고 순수 Python 타입으로 동작한다.
  - 서비스 코드는 `data/raw`, `data/processed`, `notebooks*/`를 직접 참조하지 않고 `analysis/`의 reviewed artifact만 참조한다.
  - 모델 파일이 없거나 Git LFS pointer 상태이면 가짜 대기시간을 반환하지 않고 `WaitingTimeModelUnavailableError`를 발생시킨다.
  - 현재 Phase는 Adapter 구현까지이며, Backend route orchestration이 실제 feature source를 모두 준비해 호출하는 연결은 후속 Phase로 남긴다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py -q` — 33개 통과
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py backend/tests/test_waiting_time_features.py backend/tests/test_route_orchestration.py -q` — 67개 통과
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 220개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - 실제 1.48GB joblib artifact는 현재 worktree에서 Git LFS pointer 상태라 로딩 검증은 수행하지 못했다. 대신 missing artifact/LFS pointer를 unavailable error로 처리하는 단위 테스트를 추가했다.
  - `git diff --check` — 통과. 최초 실행은 Git LFS clean filter의 `.git/lfs/tmp` 쓰기 권한 문제로 실패했으나, 권한 승인 후 동일 검증이 통과했다.
- 자체 리뷰:
  - 모델 artifact와 metadata 파일은 수정하지 않았다.
  - Backend API request schema, Frontend UI, 전일 차량운행 lookup, 날씨 lookup/API, route orchestration 순서 변경은 이번 Phase 범위에서 제외했다.
  - 테스트는 대용량 모델 파일에 의존하지 않도록 fake model loader로 Adapter 호출 흐름을 검증했다.
- 다음에 이어받을 것:
  - 실제 배포/시연 환경에서 `git lfs pull --include="analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib"` 및 backend ML 의존성 설치 후 artifact 로딩 smoke test를 수행한다.
  - Backend route orchestration에서 TMAP 차량거리 계산 후 feature source를 만들고 `estimate_waiting_minutes_for_input()`을 호출하도록 연결한다.
  - 임차택시·특장차 양쪽 `model_group` 예측 후 보수적 max를 사용하는 정책과 warning 전달 방식을 구현한다.
  - 130분 초과 warning을 Backend `RouteResult.warnings` 또는 API 응답에 연결한다.

## Backend Phase 3 — 대기시간 Prediction Adapter 통합 연결 (2026-09-14)

- 브랜치: `backend/phase3-wait-time-backend-integration` (base: 최신 `origin/dev`). 기존 로컬 작업 트리는 보존하고 Phase 전용 worktree에서만 작업했다.
- 핵심 목표: Backend 추천 orchestration이 통합 장애인 콜택시 대기시간 Prediction Adapter 입력/출력 계약을 호출할 수 있게 연결했다.
- 한 일:
  - `RecommendationRequest`에 optional `calltaxi_purpose`를 추가하고, API 계약을 지원 목적 6개 enum으로 제한했다. 이용목적이 없으면 임의 기본값을 만들지 않고 콜택시만 `unavailable` 처리한다.
  - `BackendRecommendationRouteProvider`의 콜택시 계산 순서를 TMAP 차량거리/차량시간 산출 후 대기시간 Prediction 호출로 변경했다. 모델 feature `승차거리`는 TMAP 거리(m)를 그대로 사용한다.
  - Backend orchestration이 `estimate_waiting_minutes_for_input()` 계약을 호출하도록 바꾸고, 실제 DI에는 설정 기반 `ConfiguredWaitingTimeInputBuilder`를 연결했다.
  - `ConfiguredWaitingTimeInputBuilder`는 `Location.address`의 확정 주소 metadata에서 구/동을 추출하고, 설정된 JSON lookup에서 D-1 차량운행대수와 시간별 서울 관측 날씨를 읽는다. source가 없거나 값이 누락되면 Prediction unavailable로 fail-close한다.
  - 임차택시·특장차 바로콜 양쪽 `model_group` 입력을 반드시 각각 1회 생성·검증하게 하고, 두 예측 중 더 긴 대기시간을 사용하는 보수적 max 정책과 warning을 `RouteResult.warnings`에 연결했다. 한 그룹 누락·중복·추가 group은 estimator 호출 전 unavailable 처리한다.
  - Adapter warning(`out_of_training_target_range` 등)을 콜택시 route warning에 전달한다.
  - 이용목적 누락, lookup 설정 누락, feature mapping 실패, 모델 미연결/사용 불가, invalid output을 각각 콜택시 `unavailable`로 격리하고 지하철·저상버스 추천 흐름은 유지한다.
- 산출물:
  - `backend/app/api/contracts.py`
  - `backend/app/api/recommendation.py`
  - `backend/app/services/recommendation.py`
  - `backend/app/services/route_orchestration.py`
  - `backend/app/services/waiting_time_features.py`
  - `.env.example`
  - `backend/tests/test_config.py`
  - `backend/tests/test_route_orchestration.py`
  - `backend/tests/test_recommendation_routes.py`
  - `backend/tests/test_waiting_time_features.py`
  - `docs/development-phases.md`
- 확정 동작:
  - Backend는 대기시간 숫자를 만들지 않고 AI Adapter 결과만 사용한다.
  - 실제 DI는 `APP_CALLTAXI_OPERATION_COUNT_LOOKUP_PATH`, `APP_SEOUL_WEATHER_OBSERVATION_LOOKUP_PATH`가 모두 설정된 경우 Prediction input builder를 연결한다. source가 없으면 콜택시는 unavailable이다.
  - 주소 정규화는 현재 `Location.address`에 들어온 Kakao metadata 또는 reverse geocoding 결과를 사용한다. 별도 reverse geocoding HTTP client는 아직 구현하지 않는다.
  - 한 model_group prediction만 실패하면 콜택시 전체를 unavailable 처리한다. 한쪽 성공값만 사용하는 fallback은 MVP serving 정책에 포함하지 않는다.
  - 추천 정렬 정책, 지하철/저상버스 provider, 분석 artifact, `data/`, `notebooks*/`, Frontend UI는 변경하지 않았다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests/test_waiting_time_features.py backend/tests/test_recommendation_routes.py -q` — 49개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 235개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - 실제 `get_recommendation_route_provider()`를 사용하는 TestClient integration test에서 HTTP 요청 → TMAP fake → 설정 기반 `ConfiguredWaitingTimeInputBuilder` → `estimate_waiting_minutes_for_input()` fake → 콜택시 `RouteResult.total_time_seconds` 합산 경로를 확인했다.
  - `extract_district_and_dong()`은 행정동이 포함된 주소(`서울특별시 중구 명동`)만 구/동으로 사용하고, 도로명 주소(`서울특별시 중구 세종대로 110`)와 좌표만 있는 요청은 Prediction unavailable로 fail-close하는지 확인했다.
- 자체 리뷰:
  - `calltaxi_purpose`는 optional로 추가해 기존 호출을 깨지 않되, 값이 없을 때 예측 불가를 명시한다.
  - weather/operation-count 값을 임의 생성하지 않았다. 운영 lookup path와 해당 시각 값이 없으면 실운영 콜택시 route는 unavailable일 수 있다.
  - 별도 worktree의 `git status`가 Git LFS clean filter `.git/lfs/tmp` 권한 문제로 실패할 수 있음을 확인했다. 이는 기존 Phase 3 troubleshooting의 Git LFS artifact 한계와 같은 계열이며, 현재 코드 검증은 pytest 기준으로 완료했다.
- 다음에 이어받을 것:
  - 주소 metadata가 없는 요청을 위해 Kakao REST reverse geocoding provider를 연결한다.
  - 운영 환경에서 D-1 차량운행 lookup과 공식 시간별 서울 날씨 관측 lookup을 갱신하는 배치/운영 절차를 확정한다.
  - Frontend/API 연동 Phase에서 `calltaxi_purpose` 입력 UI와 요청 payload를 연결한다.
  - `git lfs pull`로 실제 1.48GB joblib artifact를 받은 환경에서 운영 provider smoke test를 수행한다.

## AI Phase 4 — Prediction 결과 검증 (2026-09-14)

- 브랜치: `ai/phase4-prediction-result-validation` (base: 최신 `origin/dev`). 기존 로컬 작업 트리는 보존하고 Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 통합 장애인 콜택시 대기시간 Prediction 모델이 정상 입력에서 서비스가 사용할 수 있는 유효한 minutes 단위 예상 대기시간을 반환하는지 검증했다.
- 한 일:
  - `ai/waiting_time/validation.py`를 추가해 sample prediction 실행, output type/unit/finite/non-negative 검증, 130분 초과 warning 정책 확인, 기존 대기시간 분석 baseline과의 비교 report 생성을 구현했다.
  - representative sample input은 `2026-09-14 09:00 Asia/Seoul`, 치료 목적, 중구 명동→강남구 역삼동, TMAP 거리 12,500m, 전일 차량운행 412대, 맑은 날씨 feature로 고정했다.
  - `임차택시_바로콜`, `특장차_바로콜` 두 model group을 모두 실제 joblib artifact로 예측하고 conservative max minutes/seconds를 산출했다.
  - `analysis/waiting_time/usage_pattern_evidence.md`의 reviewed `접수→승차` 평균·중앙값·75분위·90분위 baseline과 sample prediction의 차이를 비교했다.
  - `Null`, `NaN`, `inf`, 음수, 비숫자 output, 130분 초과 warning 누락을 validation issue로 잡는 단위 테스트를 추가했다.
  - 실제 검증 결과를 `analysis/waiting_time/prediction_validation_phase4.json`와 `analysis/waiting_time/prediction_validation_phase4.md`에 기록했다.
  - backend venv에 ML 추론 의존성이 설치되지 않아 실제 sample 실행이 막히는 문제를 재확인하고 `docs/troubleshooting/phase3-wait-time-prediction-adapter.md`에 Phase 4 추가 메모로 남겼다.
- 산출물:
  - `ai/waiting_time/validation.py`
  - `ai/tests/test_prediction_validation.py`
  - `analysis/waiting_time/prediction_validation_phase4.json`
  - `analysis/waiting_time/prediction_validation_phase4.md`
  - `analysis/README.md`
  - `docs/troubleshooting/phase3-wait-time-prediction-adapter.md`
  - `docs/development-phases.md`
- 확정 동작:
  - 검증 모듈은 AI Adapter의 순수 Python 계약만 사용하고 FastAPI/HTTP를 import하지 않는다.
  - 모델 artifact, metadata, serving feature mapping은 참조만 하고 수정하지 않는다.
  - `data/raw`, `data/processed`, `notebooks*/`를 직접 읽지 않는다.
  - 실제 artifact smoke validation은 대용량 LFS 파일과 ML 의존성이 준비된 로컬/운영 검증이며, 일반 단위 테스트는 fake adapter 기반으로 유지한다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m ai.waiting_time.validation --output analysis/waiting_time/prediction_validation_phase4.json`
    - `임차택시_바로콜`: `41.21341000519471` minutes
    - `특장차_바로콜`: `40.50492956696943` minutes
    - conservative max: `41.21341000519471` minutes, `2473` seconds
    - Null/NaN/음수 없음, output type finite numeric, unit `minutes`, 130분 초과 warning 불필요
  - 기존 분석 baseline과 비교:
    - `임차택시_바로콜` prediction `41.21분`: 기존 평균 `42.45분`, 중앙값 `28.51분`, 90분위 `87.34분` 기준 중앙값~90분위 범위
    - `특장차_바로콜` prediction `40.50분`: 기존 평균 `46.27분`, 중앙값 `33.42분`, 90분위 `95.13분` 기준 중앙값~90분위 범위
    - reviewed 기존 분석 분포와 비교해 이 sample에서 즉시 이상으로 볼 근거가 없음을 확인했다.
  - 모델 metadata 기준 `reported_test_MAE=11.105367785137439`, `reported_test_RMSE=15.332262378232757`, `reported_test_R2=0.6010887068297474`, `training_target_max_minutes=130`도 함께 기록했다.
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py ai/tests/test_prediction_validation.py -q` — 39개 통과
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 241개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `git diff --check` — 통과
- 자체 리뷰:
  - sample 1건 검증이므로 전체 운영 입력 공간의 품질 보증으로 해석하지 않는다.
  - 실제 joblib artifact를 수정하지 않았고, 모델 재학습·feature set 변경·fallback prediction 추가를 하지 않았다.
  - generated report의 `validated_at`은 실행 시각을 기록하므로 재실행 시 값이 바뀔 수 있다.
- 다음에 이어받을 것:
  - Backend Phase에서 실제 route orchestration과 연결된 상태로 동일 validation 기준을 smoke test한다.
  - 더 넓은 sample set 또는 reviewed validation dataset export가 준비되면 model_group·시간대·이동유형별 예측 분포 검증을 확장한다.

## AI Phase 5 — Prediction 오류 및 Fallback 처리 (2026-09-14)

- 브랜치: `ai/phase5-prediction-fallback-handling` (base: 최신 `origin/dev`). 기존 로컬 작업 트리는 보존하고 Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 장애인 콜택시 대기시간 Prediction 실패 시 0분, 평균값, 임의 fallback 숫자를 사용자에게 제공하지 않고 Backend `unavailable` 상태로 전달되도록 오류 경계를 고정했다.
- 한 일:
  - `WaitingTimePredictionAdapter.estimate()`에서 모델 호출은 성공했지만 output mapping이 거부한 값을 `WaitingTimeInvalidOutputError`로 감싸 Prediction 계층의 명시적 오류로 분리했다.
  - AI Adapter 테스트에 `None`, `NaN`, `inf`, 음수, 비숫자 모델 출력이 모두 `WaitingTimeInvalidOutputError` 또는 `ValueError`로 거부되는 경로를 고정했다.
  - Backend route orchestration 테스트에 feature mapping 실패, Prediction 호출 실패, `None`·`NaN`·`inf`·음수·비숫자 estimate, 한 model_group만 실패한 경우를 추가했다.
  - 모든 실패 케이스에서 콜택시는 `status=unavailable`, numeric metric은 `null`, metric availability는 `not_available`로 유지되고 지하철·저상버스 경로는 계속 계산되는지 확인했다.
- 산출물:
  - `ai/waiting_time/estimator.py`
  - `ai/tests/test_estimator.py`
  - `backend/tests/test_route_orchestration.py`
  - `docs/development-phases.md`
- 확정 동작:
  - 모델 미연결, 모델 artifact/의존성 사용 불가, 모델 호출 실패, invalid output은 임의 대기시간으로 대체하지 않는다.
  - feature source 누락 또는 mapping 실패는 콜택시 경로만 `unavailable`로 만들고, 실패 사유를 `unavailable_reason`에 보존한다.
  - 임차택시·특장차 바로콜 중 하나라도 Prediction이 실패하면 성공한 한쪽 값만 fallback으로 사용하지 않고 콜택시 전체를 `unavailable` 처리한다.
  - 기존 API schema, 추천 정렬 정책, 모델 artifact, 분석 export, Frontend UI는 변경하지 않았다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py backend/tests/test_route_orchestration.py -q` — 53개 통과
  - `PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 253개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건
  - `git diff --check` — 통과. 최초 sandbox 실행은 Git LFS clean filter의 `.git/lfs/tmp` 쓰기 권한 문제로 실패했으나, 권한 승인 후 동일 검증이 통과했다.
- 자체 리뷰:
  - `WaitingTimeInvalidOutputError`는 AI Adapter 내부 오류 분류만 추가하며 Backend/FastAPI schema를 import하지 않는다.
  - Backend는 예측 실패를 숫자로 복구하지 않고 `RouteResult`의 기존 unavailable 계약을 사용한다.
  - 새 운영 환경 문제나 재현 가능한 설정 장애는 발생하지 않아 별도 troubleshooting 문서는 추가하지 않았다.
- 다음에 이어받을 것:
  - 실제 joblib artifact와 운영 lookup이 준비된 환경에서 Backend provider smoke test를 반복한다.
  - 운영 모니터링 Phase에서 `prediction_unavailable_reason`, 모델 버전, inference latency를 관측 가능하게 남긴다.

## AI Phase 6 — Backend 통합 검증 및 시간 기준 보강 (2026-09-14)

- 브랜치: `ai/phase6-waiting-time-backend-integration` (base: 최신 `origin/dev`). 기존 로컬 작업 트리는 보존하고 Phase 전용 worktree에서만 작업했다.
- 핵심 목표: Backend가 통합 장애인 콜택시 대기시간 Prediction 결과를 실제 Adapter 경계를 통해 사용하고, Adapter 입력과 Backend lookup이 같은 Asia/Seoul 시간 기준으로 연결되는지 확인하고 보강했다.
- 한 일:
  - `ConfiguredWaitingTimeInputBuilder`가 요청 시각을 Asia/Seoul 기준으로 정규화한 뒤 D-1 차량운행 lookup 날짜와 시간별 서울 날씨 lookup key를 만들도록 했다.
  - `JsonWeatherObservationProvider`도 입력 시각을 Asia/Seoul 기준 정시로 정규화해 날씨 observation을 찾도록 보강했다.
  - timezone-naive `requested_at`은 feature mapping 단계에서 `WaitingTimeFeatureMappingError`로 거부해 조용히 로컬 timezone으로 해석되지 않게 했다.
  - UTC로 들어온 요청 시각이 Seoul 09시 weather lookup과 전일 차량운행 lookup으로 정상 mapping되는 테스트를 추가했다.
  - `BackendRecommendationRouteProvider`가 `WaitingTimeEstimate.expected_minutes`를 직접 읽지 않고 AI Adapter의 `to_backend_output()["waitingTime"]`, `unit="minutes"` 계약을 소비해 seconds로 변환하도록 했다.
  - `ConfiguredWaitingTimeInputBuilder` → `WaitingTimePredictionAdapter`(fake model loader) → `WaitingTimeEstimate` → `BackendRecommendationRouteProvider` → `RouteResult.total_time_seconds` 전체 경로를 통합 테스트로 고정했다.
  - Git LFS filter 권한 문제로 `git status`가 실패하는 재현 가능한 worktree 문제를 `docs/troubleshooting/phase6-worktree-lfs-status.md`에 기록했다.
- 산출물:
  - `backend/app/services/route_orchestration.py`
  - `backend/tests/test_route_orchestration.py`
  - `backend/app/services/waiting_time_features.py`
  - `backend/tests/test_waiting_time_features.py`
  - `docs/troubleshooting/phase6-worktree-lfs-status.md`
  - `docs/development-phases.md`
- 확정 동작:
  - Backend는 Prediction feature source의 날짜/시간 lookup을 Asia/Seoul 서비스 시간으로 수행한다.
  - AI Adapter는 기존 계약대로 `WaitingTimePredictionInput.to_model_features()`에서 Asia/Seoul 기준 `hour`, `month`, `dayofweek`를 생성한다.
  - Backend는 AI Adapter의 Backend 출력 계약(`waitingTime`, `unit=minutes`)을 사용해 `predicted_waiting_time_seconds`와 `total_time_seconds`를 만든다.
  - 모델 artifact, metadata, analysis export, API schema, 추천 정렬 정책, Frontend UI는 변경하지 않았다.
  - 대기시간 Prediction 실패 시 fallback 숫자를 만들지 않는 Phase 5 정책을 유지한다.
- 검증 결과:
  - `PYTHONPATH=backend:. python3 -m pytest backend/tests/test_route_orchestration.py backend/tests/test_waiting_time_features.py ai/tests/test_estimator.py -q` — 92개 통과
  - `PYTHONPATH=backend:. python3 -m pytest backend/tests ai/tests` — 258개 통과
  - `PYTHONPATH=backend:. python3 -m pytest src/tests backend/tests ai/tests` — 279개 통과
  - `python3 -m src.data_quality --check-report docs/validation/phase9-audit-2026-09-13.json` — errors 없음
  - `git diff --check` — 통과
- 자체 리뷰:
  - 이번 변경은 Adapter 출력 계약 소비와 lookup key 생성의 timezone 기준을 보강하는 좁은 수정이며, 새 데이터 source나 fallback 정책을 추가하지 않았다.
  - `requested_at`을 Seoul로 정규화해 Adapter 입력에도 넘기므로 Backend lookup과 AI feature `hour/month/dayofweek`가 같은 기준을 사용한다.
  - 실제 1.48GB joblib artifact 대신 fake model loader를 주입해 CI에서 Adapter 경계와 Backend 통합 흐름만 검증한다.
  - 실제 운영 smoke test는 TMAP key, operation/weather lookup, Git LFS artifact, ML 의존성이 모두 준비된 환경에서 별도로 반복해야 한다.
- 다음에 이어받을 것:
  - 운영 lookup 갱신 절차와 stale/missing 관측값 모니터링을 확정한다.
  - `prediction_unavailable_reason`, 모델 version, inference latency를 로그/metric으로 분리한다.
  - 실제 `git lfs pull` 완료 환경에서 Backend provider end-to-end smoke test를 수행한다.

## Backend Phase 4 — 장애인 콜택시 결과 통합 (2026-09-14)

- 브랜치: `backend/phase4-calltaxi-result-integration` (base: 최신 `origin/dev`). 기존 로컬 작업 트리는 보존하고 Phase 전용 worktree에서만 작업했다.
- 핵심 목표: 차량 이동시간과 Prediction 예상 대기시간을 결합해 장애인 콜택시의 최종 비교 결과를 하나의 `RouteResult`로 반환하도록 계약과 검증을 고정했다.
- 한 일:
  - `RouteResult`에 콜택시 전용 구성요소인 `predicted_waiting_time_seconds`, `vehicle_time_seconds`를 추가했다.
  - 콜택시 `available` 결과는 `total_time_seconds = predicted_waiting_time_seconds + vehicle_time_seconds`를 만족해야 하며, 지하철·저상버스는 콜택시 전용 구성요소를 포함할 수 없도록 검증했다.
  - `BackendRecommendationRouteProvider`가 AI Adapter의 minutes 결과를 seconds로 변환해 `predicted_waiting_time_seconds`에 보존하고, TMAP 차량시간을 `vehicle_time_seconds`에 보존한 뒤 총 예상시간·거리·요금을 함께 반환하도록 했다.
  - 추천 API integration 테스트에서 HTTP 요청 → TMAP fake → Prediction fake → 콜택시 `RouteResult` 응답까지 `예상 대기시간`, `차량 이동시간`, `총 예상시간`, `이동거리`, `예상요금`이 함께 반환되는지 확인했다.
  - `frontend/src/api/recommendation.ts`의 `RouteResult` 타입에 새 optional component 필드를 반영했다. 화면 표시 로직은 변경하지 않았다.
- 산출물:
  - `backend/app/api/contracts.py`
  - `backend/app/services/route_orchestration.py`
  - `backend/app/api/routes.py`
  - `backend/tests/test_route_contracts.py`
  - `backend/tests/test_route_orchestration.py`
  - `backend/tests/test_recommendation_routes.py`
  - `frontend/src/api/recommendation.ts`
  - `docs/decisions/0004-route-metric-availability-and-recommendation-contract.md`
  - `docs/decisions/0006-wait-time-prediction-contract.md`
  - `docs/development-phases.md`
- 확정 동작:
  - `predicted_waiting_time_seconds`와 `vehicle_time_seconds`는 콜택시 총시간 산출 근거이며, `metric_availability`나 추천 정렬 지표로 사용하지 않는다.
  - 콜택시 도보 지표는 계속 `null/not_available`, 접근성은 `not_verified`로 유지한다.
  - Prediction 실패, feature source 누락, TMAP 실패는 기존처럼 콜택시 `unavailable`로 격리하고 임의 숫자로 대체하지 않는다.
  - 모델 artifact, 분석 export, 원본 `data/`, `notebooks*/`, 추천 정렬 정책, Frontend 화면 UI는 변경하지 않았다.
- 검증 결과:
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests/test_route_contracts.py backend/tests/test_route_orchestration.py backend/tests/test_recommendation_routes.py -q` — 54개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건.
  - `PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q` — 256개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건.
  - `frontend/`에서 `npm test -- --run` — 실패. 별도 worktree에 `node_modules`가 없어 `vitest: command not found`가 발생했다. 새 Frontend 변경은 API 타입의 optional field 추가뿐이며 UI 로직은 변경하지 않았다.
  - `git diff --check` — 통과.
- 자체 리뷰:
  - 새 component 필드는 공통 정렬 metric이 아니므로 `RouteMetricAvailability`에는 추가하지 않았다.
  - API 응답에 새 optional 필드가 추가되는 additive 변경이며, 기존 unavailable 경로는 component 값도 `null`로 유지한다.
  - 실제 joblib artifact smoke test와 운영 lookup 신선도 검증은 이번 Phase의 결과 통합 계약 범위가 아니므로 새로 수행하지 않았다.
- 다음에 이어받을 것:
  - Frontend 표시 Phase에서 콜택시 카드에 대기시간/차량시간/총시간 breakdown을 보여줄지 결정한다.
  - 운영 모니터링 Phase에서 대기시간 component, 차량시간, 모델 warning을 구조화 로그/관측 지표로 남긴다.

## Frontend Phase 3 — Backend 경로검색 API 연결 보강 (2026-09-14)

- 브랜치: `frontend/phase3-backend-route-search-api` (base: 최신 `origin/dev`). 기존 로컬 작업 트리는 보존하고 Phase 전용 worktree에서만 작업했다.
- 작업 전 확인:
  - 반드시 읽은 파일: `AGENTS.md`, `docs/architecture.md`, `docs/decisions/0003-frontend-map-sdk-exception.md`, `docs/decisions/0004-route-metric-availability-and-recommendation-contract.md`, `docs/development-phases.md`, `backend/app/api/contracts.py`, `frontend/src/App.tsx`, `frontend/src/api/recommendation.ts`, `frontend/src/__tests__/App.test.tsx`
  - 이번 Phase에서 수정한 파일: `frontend/src/App.tsx`, `frontend/src/api/recommendation.ts`, `frontend/src/__tests__/App.test.tsx`, `docs/development-phases.md`
  - 참고만 하고 수정하지 않은 파일: `backend/app/api/contracts.py`, `backend/app/services/route_orchestration.py`, `ai/waiting_time/estimator.py`, `analysis/`, `data/`, `notebooks*/`
  - 이번 Phase 범위에 포함하지 않은 작업: Backend 추천 정렬 변경, AI Prediction 재학습·artifact 수정, Kakao/ODsay/TMAP provider 변경, 추천 결과 카드의 콜택시 시간 breakdown UI 추가, 교통비 캘린더 변경
- 핵심 목표: 사용자가 선택한 출발지·목적지 좌표, 이동수단 선택값, 추천 우선순위를 Frontend에서 Backend 추천 API로 보내고 `RouteResult` 기반 추천 결과를 수신하는 흐름을 최신 Backend 계약에 맞춰 보강했다.
- 한 일:
  - `RecommendationRequest` 타입에 Backend가 받는 `calltaxi_purpose`를 추가했다.
  - 장애인 콜택시가 선택된 경우 이용목적을 선택해야 경로검색을 보낼 수 있도록 입력 조건을 추가했다.
  - 콜택시 선택 시 `calltaxi_purpose`를 `POST /routes/recommendations` 요청 body에 포함하고, 콜택시를 해제한 경우에는 해당 값을 전송하지 않도록 했다.
  - 입력 장소, 이동수단, 우선순위, 콜택시 이용목적이 변경되면 기존 추천 결과와 진행 중 요청을 무효화하는 기존 stale-response 방어 흐름을 유지했다.
  - 프론트 테스트에 콜택시 이용목적 필수 조건과 request body mapping 검증을 추가했다.
- 산출물:
  - `frontend/src/App.tsx`
  - `frontend/src/api/recommendation.ts`
  - `frontend/src/__tests__/App.test.tsx`
  - `docs/development-phases.md`
- 확정 동작:
  - Frontend는 출발지·목적지 좌표, 선택 이동수단, 우선순위, 콜택시 이용목적을 Backend 추천 API에 전달한다.
  - 선택하지 않은 이동수단은 Backend 요청 대상에서 제외되며, 콜택시를 선택하지 않으면 `calltaxi_purpose`도 전송하지 않는다.
  - 경로 계산, 추천 정렬, 요금·시간·도보 판단은 Frontend에서 재계산하지 않고 Backend 응답을 그대로 표시한다.
  - `data/`, `notebooks*/`, `analysis/`, `ai/`, Backend provider 로직은 변경하지 않았다.
- 검증 결과:
  - `frontend/`에서 `npm test -- --run` — 2개 파일, 22개 테스트 통과.
  - `frontend/`에서 `npm run build` — TypeScript build 및 Vite production build 통과.
  - 최초 `npm test -- --run`은 별도 worktree에 `node_modules`가 없어 `vitest: command not found`로 실패했다. `npm ci`로 `package-lock.json` 기준 의존성을 설치한 뒤 동일 명령이 통과했다.
- 자체 리뷰:
  - 새 입력값은 Backend 계약에 이미 존재하는 `calltaxi_purpose`를 전달하기 위한 UI/요청 mapping이며, 임의 목적 기본값을 넣지 않는다.
  - 이용목적이 없는 콜택시 요청을 막아 Backend가 필수 feature 누락으로 콜택시를 `unavailable` 처리하는 상황을 줄였다.
  - 기존 abort/request id 기반 stale-response 방어를 변경하지 않고, 콜택시 이용목적 변경도 동일하게 추천 결과를 무효화한다.
- 다음에 이어받을 것:
  - 콜택시 결과 카드에서 `predicted_waiting_time_seconds`, `vehicle_time_seconds`, `total_time_seconds`를 사용자에게 어떻게 나눠 보여줄지 결정한다.
  - 실제 배포 환경에서는 `VITE_API_BASE_URL`과 Backend `APP_CORS_ALLOW_ORIGINS`를 같은 origin 정책에 맞춰 설정한다.
