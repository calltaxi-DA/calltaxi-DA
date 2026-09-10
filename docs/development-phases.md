# 개발 단계 추적

## 작성 기준

- Phase는 완료된 뒤에 기록한다(계획 단계에서 미리 여러 Phase를 만들어두지 않는다).
- 각 Phase 항목: 날짜, 한 일, 만들어진 산출물(파일/브랜치/PR), 다음 Phase가 이어받을 것.
- 화면/API 설계처럼 아직 확정되지 않은 것은 "다음 Phase 산출물"에만 적고, 앞당겨 구현하지 않는다.

## Phase 0 — 모노레포 초기 스캐폴딩 (2026-09-10)

- 브랜치: `feat/service-bootstrap` (base: `dev`)
- 한 일: `backend/`(FastAPI), `ai/`(대기시간·추천 로직 골격), `frontend/`(Vite+React+TS)를 기존 데이터분석 구조와 분리해 추가. 이후 `analysis/`를 분석→서비스 경계(export 전용 공간)로 추가. `docs/`, `AGENTS.md`, 루트 `README.md` 정비.
- 산출물:
  - `GET /health` 동작(200 확인), `pytest`(backend+ai) 6개 통과, `npm run build`/`npm test`(frontend) 통과
  - `docs/architecture.md`(폴더 책임/데이터 소유권), `docs/decisions/0001-monorepo-and-stack.md`
  - `analysis/README.md` — export 규칙만 정의, 아직 실제 export된 파일은 없음
- 다음 Phase가 이어받을 것:
  - 화면 1(MAP) → 화면 2(경로 비교) → 화면 3(교통비 캘린더) 구체 설계 — 원 기획서에서 이미 다음 단계로 지정된 작업
  - 위 화면 설계가 나온 뒤 `backend/app/api/`에 실제 라우트, `ai/`에 실제 대기시간 데이터/추천 규칙 반영
  - `ai/waiting_time/estimator.py`는 지금 고정값(30분)을 반환하는 자리표시자다 — `notebooks_lye/5-1_plan_시간대별평균대기시간.ipynb` 등 기존 분석 결과를 `analysis/`로 export한 뒤 실제 lookup으로 연결해야 함
