# analysis/

`ai/`(AI Adapter)가 실제로 호출·서빙하는 **특장차/임차택시 Prediction 모델과 그 산출물의 발행처(export 대상)**. `data/`, `notebooks*/`, `src/`(탐색적 분석, 원본/중간 산출물, 팀 작업 공간)와는 구분된다 — 이 폴더에는 "서비스가 그대로 가져다 쓰기로 확정된" 모델/결과만 둔다.

## 규칙

- 노트북/스크립트가 직접 여기 쓰지 않는다. 모델 학습/검증이 끝나고 결과가 안정화되면, 사람이 검토해서 필요한 파일만 이곳에 export한다.
- `ai/`는 `data/`나 `notebooks*/`의 원본 파일을 직접 열지 않고, 이 폴더의 산출물만 참조한다(`docs/architecture.md` "대기시간 예측 흐름", "데이터 소유권" 참고).
- 파일 하나하나에 출처(어떤 노트북/분석에서 나왔는지)와 갱신 방법을 주석 또는 같은 이름의 `.md`로 남긴다.

## 현재 상태

아직 이곳으로 export된 Prediction 모델/분석 결과가 없다 — `ai/waiting_time/estimator.py`는 그래서 지금 `NotImplementedError`를 발생시킨다. 첫 후보: 특장차/임차택시 시간대별 예상 대기시간 Prediction 모델(출처 후보: `notebooks_lye/5-1_plan_시간대별평균대기시간.ipynb` 등).

요금/시간/도보 우선순위 추천 로직은 이 폴더·`ai/`가 아니라 `backend/`가 담당한다(Backend Phase 7 예정).
