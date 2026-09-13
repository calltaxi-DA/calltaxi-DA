import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import type { RecommendationResponse } from '../api/recommendation'
import RecommendationResults from '../components/RecommendationResults'

type MockPlace = { id: string; place_name: string; address_name: string; road_address_name: string; x: string; y: string }
const originPlace = createPlace('origin', '서울시청', '126.9786567', '37.566826')
const destinationPlace = createPlace('destination', '강남역', '127.027621', '37.497942')

function createPlace(id: string, placeName: string, x: string, y: string): MockPlace {
  return { id, place_name: placeName, address_name: `${placeName} 지번주소`, road_address_name: `${placeName} 도로명주소`, x, y }
}

function recommendationResult(): RecommendationResponse {
  const availableMetrics = { total_time_seconds: 'available', total_distance_meters: 'available', total_cost_won: 'available', walking_distance_meters: 'available', walking_time_seconds: 'available' } as const
  return {
    origin: { name: '서울시청', latitude: 37.566826, longitude: 126.9786567, address: '서울시청 도로명주소' },
    destination: { name: '강남역', latitude: 37.497942, longitude: 127.027621, address: '강남역 도로명주소' },
    transport_types: ['calltaxi', 'subway', 'low_floor_bus'],
    priorities: ['time', 'cost', 'walk'],
    recommendations: [
      { rank: 1, route: { transport_type: 'subway', status: 'available', total_time_seconds: 2340, total_distance_meters: 13530, total_cost_won: 1650, walking_distance_meters: 330, walking_time_seconds: 660, metric_availability: availableMetrics, accessibility_status: 'not_verified', unavailable_reason: null, summary: '을지로입구역 → 강남역 지하철 경로', warnings: ['일부 역 접근성은 상세 확인이 필요합니다.'] } },
      { rank: 2, route: { transport_type: 'low_floor_bus', status: 'available', total_time_seconds: 2460, total_distance_meters: 10366, total_cost_won: 1500, walking_distance_meters: 676, walking_time_seconds: 600, metric_availability: availableMetrics, accessibility_status: 'verified_available', unavailable_reason: null, summary: '470 저상버스 경로', warnings: ['실제 도착 차량의 저상 여부를 보장하지 않습니다.'] } },
    ],
    excluded_routes: [{ transport_type: 'calltaxi', reason: '장애인 콜택시 대기시간 예측 모델이 연결되지 않았습니다.' }],
  }
}

function setupKakaoMock(
  keywordSearch = vi.fn((keyword: string, callback: (results: MockPlace[], status: string) => void) => callback([keyword === '강남역' ? destinationPlace : originPlace], 'OK')),
) {
  vi.stubEnv('KAKAO_JS_KEY', 'test-key')
  const setCenter = vi.fn()
  const markerSetMap = vi.fn()
  const markerConstructor = vi.fn(function () { return { setMap: markerSetMap } })
  window.kakao = { maps: { load: (callback) => callback(), Map: vi.fn(function () { return { setCenter } }), LatLng: vi.fn(function (lat, lng) { return { lat, lng } }), Marker: markerConstructor, services: { Places: vi.fn(function () { return { keywordSearch } }), Status: { OK: 'OK', ZERO_RESULT: 'ZERO_RESULT' } } } }
  return { keywordSearch, markerConstructor, markerSetMap, setCenter }
}

async function selectRoutePlaces() {
  await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
  fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
  fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0]); fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
  fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '강남역' } })
  fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1]); fireEvent.click(screen.getByRole('button', { name: /강남역/ }))
}

function selectCalltaxiPurpose(purpose = '치료') {
  fireEvent.change(screen.getByLabelText('장애인 콜택시 이용목적'), { target: { value: purpose } })
}

function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done }); return { promise, resolve } }

afterEach(() => { cleanup(); vi.unstubAllEnvs(); vi.restoreAllMocks(); vi.unstubAllGlobals(); delete window.kakao })

