# Phase 9 검증 중 확인한 데이터·실행 제약

## 1. 기준연도와 수집일 혼동, 부분 매핑을 전체 성공률로 오인할 위험

- **문제 상황:** manifest에는 지하철 2025-12와 버스 2025가 있고 mapping에는 2026-09-12가 있지만, 버스 차량 metadata 364행은 `unknown`이다. 일부 예전 기준 문서는 ODsay 매핑을 아직 미완료로 설명하고, 후속 문서는 51개 검토 완료를 기록한다.
- **영향:** 이용량 기준연도나 mapping 검증일을 시설·차량의 현재 상태 기준일로 오인하거나, 51개만 서비스 연결 가능한 상태를 전체 노선 지원으로 해석할 수 있다.
- **재현 방법:** `python3 -m src.data_quality`의 `bus_mapping`, 컬럼별 결측과 warnings를 확인한다. `analysis/bus/low_floor_bus_mapping_criteria.md`의 51/65 표본 결과와 364행 master를 비교한다.
- **원인:** 이용량 집계, 원본 차량 snapshot, 외부 API lane 표본이 서로 다른 시점·모집단이다. 과거 Phase 문서는 당시 결과를 보존한다.
- **검토한 대안:** 파일 수정일을 기준일로 대체(출처 근거가 없어 제외), 누락 노선번호를 자동 매핑(타지역 동번호 오판으로 제외), 기존 분석 문서를 전부 재작성(과거 검증 이력 훼손으로 제외), 최종 보고서에서 시점·분모와 적용 범위 분리(채택).
- **해결 방법:** Phase 9 보고서에 데이터별 시점·consumer·한계를 분리하고 JSON에 unknown 364개와 master 미매핑 313개를 보존했다. export와 서비스의 fail-closed 계약은 변경하지 않았다.
- **검증 결과:** master 364, mapping 51, orphan 0. provider 51/51 일치. ID·번호·유형 불일치 153건 모두 미매핑. 버스 1155·8553 unknown 유지. 지하철 158개 내부 key 일치, 미등록 역·호선 2건 미매핑.
- **남은 한계:** 별도 수집일과 전체 외부 응답 표본을 확보하지 않아 실시간 상태·전체 mapping 성공률은 검증 불가. 기존 문서의 API 인증 실패는 과거 기록이며 이번에 외부 API를 다시 호출하지 않았다.

## 2. 원본과 export의 정밀도 차이로 품질 검사 오탐

- **문제 상황:** 원본 JSON과 export CSV를 문자열로 비교하면 저상버스 비율 168건이 불일치했다. 혼잡 max 비교에서도 `5522A` 1건이 0.005 경계에서 실패했다.
- **영향:** 정상적인 반올림 산출물을 데이터 오류로 잘못 판정하거나, 반대로 과도한 허용오차로 실제 데이터 변화를 놓칠 수 있다.
- **재현 방법:** 노선 101 원본 비율 `0.6129032258064516`과 export `0.6129`를 비교한다. `5522A` 원본 max `23440.375`와 export `23440.38`의 float 차이는 정확한 십진 0.005보다 아주 약간 커질 수 있다.
- **원인:** CSV export에서 비율은 소수 4자리, 혼잡 max/p95는 소수 2자리로 보존된다. 이진 부동소수 표현 오차도 존재한다.
- **검토한 대안:** 원본과 export를 같은 문자열로 덮어쓰기(검토된 export 보존 원칙 위반), 넓은 상대 오차 허용(큰 값일수록 오류 누락), 항목별 export 정밀도와 작은 부동소수 오차만 허용(채택).
- **해결 방법:** 비율 절대오차 0.00005(+1e-12), 혼잡 max/p95 절대오차 0.005(+1e-9)를 한도로 비교한다. 데이터는 변경하지 않고 검사만 수정했다.
- **검증 결과:** 364노선 metadata 불일치 0. 혼잡 원본 896,304행/320노선의 count/max/p95/존재 플래그 불일치 0. 테스트에서 `23440.38`은 허용하고 `23440.39`로 바꾸면 오류가 검출된다.
- **남은 한계:** 허용오차는 현재 reviewed export 정밀도에 한정한다. 향후 정밀도나 집계 정의 변경 시 근거와 검증 기준을 함께 재검토해야 한다.

## 3. 새 worktree의 원본·실행환경 누락과 Git LFS 상태 검사 권한

- **문제 상황:** 새 worktree에는 Git 미추적 지하철 정제 CSV, 버스 JSON, 혼잡 원본 CSV와 venv/node_modules가 없다. `git status`는 LFS clean filter가 공용 `.git/lfs/tmp`에 쓰려다 sandbox 권한 오류로 실패했다.
- **영향:** 원본 대조를 생략한 채 전체 검증 완료로 오인하거나, 환경 오류를 코드/데이터 실패로 혼동할 수 있다. 검토 완료 코드와 기존 작업의 분리 상태도 확인이 필요하다.
- **재현 방법:** 최신 dev에서 worktree를 생성한 후 `python3 -m src.data_quality`를 실행하면 원본 3개가 `not_verified_source_missing`이다. 동일한 restricted 환경에서 `git status`가 LFS 임시파일 쓰기를 시도할 때 `operation not permitted`가 발생할 수 있다.
- **원인:** 원본 3개와 설치환경은 Git 미추적이고, worktree의 Git 메타데이터는 원래 저장소와 공유된다.
- **검토한 대안:** 원본을 새로 Git에 추가(불필요한 대용량 데이터 변경), 원래 작업을 stash/이동(기존 변경 보존 요구에 불필요), 별도 worktree에서 원본 경로를 읽기 전용으로 지정하고 설치환경만 재사용(채택).
- **해결 방법:** `--source-root`로 원래 저장소의 원본을 읽고 SHA-256을 기록했다. 기존 서비스 Python을 절대경로로 실행하고 node_modules는 Git 미추적 링크로 재사용했다. Git 상태 확인은 승인된 권한으로 재실행했다.
- **검증 결과:** 원본 경로 지정 실행은 세 원본 모두 대조 통과. 경로 미지정 실행도 수행해 미검증 상태가 출력되는지 확인했다. 원래 작업 트리의 변경 파일은 이번 worktree에 포함하지 않았으며 LFS 원본의 변경도 없었다.
- **남은 한계:** CI는 커밋된 자료만 검사한다. 동일 원본이 없는 환경에서 원본 대조까지 통과했다고 주장할 수 없다. 실행환경 링크는 커밋되지 않으므로 다른 환경은 각 requirements/package-lock에 따라 설치해야 한다.

