# 장애인 콜택시 이용패턴 분석 근거 정리

상태: 확정 (2026-09-12)  
목적: 기존에 완료한 장애인 콜택시 이용패턴 분석 결과를 재실행하지 않고 확인해, **통합 대기시간 Prediction 모델의 입력 해석과 결과 검증에 활용할 분석 근거**를 정리한다.

## 확인한 출처

이번 Phase에서는 기존 Notebook과 저장된 output만 확인했다. 데이터 전처리, 분석 재실행, CSV/model export는 수행하지 않았다.

| 출처 | 확인 목적 |
|---|---|
| `notebooks_waiting_time/02_rental_wait_time_analysis.ipynb` | 임차택시 바로콜 이용량, 대기시간 분포, 시간대·요일·지역·이동유형별 대기시간, 취소 패턴 확인 |
| `notebooks_waiting_time/04_special_vehicle_wait_time_analysis.ipynb` | 특장차 바로콜·전일접수·심야시간 사전예약 구분, 대기시간 분포, 시간대·요일 위험 구간 확인 |
| `notebooks_lye/5-1_plan_시간대별평균대기시간.ipynb` | 전체 시간대별 평균 대기시간에서 전일접수 포함 시 왜곡되는 구간 확인 |
| `notebooks_waiting_time/05_calltaxi_wait_time_modeling.ipynb` | 바로콜 대기시간 모델링의 기본 데이터셋, target, train/validation/test 분리 기준 확인 |
| `notebooks_waiting_time/06_calltaxi_wait_time_feature_experiments.ipynb` | 수요 proxy, 장시간 대기율 proxy, 세부이동유형 피처의 성능 개선 여부와 leakage 점검 확인 |
| `notebooks_waiting_time/07_calltaxi_wait_time_hgb_modeling.ipynb` | 바로콜 통합 모델 범위, HGB 모델 해석 기준, 장시간 대기 경고 평가 기준 확인 |
| `notebooks_waiting_time/08_calltaxi_wait_time_feature_set_v2.ipynb` | 동일한 target과 split 기준을 유지한 feature set v2 설계 방향 확인 |
| `notebooks_waiting_time/corr_original.ipynb` | 원본 컬럼 기준 관계 분석, leakage 컬럼과 모델 후보 컬럼 구분 확인 |

## 분석 결과 활용 원칙

- 이 문서는 기존 분석 결과를 서비스 모델 개발에 연결하기 위한 기준 문서다.
- Notebook output에 저장된 수치와 결론만 확인하며, 결과를 새로 계산하지 않는다.
- 모델 학습용 CSV, lookup table, model 파일은 이번 Phase에서 만들지 않는다.
- `analysis/`에 실제 모델 산출물을 둘 때는 별도 export Phase에서 출처, 생성일, 입력 컬럼, target, 갱신 방법을 함께 남긴다.

## 통합 대기시간 Prediction에 활용할 핵심 분석 결과

### 1. 임차택시 바로콜 대기시간 분포

출처: `notebooks_waiting_time/02_rental_wait_time_analysis.ipynb`

기존 분석에서 임차택시 전처리 데이터는 328,875건으로 확인되었고, 바로콜 승차 대기시간 본 분석 대상은 305,729건이다.

| 구간 | 건수 | 평균(분) | 중앙값(분) | 75분위수(분) | 90분위수(분) | 95분위수(분) |
|---|---:|---:|---:|---:|---:|---:|
| 접수→배차 | 305,729 | 25.14 | 9.28 | 31.42 | 66.64 | 127.14 |
| 접수→승차 | 305,729 | 42.45 | 28.51 | 50.28 | 87.34 | 145.05 |
| 배차→승차 | 305,729 | 17.31 | 16.31 | 21.76 | 27.42 | 31.28 |

해석:

- 서비스 target인 `접수_승차_분`은 임차택시 바로콜에서 중앙값 약 28.5분, 90분위수 약 87.3분으로 확인된다.
- `배차_승차_분`은 중앙값과 평균 차이가 작아 비교적 안정적인 반면, `접수_배차_분`은 평균이 중앙값보다 크게 높아 긴 꼬리가 존재한다.
- 따라서 모델 검증에서는 평균만 보지 않고 중앙값, 75분위수, 90분위수를 함께 확인해야 한다.

모델 활용:

