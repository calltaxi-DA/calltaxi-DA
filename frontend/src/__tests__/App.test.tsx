import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import type { LowFloorBusRouteResult } from '../api/bus'
import type { SubwayRouteResult } from '../api/subway'
import LowFloorBusRouteCard from '../components/LowFloorBusRouteCard'
import SubwayRouteCard from '../components/SubwayRouteCard'

type MockPlace = {
  id: string
  place_name: string
  address_name: string
  road_address_name: string
  x: string
  y: string
}

function createPlace(id: string, placeName: string, x: string, y: string): MockPlace {
  return {
    id,
    place_name: placeName,
    address_name: `${placeName} 지번주소`,
    road_address_name: `${placeName} 도로명주소`,
    x,
    y,
  }
}

function createSubwayRoute(summary: string): SubwayRouteResult {
  return {
    transport_type: 'subway',
    status: 'available',
    total_time_seconds: 2520,
    total_distance_meters: 11400,
    total_cost_won: 1500,
    walking_distance_meters: 780,
    walking_time_seconds: 720,
    unavailable_reason: null,
    summary,
    warnings: ['접근성 lookup에 없는 역이 있어 상세 확인이 필요합니다.'],
  }
}

function createBusRoute(summary: string): LowFloorBusRouteResult {
  return {
    transport_type: 'low_floor_bus',
    status: 'available',
    total_time_seconds: 3180,
    total_distance_meters: 9200,
    total_cost_won: 1500,
    walking_distance_meters: 640,
    walking_time_seconds: 600,
    unavailable_reason: null,
    summary,
    warnings: [
      '저상버스 접근성은 노선 단위 정보이며 실제 도착 차량의 저상 여부를 보장하지 않습니다.',
      '도보 수치는 ODsay 경로의 모든 도보 구간 합계입니다.',
    ],
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

function setupKakaoMock(
  keywordSearch = vi.fn((_keyword, callback) => {
    callback([createPlace('place-1', '서울시청', '126.9786567', '37.566826')], 'OK')
  }),
) {
  vi.stubEnv('KAKAO_JS_KEY', 'test-kakao-map-key')

  const setCenter = vi.fn()
  const setMap = vi.fn()
  const markerConstructor = vi.fn(function () {
    return { setMap }
  })

  window.kakao = {
    maps: {
      load: (callback) => callback(),
      Map: vi.fn(function () {
        return { setCenter }
      }),
      LatLng: vi.fn(function (lat, lng) {
        return { lat, lng }
      }),
      Marker: markerConstructor,
      services: {
        Places: vi.fn(function () {
          return { keywordSearch }
        }),
        Status: {
          OK: 'OK',
          ZERO_RESULT: 'ZERO_RESULT',
        },
      },
    },
  }

  return { keywordSearch, markerConstructor, setCenter, setMap }
}

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  delete window.kakao
})

