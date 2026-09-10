# AGENTS.md

이 레포에서 코드를 작성/수정할 때 지키는 규칙. 자세한 배경은 [`docs/architecture.md`](docs/architecture.md)와 [`docs/decisions/`](docs/decisions/)를 참고.

## 아키텍처 규칙

1. **`backend/`는 HTTP + 추천 정렬(Rule-based ranking)을 담당한다.** 대기시간 예측은 라우터 함수 안에 직접 작성하지 않고 `ai/`(AI Adapter)를 호출한다. 요금/시간/도보 우선순위 추천 로직은 `ai/`가 아니라 `backend/`에 둔다(Backend Phase 7, 아직 미착수).
2. **`ai/`는 AI Adapter다 — 예측 모델을 호출하는 것 외의 로직(추천 정렬 등)을 갖지 않는다.** FastAPI/HTTP를 import하지 않고, 입력/출력은 일반 Python 타입(dataclass 등)으로만 주고받아 HTTP 없이도 단위 테스트가 가능해야 한다. 모델이 연결되지 않은 기능은 가짜 값을 반환하지 말고 `NotImplementedError`를 발생시킨다.
3. **`frontend/`는 `backend/`의 API를 통해서만 데이터를 얻는다.** `data/`의 CSV나 `ai/` 코드를 직접 참조하지 않는다.
4. **서비스 코드(`backend/`, `frontend/`, `ai/`)는 `data/raw`, `data/processed`, `notebooks*/`의 파일 경로를 직접 참조하지 않는다.** 분석 결과가 필요하면 사람이 검토해서 `analysis/`에 export하고, `ai/`는 `analysis/`의 파일만 읽는다.
5. **기존 `src/`, `notebooks*/`는 데이터분석 전용이다.** 서비스 기능을 이 폴더에 추가하지 않는다.
6. **`analysis/`에는 노트북/스크립트가 자동으로 쓰지 않는다.** 분석이 끝나고 결과가 안정화된 뒤 사람이 수동으로 export한다(자세한 규칙은 `analysis/README.md`).

## 폴더 책임

| 폴더 | 책임 | 하지 말아야 할 것 |
|---|---|---|
| `backend/app/api/` | 라우터, 요청/응답 스키마 | 계산 로직 직접 구현 |
| `backend/app/core/` | 설정 로딩, 로깅 등 앱 공통 인프라 | 도메인 로직 |
| `ai/waiting_time/` | 특장차/임차택시 Prediction 모델 호출(AI Adapter) | 모델 미연결 시 가짜 값 반환, 추천/정렬 로직 |
| `frontend/src/` | 화면, API 클라이언트 | 백엔드 로직 재구현 |
| `analysis/` | 서비스가 쓰기로 확정된 Prediction 모델/분석 export 결과 | 탐색적 분석, 노트북의 자동 출력 경로로 사용 |
| `docs/` | 지금 실제로 필요한 설계/운영 문서만 | 빈 문서, 미확정 내용 미리 채우기 |

## 코드 작성 기준

- 백엔드/AI: 타입 힌트 필수, 새 모듈은 dataclass 또는 Pydantic 모델로 입출력 타입을 명시한다.
- 자리표시자(placeholder) 구현은 반드시 `TODO:` 주석과 무엇으로 대체해야 하는지(예: 참조할 노트북 경로)를 남긴다.
- 새 환경변수를 추가하면 해당 영역의 `.env.example`에도 함께 추가한다.

## 테스트 기준

- `ai/`에 로직을 추가하면 최소 1개의 유닛 테스트를 같은 PR에 포함한다(입력→출력만 검증, HTTP 불필요).
- `backend/`에 라우트를 추가하면 `TestClient`로 상태 코드/응답 스키마를 검증하는 테스트를 추가한다.
- `frontend/`에 화면 컴포넌트를 추가하면 최소 1개의 렌더 테스트(React Testing Library)를 추가한다.
- 테스트 실행: 저장소 루트에서 `backend/.venv/Scripts/python -m pytest backend/tests ai/tests`, `frontend/`에서 `npm test`.

## 문서 작성 기준

- 설계 변경(폴더 구조, 기술 스택, 모듈 경계)은 `docs/decisions/`에 번호를 이어 ADR로 남긴다(`000N-제목.md`).
- Phase가 끝나면(시작 시점이 아니라) `docs/development-phases.md`에 한 일과 다음 Phase가 이어받을 것을 기록한다.
- 서비스 코드에서 실제로 겪은 문제만 `docs/troubleshooting.md`에 증상→원인→해결 형식으로 남긴다.
- 화면/API 설계처럼 아직 확정되지 않은 내용을 문서에 미리 채워 넣지 않는다 — 확정된 뒤에 작성한다.
