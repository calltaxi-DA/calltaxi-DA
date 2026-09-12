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

## Analysis Phase 5-2 — ODsay 버스 route mapping 실제 검증 (다음 Phase)

- 상태: 미완료 / 후속 Phase로 분리
- 목표: 실제 ODsay 버스 경로 응답의 `busID`, 노선번호, 버스 유형 필드를 확인하고, `analysis/bus/low_floor_bus_route_master.csv`와 연결 가능한지 검증한다.
- 필요한 일:
  - ODsay 버스 경로 실제 응답 샘플 10~20개 이상 확보
  - 응답에서 버스 구간의 `busID`, 노선번호, 버스 유형 필드명과 표기 방식 확인
  - `route_number_normalized`, `route_type_code`, `seoul_route_id`와의 매핑 성공률 산출
  - 미매핑 노선, 다중 매칭 노선, `route_type_code` 결측 노선 처리 기준 기록
  - 검토 완료된 ODsay busID ↔ route master mapping table이 필요하면 `analysis/`에 별도 export
- 주의: 이 Phase가 완료되기 전까지 `analysis/bus/low_floor_bus_route_master.csv`는 실제 ODsay 경로 연결 검증 완료 산출물이 아니라 후보 route master로 본다.
