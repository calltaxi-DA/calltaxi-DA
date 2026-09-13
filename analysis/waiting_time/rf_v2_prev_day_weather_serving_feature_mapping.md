# RF v2 prev-day weather model serving feature mapping

Status: reviewed serving contract (2026-09-13)

Model artifact under review:

```text
notebooks_waiting_time/outputs/models/rf_wait_time_v2_prev_day_weather_final.joblib
notebooks_waiting_time/outputs/models/rf_wait_time_v2_prev_day_weather_final_metadata.json
```

The model predicts `target_min`, interpreted as request-to-boarding waiting time in minutes.
Backend route responses use seconds, so the AI Adapter must convert `expected_minutes * 60`
before contributing to `RouteResult.total_time_seconds`.

## Serving Feature Map

| Feature | Type | Serving source | Status | Notes |
|---|---|---|---|---|
| `hour` | numeric | Request/search timestamp in backend | Available with backend derivation | Must reject or mark unavailable for 02:00-06:59 because the model training excluded hours 2-6. |
| `month` | numeric | Request/search timestamp in backend | Available with backend derivation | Use local Seoul service time. |
| `dayofweek` | numeric | Request/search timestamp in backend | Gate confirmed | Use pandas `Timestamp.dayofweek` convention from training: Monday=0 through Sunday=6, in local Seoul service time. |
| `출발구` | categorical | Kakao address metadata first, coordinate reverse-geocoding fallback | Gate 3 confirmed | Backend owns final normalization. Prediction unavailable if normalization fails. |
| `출발동` | categorical | Kakao address metadata first, coordinate reverse-geocoding fallback | Gate 3 confirmed | Backend owns final normalization. Prediction unavailable if normalization fails. |
| `목적구` | categorical | Kakao address metadata first, coordinate reverse-geocoding fallback | Gate 3 confirmed | Backend owns final normalization. Prediction unavailable if normalization fails. |
| `목적동` | categorical | Kakao address metadata first, coordinate reverse-geocoding fallback | Gate 3 confirmed | Backend owns final normalization. Prediction unavailable if normalization fails. |
| `승차거리` | numeric | TMAP vehicle-route distance between origin and destination | Gate confirmed | Training model input uses the original `승차거리` column, not `승차거리_km`. Historical preprocessing derived `승차거리_km = 승차거리 / 1000`, so serving must pass TMAP distance in meters with no km conversion. |
| `세부이동유형` | categorical | Backend-derived from Seoul-25 membership of normalized origin/destination districts | Gate 3 confirmed | Supported labels: `구 내 이동`, `구 간 이동`, `서울→서울 외`, `서울 외→서울`. `서울 외↔서울 외` is not in the trained encoder and must be unavailable. |
| `model_group` | categorical | Backend/AI evaluates both trained calltaxi groups and uses the conservative maximum | Gate 1 confirmed | Trained category values are exactly `임차택시_바로콜` and `특장차_바로콜`. User-facing transport type remains `calltaxi`; final prediction is `max(임차택시_바로콜, 특장차_바로콜)`. |
| `이용목적` | categorical | User-selected calltaxi purpose mapped to a supported model category | Gate 2 confirmed | MVP UI exposes only `기타`, `귀가`, `치료`, `재활`, `통학/출근`, `종교`. Backend/AI must not invent a default or reservation category. |
| `vehicle_operation_count_prev_day` | numeric | Daily refreshed calltaxi operation-count lookup | Gate 4 confirmed | Request date D uses actual operation count on D-1. Service code must not read the 2025 training CSV directly. Missing D-1 value makes prediction unavailable. |
| `temperature_c` | numeric | Official hourly Seoul weather lookup/API | Gate 5 confirmed | Current/immediate-call MVP supports observed weather only. Missing hourly observation makes prediction unavailable. |
| `precipitation_mm` | numeric | Official hourly Seoul weather lookup/API | Gate 5 confirmed | No zero-fill, stale-value reuse, or climatology fallback in MVP. |
| `wind_speed_ms` | numeric | Official hourly Seoul weather lookup/API | Gate 5 confirmed | Same weather source as above. |
| `snow_depth_cm` | numeric | Official hourly Seoul weather lookup/API | Gate 5 confirmed | Same weather source as above. |
| `is_bad_weather` | numeric | Backend feature builder derives from weather observation using training rule | Gate 5 confirmed | `is_rain OR is_snow OR is_cold_wave_like OR is_strong_wind`. Snow derivation needs `new_snow_3h_cm` as well as `snow_depth_cm`. |