- `model_group = 임차택시_바로콜`은 offline evaluation segment의 baseline 분포로 사용한다.
- 예측값 검증 시 임차택시의 일반 대기시간은 `접수_승차_분` 중앙값·90분위수와 비교한다.
- `접수_배차_분`은 서비스 target이 아니라 배차 병목 설명용 KPI로 유지한다.

### 2. 특장차 접수유형별 대기시간 분리

출처: `notebooks_waiting_time/04_special_vehicle_wait_time_analysis.ipynb`

기존 분석에서 특장차 전처리 전체는 1,393,534건, 탑승완료 정상 건은 1,164,430건으로 확인되었다. 접수유형 후보별 분포는 다음과 같다.

| 접수유형 후보 | 건수 | 전체 대비 비율 |
|---|---:|---:|
| 바로콜 후보 | 1,099,084 | 78.87% |
| 전일접수 후보 | 48,931 | 3.51% |
| 심야시간 사전예약 후보 | 116 | 0.01% |
| 기타 예약성/미분류 | 16,299 | 1.17% |
| 취소 전체 | 228,987 | 16.43% |

특장차 바로콜 후보 대기시간은 다음처럼 확인되었다.

| 구간 | 건수 | 평균(분) | 중앙값(분) | 75분위수(분) | 90분위수(분) | 95분위수(분) |
|---|---:|---:|---:|---:|---:|---:|
| 접수→배차 | 1,099,084 | 27.47 | 11.98 | 36.92 | 72.12 | 107.83 |
| 접수→승차 | 1,099,084 | 46.27 | 33.42 | 57.33 | 95.13 | 133.94 |
| 배차→승차 | 1,099,084 | 18.80 | 17.85 | 23.56 | 29.42 | 33.46 |

해석:

- 특장차 바로콜도 임차택시처럼 `접수→배차`에서 긴 꼬리가 나타난다.
- 서비스 target인 `접수_승차_분` 기준으로 특장차 바로콜은 중앙값 약 33.4분, 90분위수 약 95.1분이다.
- 전일접수와 심야시간 사전예약은 `접수→승차`를 바로콜 대기시간처럼 해석하면 안 되므로 1차 통합 서비스 Prediction 모델에서 제외한다.

모델 활용:

- `model_group = 특장차_바로콜`은 offline evaluation segment의 baseline 분포로 사용한다.
- 특장차 바로콜은 임차택시 바로콜과 같은 통합 모델에 포함하되, production feature에는 offline 바로콜 판정값인 `model_group`을 직접 넣지 않고 inference 시점에 알 수 있는 `차량구분`을 사용한다.
- 전일접수·심야시간 사전예약은 예정시각 기준 Prediction을 설계하는 후속 Phase로 넘긴다.

### 3. 시간대별 이용량과 대기 위험

출처:

- `notebooks_waiting_time/04_special_vehicle_wait_time_analysis.ipynb`
- `notebooks_lye/5-1_plan_시간대별평균대기시간.ipynb`

특장차 바로콜 분석에서는 이용량이 많은 시간대와 장시간 대기 위험이 높은 시간대가 다르게 나타났다.

- 낮 10~15시: 이용량은 많지만 대기시간은 비교적 안정적
- 새벽 02~06시: 이용량은 적지만 장시간 대기 위험이 큼
- 04시 전후: 여러 요일에서 90분위수가 높아 위험 안내 필요
- 금요일 오후·저녁, 일요일 저녁: 추가 확인이 필요한 보조 위험 구간

또한 전체 시간대별 평균 분석에서는 전일접수 후보를 제외하지 않으면 07시, 08시, 10시에 `접수→배차` 평균이 크게 왜곡되는 것으로 확인되었다.

| 접수시간대 | 전체 포함 평균(분) | 전일접수 제외 평균(분) | 포함/제외 배수 |
|---:|---:|---:|---:|
| 07시 | 335.89 | 145.39 | 2.3 |
| 08시 | 284.62 | 43.14 | 6.6 |
| 10시 | 177.96 | 20.92 | 8.5 |

해석:

- 전일접수를 섞으면 특정 시간대가 비정상적으로 긴 대기시간처럼 보인다.
- 1차 바로콜 모델은 전일접수·심야 사전예약을 제외한 바로콜 데이터만 사용해야 한다.
- 시간대 feature는 모델 입력과 결과 검증 모두에서 중요하다.

