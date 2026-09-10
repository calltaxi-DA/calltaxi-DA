# 아키텍처

## 이 레포의 세 축

`calltaxi-DA`는 하나의 모노레포 안에 서로 다른 세 종류의 산출물을 담는다.

| 축 | 폴더 | 산출물 | 실행 주체 |
|---|---|---|---|
| 데이터 분석 (기존) | `data/`, `notebooks*/`, `src/` | 탐색적 분석 노트북, 배치성 전처리 스크립트 | 분석 담당자가 로컬에서 수동 실행 |
| 분석 결과 발행 (신규, 경계) | `analysis/` | 서비스가 그대로 가져다 쓰기로 확정된 export 결과 | 분석 담당자가 검토 후 수동 export |
| 서비스 (신규) | `backend/`, `frontend/`, `ai/` | 장애인콜택시 추천 웹서비스 | 상시 구동되는 백엔드/프론트엔드 프로세스 |

세 축은 서로 다른 실행 주기(1회성 분석 vs 상시 서비스)와 데이터 신선도 요구사항을 가지므로 분리되어 있다. `data/`, `notebooks*/`는 탐색적·불안정한 작업 공간이라 서비스가 직접 참조하지 않는다.

**대기시간 예측 흐름**: `analysis/`는 분석이 만들어낸 **장애인 콜택시 통합 대기시간 Prediction 모델**(또는 그 산출물)이 놓이는 곳이고, `ai/`는 그 모델을 직접 호출·서빙하는 **AI Adapter**다 — 예측 로직 자체를 갖지 않고 모델을 감싸기만 한다.

```text
notebooks*/ (모델 학습·검증) → analysis/ (장애인 콜택시 통합 대기시간 Prediction 모델) → ai/ (AI Adapter) → backend/
```

`ai/`는 오직 `analysis/`의 산출물만 참조하며, 모델이 아직 연결되지 않은 동안에는 가짜 값을 반환하지 않고 명확히 실패(`NotImplementedError`)한다 — `backend/`가 "예측 불가" 상태를 받아 처리하도록 강제한다.

> 요금/시간/도보 우선순위에 따른 **추천 로직(Rule-based ranking)은 `ai/`에 두지 않는다.** `ai/`는 예측 모델 어댑터 전용이고, 추천 정렬은 백엔드 개발 로드맵의 **Backend Phase 7**에서 `backend/` 쪽에 구현할 예정이다(아직 미착수).

## 서비스 개요 (기획 요약)

출발지·목적지를 입력하면 지하철·저상버스·장애인콜택시의 이동시간/비용/도보거리를 비교하고, 장애인콜택시는 분석으로 산출한 예상 대기시간을 총 이동시간에 반영해 추천한다(핵심 지표: `총 이동시간 = 예상 대기시간 + 차량 이동시간`). 추천은 복잡한 ML 모델이 아니라 Rule-based(요금/시간/도보 우선순위 정렬)로 계산한다. 부가 기능으로 월별 교통비 지원 현황을 보여주는 캘린더가 있다.

> 화면 구성(MAP/경로비교/캘린더)과 API 스펙은 아직 확정되지 않았다 — 이번 초기 세팅은 그 설계가 나오기 전에 각 영역의 실행 골격만 만드는 것이 목적이다. 화면/API가 정해지면 이 문서와 `backend/app/api/`, `frontend/src/`를 함께 갱신한다.

## 폴더 책임

- **`backend/`** — FastAPI HTTP 계층. 요청을 받아 `ai/`(예측)를 호출하고, 요금/시간/도보 우선순위 추천 정렬(Rule-based, Backend Phase 7 예정)도 여기서 구현한다. 대기시간 예측 모델 자체는 갖지 않는다.
- **`ai/`** — **AI Adapter.** `analysis/`의 장애인 콜택시 통합 대기시간 Prediction 모델을 호출하는 어댑터. 순수 Python이며 FastAPI/HTTP를 알지 못한다(단독 테스트·재사용 가능해야 함). 예측 로직·추천 로직을 직접 갖지 않는다 — 모델이 없으면 `NotImplementedError`로 실패한다.
- **`frontend/`** — 사용자 화면. `backend/`가 노출하는 API만 호출하고, 데이터 파일이나 `ai/`를 직접 참조하지 않는다.
- **`analysis/`** — 분석이 만들어낸 Prediction 모델/산출물 중 서비스가 쓰기로 확정된 것만 모아두는 export 공간. 노트북이 자동으로 쓰지 않고 사람이 검토 후 옮긴다. 자세한 규칙은 [`analysis/README.md`](../analysis/README.md).
- **`data/`, `notebooks*/`, `src/`** — 기존 데이터분석 자산(탐색적, 원본/중간 산출물). 서비스 코드(`backend/`, `frontend/`, `ai/`)가 이 폴더의 파일 경로를 직접 참조하지 않는다 — 필요하면 `analysis/`를 거친다.
- **`docs/`** — 이 저장소를 다루는 데 필요한 설계/운영 문서. 노트북 단위의 분석 계획 문서는 `notebooks_docs_lye/`(gitignore 대상, 팀 공유 문서 아님)에 남는다.

## 데이터 소유권

- 장애인콜택시 원본/전처리 데이터(`data/raw`, `data/processed`)의 소유권과 갱신 책임은 분석 축에 있다. 서비스가 이 데이터의 최신 값이 필요하면, 분석 담당자가 검토해서 `analysis/`에 export하고 `ai/`는 그 export 파일만 읽는다 — `ai/`나 `backend/`가 `data/raw`/`data/processed`의 원본 CSV 경로를 직접 열지 않는다.
- 서비스가 자체적으로 생성하는 데이터(사용자 입력, 교통비 기록 등)는 아직 없다 — 저장소/DB 도입 시 이 문서에 소유권을 추가한다.

## Python 실행환경 분리

- 루트 `.venv` + 루트 `requirements.txt`: 데이터분석/주피터 전용(기존 그대로).
- `backend/.venv` + `backend/requirements.txt`: 서비스(백엔드+`ai/`) 전용. `ai/`는 별도 가상환경을 두지 않고 `backend/.venv`를 공유한다(둘 다 같은 프로세스에서 실행되므로 분리 실익이 없음).

## 개발 단계 추적, 트러블슈팅, 설계 결정 문서 위치

- 진행 단계: [`docs/development-phases.md`](./development-phases.md)
- 트러블슈팅: [`docs/troubleshooting.md`](./troubleshooting.md)
- 아키텍처/기술 선택 근거(ADR): [`docs/decisions/`](./decisions/)
