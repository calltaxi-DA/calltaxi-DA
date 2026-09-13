import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { HospitalAnalyticsResponse } from '../api/hospitalAnalytics'
import HospitalAnalytics from '../components/HospitalAnalytics'

describe('hospital analytics', () => {
  it('renders backend-owned table, period, limitations and reviewed chart', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://backend.test')
    const result: HospitalAnalyticsResponse = {
      schema_version: '1.0',
      source_period: { start_date: '2025-01-01', end_date: '2025-12-31', basis: '접수일시', timezone: 'Asia/Seoul' },
      analyses: [{
        analysis_id: 'medical_destination_top_regions', title: '의료목적콜 도착이 많은 지역',
        population_definition: '의료목적 탑승완료', aggregation_unit: '자치구',
        values: { district_top5: [{ name: '노원구', count: 11531 }], neighborhood_top5: [] }, limitations: ['개별 병원 방문량이 아닙니다.'],
      }],
      charts: [{ chart_id: 'chart', title: '이동 비교', alt_text: '이동 비율 비교 그래프', asset_url: '/analytics/hospital/charts/chart', analysis_ids: [] }],
    }
    render(<HospitalAnalytics result={result} />)
    expect(screen.getByText('2025-01-01~2025-12-31 접수일시 기준')).toBeInTheDocument()
    expect(screen.getByText('노원구')).toBeInTheDocument()
    expect(screen.getByText('11,531건')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '이동 비율 비교 그래프' })).toHaveAttribute('src', 'http://backend.test/analytics/hospital/charts/chart')
    expect(screen.getByText('개별 병원 방문량이 아닙니다.')).toBeInTheDocument()
    vi.unstubAllEnvs()
  })
})
