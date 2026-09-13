import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import type { RecommendationResponse } from '../api/recommendation'
import TransportCostTracker from '../components/TransportCostTracker'

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  vi.setSystemTime(new Date('2026-09-13T00:00:00+09:00'))
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
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

const dailyResponse = {
  date: '2026-09-13',
  records: [{
    id: 1,
    travel_date: '2026-09-13',
    actual_cost_won: 2000,
    recommended_cost_won: 1400,
    potential_savings_won: 600,
    selected_transport_type: 'subway',
    recommended_transport_type: 'low_floor_bus',
    created_at: '2026-09-13T00:00:00Z',
  }],
  totals: { actual_cost_won: 2000, recommended_cost_won: 1400, potential_savings_won: 600 },
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

function mockTransportCostFetch({ failDaily = false }: { failDaily?: boolean } = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
    const url = String(input)
    if (init && 'method' in init && init.method === 'POST') {
      return jsonResponse({
        id: 2, travel_date: '2026-09-13', actual_cost_won: 2100,
        recommended_cost_won: 1400, potential_savings_won: 700,
        selected_transport_type: 'subway', recommended_transport_type: 'low_floor_bus', created_at: '2026-09-13T00:00:00Z',
      }, 201)
    }
    if (url.includes('/transport-cost-records/monthly')) return jsonResponse(monthlyResponse)
    if (url.includes('/transport-cost-records/daily')) {
      if (failDaily) return jsonResponse({ detail: 'daily lookup failed' }, 500)
      return jsonResponse(dailyResponse)
    }
    return jsonResponse({}, 404)
  })
}

test('renders Backend monthly totals without recalculating them', async () => {
  mockTransportCostFetch()
  render(<TransportCostTracker result={result} />)

  expect(screen.getByRole('status', { name: '' })).toHaveTextContent('월별 교통비를 불러오는 중입니다.')
  expect((await screen.findAllByText('2,000원')).length).toBeGreaterThan(0)
  expect(screen.getAllByText('600원').length).toBeGreaterThan(0)
  expect(screen.getByRole('grid', { name: '2026-09 교통비 캘린더' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /2026-09-13 교통비 실제 2,000원/ })).toBeInTheDocument()
  expect(screen.getByText(/지하철 실제 2,000원/)).toBeInTheDocument()
})

test('announces an empty daily detail without treating it as an error', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = String(input)
    if (url.includes('/transport-cost-records/monthly')) {
      return jsonResponse({ ...monthlyResponse, daily_summaries: [], totals: { actual_cost_won: 0, recommended_cost_won: 0, potential_savings_won: 0 } })
    }
    if (url.includes('/transport-cost-records/daily')) {
      return jsonResponse({ ...dailyResponse, records: [], totals: { actual_cost_won: 0, recommended_cost_won: 0, potential_savings_won: 0 } })
    }
    return jsonResponse({}, 404)
  })
  render(<TransportCostTracker result={result} />)

  expect(await screen.findByText('선택한 날짜의 교통비 기록이 없습니다.')).toBeInTheDocument()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

test('submits actual cost and route conditions then refreshes the month', async () => {
  const fetchMock = mockTransportCostFetch()
  render(<TransportCostTracker result={result} />)

  fireEvent.change(screen.getByLabelText('이용 날짜'), { target: { value: '2026-09-13' } })
  fireEvent.change(screen.getByLabelText('실제 이용금액(원)'), { target: { value: '2100' } })
  fireEvent.click(screen.getByRole('button', { name: '교통비 저장' }))

  expect(await screen.findByText('교통비를 저장했습니다.')).toBeInTheDocument()
  await waitFor(() => expect(fetchMock.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(true))
  const postCall = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST')
  const [, postOptions] = postCall ?? []
  expect(postOptions?.method).toBe('POST')
  expect(JSON.parse(postOptions?.body as string)).toMatchObject({
    actual_cost_won: 2100,
    selected_transport_type: 'subway',
    transport_types: ['subway', 'low_floor_bus'],
  })
})

test('keeps saved status when refresh after saving fails', async () => {
  mockTransportCostFetch({ failDaily: true })
  render(<TransportCostTracker result={result} />)

  fireEvent.change(screen.getByLabelText('이용 날짜'), { target: { value: '2026-09-13' } })
  fireEvent.change(screen.getByLabelText('실제 이용금액(원)'), { target: { value: '2100' } })
  fireEvent.click(screen.getByRole('button', { name: '교통비 저장' }))

  expect(await screen.findByText('교통비를 저장했습니다.')).toBeInTheDocument()
  expect(screen.queryByText('교통비를 저장하지 못했습니다.')).not.toBeInTheDocument()
  expect(await screen.findByText('선택한 날짜의 상세 기록을 불러오지 못했습니다.')).toBeInTheDocument()
  expect(screen.getByRole('grid', { name: '2026-09 교통비 캘린더' })).toBeInTheDocument()
})
