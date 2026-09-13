# Phase 3 대기시간 Prediction Adapter 연결 이슈

## 문제 상황

Phase 3에서 `ai/waiting_time/estimator.py`가 `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib`을 실제로 호출하도록 Adapter를 구현하는 과정에서 두 가지 재현 가능한 실행 조건 문제가 확인됐다.

1. Git LFS artifact가 실제 joblib 파일이 아니라 pointer 파일 상태일 수 있다.
2. backend 전용 가상환경에는 기존에 `joblib`, `pandas`, `scikit-learn`이 설치되어 있지 않았다.

## 영향

- 모델 파일이 pointer 상태이면 실제 RandomForest pipeline을 로딩할 수 없다.
- pandas/joblib/scikit-learn이 없으면 모델 입력 DataFrame 생성 또는 joblib 로딩이 실패한다.
- 이 상황에서 fallback 숫자를 반환하면 서비스가 검증되지 않은 대기시간을 총 이동시간에 반영할 수 있으므로, Adapter는 명시적 `WaitingTimeModelUnavailableError`를 발생시키도록 했다.

## 재현 방법

```bash
head -5 analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib
```

출력이 아래와 같으면 실제 모델이 아니라 Git LFS pointer 상태다.

```text
version https://git-lfs.github.com/spec/v1
oid sha256:...
size 1480271962
```

backend venv 의존성은 아래처럼 확인했다.

```bash
/Users/blaumonde/calltaxi-DA/backend/.venv/bin/python - <<'PY'
import importlib.util
for name in ["joblib", "pandas", "sklearn"]:
    print(name, "OK" if importlib.util.find_spec(name) else "MISSING")
PY
```

## 원인

- 모델 artifact는 1.48GB 규모라 Git LFS로 관리된다. 새 worktree나 fresh clone에서는 smudge가 비활성화되거나 LFS pull을 수행하지 않으면 pointer만 존재할 수 있다.
- 서비스용 `backend/requirements.txt`는 기존 FastAPI/테스트 의존성만 포함했고, 분석용 루트 `requirements.txt`와 분리되어 있어 ML 추론 의존성이 누락되어 있었다.

## 검토한 대안

1. **pointer 파일이어도 예측 fallback 반환**
   - 장점: 서비스가 멈추지 않는다.
   - 단점: AGENTS.md의 “모델 미연결 시 가짜 값 반환 금지”와 충돌한다.
   - 판단: 채택하지 않음.

2. **테스트에서 실제 1.48GB 모델을 항상 로딩**
   - 장점: 실제 artifact와 완전히 동일한 경로를 검증한다.
   - 단점: CI/로컬 테스트가 LFS 다운로드와 대용량 메모리에 의존하게 된다.
   - 판단: 단위 테스트에서는 fake model loader로 Adapter 흐름을 검증하고, 실제 artifact 다운로드 검증은 별도 운영/통합 검증으로 분리한다.

3. **Adapter에서 명시적 unavailable error 반환**
   - 장점: 운영자가 원인을 파악할 수 있고, 서비스가 검증되지 않은 숫자를 쓰지 않는다.
   - 단점: artifact와 의존성이 준비되지 않으면 콜택시 예측은 unavailable 처리된다.
   - 판단: 채택.

## 해결 방법

- `WaitingTimePredictionAdapter`를 추가해 모델 artifact를 lazy-load한다.
- 모델 파일이 없거나 Git LFS pointer이면 `WaitingTimeModelUnavailableError`를 발생시킨다.
- `backend/requirements.txt`에 `joblib`, `pandas`, `scikit-learn`을 추가한다.
- 모델 raw output은 Phase 2의 `map_prediction_output_to_waiting_time()`을 통해 검증한다.
- 단위 테스트는 fake model loader와 fake model로 입력 전달, lazy-load 재사용, output mapping, missing artifact, LFS pointer reject를 검증한다.

## 검증 결과

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py -q
```

- 31개 통과

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest ai/tests/test_estimator.py backend/tests/test_waiting_time_features.py backend/tests/test_route_orchestration.py -q
```

- 65개 통과

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pytest backend/tests ai/tests -q
```

- 218개 통과, 기존 Starlette/anyio `DeprecationWarning` 1건

## 남은 한계

- 현재 worktree의 모델 파일은 Git LFS pointer 상태이므로 실제 1.48GB artifact 로딩 검증은 별도 `git lfs pull` 이후 수행해야 한다.
- Backend route orchestration은 아직 feature source를 모두 준비해 `estimate_waiting_minutes_for_input()`으로 넘기도록 연결되지 않았다.
- 임차택시·특장차 양쪽 `model_group` 예측 후 보수적 max를 사용하는 정책은 후속 Phase에서 구현해야 한다.