모델 활용:

- `hour`, `is_night`, `is_commute` 같은 시간대 feature를 유지한다.
- 새벽 02~06시는 제거하기보다 위험 시간대 flag 또는 별도 검증 segment로 관리한다.
- 시간대별 예측값 분포가 기존 분석의 중앙값·90분위수와 크게 어긋나는지 확인한다.

### 4. 요일별 이용패턴과 검증 기준

출처: `notebooks_waiting_time/04_special_vehicle_wait_time_analysis.ipynb`

특장차 바로콜의 요일별 `접수_승차_분`은 다음처럼 확인되었다.

| 요일 | 승차완료건수 | 접수→승차 중앙값(분) | 접수→승차 90분위수(분) |
|---|---:|---:|---:|
| 월 | 187,531 | 31.60 | 94.91 |
| 화 | 184,885 | 33.28 | 95.24 |
| 수 | 190,139 | 33.84 | 98.87 |
| 목 | 180,334 | 32.41 | 95.08 |
| 금 | 183,115 | 33.60 | 100.78 |
| 토 | 91,178 | 36.29 | 88.38 |
| 일 | 81,902 | 34.76 | 84.34 |

해석:

- 평일은 건수가 많고, 금요일은 90분위수가 상대적으로 높다.
- 주말은 건수가 적지만 중앙값이 반드시 낮지는 않다.
- 요일은 단독 핵심 설명 변수라기보다 시간대·차량유형·지역과 함께 검증해야 한다.

모델 활용:

- `dayofweek`, `is_weekend`를 feature 후보로 유지한다.
- 모델 검증 리포트에는 요일별 MAE/Median AE와 예측 분포를 포함한다.

### 5. 취소 패턴은 target 학습과 분리

출처: `notebooks_waiting_time/02_rental_wait_time_analysis.ipynb`

임차택시 바로콜 취소는 16,183건으로 확인되었다. 접수 후 취소 누적 비율은 다음과 같다.

| 기준 | 누적 취소건수 | 누적 취소비율 |
|---|---:|---:|
| 10분 이내 | 5,853 | 36.17% |
| 20분 이내 | 8,889 | 54.93% |
| 30분 이내 | 10,715 | 66.21% |
| 60분 이내 | 13,350 | 82.49% |
| 120분 이내 | 14,362 | 88.75% |
| 180분 이내 | 16,080 | 99.36% |

해석:

- 취소는 장시간 대기 후에만 발생하는 것이 아니라 접수 초기에도 많이 발생한다.
- 취소 건은 `접수_승차_분` target을 만들 수 없으므로 1차 승차완료 대기시간 모델 학습에 섞지 않는다.
- 취소율은 후속 운영 분석 또는 취소 위험 모델에서 별도로 다룬다.

모델 활용:

- 1차 대기시간 모델 학습 대상은 승차완료 바로콜로 제한한다.
- 취소율은 결과 해석 보조 지표 또는 후속 모델 후보로 둔다.

### 6. 이동유형과 지역 수요 proxy

출처:

- `notebooks_waiting_time/06_calltaxi_wait_time_feature_experiments.ipynb`
- `notebooks_waiting_time/corr_original.ipynb`

기존 실험에서는 수요 proxy와 세부이동유형이 성능 개선에 도움이 되는 것으로 확인되었다.

| 모델 | MAE | RMSE | R² | 장시간 대기 Recall | 장시간 대기 F1 |
|---|---:|---:|---:|---:|---:|
| RF 기본 | 16.4839 | 25.4864 | 0.4988 | 0.3338 | 0.4665 |
| RF + 수요 proxy | 16.0644 | 25.2027 | 0.5099 | 0.3383 | 0.4712 |
| RF + 수요 proxy + 장시간 대기율 proxy | 15.8448 | 24.7221 | 0.5284 | 0.3500 | 0.4842 |
| RF + 수요 proxy + 장시간 대기율 proxy + 세부이동유형 | 15.7936 | 24.6245 | 0.5321 | 0.3541 | 0.4886 |

해석:

