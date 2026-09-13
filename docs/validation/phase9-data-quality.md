# Analysis Phase 9 — 데이터 품질 및 최종 분석 검증

검증일: 2026-09-13. 기준 코드: `origin/dev`의 `2c7b12b`. 작업 브랜치: `analysis/phase9-data-quality`.

## 판정과 검증 범위

**현재 확정된 정적 export의 품질·출처 일치·서비스 연결 경계 검증 완료.** 실시간 데이터 품질, 전체 ODsay 경로의 매핑 성공률, AI 예측 성능까지 검증 완료했다는 뜻은 아니다. 기준일 미확인과 매핑 범위 부족은 아래와 같이 보존한다. 분석 export, 기존 데이터와 노트북을 수정하거나 재실행하지 않았다.

병원은 Phase 8에서 `reviewed_not_served`로 확정됐으므로 JSON·이미지와 출처의 일치, API·Frontend **미노출**을 검증했다. 병원 화면을 다시 연결하지 않는다. 모델이 없는 AI는 예측값을 검증하는 대신 기존 `NotImplementedError` 및 Backend의 unavailable 처리를 테스트했다.

[기계 판독 결과](phase9-audit-2026-09-13.json)는 검토 후 보존한 이번 실행 결과다. 행 수·전체 행 중복·키 중복·컬럼별 빈 값·SHA-256·미매핑 목록·원본 대조 결과를 포함한다. `errors=[]`는 실행한 검사에 오류가 없다는 뜻이고 `warnings`는 사용 제한이다. 공백/빈 문자열을 결측으로 집계하며, `unknown`과 시설 상세의 `없음`은 빈 값과 구분한다. 숫자형 의미 오류는 별도 검사한다. CI는 `--check-report`로 현재 커밋된 export와 repo 안 증거가 이 JSON의 비교 가능 snapshot에서 drift되지 않았는지 검사한다. 로컬 원본 파일이 필요한 source comparison metrics와 source availability warning은 CI 비교 범위에서 제외한다.

## 작업 전 구분

- 필수 확인: `AGENTS.md`, `docs/architecture.md`, ADR 0001~0005, Phase 3~8 결과, 기존 troubleshooting, `analysis/README.md`, manifest, 지하철·버스·병원·대기시간 기준 문서와 실제 provider/테스트.
- 이번 변경: `src/data_quality.py`, `src/tests/test_data_quality.py`, `backend/tests/test_phase9_data_quality.py`, `.github/workflows/data-quality.yml`, 이 보고서·검증 JSON·Phase 결과·`docs/troubleshooting/phase9-data-quality.md`.
- 참고 전용: `analysis/` CSV·JSON·PNG와 기존 기준 문서, `data/`, 기존 노트북, Backend/Frontend/AI 서비스 코드, 기존 ADR·README.
- 제외: 모델 학습·서빙, 데이터 수집·재export, 병원 서비스 노출, 실시간 차량/혼잡/엘리베이터 상태, 지도·교통비 기능, API 계약·데이터 소유권 변경.

GitHub 기본 브랜치는 `main`이지만 서비스 코드가 없고, 기존 Phase의 통합 기준은 `dev`다. `main`/`dev`를 원격 최신 상태로 갱신한 뒤 `dev`에서 전용 worktree를 만들었다. 원래 작업 공간의 미커밋 13개 파일과 실행 중인 서비스는 이번 브랜치에 가져오지 않았다.

## 데이터별 결과와 활용 한계

