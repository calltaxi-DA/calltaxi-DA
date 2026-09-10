# ADR 0002: `ai/`는 예측 모델 어댑터 전용, 추천 정렬은 `backend/`로 이동

- 상태: 결정됨 (2026-09-10)
- 관련: [ADR 0001](./0001-monorepo-and-stack.md)

## 배경

ADR 0001에서는 `ai/`에 대기시간 산출(`waiting_time/`)과 Rule-based 추천 정렬(`recommendation/`)을 함께 두었다. 이후 다음 두 가지를 반영해 재조정한다.

1. `ai/waiting_time/estimator.py`가 고정값(30분)을 반환하고 있었는데, 모델이 아직 없는 상태에서 그럴듯한 가짜 값을 반환하는 것은 실제 미연결 상태를 숨겨 위험하다.
2. `ai/`의 역할을 "특장차/임차택시 Prediction 모델을 호출하는 어댑터"로 좁히기로 했다 — 추천 정렬은 예측 모델과 무관한 별도 로직이라 어댑터 계층에 둘 이유가 없다.

## 결정

1. **`ai/waiting_time/estimator.py`는 모델이 연결되기 전까지 `NotImplementedError`를 발생시킨다.** 가짜 값을 반환하지 않는다 — 호출자(`backend/`)가 "예측 불가" 상태를 명시적으로 처리해야 한다.
2. **`ai/recommendation/`(Rule-based 정렬)을 `ai/`에서 제거한다.** 이 로직은 예측 모델과 무관하므로 AI Adapter의 책임이 아니다.
3. **추천 정렬 로직은 이후 `backend/`에 구현한다(Backend Phase 7).** 지금은 미착수 상태이며, 화면/API 설계가 나온 뒤 진행한다.
4. **`analysis/`는 특장차/임차택시 Prediction 모델(또는 그 산출물)이 놓이는 곳으로 역할을 명확히 한다.** 데이터 흐름: `notebooks*/ → analysis/(Prediction 모델) → ai/(AI Adapter) → backend/`.

## 영향

- `ai/tests/test_estimator.py`는 "모델 미연결 시 `NotImplementedError`가 발생하는지"를 검증하도록 바뀐다(이전: 고정값이 반환되는지 검증).
- `ai/tests/test_ranker.py`, `ai/recommendation/`은 삭제한다.
- `docs/architecture.md`, `AGENTS.md`, `analysis/README.md`, 루트 `README.md`의 `ai/` 설명을 "AI Adapter"로 통일한다.