- 직전 30분/60분 접수량, 차량·호출유형별 직전 60분 접수량, 출발구별 직전 60분 접수량은 대기시간 예측에 유의미한 정보를 제공한다.
- 출발구·시간대별 과거 장시간 대기율도 도움이 되지만, validation/test target을 섞으면 leakage가 발생할 수 있으므로 train 기준 통계 또는 out-of-fold 방식만 허용한다.
- `세부이동유형`은 서비스 요청 시 출발지·목적지로 계산 가능하고, 서울 내부/외부 이동 부담을 요약하므로 1차 feature 후보로 유지한다.

모델 활용:

- `request_count_prev_30m`, `request_count_prev_60m`, `model_group_request_count_prev_60m`, `origin_gu_request_count_prev_60m`는 현재 서비스 아키텍처에서 실시간 전체 접수 stream/API/DB가 없으므로 1차 production feature set에서는 제외한다.
- 위 rolling 수요량 feature는 기존 실험에서 성능 개선 근거로만 유지하고, 실시간 접수 데이터 소스가 확정되는 후속 Phase에서 production feature 편입 여부를 다시 판단한다.
- `origin_gu_hour_long_wait_rate`, `model_group_hour_long_wait_rate`는 train 기준 통계 또는 out-of-fold 방식으로만 생성한다. 이 값도 production에서 사용할 경우 학습 시점에 저장된 lookup table을 `analysis/`에 export해야 하며, validation/test target이나 실시간 이후 결과를 사용해 계산하지 않는다.
- `세부이동유형`은 출발지·목적지로 inference 시점에 계산 가능하므로 production feature 후보로 유지한다.

### 6-1. Feature별 train/inference 생성 가능성

현재 기준으로 production feature 여부는 “서비스 요청 시점에 생성 가능한가”를 우선한다.

| feature | train 생성 가능 | inference 생성 가능 | 데이터 출처/조건 | 1차 production feature 여부 |
|---|---|---|---|---|
| `차량구분` | 가능 | 가능 | 사용자가 선택하거나 서비스가 경로 후보별로 지정 | 포함 |
| `hour`, `dayofweek`, `month`, `is_weekend`, `is_night`, `is_commute` | 가능 | 가능 | 요청시각 또는 접수시각 | 포함 |
| `출발구`, `목적구` | 가능 | 가능 | 장소검색/좌표→행정구 매핑 | 포함 |
| `세부이동유형` | 가능 | 가능 | 출발구·목적구 기준 생성 | 포함 |
| `request_count_prev_30m` | 가능 | 현재 불가 | 최근 30분 전체 장애인콜택시 접수 stream/API/DB 필요 | 제외 |
| `request_count_prev_60m` | 가능 | 현재 불가 | 최근 60분 전체 장애인콜택시 접수 stream/API/DB 필요 | 제외 |
| `model_group_request_count_prev_60m` | 가능 | 현재 불가 | 차량·호출유형별 최근 접수 stream/API/DB 필요 | 제외 |
| `origin_gu_request_count_prev_60m` | 가능 | 현재 불가 | 출발구별 최근 접수 stream/API/DB 필요 | 제외 |
| `origin_gu_hour_long_wait_rate` | 가능 | lookup 방식만 가능 | train 기준 집계 후 `analysis/` export 필요 | 보류 |
| `model_group_hour_long_wait_rate` | 가능 | lookup 방식만 가능 | train 기준 집계 후 `analysis/` export 필요. 단 `model_group`은 evaluation segment 기준이므로 production에서는 `차량구분` 기반 lookup으로 재정의 필요 | 보류 |
| `model_group` | 가능 | 기존 offline 정의는 불가 | offline 바로콜 분류에 사후 결과가 포함될 수 있음 | feature 제외, evaluation segment 전용 |

따라서 1차 production feature set은 `차량구분`, 시간 변수, 출발·목적 위치, 세부이동유형처럼 inference 시점에 생성 가능한 값으로 제한한다. rolling 수요량 feature는 실시간 수요 데이터 소스가 확정될 때까지 offline 실험 결과로만 보관한다.

### 7. 원본 컬럼 기준 leakage 방지

출처: `notebooks_waiting_time/corr_original.ipynb`

기존 원본 컬럼 관계 분석은 다음 컬럼을 모델 입력에서 제외해야 한다고 정리했다.

