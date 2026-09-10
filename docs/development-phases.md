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
