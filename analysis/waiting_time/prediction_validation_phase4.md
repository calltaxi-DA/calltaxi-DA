# Phase 4 Prediction 결과 검증

검증일: 2026-09-14

## 목적

통합 장애인 콜택시 대기시간 Prediction 모델이 서비스에서 사용할 수 있는 정상적인 `minutes` 단위 예상 대기시간을 반환하는지 확인한다. 검증은 `analysis/`에 export된 reviewed artifact만 사용하며, `data/processed`나 Notebook 산출물을 직접 읽지 않는다.

## Sample Input

| Feature | Value |
|---|---|
| 요청시각 | `2026-09-14T09:00:00+09:00` |
| 이용목적 | `치료` |
| 승차거리 | `12500` meters |
| 출발 | `중구 명동` |
| 목적 | `강남구 역삼동` |
| 세부이동유형 | `구 간 이동` |
| 전일 차량운행대수 | `412` |
| 날씨 | `23.5°C`, 강수 `0mm`, 풍속 `2.1m/s`, 적설 `0cm`, 악천후 `false` |
| model_group 정책 | `임차택시_바로콜`, `특장차_바로콜` 모두 예측 후 max |

## 검증 결과

| model_group | expected_minutes | unit | valid | warnings |
|---|---:|---|---|---|
| `임차택시_바로콜` | `41.21341000519471` | `minutes` | true | 없음 |
| `특장차_바로콜` | `40.50492956696943` | `minutes` | true | 없음 |

보수적 정책 기준 서비스 사용값:

- `conservative_expected_minutes`: `41.21341000519471`
- `conservative_expected_seconds`: `2473`

## Output Validation

- `Null`: 없음
- `NaN`: 없음
- 음수값: 없음
- output type: finite numeric
- output unit: `minutes`
- 130분 초과 여부: 초과하지 않음
- `out_of_training_target_range` warning 필요 여부: 필요 없음

## 기존 분석 결과와 비교

비교 기준은 reviewed artifact인 [`usage_pattern_evidence.md`](usage_pattern_evidence.md)의 바로콜 `접수→승차` 분포다.

| model_group | prediction(분) | 기존 평균(분) | 기존 중앙값(분) | 기존 75분위수(분) | 기존 90분위수(분) | 중앙값 대비 | 평균 대비 | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `임차택시_바로콜` | `41.21` | `42.45` | `28.51` | `50.28` | `87.34` | `+12.70` | `-1.24` | 중앙값~90분위 범위 |
| `특장차_바로콜` | `40.50` | `46.27` | `33.42` | `57.33` | `95.13` | `+7.08` | `-5.77` | 중앙값~90분위 범위 |

모델 metadata의 기존 성능 지표:

| Metric | Value |
|---|---:|
| reported_test_MAE | `11.105367785137439` |
| reported_test_RMSE | `15.332262378232757` |
| reported_test_R2 | `0.6010887068297474` |
| training_target_max_minutes | `130` |

이번 sample의 두 model group 예측값은 reviewed 기존 분석의 각 `접수→승차` 중앙값보다 높고 90분위수보다 낮다. 보수적 max `41.21분`도 두 baseline의 평균 또는 중앙값~90분위 범위 안에 있으므로, 이 sample에서는 기존 대기시간 분석 결과와 비교해 즉시 이상으로 볼 근거가 없다.

## 산출물

- Machine-readable report: [`prediction_validation_phase4.json`](prediction_validation_phase4.json)
- 실행 명령:

```bash
PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m ai.waiting_time.validation --output analysis/waiting_time/prediction_validation_phase4.json
```

## 남은 한계

- 단일 대표 sample 검증이므로 전체 운영 입력 공간의 성능 검증을 의미하지 않는다.
- 실제 서비스 추천 경로에서는 Backend가 최신 lookup과 주소 정규화 source를 제공해야 한다.
- CI에서는 1.4GB LFS artifact와 ML 의존성 설치 상태에 따라 실제 model smoke test를 항상 수행하지 않을 수 있다.
