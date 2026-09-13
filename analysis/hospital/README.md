# 병원 분석 reviewed export

- `hospital_analytics.json`: Phase 3에서 검토·확정한 네 분석 ID의 정적 reviewed 데이터다.
- `figures/*.png`: 기존 Notebook 저장 그래프 중 reviewed asset으로 사람이 선택해 복사한 파일이다.
- 출처와 해석 제한: `hospital_destination_insights.md`
- 기준 기간: 2025-01-01~2025-12-31, 접수일시, Asia/Seoul

현재 Backend API와 Frontend UI에서는 이 데이터를 제공하지 않는다. 갱신 시 원본 Notebook 결과를 검토한 뒤 JSON schema version, 모집단, 기간, 제한사항과 그래프를 함께 갱신한다. 서비스 노출을 다시 결정하기 전까지 consumer나 서비스 URL을 추가하지 않는다.
