# ADR 0003: Frontend의 브라우저 지도 SDK 직접 사용 예외

- 상태: 결정됨 (2026-09-11)
- 관련: [ADR 0001](./0001-monorepo-and-stack.md), [ADR 0002](./0002-ai-as-adapter-only.md)

## 배경

기존 아키텍처 규칙은 `frontend/`가 데이터를 `backend/` API를 통해서만 얻도록 제한했다. 이 규칙은 경로 계산, 추천, 요금/시간/도보 판단, 서비스 비즈니스 데이터의 소유권을 `backend/`에 두기 위한 것이다.

Frontend Phase 2에서는 사용자가 실제 장소를 검색하고 지도에서 출발지·목적지를 확인해야 한다. 요구 기능은 Kakao Maps JavaScript SDK, 장소검색, 지도 Marker, 지도 위치 이동이다. Kakao Maps JavaScript SDK의 지도 렌더링과 `services.Places` 장소검색은 브라우저에서 동작하는 SDK 기능이며, 지도 UI와 직접 결합되어 있다.

## 결정

1. **지도 렌더링과 Kakao Maps JavaScript SDK의 브라우저 전용 기능은 `frontend/`에서 직접 사용할 수 있다.**
   - 지도 생성
   - Marker 생성·제거
   - 지도 중심 이동
   - `services.Places` 기반 장소검색
2. **경로 계산과 추천 판단은 여전히 `backend/` 책임이다.**
   - 장애인 콜택시/지하철/저상버스 경로 계산
   - 요금, 시간, 도보거리 기반 추천 정렬
   - 대기시간 모델 호출 결과 반영
   - 서비스 비즈니스 데이터 조회
3. **`frontend/`는 분석 데이터와 AI 코드를 직접 참조하지 않는다.**
   - `data/raw`, `data/processed`, `notebooks*/`, `src/`, `ai/` 직접 참조 금지 규칙은 유지한다.
4. **브라우저 SDK 키는 저장소 루트 `.env`의 `KAKAO_JS_KEY`로 관리하고 커밋하지 않는다.**
   - 커밋되는 파일에는 루트 `.env.example`의 `KAKAO_JS_KEY=` 자리만 둔다.
   - `KAKAO_JS_KEY`는 브라우저에 노출되는 JavaScript SDK 키로만 사용한다. 같은 prefix로 비밀값이나 서버 전용 키를 만들지 않는다.

## 영향

- Frontend Phase 2의 Kakao 장소검색 직접 호출은 아키텍처 예외로 허용된다.
- 향후 실제 경로검색 API, 추천 정렬, 대기시간 반영은 `backend/`를 통해 구현해야 한다.
- 다른 외부 데이터 API를 `frontend/`에서 직접 호출하려면 이 ADR의 예외 범위에 해당하는지 확인해야 하며, 경로/추천/비즈니스 데이터라면 `backend/`를 거쳐야 한다.
