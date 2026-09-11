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
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 24개 통과
  - `uvicorn app.main:app --host 127.0.0.1 --port 8011` 실행 후 `GET /routes/sample` — 200, `calltaxi`, `subway`, `low_floor_bus` 3개 이동수단과 도보거리·도보시간 필드 포함 확인
  - `create_app()` 기본 설정과 `create_app(include_sample_routes=False)` 기준 `/routes/sample` — 404 확인
  - `create_app(include_sample_routes=True)` 기준 `/routes/sample` — 200 확인
- 다음 Phase가 이어받을 것:
  - 실제 카카오/티맵/ODSAY 등 외부 경로 API 호출은 이번 Phase 범위가 아니므로 이후 Backend Phase에서 구현한다.
  - 추천 정렬, 경로 점수화, 대기시간 모델 연결은 아직 구현하지 않는다.
