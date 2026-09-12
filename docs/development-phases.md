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
  - `backend/app/core/config.py`, `backend/.env.example` — `APP_TMAP_APP_KEY` 설정 추가
  - `backend/tests/test_calltaxi_routes.py` — 라우터 응답, 좌표 검증, 키 누락, TMAP 실패·invalid JSON 처리 테스트
  - `backend/tests/test_calltaxi_service.py` — 요금 계산, TMAP 응답 파싱, outbound 요청 URL·헤더·payload 검증 테스트
  - `docs/troubleshooting.md` — 실제 TMAP smoke test `403 Forbidden` 이슈 기록
- 검증 결과:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 41개 통과
  - 로컬 `APP_TMAP_APP_KEY` 존재 확인 — 키 값은 출력하지 않고 존재 여부만 확인
  - 실제 TMAP 자동차 경로안내 smoke test — `403 Forbidden`으로 실패. 코드 요청/응답 처리 검증은 완료됐지만, 실제 키의 자동차 경로안내 API 상품 권한 또는 제한 설정 확인이 필요하다.
- 다음 Phase가 이어받을 것:
  - TMAP 개발자 콘솔에서 App Key가 자동차 경로안내 API를 사용할 수 있는지 확인하고 실제 smoke test를 재실행한다.
  - 프론트엔드 경로검색 버튼과 `/routes/calltaxi` 연결은 이번 Phase 범위가 아니므로 이후 Frontend/API 연동 Phase에서 진행한다.
  - 장애인 콜택시 대기시간 예측 모델 연결과 총 이동시간에 대기시간을 합산하는 작업은 AI Adapter/대기시간 Phase에서 진행한다.
  - 지하철·저상버스 경로 API와 추천 정렬은 별도 Backend Phase에서 구현한다.
