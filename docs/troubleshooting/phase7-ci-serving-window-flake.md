# Phase 7 CI serving window flake

## 문제 상황

PR #72에서 최신 `dev`를 병합한 뒤 GitHub Actions의 `Backend and AI tests`와 `Reviewed data quality`가 모두 실패했다. 로컬 Python 3.11에서는 같은 테스트가 통과했지만, CI가 실행된 한국시간 새벽 02시대에는 `test_recommendations_production_provider_calls_waiting_prediction_when_sources_are_configured`가 실패했다.

## 영향

장애인 콜택시 Prediction production-provider 테스트가 현재 시각에 의존해 새벽 시간대에는 Prediction estimator 호출 경로를 검증하지 못했다. 실제 서비스 로직은 serving window 밖 요청을 unavailable로 처리하는 정상 동작이지만, 테스트는 항상 모델 호출이 발생한다고 가정하고 있었다.

## 재현 방법

1. Python 3.12 환경에서 의존성을 설치한다.
2. 한국시간 02:00~06:59 사이에 다음 명령을 실행한다.

```bash
PYTHONPATH=backend:. python -m pytest backend/tests/test_recommendation_routes.py
```

3. `seen_model_groups`가 빈 리스트로 남고, 응답의 excluded route reason이 `02:00~06:59 시간대는 일반구간 대기시간 모델 serving 대상이 아닙니다`가 된다.

## 원인

테스트가 lookup fixture를 `datetime.now(Asia/Seoul)` 기준으로 만들면서도 Backend provider의 `current_time_provider` 역시 실제 현재 시각을 사용했다. 이 때문에 CI 실행 시간이 일반구간 모델 serving window 밖이면 feature builder 단계에서 fail-close되어 fake estimator까지 도달하지 않았다.

## 검토한 대안

- 운영 코드에 테스트 전용 clock 설정을 추가한다.
- 테스트에서 FastAPI dependency를 더 깊게 override한다.
- 해당 테스트에서 `app.api.recommendation.datetime.now()`만 deterministic한 Asia/Seoul 시각으로 고정한다.

운영 계약을 바꾸지 않고 production-provider wiring만 검증하면 되므로, 테스트 내부에서 recommendation 모듈의 datetime만 고정하는 방식을 선택했다.

## 해결 방법

테스트 요청 기준 시각을 `2026-09-13T09:15:00+09:00`으로 고정하고, `recommendation_module.datetime.now()`도 같은 시각을 반환하도록 monkeypatch했다. 이 시각은 serving window 안에 있으므로 CI 실행 시간과 무관하게 Prediction estimator 호출 경로를 검증한다.

## 검증 결과

Python 3.12 임시 venv에서 CI 명령을 재실행했다.

```bash
PYTHONPATH=backend:. .venv-ci312/bin/python -m pytest backend/tests ai/tests
PYTHONPATH=backend:. .venv-ci312/bin/python -m pytest src/tests backend/tests ai/tests
python3 -m src.data_quality --check-report docs/validation/phase9-audit-2026-09-13.json
```

- `backend/tests ai/tests`: 260개 통과
- `src/tests backend/tests ai/tests`: 281개 통과
- data quality report: errors 없음

## 남은 한계

테스트는 fake estimator와 fake TMAP client를 사용한다. 실제 joblib artifact, 운영 lookup 파일, 외부 TMAP 호출을 포함한 smoke test는 실행환경 및 모델 파일 관리 Phase에서 별도로 검증해야 한다.
