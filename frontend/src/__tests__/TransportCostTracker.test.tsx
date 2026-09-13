import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'

import type { RecommendationResponse } from '../api/recommendation'
import TransportCostTracker from '../components/TransportCostTracker'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

const result: RecommendationResponse = {
  origin: { name: '서울시청', latitude: 37.5666, longitude: 126.9784, address: '' },
  destination: { name: '강남역', latitude: 37.4979, longitude: 127.0276, address: '' },
  transport_types: ['subway', 'low_floor_bus'],
  priorities: ['time', 'cost', 'walk'],
  recommendations: [
    {
      rank: 1,
      route: {
        transport_type: 'subway', status: 'available', total_time_seconds: 2400,
        total_distance_meters: 12000, total_cost_won: 1500, walking_distance_meters: 300,
        walking_time_seconds: 360,
        metric_availability: {
          total_time_seconds: 'available', total_distance_meters: 'available',
          total_cost_won: 'available', walking_distance_meters: 'available', walking_time_seconds: 'available',
        },
        accessibility_status: 'verified_available', unavailable_reason: null, summary: null, warnings: [],
      },
    },
  ],
  excluded_routes: [],
}

const monthlyResponse = {
  month: '2026-09',
  daily_summaries: [{
    date: '2026-09-13', record_count: 1, actual_cost_won: 2000,
    recommended_cost_won: 1400, potential_savings_won: 600,
  }],
  totals: { actual_cost_won: 2000, recommended_cost_won: 1400, potential_savings_won: 600 },
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

test('renders Backend monthly totals without recalculating them', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse(monthlyResponse))
  render(<TransportCostTracker result={result} />)
  fireEvent.click(screen.getByRole('button', { name: '월별 조회' }))

  expect(await screen.findByText('2,000원')).toBeInTheDocument()
  expect(screen.getByText('600원')).toBeInTheDocument()
  expect(screen.getByText(/2026-09-13: 실제/)).toBeInTheDocument()
})

test('submits actual cost and route conditions then refreshes the month', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch')
    .mockImplementationOnce(() => jsonResponse({
      id: 2, travel_date: '2026-09-13', actual_cost_won: 2100,
      recommended_cost_won: 1400, potential_savings_won: 700,
      selected_transport_type: 'subway', recommended_transport_type: 'low_floor_bus', created_at: '2026-09-13T00:00:00Z',
    }, 201))
    .mockImplementationOnce(() => jsonResponse(monthlyResponse))
  render(<TransportCostTracker result={result} />)

  fireEvent.change(screen.getByLabelText('이용 날짜'), { target: { value: '2026-09-13' } })
  fireEvent.change(screen.getByLabelText('실제 이용금액(원)'), { target: { value: '2100' } })
  fireEvent.click(screen.getByRole('button', { name: '교통비 저장' }))

  expect(await screen.findByText('교통비를 저장했습니다.')).toBeInTheDocument()
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  const [, postOptions] = fetchMock.mock.calls[0]
  expect(postOptions?.method).toBe('POST')
  expect(JSON.parse(postOptions?.body as string)).toMatchObject({
    actual_cost_won: 2100,
    selected_transport_type: 'subway',
    transport_types: ['subway', 'low_floor_bus'],
  })
})