describe('App', () => {
  it('renders the route search input UI', () => {
    vi.stubEnv('KAKAO_JS_KEY', '')

    render(<App />)

    expect(
      screen.getByRole('heading', { name: /어디로 이동할까요/i }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('출발지')).toBeInTheDocument()
    expect(screen.getByLabelText('목적지')).toBeInTheDocument()
    expect(screen.getByLabelText('지도 위치 확인')).toBeInTheDocument()
    expect(screen.getByText(/Kakao Maps 앱 키를 설정하면 지도와 장소검색을 사용할 수 있습니다/)).toBeInTheDocument()
    expect(screen.getByLabelText('경로 검색 패널')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: '검색' })).toHaveLength(2)
    expect(screen.getByLabelText('장애인 콜택시')).toBeChecked()
    expect(screen.getByLabelText('지하철')).toBeChecked()
    expect(screen.getByLabelText('저상버스')).toBeChecked()
    expect(screen.getByLabelText('1순위')).toHaveValue('time')
    expect(screen.getByLabelText('2순위')).toHaveValue('cost')
    expect(screen.getByLabelText('3순위')).toHaveValue('walk')
    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })

  it('requires selected origin and destination places before users can submit', async () => {
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const destinationPlace = createPlace('destination-place', '서울역', '126.970671', '37.554678')
    setupKakaoMock(
      vi.fn((keyword, callback) => {
        callback([keyword === '서울역' ? destinationPlace : originPlace], 'OK')
      }),
    )
    render(<App />)

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.change(screen.getByLabelText('1순위'), { target: { value: 'walk' } })

    const searchButton = screen.getByRole('button', { name: '경로검색' })
    expect(searchButton).toBeDisabled()

    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    expect(searchButton).toBeDisabled()

    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    expect(searchButton).toBeEnabled()

    fireEvent.click(searchButton)

    expect(
      screen.getByText(
        /서울시청\(37.566826, 126.978657\)에서 서울역\(37.554678, 126.970671\)까지 장애인 콜택시, 지하철, 저상버스 기준으로 1순위 도보 최소, 2순위 비용 최소, 3순위 시간 최소 경로를 검색합니다/,
      ),
    ).toBeInTheDocument()
  })

  it('shows subway time, cost, walking burden, route, and accessibility information', async () => {
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const destinationPlace = createPlace('destination-place', '서울역', '126.970671', '37.554678')
    setupKakaoMock(
      vi.fn((keyword, callback) => {
        callback([keyword === '서울역' ? destinationPlace : originPlace], 'OK')
      }),
    )
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        transport_type: 'subway',
        status: 'available',
        total_time_seconds: 2520,
        total_distance_meters: 11400,
        total_cost_won: 1500,
        walking_distance_meters: 780,
        walking_time_seconds: 720,
        unavailable_reason: null,
        summary: '1호선 → 2호선',
        warnings: ['시청역 엘리베이터 접근 가능', '환승 내부 도보시간은 포함되지 않습니다.'],
      }),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    fireEvent.click(screen.getByLabelText('저상버스'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))

    expect(screen.getByText('지하철 경로와 접근성 정보를 확인하고 있습니다.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: '1호선 → 2호선' })).toBeInTheDocument())
    expect(screen.getByText('42분')).toBeInTheDocument()
    expect(screen.getByText('1,500원')).toBeInTheDocument()
    expect(screen.getByText('780m')).toBeInTheDocument()
    expect(screen.getByText('12분')).toBeInTheDocument()
    expect(screen.getByText('시청역 엘리베이터 접근 가능')).toBeInTheDocument()
    expect(screen.getByText('환승 내부 도보시간은 포함되지 않습니다.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/routes\/subway$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          origin: {
            name: '서울시청',
            latitude: 37.566826,
            longitude: 126.9786567,
            address: '서울시청 도로명주소',
          },
          destination: {
            name: '서울역',
            latitude: 37.554678,
            longitude: 126.970671,
            address: '서울역 도로명주소',
          },
        }),
      }),
    )
  })

  it('shows a recoverable error when the subway API request fails', async () => {
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const destinationPlace = createPlace('destination-place', '서울역', '126.970671', '37.554678')
    setupKakaoMock(
      vi.fn((keyword, callback) => {
        callback([keyword === '서울역' ? destinationPlace : originPlace], 'OK')
      }),
    )
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 }))
    render(<App />)
    fireEvent.click(screen.getByLabelText('저상버스'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('지하철 경로를 불러오지 못했어요')
    expect(screen.getByText(/백엔드 실행 상태와 ODsay 설정/)).toBeInTheDocument()
  })

  it('does not show an in-flight subway response after subway is unchecked', async () => {
    const pending = deferred<{ ok: boolean; json: () => Promise<SubwayRouteResult> }>()
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const destinationPlace = createPlace('destination-place', '서울역', '126.970671', '37.554678')
    setupKakaoMock(vi.fn((keyword, callback) => callback([keyword === '서울역' ? destinationPlace : originPlace], 'OK')))
    const fetchMock = vi.fn().mockReturnValue(pending.promise)
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    fireEvent.click(screen.getByLabelText('저상버스'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))

    const signal = fetchMock.mock.calls[0][1].signal as AbortSignal
    fireEvent.click(screen.getByLabelText('지하철'))
    expect(signal.aborted).toBe(true)

    await act(async () => {
      pending.resolve({ ok: true, json: async () => createSubwayRoute('이전 지하철 경로') })
      await pending.promise
    })
    expect(screen.queryByRole('heading', { name: '이전 지하철 경로' })).not.toBeInTheDocument()
  })

  it('does not show an in-flight response after a different destination is selected', async () => {
    const pending = deferred<{ ok: boolean; json: () => Promise<SubwayRouteResult> }>()
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const firstDestination = createPlace('destination-1', '서울역', '126.970671', '37.554678')
    const nextDestination = createPlace('destination-2', '강남역', '127.027621', '37.497942')
    let destinationSearchCount = 0
    setupKakaoMock(vi.fn((keyword, callback) => {
      if (keyword === '서울시청') {
        callback([originPlace], 'OK')
        return
      }
      destinationSearchCount += 1
      callback([destinationSearchCount === 1 ? firstDestination : nextDestination], 'OK')
    }))
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pending.promise))
    render(<App />)
    fireEvent.click(screen.getByLabelText('저상버스'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /강남역/ }))

    await act(async () => {
      pending.resolve({ ok: true, json: async () => createSubwayRoute('서울역 기준 이전 경로') })
      await pending.promise
    })
    expect(screen.queryByRole('heading', { name: '서울역 기준 이전 경로' })).not.toBeInTheDocument()
  })

  it('keeps the newest subway result when an older request resolves later', async () => {
    const firstRequest = deferred<{ ok: boolean; json: () => Promise<SubwayRouteResult> }>()
    const secondRequest = deferred<{ ok: boolean; json: () => Promise<SubwayRouteResult> }>()
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const firstDestination = createPlace('destination-1', '서울역', '126.970671', '37.554678')
    const nextDestination = createPlace('destination-2', '강남역', '127.027621', '37.497942')
    setupKakaoMock(vi.fn((keyword, callback) => {
      callback([keyword === '서울시청' ? originPlace : keyword === '강남역' ? nextDestination : firstDestination], 'OK')
    }))
    vi.stubGlobal('fetch', vi.fn().mockReturnValueOnce(firstRequest.promise).mockReturnValueOnce(secondRequest.promise))
    render(<App />)
    fireEvent.click(screen.getByLabelText('저상버스'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '강남역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /강남역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))

    await act(async () => {
      secondRequest.resolve({ ok: true, json: async () => createSubwayRoute('최신 강남역 경로') })
      await secondRequest.promise
    })
    expect(await screen.findByRole('heading', { name: '최신 강남역 경로' })).toBeInTheDocument()

    await act(async () => {
      firstRequest.resolve({ ok: true, json: async () => createSubwayRoute('늦게 도착한 서울역 경로') })
      await firstRequest.promise
    })
    expect(screen.getByRole('heading', { name: '최신 강남역 경로' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: '늦게 도착한 서울역 경로' })).not.toBeInTheDocument()
  })

  it('shows low-floor bus time, cost, walking burden, route, and accessibility information', async () => {
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const destinationPlace = createPlace('destination-place', '서울역', '126.970671', '37.554678')
    setupKakaoMock(vi.fn((keyword, callback) => {
      callback([keyword === '서울역' ? destinationPlace : originPlace], 'OK')
    }))
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => createBusRoute('701번 저상버스 경로'),
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    fireEvent.click(screen.getByLabelText('지하철'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))

    expect(screen.getByText('저상버스 경로와 접근성 정보를 확인하고 있습니다.')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: '701번 저상버스 경로' })).toBeInTheDocument()
    expect(screen.getByText('53분')).toBeInTheDocument()
    expect(screen.getByText('1,500원')).toBeInTheDocument()
    expect(screen.getByText('640m')).toBeInTheDocument()
    expect(screen.getByText('10분')).toBeInTheDocument()
    expect(screen.getByText(/실제 도착 차량의 저상 여부를 보장하지 않습니다/)).toBeInTheDocument()
    expect(screen.getByText(/모든 도보 구간 합계입니다/)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/routes\/bus$/),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          origin: {
            name: '서울시청', latitude: 37.566826, longitude: 126.9786567, address: '서울시청 도로명주소',
          },
          destination: {
            name: '서울역', latitude: 37.554678, longitude: 126.970671, address: '서울역 도로명주소',
          },
        }),
      }),
    )
  })

  it('shows a recoverable error when the low-floor bus API request fails', async () => {
    const originPlace = createPlace('origin-place', '서울시청', '126.9786567', '37.566826')
    const destinationPlace = createPlace('destination-place', '서울역', '126.970671', '37.554678')
    setupKakaoMock(vi.fn((keyword, callback) => {
      callback([keyword === '서울역' ? destinationPlace : originPlace], 'OK')
    }))
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 502 }))
    render(<App />)
    fireEvent.click(screen.getByLabelText('지하철'))

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[1])
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))
    fireEvent.click(screen.getByRole('button', { name: '경로검색' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('저상버스 경로를 불러오지 못했어요')
    expect(screen.getByText(/백엔드 실행 상태와 ODsay 설정/)).toBeInTheDocument()
  })

  it('renders an unavailable low-floor bus route without numeric placeholders', () => {
    render(<LowFloorBusRouteCard route={{
      transport_type: 'low_floor_bus',
      status: 'unavailable',
      total_time_seconds: null,
      total_distance_meters: null,
      total_cost_won: null,
      walking_distance_meters: null,
      walking_time_seconds: null,
      unavailable_reason: '이용 가능한 저상버스 경로가 없습니다.',
      summary: null,
      warnings: [],
    }} />)

    expect(screen.getByText('이용 가능한 저상버스 경로가 없습니다.')).toBeInTheDocument()
    expect(screen.queryByText('0분')).not.toBeInTheDocument()
    expect(screen.queryByText('0원')).not.toBeInTheDocument()
  })

  it('renders the unavailable contract without numeric placeholders', () => {
    render(
      <SubwayRouteCard route={{
        transport_type: 'subway',
        status: 'unavailable',
        total_time_seconds: null,
        total_distance_meters: null,
        total_cost_won: null,
        walking_distance_meters: null,
        walking_time_seconds: null,
        unavailable_reason: '이용 가능한 지하철 경로가 없습니다.',
        summary: null,
        warnings: [],
      }} />,
    )

    expect(screen.getByText('이용 가능한 지하철 경로가 없습니다.')).toBeInTheDocument()
    expect(screen.queryByText('0분')).not.toBeInTheDocument()
    expect(screen.queryByText('0원')).not.toBeInTheDocument()
  })

  it('guides users to wait when place search is used before the map service is ready', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    expect(screen.getByText('지도 서비스가 준비된 뒤 다시 검색하세요.')).toBeInTheDocument()
  })

  it('shows an error when the Kakao script loads without the maps namespace', async () => {
    vi.stubEnv('KAKAO_JS_KEY', 'test-kakao-map-key')

    render(<App />)

    const script = document.querySelector<HTMLScriptElement>('script[data-kakao-map-sdk]')
    script?.dispatchEvent(new Event('load'))

    await waitFor(() =>
      expect(
        screen.getByText('Kakao Maps SDK를 불러오지 못했습니다. 앱 키와 도메인 설정을 확인하세요.'),
      ).toBeInTheDocument(),
    )
  })

  it('searches places, stores selected coordinates, and creates a map marker', async () => {
    const keywordSearch = vi.fn((_keyword, callback) => {
      callback(
        [
          {
            id: 'place-1',
            place_name: '서울시청',
            address_name: '서울 중구 태평로1가',
            road_address_name: '서울 중구 세종대로 110',
            x: '126.9786567',
            y: '37.566826',
          },
        ],
        'OK',
      )
    })
    const { markerConstructor, setCenter } = setupKakaoMock(keywordSearch)

    render(<App />)

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    expect(keywordSearch).toHaveBeenCalledWith('서울시청', expect.any(Function))
    expect(screen.getByText('서울 중구 세종대로 110')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))

    expect(screen.getByDisplayValue('서울시청')).toBeInTheDocument()
    expect(screen.getByText(/37.566826/)).toBeInTheDocument()
    expect(screen.getByText(/126.978657/)).toBeInTheDocument()
    await waitFor(() => expect(markerConstructor).toHaveBeenCalledTimes(1))
    expect(setCenter).toHaveBeenCalledTimes(1)
  })

  it('removes an existing marker when the selected place input changes', async () => {
    const { setMap } = setupKakaoMock()

    render(<App />)

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.click(screen.getByRole('button', { name: /서울시청/ }))

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '강남역' } })

    expect(setMap).toHaveBeenCalledWith(null)
    expect(screen.queryByText(/37.566826/)).not.toBeInTheDocument()
  })

  it('ignores stale place search responses when a newer search finishes first', async () => {
    const callbacks: Array<(results: MockPlace[], status: string) => void> = []
    const keywordSearch = vi.fn((_keyword, callback) => {
      callbacks.push(callback)
    })
    setupKakaoMock(keywordSearch)

    render(<App />)

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])
    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '강남역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    act(() => {
      callbacks[1]([createPlace('place-2', '강남역', '127.027621', '37.497942')], 'OK')
    })
    await waitFor(() => expect(screen.getByText('강남역 도로명주소')).toBeInTheDocument())

    act(() => {
      callbacks[0]([createPlace('place-1', '서울역', '126.970671', '37.554678')], 'OK')
    })
    expect(screen.getByText('강남역 도로명주소')).toBeInTheDocument()
    expect(screen.queryByText('서울역 도로명주소')).not.toBeInTheDocument()
  })

  it('ignores pending place search responses after a place is selected', async () => {
    const callbacks: Array<(results: MockPlace[], status: string) => void> = []
    const keywordSearch = vi.fn((_keyword, callback) => {
      callbacks.push(callback)
    })
    setupKakaoMock(keywordSearch)

    render(<App />)

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    act(() => {
      callbacks[0]([createPlace('place-1', '서울역', '126.970671', '37.554678')], 'OK')
    })
    await waitFor(() => expect(screen.getByText('서울역 도로명주소')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '강남역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    act(() => {
      callbacks[2]([createPlace('place-3', '서울역', '126.970671', '37.554678')], 'OK')
    })
    await waitFor(() => expect(screen.getByText('서울역 도로명주소')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: /서울역/ }))

    act(() => {
      callbacks[1]([createPlace('place-2', '강남역', '127.027621', '37.497942')], 'OK')
    })
    await waitFor(() => expect(screen.getByText(/서울역 도로명주소/)).toBeInTheDocument())
    expect(screen.queryByText(/강남역 도로명주소/)).not.toBeInTheDocument()
  })

  it('distinguishes a Kakao Places service error from no search results', async () => {
    vi.stubEnv('KAKAO_JS_KEY', 'test-kakao-map-key')

    const keywordSearch = vi.fn((_keyword, callback) => {
      callback([], 'ERROR')
    })

    window.kakao = {
      maps: {
        load: (callback) => callback(),
        Map: vi.fn(function () {
          return { setCenter: vi.fn() }
        }),
        LatLng: vi.fn(function (lat, lng) {
          return { lat, lng }
        }),
        Marker: vi.fn(function () {
          return { setMap: vi.fn() }
        }),
        services: {
          Places: vi.fn(function () {
            return { keywordSearch }
          }),
          Status: {
            OK: 'OK',
            ZERO_RESULT: 'ZERO_RESULT',
          },
        },
      },
    }

    render(<App />)

    await waitFor(() => expect(screen.getByText('장소를 검색하고 출발지·목적지를 선택하세요.')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    expect(
      screen.getByText('장소검색 서비스가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도하세요.'),
    ).toBeInTheDocument()
  })

  it('swaps priority ranks instead of allowing duplicate priority values', () => {
    render(<App />)

    const firstPriority = screen.getByLabelText('1순위') as HTMLSelectElement
    const secondPriority = screen.getByLabelText('2순위') as HTMLSelectElement
    const thirdPriority = screen.getByLabelText('3순위') as HTMLSelectElement

    fireEvent.change(firstPriority, { target: { value: 'walk' } })

    expect(firstPriority).toHaveValue('walk')
    expect(secondPriority).toHaveValue('cost')
    expect(thirdPriority).toHaveValue('time')
    expect(new Set([firstPriority.value, secondPriority.value, thirdPriority.value]).size).toBe(3)
  })

  it('allows users to select transport types', () => {
    render(<App />)

    fireEvent.click(screen.getByLabelText('지하철'))

    const searchButton = screen.getByRole('button', { name: '경로검색' })
    expect(screen.getByLabelText('지하철')).not.toBeChecked()
    expect(searchButton).toBeDisabled()
  })

  it('disables search when all transport types are unchecked and enables it again', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })

    fireEvent.click(screen.getByLabelText('장애인 콜택시'))
    fireEvent.click(screen.getByLabelText('지하철'))
    fireEvent.click(screen.getByLabelText('저상버스'))

    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()

    fireEvent.click(screen.getByLabelText('지하철'))

    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })

  it('keeps search disabled for whitespace-only origin or destination', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '   ' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })

    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })
})
