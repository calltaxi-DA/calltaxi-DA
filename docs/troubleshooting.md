# 트러블슈팅

## 작성 기준

- 실제로 겪고 해결한 문제만 기록한다(예상되는 문제를 미리 나열하지 않는다).
- 형식: **증상 → 원인 → 해결/우회 → 관련 커밋 또는 파일**.
- 노트북/분석 작업 중 겪은 이슈(예: Jupyter 커널 크래시, 인코딩 문제)는 이 서비스 문서가 아니라 해당 분석 브랜치의 `notebooks_docs_lye/`에 남긴다 — 이 문서는 `backend/`, `frontend/`, `ai/` 서비스 코드 관련 이슈 전용이다.

## 기록된 이슈

### 2026-09-12 — TMAP 자동차 경로안내 smoke test 403 Forbidden

- **문제 상황**: Backend Phase 2에서 로컬 `APP_TMAP_APP_KEY`를 사용해 `https://apis.openapi.sk.com/tmap/routes?version=1` 자동차 경로안내 API를 실제 호출했을 때 `403 Forbidden`이 반환됐다.
- **영향**: 애플리케이션 코드의 요청 생성·응답 파싱·요금 계산은 mock 기반 테스트로 검증됐지만, 현재 로컬 키 상태에서는 실제 TMAP 자동차 경로 결과를 받을 수 없다. 운영에서도 같은 키 권한이면 `/routes/calltaxi`가 TMAP 실패로 `502`를 반환한다.
- **재현 방법**:
  1. `backend/.env` 또는 실행 환경에 `APP_TMAP_APP_KEY`를 설정한다.
  2. 서울시청 → 서울역 좌표로 `TmapRouteClient.get_vehicle_route()`를 호출한다.
  3. TMAP 응답이 `403 Forbidden`으로 실패한다.
- **원인**: HTTP 요청 자체는 TMAP 자동차 경로안내 문서의 `appKey` 헤더, `version=1`, WGS84 좌표, `totalValue=2` 기준으로 구성했다. 따라서 현재 확인 가능한 원인은 코드 파싱 문제가 아니라 발급 키의 자동차 경로안내 API 사용 권한, 상품 신청/활성화 상태, 또는 SK OpenAPI 콘솔의 키 제한 설정 문제로 판단한다.
- **검토한 대안**:
  - 실제 API를 테스트에 직접 포함: 키·네트워크·쿼터에 의존해 CI가 불안정해져 제외했다.
  - TMAP 실패 시 가짜 거리/시간 반환: 실제 서비스 오판 위험이 있어 제외했다.
  - TMAP 실패 시 명시적 `502` 반환: 외부 API 실패를 숨기지 않아 현재 Phase에 적합하다고 판단했다.
- **해결 방법**: 코드에서는 `httpx.HTTPError`, HTTP 오류 상태, JSON decode 실패, 응답 스키마 오류를 `TmapRouteError`로 감싸고 API 라우터에서 `502 {"detail": "Failed to calculate calltaxi vehicle route"}`로 변환하도록 했다. 테스트는 실제 키 대신 fake client와 `httpx.MockTransport`로 `totalDistance`, `totalTime`, 예상요금 계산, outbound 요청 구조를 검증한다.
- **검증 결과**:
  - `PYTHONPATH=backend:. backend/.venv/bin/python -m pytest backend/tests ai/tests` — 41개 통과
  - 실제 TMAP smoke test — `403 Forbidden` 재현
- **남은 한계**: TMAP 개발자 콘솔에서 해당 App Key가 자동차 경로안내 API 상품을 사용할 수 있는지, 도메인/IP/서비스 제한이 있는지 확인한 뒤 같은 smoke test를 다시 실행해야 한다.
