# 장애인 콜택시 대기시간 Prediction 실행환경

## 목적

새로운 개발환경에서도 통합 장애인 콜택시 대기시간 Prediction 모델을 같은 조건으로 실행하기 위한 기준을 고정한다.

## 실행 기준

| 항목 | 기준 |
|---|---|
| Python | 3.12.x |
| 의존성 파일 | `backend/requirements.txt` |
| 모델 artifact | `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib` |
| 모델 metadata | `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final_metadata.json` |
| 모델 alias | `rf_wait_time_v2_prev_day_weather_final` |
| artifact 저장 방식 | Git LFS |
| 예측 단위 | minutes |

모델 추론 의존성은 Backend 서비스용 의존성에 포함한다.

- `joblib==1.4.2`
- `pandas==2.2.3`
- `scikit-learn==1.9.0`

## 환경 변수

기본값을 그대로 쓰는 경우 환경 변수를 비워도 된다. 다른 위치에 모델 파일을 두는 로컬 환경에서는 루트 `.env`에 아래 값을 설정한다.

```bash
APP_WAITING_TIME_MODEL_PATH=analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib
APP_WAITING_TIME_MODEL_METADATA_PATH=analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final_metadata.json
```

상대경로는 저장소 루트 기준으로 해석한다. 절대경로도 사용할 수 있다.
`ai.waiting_time` Adapter는 `python-dotenv`가 설치된 환경에서 루트 `.env`를 선택적으로 읽고, 이미 export된 OS 환경변수는 덮어쓰지 않는다.

## 새 개발환경 준비 절차

```bash
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
git lfs install
git lfs pull --include="analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib"
```

## 런타임 점검

아래 명령은 Python 버전, 추론 의존성 버전, 모델 artifact 경로, Git LFS pointer 여부, metadata feature drift를 확인한다.

```bash
PYTHONPATH=backend:. backend/.venv/bin/python -m ai.waiting_time.runtime
```

성공 조건은 다음과 같다.

- Python 3.12.x
- `backend/requirements.txt`와 같은 ML 추론 의존성 버전
- 모델 artifact가 존재하고 Git LFS pointer가 아님
- metadata의 `target_unit`이 `minutes`
- metadata feature 순서가 AI Adapter의 `MODEL_FEATURE_COLUMNS`와 일치

## 실제 모델 smoke validation

runtime check가 통과한 뒤 실제 artifact 추론값까지 확인하려면 아래 명령을 실행한다.

```bash
PYTHONPATH=backend:. backend/.venv/bin/python -m ai.waiting_time.validation --output analysis/waiting_time/prediction_validation_phase4.json
```

이 명령은 임차택시 바로콜과 특장차 바로콜 sample을 모두 예측하고, 두 값 중 큰 값을 conservative expected minutes/seconds로 기록한다.

## 실패 시 해석

- `model artifact is a Git LFS pointer`: `git lfs pull --include="analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib"`를 실행해야 한다.
- `dependency:* is not installed` 또는 버전 mismatch: `backend/.venv/bin/python -m pip install -r backend/requirements.txt`를 다시 실행한다.
- `metadata feature list does not match adapter feature columns`: 모델 metadata와 `ai/waiting_time/estimator.py`의 feature 계약이 drift된 상태이므로, 임의로 실행하지 말고 artifact/adapter 중 어느 쪽이 최신 계약인지 확인한다.
- Python version mismatch: CI와 같은 Python 3.12 환경으로 재생성한다.

## 범위 밖

- 모델 재학습
- joblib artifact 교체
- feature set 변경
- Backend 추천 정렬 변경
- Frontend 표시 변경
