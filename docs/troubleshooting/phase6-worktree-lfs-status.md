# Phase 6 worktree Git LFS status issue

## 문제 상황

Phase 6 전용 worktree(`/private/tmp/calltaxi-phase6-ai-backend-integration`)에서 `git status`를 실행하면 Git LFS clean filter가 모델 artifact를 처리하려다 실패했다.

```text
Error cleaning Git LFS object: open /Users/pakrchansik/Desktop/calltaxi-DA/.git/lfs/tmp/...: operation not permitted
error: external filter 'git-lfs filter-process' failed
fatal: analysis/waiting_time/rf_wait_time_v2_prev_day_weather_final.joblib: clean filter 'lfs' failed
```

## 영향

- 일반 `git status`가 실패해 worktree 변경 상태 확인과 커밋 전 자체 리뷰 흐름이 막힌다.
- 모델 artifact 자체는 이번 Phase 수정 대상이 아니지만, Git LFS filter가 status 과정에서 대용량 joblib 파일을 다시 clean하려고 시도하면서 실패한다.
- 코드 실행과 pytest 검증에는 직접 영향이 없었다.

## 재현 방법

새 worktree에서 아래 명령을 실행한다.

```bash
git status --short --branch
```

root repository의 `.git/lfs/tmp`에 쓰기 권한이 없으면 동일 오류가 발생한다.

## 원인

Phase 전용 worktree는 `/private/tmp`에 있고 Git metadata와 LFS storage는 원본 repository의 `.git` 아래에 있다. sandbox 권한에서는 `/Users/pakrchansik/Desktop/calltaxi-DA/.git/lfs/tmp` 쓰기가 허용되지 않아 Git LFS clean filter가 임시 파일을 만들지 못했다.

## 검토한 대안

1. **모델 artifact를 수정하거나 다시 checkout**
   - 장점: status 실패 원인이 사라질 수 있다.
   - 단점: 이번 Phase 수정 대상이 아닌 1.48GB LFS artifact를 건드릴 위험이 있다.
   - 판단: 채택하지 않음.

2. **Git LFS filter를 우회**
   - 장점: status 확인만 빠르게 진행할 수 있다.
   - 단점: 실제 커밋 대상 확인을 왜곡할 수 있고 repository 설정을 임의 변경할 수 있다.
   - 판단: 채택하지 않음.

3. **필요한 Git 명령만 권한 승인 후 실행**
   - 장점: artifact나 repository 설정을 바꾸지 않고 status/commit 확인을 정상 Git 경로로 수행한다.
   - 단점: 권한 승인이 필요하다.
   - 판단: 채택.

## 해결 방법

- 코드 검증은 pytest로 먼저 수행했다.
- 변경 파일은 `git diff -- <수정 파일>`로 제한해 확인했다.
- 커밋 전 최종 `git status`와 commit은 Git LFS metadata 쓰기가 가능한 권한 승인 상태에서 수행한다.

## 검증 결과

아래 기능 검증은 Git LFS status 실패와 무관하게 통과했다.

```bash
PYTHONPATH=backend:. python3 -m pytest backend/tests/test_waiting_time_features.py backend/tests/test_route_orchestration.py backend/tests/test_recommendation_routes.py ai/tests/test_estimator.py -q
```

- 103개 통과

```bash
PYTHONPATH=backend:. python3 -m pytest backend/tests ai/tests
```

- 254개 통과

## 남은 한계

- worktree에서 일반 `git status`는 sandbox 권한에 따라 계속 실패할 수 있다.
- 실제 1.48GB 모델 artifact smoke test는 기존 Phase 3/4 문서처럼 Git LFS artifact와 ML 의존성이 준비된 환경에서 별도로 수행해야 한다.
