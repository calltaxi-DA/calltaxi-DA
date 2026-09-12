# analysis/

`ai/`(AI Adapter)가 실제로 호출·서빙하는 **장애인 콜택시 통합 대기시간 Prediction 모델과 그 산출물의 발행처(export 대상)**. `data/`, `notebooks*/`, `src/`(탐색적 분석, 원본/중간 산출물, 팀 작업 공간)와는 구분된다 — 이 폴더에는 "서비스가 그대로 가져다 쓰기로 확정된" 모델/결과만 둔다.

## 규칙

- 노트북/스크립트가 직접 여기 쓰지 않는다. 모델 학습/검증이 끝나고 결과가 안정화되면, 사람이 검토해서 필요한 파일만 이곳에 export한다.
- `ai/`는 `data/`나 `notebooks*/`의 원본 파일을 직접 열지 않고, 이 폴더의 산출물만 참조한다(`docs/architecture.md` "대기시간 예측 흐름", "데이터 소유권" 참고).
- 파일 하나하나에 출처(어떤 노트북/분석에서 나왔는지)와 갱신 방법을 주석 또는 같은 이름의 `.md`로 남긴다.

## 현재 상태

아직 이곳으로 export된 Prediction 모델 파일이나 lookup table은 없다 — `ai/waiting_time/estimator.py`는 그래서 지금 `NotImplementedError`를 발생시킨다.

다만 통합 대기시간 Prediction 모델과 서비스 개발에서 사용할 데이터 기준은 [`waiting_time/data_criteria.md`](waiting_time/data_criteria.md)에 정리했다. 이 문서는 기존 전처리 Notebook을 재실행하지 않고, 임차택시·특장차 대기시간 전처리 기준, 당일/전일 접수 구분, 서비스 목표값(`접수_승차_분`)과 운영 KPI(`접수_배차_분`)의 차이를 확정하기 위한 기준 문서다. 실제 모델 파일이나 분석 산출물을 export할 때는 이 기준을 따른다.

기존 이용패턴 분석 결과 중 통합 대기시간 Prediction 모델의 입력 해석과 결과 검증에 활용할 근거는 [`waiting_time/usage_pattern_evidence.md`](waiting_time/usage_pattern_evidence.md)에 정리했다. 이 문서는 시간대·요일·차량유형·이동유형별 대기시간 분포, 수요 proxy, 장시간 대기율 proxy, leakage 방지 기준을 기존 Notebook output 기준으로 확인한 문서다. 단, 실시간 접수 stream/API/DB가 필요한 rolling 수요량 feature는 현재 1차 production feature에서 제외하고 offline 실험 근거로만 유지한다.

지하철 경로와 접근성 데이터를 연결하기 위한 기준은 [`subway/accessibility_mapping_criteria.md`](subway/accessibility_mapping_criteria.md)에 정리했다. 이 문서는 기존 지하철 전처리 결과, 역명·호선 매핑 기준, 엘리베이터·휠체어리프트·안전발판 등 접근성 시설 연결 기준, ODsay 지하철역 정보와 연결할 key 후보를 정리한 문서다. 아직 ODsay stationID 매핑 테이블이나 지하철 접근성 lookup export 파일은 없다.

요금/시간/도보 우선순위 추천 로직은 이 폴더·`ai/`가 아니라 `backend/`가 담당한다(Backend Phase 7 예정).