## 4. 커밋된 audit JSON과 현재 export의 drift 누락 위험

- **문제 상황:** CI가 `python -m src.data_quality`만 실행하면 현재 데이터가 유효한지만 확인하고, `docs/validation/phase9-audit-2026-09-13.json`에 보존된 행 수·SHA-256·미매핑 목록이 현재 export와 계속 일치하는지는 확인하지 못한다.
- **영향:** 누군가 `analysis/` export를 수정하고 audit JSON을 갱신하지 않아도 CI가 통과할 수 있다. 그러면 Phase 9의 "최종 검증 결과" 문서가 실제 서비스 export와 달라진다.
- **재현 방법:** `analysis/bus/low_floor_bus_route_master.csv`의 값을 테스트 브랜치에서 바꾸고 audit JSON을 그대로 둔 뒤 `python3 -m src.data_quality --check-report docs/validation/phase9-audit-2026-09-13.json`를 실행한다.
- **원인:** 최초 CI는 실행 시점의 오류 여부만 보고 committed report와의 동등성을 비교하지 않았다. 또한 GitHub Actions에는 미추적 원본 파일이 없어 로컬 source comparison 전체를 그대로 비교할 수 없다.
- **검토한 대안:** CI에서 전체 `asdict(result)`를 비교(원본 부재 warning과 source metrics 때문에 항상 실패), audit JSON을 원본 없는 결과로 축소(로컬 전체 검증 산출물 손실), 커밋된 export와 repo 내부 증거의 snapshot만 비교하고 원본 source metrics는 제외(채택).
- **해결 방법:** `src.data_quality`에 `--check-report`와 `export_snapshot()`을 추가했다. CI는 현재 export snapshot과 committed audit JSON의 비교 가능 영역을 비교하고, drift가 있으면 종료 코드 1로 실패한다. workflow path에 `docs/validation/**`를 추가하고 job summary에 원본 대조가 CI에서 실행되지 않는다고 출력한다.
- **검증 결과:** 현재 report는 `--check-report`로 통과했다. 단위 테스트에서 expected JSON의 버스 master 행 수를 `999`로 바꾸면 `report drift: metrics.analysis/bus/low_floor_bus_route_master.csv` 오류가 발생한다.
- **남은 한계:** 원본 파일을 포함하지 않는 CI는 로컬 source comparison SHA와 원본 재집계를 검증하지 않는다. 원본까지 바뀐 경우에는 동일 원본을 가진 로컬 환경에서 `--source-root` 전체 대조를 다시 실행하고 audit JSON을 갱신해야 한다.

## 5. 원본 없는 CI에서 버스 플래그와 수치의 내부 모순 누락 위험

- **문제 상황:** 원본 혼잡 CSV가 없는 CI에서는 `compare_congestion()`이 `not_verified_source_missing`으로 남는다. 이때 export 안에서 `congestion_data_available=0`인데 row count와 proxy 값이 남아 있거나, `low_floor_bus_count=0`인데 `has_low_floor_bus=1`인 모순을 자체 검사로 충분히 잡아야 한다.
- **영향:** 원본 재집계가 없는 환경에서 형식상 유효하지만 의미상 모순된 버스 export가 통과할 수 있다. 서비스는 이 export를 provider로 쓰므로 접근성/혼잡 해석이 틀어질 수 있다.
- **재현 방법:** 버스 master fixture에서 `low_floor_bus_count`, `has_low_floor_bus`, `accessibility_status`, `congestion_data_available`, `congestion_row_count`, `max_low_floor_bus_load_per_bus`, `p95_low_floor_bus_load_per_bus` 중 하나를 상충되게 바꾸고 `validate_bus()`를 실행한다.
- **원인:** 최초 검사는 개별 숫자 domain과 접근성 status 일부만 검증했고, availability 플래그와 관련 수치 컬럼의 상호 관계를 명시적으로 모두 확인하지 않았다.
- **검토한 대안:** 원본 혼잡 CSV를 CI에 추가(대용량 원본 관리 범위 변경), CI에서만 fixture 비교(실제 export 내부 모순을 놓침), `validate_bus()` 자체의 상호 정합성 규칙 강화(채택).
- **해결 방법:** `has_low_floor_bus` domain, 저상버스 count와 flag/status 관계, missing count와 unknown 상태, congestion availability와 row count/proxy 값 관계를 `validate_bus()`에 추가했다.
- **검증 결과:** 단위 테스트에서 6개 상호 모순 fixture가 모두 오류로 검출된다. 현재 committed bus export는 강화된 검사로도 오류 0이다.
- **남은 한계:** peak 시간·정류장·방향의 원본 재집계는 여전히 로컬 원본이 있어야 가능하다. CI는 export 내부 모순과 committed snapshot drift까지만 보장한다.
