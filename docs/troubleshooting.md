# 트러블슈팅

## 작성 기준

- 실제로 겪고 해결한 문제만 기록한다(예상되는 문제를 미리 나열하지 않는다).
- 형식: **증상 → 원인 → 해결/우회 → 관련 커밋 또는 파일**.
- 노트북/분석 작업 중 겪은 이슈(예: Jupyter 커널 크래시, 인코딩 문제)는 이 서비스 문서가 아니라 해당 분석 브랜치의 `notebooks_docs_lye/`에 남긴다 — 이 문서는 `backend/`, `frontend/`, `ai/` 서비스 코드 관련 이슈 전용이다.

## 기록된 이슈

### 2026-09-12 — ODsay 버스 route mapping smoke test ApiKeyAuthFailed

- **문제 상황**: Analysis Phase 5-2 시작 시 로컬 `.env`의 `ODSAY_API_KEY`를 사용해 `https://api.odsay.com/v1/api/searchPubTransPathT` 버스 경로 API를 실제 호출했지만, HTTP 상태는 `200`이고 본문은 ODsay application error로 반환됐다.

  ```text
  [ApiKeyAuthFailed] ApiKey authentication failed.
  ```

- **영향**: 현재 키 상태에서는 실제 ODsay 버스 경로 응답 샘플을 확보할 수 없다. 따라서 Analysis Phase 5-2의 핵심 검증 대상인 버스 구간의 `busID`, 노선번호, 버스 유형 필드명과 표기 방식, `analysis/bus/low_floor_bus_route_master.csv`와의 매핑 성공률을 확인할 수 없다.
- **재현 방법**:
  1. 루트 `.env`에 `APP_ODSAY_API_KEY` 또는 호환 변수 `ODSAY_API_KEY`를 설정한다.
  2. 서울시청→홍대입구, 강남역→잠실역, 서울역→이태원 같은 샘플 좌표로 `searchPubTransPathT`를 호출한다.
  3. 요청 파라미터에는 `SearchType=0`, `SearchPathType=2`, `SX`, `SY`, `EX`, `EY`, `apiKey`를 포함한다.
  4. 응답 본문에 `error`가 포함되고 `[ApiKeyAuthFailed] ApiKey authentication failed.`가 반환된다.
- **확인된 사실**:
  - 루트 `.env`에는 `APP_ODSAY_API_KEY`는 없고 `ODSAY_API_KEY`가 존재한다.
  - 첫 시도에서 로컬 Python SSL 인증서 오류가 발생했지만, 프로젝트 venv의 `httpx`로 재시도해 SSL 문제는 해소됐다.
  - 요청 자체는 ODsay 서버에 도달했고 HTTP `200` 응답을 받았다.
  - 응답 본문은 정상 `result.path`가 아니라 application-level `ApiKeyAuthFailed` 오류였다.
  - 키가 URL-encoded 형태로 저장됐을 가능성을 확인하기 위해 raw 값과 URL-decoded 값을 각각 사용했지만 둘 다 같은 인증 오류가 반환됐다.
  - 따라서 현재 확인된 범위에서는 JSON 파싱 문제, 네트워크 연결 실패, 단순 URL 인코딩 문제가 아니라 ODsay 인증 단계에서 실패한 것이다.
- **확정 원인**: 아직 확인되지 않았다.
- **미확정 원인 후보**:
  - 현재 키가 backend/server 호출용 키가 아닐 가능성
  - ODsay 대중교통/버스 경로 API 권한이 활성화되지 않았을 가능성
  - Server Key에 필요한 IP 등록이 누락됐을 가능성
  - ODsay 콘솔의 키 제한 설정과 현재 호출 환경이 맞지 않을 가능성
- **검토한 대안**:
  - 인증 실패 상태에서 mock 응답으로 busID/노선번호 매핑을 확정: 실제 ODsay 응답 필드 검증이라는 Phase 목적에 맞지 않아 제외했다.
  - `route_number_normalized` 단독으로 실제 연결 가능하다고 간주: ODsay 노선번호 필드와 표기 방식을 아직 확인하지 못했으므로 제외했다.
  - ODsay 실제 키가 정상화될 때까지 Phase 5-2를 보류: 실제 응답 기반 매핑 검증이라는 Phase 목적에 가장 맞는 방식으로 판단했다.