describe('Frontend Phase 7 recommendation UI', () => {
  it('selects all three transports initially and shows draggable priority controls', () => {
    vi.stubEnv('KAKAO_JS_KEY', ''); render(<App />)
    expect(screen.getByLabelText('장애인 콜택시')).toBeChecked(); expect(screen.getByLabelText('지하철')).toBeChecked(); expect(screen.getByLabelText('저상버스')).toBeChecked()
    expect(screen.getByText('1순위 시간 우선')).toBeInTheDocument(); expect(screen.getByText('2순위 금액 우선')).toBeInTheDocument(); expect(screen.getByText('3순위 최소 도보')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })

  it('disables search when all transports are unchecked and enables it after one is selected', async () => {
    setupKakaoMock(); render(<App />); await selectRoutePlaces()
    fireEvent.click(screen.getByLabelText('장애인 콜택시')); fireEvent.click(screen.getByLabelText('지하철')); fireEvent.click(screen.getByLabelText('저상버스'))
    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
    fireEvent.click(screen.getByLabelText('지하철'))
    expect(screen.getByRole('button', { name: '경로검색' })).toBeEnabled()
  })

  it('requires calltaxi purpose when calltaxi is selected', async () => {
    setupKakaoMock(); render(<App />); await selectRoutePlaces()
    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
    expect(screen.getByText('장애인 콜택시를 포함해 검색하려면 이동 조건 설정에서 이용목적을 선택해주세요.')).toBeInTheDocument()
    selectCalltaxiPurpose()
    expect(screen.getByRole('button', { name: '경로검색' })).toBeEnabled()
    expect(screen.queryByText('장애인 콜택시를 포함해 검색하려면 이동 조건 설정에서 이용목적을 선택해주세요.')).not.toBeInTheDocument()
  })

  it('sends only selected transport types to the backend', async () => {
    setupKakaoMock(); const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...recommendationResult(), transport_types: ['subway', 'low_floor_bus'] }) }); vi.stubGlobal('fetch', fetchMock); render(<App />); await selectRoutePlaces()
    fireEvent.click(screen.getByLabelText('장애인 콜택시')); fireEvent.click(screen.getByRole('button', { name: '경로검색' }))
    expect(screen.getByText('선택한 이동수단의 경로와 추천 순위를 계산하고 있습니다.')).toBeInTheDocument()
    expect(screen.queryByText(/세 이동수단의 경로/)).not.toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.transport_types).toEqual(['subway', 'low_floor_bus'])
    expect(body.calltaxi_purpose).toBeUndefined()
  })

  it('requests backend-owned recommendations and compares ranked metrics and accessibility', async () => {
    setupKakaoMock(); const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => recommendationResult() }); vi.stubGlobal('fetch', fetchMock); render(<App />)
    await selectRoutePlaces(); selectCalltaxiPurpose(); fireEvent.click(screen.getByRole('button', { name: '경로검색' }))
    expect(screen.getByText('선택한 이동수단의 경로와 추천 순위를 계산하고 있습니다.')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: '추천 경로 최대 TOP 3' })).toBeInTheDocument()
    expect(screen.getByText('1위')).toBeInTheDocument(); expect(screen.getByText('2위')).toBeInTheDocument()
    expect(screen.getByText('39분')).toBeInTheDocument(); expect(screen.getByText('1,650원')).toBeInTheDocument(); expect(screen.getByText('330m')).toBeInTheDocument(); expect(screen.getByText('11분')).toBeInTheDocument()
    expect(screen.getByText('접근성 미확인')).toBeInTheDocument(); expect(screen.getByText('접근성 확인됨')).toBeInTheDocument()
    expect(screen.getByText(/대기시간 예측 모델이 연결되지 않았습니다/)).toBeInTheDocument()
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.priorities).toEqual(['time', 'cost', 'walk']); expect(body.transport_types).toEqual(['calltaxi', 'subway', 'low_floor_bus'])
    expect(body.calltaxi_purpose).toBe('치료')
  })

  it('sends the swapped priority order without ranking routes in the frontend', async () => {
    setupKakaoMock(); const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...recommendationResult(), priorities: ['walk', 'cost', 'time'] }) }); vi.stubGlobal('fetch', fetchMock); render(<App />)
    await selectRoutePlaces(); selectCalltaxiPurpose()
    const walkItem = screen.getByText('3순위 최소 도보').closest('li'); const timeItem = screen.getByText('1순위 시간 우선').closest('li')
    fireEvent.dragStart(walkItem!); fireEvent.dragOver(timeItem!); fireEvent.drop(timeItem!)
    expect(screen.getByText('1순위 최소 도보')).toBeInTheDocument(); expect(screen.getByText('2순위 시간 우선')).toBeInTheDocument(); expect(screen.getByText('3순위 금액 우선')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled()); expect(JSON.parse(fetchMock.mock.calls[0][1].body).priorities).toEqual(['walk', 'time', 'cost'])
  })

  it('shows a recoverable error when the recommendation API fails', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    setupKakaoMock(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 })); render(<App />)
    await selectRoutePlaces(); selectCalltaxiPurpose(); fireEvent.click(screen.getByRole('button', { name: '경로검색' })); expect(await screen.findByRole('alert')).toHaveTextContent('추천 경로를 불러오지 못했어요')
    expect(consoleError).toHaveBeenCalledWith('Recommendation request failed', expect.objectContaining({ requestUrl: 'http://127.0.0.1:8000/routes/recommendations', status: 502 }))
  })

  it('ignores an older response after the destination changes', async () => {
    setupKakaoMock(); const pending = deferred<{ ok: boolean; json: () => Promise<RecommendationResponse> }>(); const fetchMock = vi.fn().mockReturnValue(pending.promise); vi.stubGlobal('fetch', fetchMock); render(<App />); await selectRoutePlaces()
    selectCalltaxiPurpose(); fireEvent.click(screen.getByRole('button', { name: '경로검색' })); const signal = fetchMock.mock.calls[0][1].signal as AbortSignal
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } }); expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve({ ok: true, json: async () => recommendationResult() }); await pending.promise }); expect(screen.queryByRole('heading', { name: '추천 경로 최대 TOP 3' })).not.toBeInTheDocument()
  })

  it('aborts and ignores an in-flight response when transport selection changes', async () => {
    setupKakaoMock(); const pending = deferred<{ ok: boolean; json: () => Promise<RecommendationResponse> }>(); const fetchMock = vi.fn().mockReturnValue(pending.promise); vi.stubGlobal('fetch', fetchMock); render(<App />); await selectRoutePlaces()
    selectCalltaxiPurpose(); fireEvent.click(screen.getByRole('button', { name: '경로검색' })); const signal = fetchMock.mock.calls[0][1].signal as AbortSignal
    fireEvent.click(screen.getByLabelText('장애인 콜택시')); expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve({ ok: true, json: async () => recommendationResult() }); await pending.promise })
    expect(screen.queryByRole('heading', { name: '추천 경로 최대 TOP 3' })).not.toBeInTheDocument()
  })

  it('aborts and ignores an in-flight response when priority order changes', async () => {
    setupKakaoMock(); const pending = deferred<{ ok: boolean; json: () => Promise<RecommendationResponse> }>(); const fetchMock = vi.fn().mockReturnValue(pending.promise); vi.stubGlobal('fetch', fetchMock); render(<App />); await selectRoutePlaces()
    selectCalltaxiPurpose(); fireEvent.click(screen.getByRole('button', { name: '경로검색' })); const signal = fetchMock.mock.calls[0][1].signal as AbortSignal
    fireEvent.click(screen.getByRole('button', { name: '3순위 위로 이동' })); expect(signal.aborted).toBe(true)
    await act(async () => { pending.resolve({ ok: true, json: async () => recommendationResult() }); await pending.promise })
    expect(screen.queryByRole('heading', { name: '추천 경로 최대 TOP 3' })).not.toBeInTheDocument()
  })

  it('shows unknown walking metrics as comparison unavailable rather than zero', () => {
    const result = recommendationResult(); result.recommendations[0].route.metric_availability = { ...result.recommendations[0].route.metric_availability, walking_distance_meters: 'not_available', walking_time_seconds: 'not_available' }
    render(<RecommendationResults result={result} />); expect(screen.getAllByText('비교 불가')).toHaveLength(2); expect(screen.queryByText('0m')).not.toBeInTheDocument(); expect(screen.queryByText('0분')).not.toBeInTheDocument()
  })

  it('can display all three ranked transports while preserving unknown calltaxi walking metrics', () => {
    const result = recommendationResult()
    result.recommendations.push({ rank: 3, route: {
      transport_type: 'calltaxi', status: 'available', total_time_seconds: 3600, total_distance_meters: 12000,
      total_cost_won: 2500, predicted_waiting_time_seconds: 1500, vehicle_time_seconds: 2100,
      walking_distance_meters: null, walking_time_seconds: null,
      metric_availability: { total_time_seconds: 'available', total_distance_meters: 'available', total_cost_won: 'available', walking_distance_meters: 'not_available', walking_time_seconds: 'not_available' },
      accessibility_status: 'not_verified', unavailable_reason: null, summary: '장애인 콜택시 경로',
      warnings: ['콜택시 승하차 접근 도보 데이터가 없어 도보 지표를 비교할 수 없습니다.'],
    } })
    result.excluded_routes = []
    render(<RecommendationResults result={result} />)
    expect(screen.getByText('3위')).toBeInTheDocument(); expect(screen.getAllByText('장애인 콜택시')).toHaveLength(1)
    expect(screen.getAllByText('비교 불가')).toHaveLength(2); expect(screen.getByText(/승하차 접근 도보 데이터가 없어/)).toBeInTheDocument()
    const breakdown = screen.getByLabelText('장애인 콜택시 시간 구성')
    expect(within(breakdown).getByText('예상 대기시간')).toBeInTheDocument()
    expect(within(breakdown).getByText('차량 이동시간')).toBeInTheDocument()
    expect(within(breakdown).getByText('총 예상시간')).toBeInTheDocument()
    expect(within(breakdown).getByText('25분')).toBeInTheDocument()
    expect(within(breakdown).getByText('35분')).toBeInTheDocument()
    expect(within(breakdown).getByText('1시간')).toBeInTheDocument()
    expect(screen.getByText('12.0km')).toBeInTheDocument()
    expect(screen.getByText('2,500원')).toBeInTheDocument()
  })

  it('requires both selected places before requesting recommendations', async () => {
    setupKakaoMock(); render(<App />)
    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0]); fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })

  it('guides users when place search is used before the map service is ready', () => {
    render(<App />); fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } }); fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    expect(screen.getByText('지도 서비스가 준비된 뒤 다시 검색하세요.')).toBeInTheDocument()
  })

  it('shows every backend exclusion reason when no route can be recommended', () => {
    const result = recommendationResult(); result.recommendations = []; result.excluded_routes = [
      { transport_type: 'calltaxi', reason: '대기시간 예측 불가' },
      { transport_type: 'subway', reason: '지하철 경로 계산 불가' },
      { transport_type: 'low_floor_bus', reason: '저상버스 경로 계산 불가' },
    ]
    render(<RecommendationResults result={result} />)
    expect(screen.getByText('현재 추천 가능한 경로가 없습니다.')).toBeInTheDocument()
    expect(screen.getByText(/대기시간 예측 불가/)).toBeInTheDocument(); expect(screen.getByText(/지하철 경로 계산 불가/)).toBeInTheDocument(); expect(screen.getByText(/저상버스 경로 계산 불가/)).toBeInTheDocument()
  })

  it('renders search and recommendation results inside the same route panel', async () => {
    setupKakaoMock(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => recommendationResult() })); render(<App />); await selectRoutePlaces(); selectCalltaxiPurpose(); fireEvent.click(screen.getByRole('button', { name: '경로검색' }))
    const panel = screen.getByLabelText('경로 검색 패널')
    expect(panel).toContainElement(screen.getByLabelText('경로 검색 조건'))
    expect(panel).toContainElement(await screen.findByRole('heading', { name: '추천 경로 최대 TOP 3' }))
  })

  it('stores selected coordinates and creates a marker centered on the selected place', async () => {
    const { markerConstructor, setCenter } = setupKakaoMock()
    render(<App />)
    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    expect(screen.getByText(/37.566826/)).toBeInTheDocument()
    expect(screen.getByText(/126.978657/)).toBeInTheDocument()
    expect(markerConstructor).toHaveBeenCalledTimes(1)
    expect(setCenter).toHaveBeenCalledTimes(1)
  })

  it('ignores a stale place response after a newer search response', async () => {
    const callbacks: Array<(results: MockPlace[], status: string) => void> = []
    setupKakaoMock(vi.fn((_keyword: string, callback: (results: MockPlace[], status: string) => void) => { callbacks.push(callback) }))
    render(<App />)
    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    const originInput = screen.getByLabelText('출발지')
    fireEvent.change(originInput, { target: { value: '서울' } }); fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.change(originInput, { target: { value: '강남' } }); fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    act(() => callbacks[1]([destinationPlace], 'OK'))
    expect(screen.getByRole('button', { name: /강남역/ })).toBeInTheDocument()
    act(() => callbacks[0]([originPlace], 'OK'))
    expect(screen.queryByRole('button', { name: /서울시청/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /강남역/ })).toBeInTheDocument()
  })

  it('distinguishes a Kakao Places service error from no search results', async () => {
    setupKakaoMock(vi.fn((_keyword: string, callback: (results: MockPlace[], status: string) => void) => callback([], 'ERROR')))
    render(<App />)
    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    expect(screen.getByText('장소검색 서비스가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도하세요.')).toBeInTheDocument()
    expect(screen.queryByText(/검색 결과가 없습니다/)).not.toBeInTheDocument()
  })
})