| 데이터 | 이번 실행 결과 | 기준시점 | 실제 활용 / 한계 |
|---|---|---|---|
| 지하철 접근성 master | 158행, 키·행 중복 0, 빈 값 0. 실제 provider에서 158/158 역 일치 | 이용량 선택월 2025-12. 시설의 별도 수집 기준일 미기록 | Backend 역 단위 정적 접근성. 전체 수도권 역, 실시간 고장, 모든 환승 내부 동선을 보장하지 않음 |
| 지하철 원본 정제 CSV | 1,896행, 월+호선+정규화역 키 중복 0. 최신월 158행의 export 컬럼 전부 일치 | 2025-01~12, 최신월 2025-12 | 오프라인 대조용. 서비스가 직접 읽지 않음 |
| 저상버스 master | 364행, 키·행 중복 0. available 322 / unavailable 40 / unknown 2. 저상버스 count·flag·status와 혼잡 availability·row count·proxy 값 상호 정합성 통과 | 승하차 2025년. 차량 metadata 기준일 364행 모두 unknown | Backend 노선 단위 저상버스 보유 상태. 특정 차량의 실제 도착 여부로 사용 금지 |
| ODsay 버스 mapping | 51행, 키·행 중복 0, 빈 값 0, master 미참조 0. 실제 provider 51/51 일치 | validation_date 2026-09-12 | ID+노선번호+유형이 모두 일치해야 함. 임의 노선번호 fallback 없음 |
| 버스 원본 JSON | 364노선의 ID·유형·기종점·인가대수·저상대수·비율 대조, 불일치 0 | 명시적 수집일 없음 | 비율 168건은 소수 넷째 자리 반올림 차이. 날짜를 파일 수정일로 추정하지 않음 |
| 혼잡 보조지표 원본 | 896,304행 / 320노선, proxy 결측·음수·비유한 값 0. count/max/p95/존재 플래그 불일치 0 | 2025년 집계 | 연간 추정 재차인원 보조지표. 현재 차량 혼잡으로 사용 금지. peak 시간·정류장·방향은 이번 독립 집계 대조 대상 아님 |
| 병원 목적지 집계 | 구 25행 / 동 416행, 키 중복·빈 값 0, 합계 각각 126,705. 상위 5개 구·동 JSON 일치 | 2025년 접수, Asia/Seoul | reviewed 분석 전용. 개별 병원 방문·선호도 판단 금지 |
| 병원 범위·거리·순유입 | 저장된 노트북 output과 3개 분석 수치 일치, 이미지 2개 byte 동일 | 거리/범위 모집단 126,561, 순유입 126,566 | 100km 초과 5건 제외 여부가 다름. 모집단을 혼합하지 않음 |
| 대기시간 분석·AI | 기존 AI 미연결 오류 및 Backend unavailable 회귀 테스트 통과 | 기존 2025년 분석 근거, production 모델 없음 | 통계 중앙값을 예측값으로 대체하지 않음. 실시간 수요 stream, inference-safe 모델/lookup과 모델 성능 검증은 별도 |
| 의료기관 보강·시설 CSV | 현재 manifest consumer 없음 | 파일별 기준이 다름. `20260630` 시설 파일의 시점을 병원 이동 분석에 전파하지 않음 | 서비스 미사용 참고자료. 전체 의료기관 공급량·실시간 의료서비스 가용성의 검증 대상이 아님 |

### 결측과 매핑 실패 상세

- 버스 `1155`, `8553`: 서울 노선 ID·기종점·인가대수·저상대수·비율 등 2행 결측. `unknown` 유지, 가짜 0 보충 없음.
- 버스 `route_type_code`: 34행 결측. ODsay의 별도 검토 유형을 서울 원본 유형으로 복사하지 않는다.
- 버스 혼잡 max/p95/peak 관련: 44행 결측, 혼잡 보조지표 없는 노선. 혼잡도를 0으로 보지 않는다.
- master 364개 중 명시적 ODsay mapping이 있는 노선은 51개(14.01%), 없는 노선은 313개(85.99%). 전체 미매핑 목록은 JSON에 포함했다.
- 기존 2026-09-12 문서의 `51/65 = 78.46%`는 성공 요청 11건에서 얻은 lane 표본의 검토 비율이다. 이번의 `51/364`와 분모가 다르다. 제외 14개 lane 원본이 reviewed export에 없으므로 78.46%를 이번에 재현한 실측 성공률로 주장하지 않는다.
- 지하철은 stationID 매핑 테이블이 없고 호선+역명으로 조회한다. 알려진 158개 key의 내부 일치율은 외부 전체 역의 매핑 성공률이 아니다.
- provider 테스트에서 잘못된 버스 ID·번호·유형 각각 51건, 미등록 지하철 역·호선 2건이 미매핑으로 반환됨을 확인했다. 기존 경로 parser 테스트도 unknown/unavailable 구간을 임의 허용하지 않는지 검증했다.

## 출처 대조 방법