| 구분 | 컬럼 | 이유 |
|---|---|---|
| target/leakage | `접수_승차_분` | 예측 대상 자체 |
| leakage | `접수_배차_분`, `배차_승차_분` | 접수 이후 배차·승차 결과 |
| leakage | `접수_취소_분`, `배차_취소_분` | 취소 결과 |
| leakage | `예정_배차_분`, `예정_승차_분` | 예약/전일접수용 사후 결과 |
| 비추천 | `요금` | 실제 운행 이후 확정될 가능성이 큼 |
| 중복 | `접수시간대`, `접수시간대_HH`, `접수시` | `hour`와 중복 |

모델 활용:

- 상관관계가 높아도 사후 결과 컬럼은 feature로 사용하지 않는다.
- 원본 컬럼 기반 1차 production 후보는 `차량구분`, `출발구`, `목적구`, `세부이동유형`, `이용목적`, `장애유형`, `hour`, `dayofweek`, `month` 정도로 제한한다.
- 기존 Notebook의 `model_group`은 offline 분류와 평가 segment에는 사용할 수 있지만, production feature로는 사용하지 않는다. 1차 모델은 바로콜만 대상으로 하므로 서비스 입력 feature는 `model_group` 대신 inference 시점에 안전하게 알 수 있는 `차량구분`을 사용한다.
- 실제 `승차거리_km`는 서비스 요청 시점에 확정되지 않으므로, 사용할 경우 TMAP 등 경로 API 기반 예상거리로 대체해야 한다.

## Prediction 모델 검증에 사용할 기준

후속 모델 학습/평가 Phase에서는 기존 이용패턴 분석을 다음 기준으로 활용한다.

| 검증 항목 | 확인 내용 |
|---|---|
| model_group별 분포 | offline evaluation segment인 임차택시_바로콜, 특장차_바로콜의 `접수_승차_분` 중앙값·90분위수가 기존 분석과 크게 어긋나지 않는지 확인 |
| 시간대별 분포 | 새벽 02~06시, 04시 전후, 출퇴근 시간대의 오차와 예측 분포를 별도로 확인 |
| 요일별 분포 | 금요일, 주말 구간의 예측 오차를 별도로 확인 |
| 이동유형별 분포 | 구 내 이동, 구 간 이동, 서울→서울 외, 서울 외→서울을 분리해 오차 확인 |
| 장시간 대기 위험 | train set의 `접수_승차_분` 90분위수를 기준으로 Precision, Recall, F1을 함께 확인 |
| leakage 점검 | validation/test target을 사용해 만든 집계 feature가 없는지 확인 |
| 취소 분리 | 취소 건이 승차완료 대기시간 target 학습에 섞이지 않았는지 확인 |

## 이번 Phase에서 선정한 활용 대상

통합 대기시간 Prediction 모델의 입력 해석 또는 검증에 사용할 분석 결과는 다음으로 확정한다.

1. offline evaluation segment(`model_group`)별 `접수_승차_분` 분포
2. 시간대별 `접수_승차_분` 및 `접수_배차_분` 분포
3. 요일별 `접수_승차_분` 분포
4. 세부이동유형별 대기시간 차이
5. 직전 수요량 proxy의 offline 성능 개선 근거. 단, 실시간 접수 데이터 소스가 없으므로 1차 production feature에서는 제외
6. train 기준 장시간 대기율 proxy의 성능 개선 근거와 leakage 점검 결과. 단, production 사용은 `analysis/` lookup export와 inference-safe key 재정의 이후 판단
7. 취소 건은 target 학습에서 제외하고 운영 분석 보조 지표로만 사용하는 기준

## 다음 Phase가 해야 할 일

- 위 기준을 바탕으로 실제 학습용 바로콜 dataset을 export한다.
- export 시 row count, target 결측/음수 제외 건수, `model_group`별 건수, 시간대별 건수, 취소 제외 건수를 함께 기록한다.
- `접수_승차_분 ≈ 접수_배차_분 + 배차_승차_분` 관계를 검증하고 오차/결측 건수를 기록한다.
- 모델 학습 Phase에서는 전체 MAE만 보지 않고 model_group·시간대·요일·이동유형별 성능표를 함께 남긴다.
- 새벽 위험 시간대는 삭제 대상이 아니라 별도 안내 또는 segment 검증 대상으로 유지한다.
- production feature set 확정 전, 각 feature가 inference 시점에 생성 가능한지와 데이터 출처가 무엇인지 다시 검증한다.