## Current Service Contract Gaps

- `RouteRequest` and `RecommendationRequest` currently provide only `origin`, `destination`,
  selected transport types, and recommendation priorities. They do not carry `이용목적`,
  `model_group`, or a planned request datetime.
- `Location.address` is optional free text. It is not enough by itself to guarantee `구` and `동`
  feature creation.
- `BackendRecommendationRouteProvider` currently calls the waiting-time adapter with only
  `hour_of_day`, so the adapter contract must expand before this model can be connected.
- TMAP distance is available in the calltaxi route flow, but current orchestration calls waiting-time
  estimation before TMAP route calculation. This order must change because `승차거리` is served from
  TMAP vehicle-route distance in meters.

## Confirmed Serving Policies

### Gate 1: `model_group`

- User-facing transport type remains `calltaxi`.
- Backend/AI evaluates both supported trained `model_group` values:
  - `임차택시_바로콜`
  - `특장차_바로콜`
- Final waiting-time prediction is the longer of the two predictions.
- Rationale: conservative MVP policy to reduce underestimation when the actual dispatched vehicle
  group is unknown.
- Response warnings must state that the actual dispatched vehicle group is unknown and that the
  conservative maximum of the two supported vehicle-group predictions was used.
- If one vehicle-group prediction fails, the response must not silently hide it. Serving should either
  mark the calltaxi route unavailable or return the successful prediction with an explicit warning,
  depending on the final error policy chosen during adapter implementation.
- If both vehicle-group predictions fail, `calltaxi` must be returned as `unavailable`.

### Gate 2: `이용목적`

- `calltaxi` prediction requires a user-selected purpose.
- Frontend exposes a dropdown only for the MVP-supported purpose values:
  - `기타`
  - `귀가`
  - `치료`
  - `재활`
  - `통학/출근`
  - `종교`
- The model input value is exactly the selected supported value:

| UI value | Model input `이용목적` |
|---|---|
| `기타` | `기타` |
| `귀가` | `귀가` |
| `치료` | `치료` |
| `재활` | `재활` |
| `통학/출근` | `통학/출근` |
| `종교` | `종교` |

- Backend/AI does not create arbitrary defaults.
- Reservation categories are not generated in the MVP because the request contract does not separately
  capture reservation status. If a future UI captures reservation semantics, the mapping must be
  revisited.
- Rare or operationally ambiguous training categories are not directly exposed in the MVP:
  `공항티켓`, `쇼핑`, `심야예약`, `업무`, `예약광역`, `예약귀가`, `예약기타`, `예약재활`,
  `예약치료`, `예약통학/출근`, `치료광역`.
- Unsupported submitted values must make prediction unavailable rather than being silently coerced.

### Gate 3: Location Normalization And `세부이동유형`

- Frontend does not submit `세부이동유형` directly.
- Frontend may submit Kakao place/address metadata, but Backend owns final feature normalization.
- Backend resolves `출발구`, `출발동`, `목적구`, and `목적동` with this priority:
  1. Kakao address metadata from the selected place.
  2. Coordinate-based reverse geocoding fallback when metadata is missing or incomplete.
- If any required district/dong value cannot be normalized, calltaxi prediction is unavailable.
- `세부이동유형` is derived by Backend from normalized districts using the training rule:

| Rule | `세부이동유형` |
|---|---|
| origin district in Seoul 25, destination district in Seoul 25, same district | `구 내 이동` |
| origin district in Seoul 25, destination district in Seoul 25, different district | `구 간 이동` |
| origin district in Seoul 25, destination district outside Seoul 25 | `서울→서울 외` |
| origin district outside Seoul 25, destination district in Seoul 25 | `서울 외→서울` |
| origin district outside Seoul 25, destination district outside Seoul 25 | unavailable |

- The trained encoder does not include `서울 외↔서울 외`, so Seoul-outside to Seoul-outside trips
  must not be sent to the model.

### Gate 4: `vehicle_operation_count_prev_day`