- **상태**: 미해결
- **다음 확인 절차**:
  1. ODsay 콘솔에서 현재 키가 backend/server 호출용 키인지 확인한다.
  2. 대중교통/버스 경로 API 권한 또는 상품이 활성화되어 있는지 확인한다.
  3. IP 제한이 있다면 현재 호출 환경의 IP가 등록되어 있는지 확인한다.
  4. 동일한 샘플 요청을 다시 실행해 정상 `result.path`가 반환되는지 확인한다.
  5. 정상 응답이 확인되면 버스 구간의 `busID`, 노선번호, 버스 유형 필드를 추출해 `analysis/bus/low_floor_bus_route_master.csv`와 매핑 성공률을 검증한다.
  6. 원인이 확인되면 이 문서의 `확정 원인`과 해결 내용을 갱신한다.
- **검증 결과**:
  - `backend/.venv/bin/python` + `httpx` 기준 실제 ODsay 호출은 수행됨
  - 샘플 요청 모두 HTTP `200` + ODsay `error` 본문 반환
- **남은 한계**: 올바른 ODsay 키/권한/IP 등록이 준비되기 전까지 Analysis Phase 5-2의 실제 버스 응답 샘플 확보와 route master 매핑 검증은 진행할 수 없다.

### 2026-09-12 — ODsay 지하철 경로 smoke test ApiKeyAuthFailed

- **문제 상황**: Backend Phase 5-2 시작 시 로컬 `.env`의 ODsay 키를 사용해 `https://api.odsay.com/v1/api/searchPubTransPathT` 지하철 경로 API를 실제 호출했지만, 모든 샘플 경로에서 HTTP 상태는 `200`이고 본문은 ODsay application error로 반환됐다.

  ```text
  [ApiKeyAuthFailed] ApiKey authentication failed.
  ```

- **영향**: 현재 키 상태에서는 환승 0회·1회·2회 실제 ODsay 응답 샘플을 확보할 수 없다. 따라서 Backend Phase 5-2의 핵심 검증 대상인 ODsay 응답의 `stationID`, 역명, 노선명, 도보 subPath, 환승 내부 도보거리·도보시간 포함 여부를 확인할 수 없다.
- **재현 방법**:
  1. 루트 `.env`에 `APP_ODSAY_API_KEY` 또는 호환 변수 `ODSAY_API_KEY`를 설정한다.
  2. 서울시청→강남역, 서울역→강남역, 홍대입구→고속터미널 같은 샘플 좌표로 `searchPubTransPathT`를 호출한다.
  3. 요청 파라미터에는 `SearchType=0`, `SearchPathType=1`, `SX`, `SY`, `EX`, `EY`, `apiKey`를 포함한다.
  4. 응답 본문에 `error`가 포함되고 `[ApiKeyAuthFailed] ApiKey authentication failed.`가 반환된다.
- **확인된 사실**:
  - 첫 시도에서 로컬 Python SSL 인증서 오류가 발생했지만, 프로젝트 venv의 `httpx`로 재시도해 SSL 문제는 해소됐다.
  - 요청 자체는 ODsay 서버에 도달했고 HTTP `200` 응답을 받았다.
  - 응답 본문은 정상 `result.path`가 아니라 application-level `ApiKeyAuthFailed` 오류였다.
  - 따라서 현재 확인된 범위에서는 JSON 파싱 문제나 네트워크 연결 실패가 아니라 ODsay 인증 단계에서 실패한 것이다.
- **확정 원인**: 아직 확인되지 않았다.
- **미확정 원인 후보**:
  - 현재 키가 backend/server 호출용 키가 아닐 가능성
  - ODsay 대중교통/지하철 경로 API 권한이 활성화되지 않았을 가능성
  - Server Key에 필요한 IP 등록이 누락됐을 가능성
  - ODsay 콘솔의 키 제한 설정과 현재 호출 환경이 맞지 않을 가능성
- **검토한 대안**:
  - 인증 실패 상태에서 mock 응답으로 Phase 5-2를 완료 처리: 실제 환승 내부 도보거리·도보시간 검증 목적에 맞지 않아 제외했다.
  - 임의 환승시간/거리 보정값 사용: 이동약자 대상 서비스에서 근거 없는 과소/과대 추정 위험이 있어 제외했다.
  - ODsay 실제 키가 정상화될 때까지 5-2를 보류: 실제 응답 기반 검증이라는 Phase 목적에 가장 맞는 방식으로 판단했다.
