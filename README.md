# calltaxi-DA

서울시 장애인콜택시 데이터를 분석하고, 그 결과(예상 대기시간)를 반영해 지하철·저상버스·장애인콜택시 이동경로를 추천하는 서비스를 만드는 모노레포입니다.

- **분석**: `data/`, `notebooks*/`, `src/` — 대기시간·이동패턴 분석 (기존)
- **분석 결과 발행**: `analysis/` — 서비스가 쓰기로 확정된 export 결과만 모아두는 경계 (신규)
- **서비스**: `backend/`(FastAPI), `frontend/`(Vite+React+TS), `ai/`(대기시간·추천 로직, `analysis/`만 참조) — 신규

구조와 각 폴더의 책임은 [`docs/architecture.md`](docs/architecture.md)에, 코드 작성 규칙은 [`AGENTS.md`](AGENTS.md)에 있습니다.

## 실행

### 백엔드

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # macOS/Linux: .venv/bin/pip
cp .env.example .env
./.venv/Scripts/uvicorn app.main:app --reload      # macOS/Linux: .venv/bin/uvicorn ...
curl http://localhost:8000/health
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

### 데이터 분석

```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt
jupyter lab
```

## 테스트

```bash
# 백엔드 + ai (저장소 루트에서)
backend/.venv/Scripts/python -m pytest backend/tests ai/tests

# 프론트엔드
cd frontend && npm test
```

## 문서

- [아키텍처 / 폴더 책임 / 데이터 소유권](docs/architecture.md)
- [개발 단계 추적](docs/development-phases.md)
- [트러블슈팅](docs/troubleshooting.md)
- [설계 결정(ADR)](docs/decisions/)
- [코드 작성 규칙(AGENTS.md)](AGENTS.md)

## 브랜치 전략

- `main`: 최종 안정 버전
- `dev`: 통합 개발 브랜치
- `feat/*`: 기능/분석 단위 작업 브랜치 (예: `feat/data-preprocessing`, `feat/service-bootstrap`)