- Source: daily refreshed calltaxi operation-count lookup.
- Feature value for request date D is the actual 장애인콜택시 operation count on D-1.
- Training provenance: the model was trained from
  `data/processed/서울시설공단_장애인콜택시 일별이용현황_20251231.csv`, using columns:
  - `기준일`
  - `차량운행`
- Training construction shifted the daily table by one day so that request date D receives D-1
  `차량운행`.
- Service code must not read the historical 2025 training CSV directly.
- If the D-1 operation count is unavailable, calltaxi prediction is unavailable.
- Do not silently use stale, fabricated, or last-known operation-count values.
- Median fallback is not part of the MVP serving policy. If introduced later, the exact fallback value,
  eligibility condition, and user-facing warning must be recorded in metadata and this serving contract.

### Gate 5: Weather Features

- Source: official hourly Seoul weather lookup/API.
- MVP serving scope is current/immediate call prediction with observed hourly weather.
- Future request times require a separate forecast source and are not supported by this MVP policy.
- Service code must not read the historical 2025 training weather CSV directly.
- Required model weather features:
  - `temperature_c`
  - `precipitation_mm`
  - `wind_speed_ms`
  - `snow_depth_cm`
  - `is_bad_weather`
- `is_bad_weather` must be derived with the exact training-time rule:

```python
is_rain = precipitation_mm > 0
is_snow = (snow_depth_cm > 0) or (new_snow_3h_cm > 0)
is_cold_wave_like = temperature_c <= -5
is_strong_wind = wind_speed_ms >= 5
is_bad_weather = is_rain or is_snow or is_cold_wave_like or is_strong_wind
```

- Even though `new_snow_3h_cm` is not a model feature, the serving weather source must provide it or
  an equivalent value to reproduce `is_snow`.
- If the required hourly weather observation or any required value is unavailable, calltaxi prediction
  is unavailable.
- No silent zero-fill, stale-value reuse, climatology fallback, or historical-average fallback in MVP.

### Gate 6: Prediction Domain And Output Validation

- Supported request hours:
  - `00:00` through `01:59`
  - `07:00` through `23:59`
- Requests from `02:00` through `06:59` are prediction unavailable.
- No fallback prediction is produced for excluded hours.
- Training rows with `target_min > 130` were excluded.
- Very long waiting-time situations are therefore outside the validated training domain.
- This limitation must be surfaced in model metadata/documentation and route warnings.
- Predictions must be presented as estimated waiting time, not guaranteed arrival time.
- Model output validation:
  - `NaN`, `inf`, non-numeric, or negative output: prediction unavailable.
  - Valid numeric output: use as predicted waiting minutes.
  - Do not clamp predictions to 130 minutes.
  - If predicted waiting minutes exceed 130, keep the numeric prediction and add an
    `out_of_training_target_range` warning.

## Domain Constraints

- Output unit: minutes from the model, seconds in backend route totals.
- Training domain excludes rows where `target_min > 130`.
- Training domain excludes request hours 02 through 06. Serving returns prediction unavailable
  for 02:00-06:59.
- Extreme congestion can be underpredicted because waits over 130 minutes were excluded.

## Serving Gate Status

All six serving gates are confirmed:

1. `model_group`: evaluate `임차택시_바로콜` and `특장차_바로콜`, use the conservative maximum.
2. `이용목적`: user-selected MVP dropdown mapped to one of six supported model categories.
3. Location normalization and `세부이동유형`: Backend-derived from Kakao metadata/reverse geocoding.
4. `vehicle_operation_count_prev_day`: daily refreshed D-1 operation-count lookup; missing value is unavailable.
5. Weather features: official hourly Seoul observation lookup/API; missing value is unavailable.
6. Prediction domain: 02:00-06:59 unavailable; `target_min > 130` is an OOD warning threshold, not a cap.

## Next Steps Before Adapter Wiring

1. Reflect these confirmed policies in the model metadata or companion serving contract.
2. Get review approval for the finalized serving contract.
3. Export the model and metadata to `analysis/waiting_time/`.
4. Register the exported artifacts in `analysis/service_data_manifest.json`.
5. Expand `ai/waiting_time/` from `hour_of_day` to the serving feature contract.
6. Reorder Backend orchestration so TMAP distance is available before waiting-time inference.