1. 지하철 원본의 실제 컬럼은 `역명`이다. 분석 기준의 `역명정규화`는 검증 과정에서 공백과 끝 `역`을 제거해 메모리에서 파생한다. 최신월 선택 후 station_key를 제외한 export의 모든 컬럼을 비교한다. 파일은 쓰지 않는다.
2. 버스 원본 값은 숫자·문자 표현을 정규화해 비교한다. 비율은 export 소수 4자리의 반올림 오차 0.00005만 허용한다.
3. 혼잡 p95는 정렬 후 선형 보간으로 재계산한다. max/p95의 export 소수 2자리 반올림 오차 0.005와 부동소수 연산 오차 1e-9만 허용한다. 오차 범위를 넘는 값은 실패한다.
4. 병원 상위 지역은 커밋된 구·동 집계 CSV에서 대조한다. 범위·5km는 `04_3` 노트북 저장 output, 순유입은 `07_2` 저장 output과 대조한다. 노트북을 실행하거나 개인별 탑승내역을 출력하지 않는다.
5. 기존 manifest 테스트로 provider 경로·consumer와 reviewed/served 분리, 새 테스트로 전체 lookup 값과 병원 미노출을 검증한다.

## 재현 명령과 실제 결과

저장소 루트, Python 3.11.9 서비스 venv 사용. 새 worktree에는 venv와 node_modules가 없으므로 기존 설치된 Backend Python을 절대경로로 사용하고 Frontend node_modules만 링크했다. 새 의존성은 없다.

```sh
# 커밋된 자료만: 원본 3개가 없으면 not_verified_source_missing을 명시
python3 -m src.data_quality

# 커밋된 audit JSON과 현재 export snapshot drift 검사
python3 -m src.data_quality --check-report docs/validation/phase9-audit-2026-09-13.json

# 로컬 원본이 있는 저장소를 읽기 전용으로 지정한 이번 전체 대조
python3 -m src.data_quality --source-root /Users/pakrchansik/Desktop/calltaxi-DA

# 이번 환경의 실제 Python 테스트 명령
PYTHONPATH=backend:. /Users/pakrchansik/Desktop/calltaxi-DA/backend/.venv/bin/python -m pytest src/tests backend/tests ai/tests -q

npm test --prefix frontend
npm run build --prefix frontend
npm run lint --prefix frontend
git diff --check
```

- 전체 대조: 종료 코드 0, errors 0. 버스 결측·날짜 미확정·외부 mapping 한계 warning 5건 유지.
- 원본 없는 clean worktree 대조: 종료 코드 0, export 검사는 통과. 원본 3개는 `not_verified_source_missing`이며 독립 재검증 완료로 세지 않는다. CI도 이 범위다. 다만 CI는 `--check-report docs/validation/phase9-audit-2026-09-13.json`로 행 수·해시·결측·미매핑 목록 등 커밋된 export snapshot의 drift를 실패 처리한다.
- Python: 181개 통과(Backend/AI 160 + 데이터 품질 21). 기존 Starlette/anyio DeprecationWarning 1건.
- Frontend: 21개 통과. TypeScript/Vite production build와 oxlint 통과.
- 최초 검증 실패도 확인했다: 원본 지하철의 파생 key 컬럼 부재, 비율 168건의 문자열 정밀도 차이, `5522A` max의 부동소수 반올림 경계 차이. 데이터 변경 없이 원본 스키마에 맞춘 파생 key와 명시한 정밀도 비교로 수정하고 재실행했다. 실제 값 변화가 허용 범위를 넘으면 실패하는 테스트를 포함했다.
- Git 상태 확인은 최초 LFS 임시파일 권한 부족으로 실패했다. 승인된 권한으로 재실행해 정상 확인했으며 기존 원본 데이터는 변경하지 않았다.

## 잔여 한계와 다음 인계

현재 범위의 Phase 9는 완료다. 운영 전체 데이터가 완전하거나 최신이라는 판정은 아니다. 다음 작업은 검토된 시설·차량 기준일 확보, ODsay 표본 확대와 미매핑 근거 보존, Prediction 산출물·추론 계약 검증이다. 원본 3개는 Git 미추적이므로 다른 환경의 전체 재검증에는 동일 SHA-256 원본을 별도 준비해야 한다. 외부 API는 이번에 호출하지 않았고 2026-09-12의 인증·HTTP 제약을 현재 서비스 장애로 재단정하지 않는다. 병원 데이터와 미확정 실시간 데이터를 서비스로 추가하는 변경은 포함하지 않았다.

문제와 대안은 [Phase 9 트러블슈팅](../troubleshooting/phase9-data-quality.md)에 기록했다.
