# ADR 0006: 장애인 콜택시 대기시간 Prediction 연동 계약

- 상태: 결정됨 (2026-09-13)
- 관련: [ADR 0002](./0002-ai-as-adapter-only.md), [ADR 0004](./0004-route-metric-availability-and-recommendation-contract.md), [`analysis/waiting_time/rf_v2_prev_day_weather_serving_feature_mapping.md`](../../analysis/waiting_time/rf_v2_prev_day_weather_serving_feature_mapping.md)

## 배경

`analysis/waiting_time/`에 검토 완료된 통합 장애인 콜택시 대기시간 Prediction 모델 산출물이 export되었다. Backend는 콜택시 총 소요시간을 `예측 대기시간 + 차량 이동시간`으로 계산해야 하지만, 기존 AI Adapter는 임시로 `hour_of_day` 하나만 받는 placeholder였다.

최종 모델은 시간대뿐 아니라 출발·목적 행정동, TMAP 차량거리, 이용목적, 차량유형 proxy, 전일 차량운행 대수, 날씨 feature를 요구한다. 따라서 Backend가 어떤 입력을 만들어 AI Adapter에 넘기고, 실패 시 어떤 방식으로 경로를 unavailable 처리할지 계약을 먼저 확정한다.

## 결정

1. **AI Adapter 입력은 `WaitingTimePredictionInput` dataclass로 정의한다.** HTTP/Pydantic 모델이 아니라 순수 Python 타입이며, `ai/`는 FastAPI나 Backend schema를 import하지 않는다.
2. **예측 목표값은 `접수→승차 대기시간`이고 단위는 분(minutes)이다.** Backend `RouteResult.total_time_seconds`에 반영할 때만 초(seconds)로 변환한다.
3. **모델 feature 이름은 학습 feature와 동일하게 유지한다.** Adapter의 `to_model_features()`가 다음 feature dict를 만든다.
   - `hour`, `month`, `dayofweek`
   - `이용목적`
   - `승차거리`
   - `출발구`, `출발동`, `목적구`, `목적동`
   - `세부이동유형`
   - `model_group`
   - `vehicle_operation_count_prev_day`
   - `temperature_c`, `precipitation_mm`, `wind_speed_ms`, `snow_depth_cm`, `is_bad_weather`
4. **Backend는 Prediction 호출 전에 serving feature를 모두 준비해야 한다.**
   - 검색/요청 시각은 timezone-aware datetime이어야 하며, Adapter가 Asia/Seoul 기준으로 정규화한 뒤 `hour`, `month`, `dayofweek`를 생성한다.
   - `승차거리`는 TMAP 차량 경로 거리이며 단위는 미터다. `승차거리_km`로 변환하지 않는다.
   - 출발·목적 구/동은 Kakao metadata 또는 reverse geocoding으로 정규화한다.
   - `세부이동유형`은 Backend가 구 기준으로 파생한다.
   - 전일 차량운행 대수와 날씨는 서비스에서 승인된 lookup/API에서 가져오며, `data/processed` CSV를 직접 읽지 않는다.
5. **`model_group`은 통합 콜택시 transport 안에서 모델 feature로만 사용한다.** 실제 사용자-facing transport type은 계속 `calltaxi`다. 차량유형이 확정되지 않은 MVP에서는 `임차택시_바로콜`, `특장차_바로콜`을 모두 예측하고 보수적으로 더 큰 값을 사용하는 정책을 유지한다.
6. **02:00~06:59는 일반구간 모델 serving 대상에서 제외한다.** 이 시간대에는 fallback 값을 만들지 않고 콜택시 대기시간 예측을 unavailable 처리한다.
7. **예측 오류는 숫자 대체 없이 경로 unavailable로 연결한다.** 모델 미연결, feature 누락, 미지원 category, NaN/inf/음수 예측은 `calltaxi` route의 `unavailable_reason`으로 설명한다.
8. **Phase 0에서는 실제 모델 artifact 로딩을 구현하지 않는다.** `estimate_waiting_minutes_for_input()`은 계약만 검증하고 `NotImplementedError`를 유지한다. 실제 joblib 로딩, lookup 연결, Backend orchestration 순서 변경은 후속 AI 연결 Phase에서 구현한다.

## Backend 호출 순서

후속 연결 Phase의 정상 흐름은 아래 순서를 따른다.

```text
RouteRequest 수신
→ TMAP 차량 경로 계산으로 vehicle_distance_meters 확보
→ 주소 정규화로 출발/목적 구·동 확보
→ 요청 시각, 이용목적, 세부이동유형, 전일 차량운행, 날씨 feature 생성
→ ai.waiting_time.estimate_waiting_minutes_for_input(...)
→ expected_minutes * 60을 차량 이동시간에 더해 calltaxi total_time_seconds 생성
```

현재 `BackendRecommendationRouteProvider`는 아직 기존 `hour_of_day` 기반 placeholder를 호출한다. 이는 모델 미연결 상태를 명시적으로 유지하기 위한 임시 경계이며, 실제 artifact 호출 Phase에서 위 순서로 변경한다.

## 영향

- `ai/waiting_time/estimator.py`에 Prediction 입력 dataclass와 학습 feature 변환 규칙이 추가된다.
- 기존 `estimate_waiting_minutes(hour_of_day)`는 Backend placeholder 호환을 위해 유지하되, 계속 `NotImplementedError`를 발생시킨다.
- `frontend/`는 이 계약을 직접 사용하지 않는다. 필요한 입력 UI(예: 이용목적 선택)는 후속 Frontend Phase에서 Backend API 계약 변경과 함께 진행한다.
- `analysis/`의 joblib·metadata·serving feature mapping은 참조 대상이며, Phase 0에서는 모델 파일을 수정하지 않는다.

## 남은 작업

- Backend 추천 요청/경로 provider가 `WaitingTimePredictionInput`을 만들 수 있도록 API 입력과 orchestration 순서를 확장한다.
- 전일 차량운행 lookup과 시간별 날씨 lookup/API를 서비스용 `analysis/` export 또는 운영 provider로 연결한다.
- AI Adapter가 `analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib`을 lazy-load하고 예측값 검증·경고를 반환하도록 구현한다.
- 예측값 130분 초과 경고, 양쪽 `model_group` 예측 중 일부 실패 정책, lookup stale 정책을 통합 테스트로 고정한다.
