# Phase 8 대기시간 모델 실행환경 검증 이슈

## 문제 상황

Phase 8에서 통합 장애인 콜택시 대기시간 Prediction 모델 실행환경을 검증하는 과정에서 다음 문제가 재현됐다.

1. `backend/.venv`는 Python 3.12이지만 `pip`가 없어 `backend/requirements.txt` 설치 명령을 실행할 수 없었다.
2. 루트 `.venv`에는 `pip`가 있었지만 `joblib`, `pandas` 버전이 `backend/requirements.txt`와 달랐다.
3. sandbox 네트워크 제한 상태에서는 PyPI DNS 조회가 실패해 requirements 설치가 실패했다.

## 영향

- Python 버전이 맞아도 ML 추론 의존성 버전이 다르면 RandomForest joblib artifact를 같은 조건으로 실행했다고 보기 어렵다.
- `pip`가 없는 venv에서는 새 개발자가 requirements를 재설치하거나 버전 drift를 복구하기 어렵다.
- 네트워크 제한 환경에서는 dependencies 설치가 실패할 수 있으므로, 실패 원인을 모델 파일 문제와 구분해야 한다.

## 재현 방법

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m ai.waiting_time.runtime
```

초기에는 `joblib`, `pandas`, `scikit-learn`이 설치되지 않은 것으로 확인됐다.

```bash
/Users/blaumonde/calltaxi-DA/backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

위 명령은 `No module named pip`로 실패했다.

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/.venv/bin/python -m ai.waiting_time.runtime
```

루트 `.venv`에서는 Python 3.12과 모델 artifact는 준비되어 있었지만, `joblib==1.6.0`, `pandas==3.0.5`로 requirements와 달라 runtime check가 실패했다.

## 원인

- `backend/.venv`가 최소 Python 실행환경으로만 남아 있어 `pip`가 포함되지 않았다.
- 루트 `.venv`는 분석/개발 과정에서 별도 패키지 버전이 설치되어 서비스용 `backend/requirements.txt`와 drift가 생겼다.
- sandbox 환경은 기본적으로 외부 네트워크 접근이 제한되어 PyPI 다운로드가 막혔다.

## 검토한 대안

1. **버전 mismatch를 warning만 두고 통과**
   - 장점: 기존 venv를 덜 건드린다.
   - 단점: “동일 조건 실행” 검증이라는 Phase 8 목표와 맞지 않는다.
   - 판단: 채택하지 않음.

2. **모델을 로딩하지 않고 문서만 갱신**
   - 장점: 빠르게 완료할 수 있다.
   - 단점: 실제 새 환경에서 어디가 깨지는지 확인할 수 없다.
   - 판단: 채택하지 않음.

3. **runtime checker로 Python/의존성/artifact/metadata를 분리 검증**
   - 장점: 원인이 Python, dependency, LFS artifact, metadata drift 중 어디인지 즉시 구분할 수 있다.
   - 단점: 실제 requirements 설치는 네트워크가 가능한 환경이어야 한다.
   - 판단: 채택.

## 해결 방법

- `ai.waiting_time.runtime` 모듈을 추가해 Python 3.12, `joblib/pandas/scikit-learn` pinned version, joblib artifact 존재 여부, Git LFS pointer 여부, metadata feature drift를 점검한다.
- 루트 `.env.example`에 `APP_WAITING_TIME_MODEL_PATH`, `APP_WAITING_TIME_MODEL_METADATA_PATH`를 추가해 새 환경에서 artifact 경로를 명시적으로 설정할 수 있게 했다.
- 네트워크 권한을 허용한 뒤 루트 `.venv`에 `backend/requirements.txt`를 설치해 `joblib==1.4.2`, `pandas==2.2.3`, `scikit-learn==1.9.0` 상태로 맞췄다.

## 검증 결과

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/.venv/bin/python -m ai.waiting_time.runtime
```

- Python 3.12.14 확인
- `joblib==1.4.2`, `pandas==2.2.3`, `scikit-learn==1.9.0` 확인
- `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib` 실제 artifact 확인
- metadata `target_unit=minutes`, feature 순서 일치 확인

```bash
PYTHONPATH=backend:. /Users/blaumonde/calltaxi-DA/.venv/bin/python -m ai.waiting_time.validation --output analysis/waiting_time/prediction_validation_phase4.json
```

- 임차택시 바로콜: `41.21341000519471` minutes
- 특장차 바로콜: `40.50492956696943` minutes
- conservative max: `41.21341000519471` minutes, `2473` seconds
- 출력 단위와 값 범위 검증 통과

## 남은 한계

- `backend/.venv` 자체에는 여전히 `pip`가 없으므로, 새 환경에서는 `python3.12 -m venv backend/.venv`로 재생성하거나 `ensurepip`가 가능한 Python 배포판을 사용해야 한다.
- CI 기본 테스트는 1.48GB Git LFS artifact 로딩을 매번 수행하지 않는다. 실제 artifact smoke validation은 모델 파일과 ML 의존성이 준비된 로컬/운영 검증 환경에서 별도로 실행한다.