- **상태**: 미해결
- **다음 확인 절차**:
  1. ODsay 콘솔에서 현재 키가 backend/server 호출용 키인지 확인한다.
  2. 대중교통/지하철 경로 API 권한 또는 상품이 활성화되어 있는지 확인한다.
  3. IP 제한이 있다면 현재 호출 환경의 IP가 등록되어 있는지 확인한다.
  4. 동일한 샘플 요청을 다시 실행해 정상 `result.path`가 반환되는지 확인한다.
  5. 정상 응답이 확인되면 이 문서의 `확정 원인`과 해결 내용을 갱신한다.
- **검증 결과**:
  - `backend/.venv/bin/python` + `httpx` 기준 실제 ODsay 호출은 수행됨
  - 세 샘플 모두 HTTP `200` + ODsay `error` 본문 반환
- **남은 한계**: 올바른 ODsay 키/권한/IP 등록이 준비되기 전까지 Backend Phase 5-2의 실제 응답 샘플 확보와 총 도보거리·총 도보시간 검증은 진행할 수 없다.

### 2026-09-12 — TMAP 자동차 경로안내 smoke test 403 Forbidden

- **문제 상황**: Backend Phase 2에서 로컬 `APP_TMAP_APP_KEY` 또는 호환 변수 `TMAP_APP_KEY`를 사용해 `https://apis.openapi.sk.com/tmap/routes?version=1` 자동차 경로안내 API를 실제 호출했을 때 `403 Forbidden`이 반환됐다.
- **영향**: 애플리케이션 코드의 요청 생성·응답 파싱·요금 계산은 mock 기반 테스트로 검증됐지만, 현재 로컬 키 상태에서는 실제 TMAP 자동차 경로 결과를 받을 수 없다. 운영에서도 같은 키 권한이면 `/routes/calltaxi`가 TMAP 실패로 `502`를 반환한다.
- **재현 방법**:
  1. `backend/.env` 또는 실행 환경에 `APP_TMAP_APP_KEY`를 설정한다(`TMAP_APP_KEY`도 로컬 호환용으로 읽을 수 있다).
  2. 서울시청 → 서울역 좌표로 `TmapRouteClient.get_vehicle_route()`를 호출한다.
  3. TMAP 응답이 `403 Forbidden`으로 실패한다.
- **원인**: HTTP 요청 자체는 TMAP 자동차 경로안내 문서의 `appKey` 헤더, `version=1`, WGS84 좌표, `totalValue=2` 기준으로 구성했다. 따라서 현재 확인 가능한 원인은 코드 파싱 문제가 아니라 발급 키의 자동차 경로안내 API 사용 권한, 상품 신청/활성화 상태, 또는 SK OpenAPI 콘솔의 키 제한 설정 문제로 판단한다.
- **검토한 대안**:
  - 실제 API를 테스트에 직접 포함: 키·네트워크·쿼터에 의존해 CI가 불안정해져 제외했다.
  - TMAP 실패 시 가짜 거리/시간 반환: 실제 서비스 오판 위험이 있어 제외했다.
  - TMAP 실패 시 명시적 `502` 반환: 외부 API 실패를 숨기지 않아 현재 Phase에 적합하다고 판단했다.
- **해결 방법**: 코드에서는 `httpx.HTTPError`, HTTP 오류 상태, JSON decode 실패, 응답 스키마 오류를 `TmapRouteError`로 감싸고 API 라우터에서 `502 {"detail": "Failed to calculate calltaxi vehicle route"}`로 변환하도록 했다. 테스트는 실제 키 대신 fake client와 `httpx.MockTransport`로 `totalDistance`, `totalTime`, 예상요금 계산, outbound 요청 구조를 검증한다.
- **검증 결과**:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 46개 통과
  - 실제 TMAP smoke test — `403 Forbidden` 재현
- **남은 한계**: TMAP 개발자 콘솔에서 해당 App Key가 자동차 경로안내 API 상품을 사용할 수 있는지, 도메인/IP/서비스 제한이 있는지 확인한 뒤 같은 smoke test를 다시 실행해야 한다.
