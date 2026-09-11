import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

afterEach(() => {
  cleanup()
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
  delete window.kakao
})

describe('App', () => {
  it('renders the route search input UI', () => {
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

  it('allows users to enter search conditions and submit them', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.change(screen.getByLabelText('1순위'), { target: { value: 'walk' } })

    const searchButton = screen.getByRole('button', { name: '경로검색' })
    expect(searchButton).toBeEnabled()

    fireEvent.click(searchButton)

    expect(
      screen.getByText(
        /서울시청에서 서울역까지 장애인 콜택시, 지하철, 저상버스 기준으로 1순위 도보 최소, 2순위 비용 최소, 3순위 시간 최소 경로를 검색합니다/,
      ),
    ).toBeInTheDocument()
  })

  it('guides users to wait when place search is used before the map service is ready', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.click(screen.getAllByRole('button', { name: '검색' })[0])

    expect(screen.getByText('지도 서비스가 준비된 뒤 다시 검색하세요.')).toBeInTheDocument()
  })

  it('shows an error when the Kakao script loads without the maps namespace', async () => {
    vi.stubEnv('VITE_KAKAO_MAP_APP_KEY', 'test-kakao-map-key')

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
    vi.stubEnv('VITE_KAKAO_MAP_APP_KEY', 'test-kakao-map-key')

    const setCenter = vi.fn()
    const setMap = vi.fn()
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

  it('distinguishes a Kakao Places service error from no search results', async () => {
    vi.stubEnv('VITE_KAKAO_MAP_APP_KEY', 'test-kakao-map-key')

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

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '서울시청' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })
    fireEvent.click(screen.getByLabelText('지하철'))

    const searchButton = screen.getByRole('button', { name: '경로검색' })
    expect(searchButton).toBeEnabled()

    fireEvent.click(searchButton)

    expect(screen.getByText(/장애인 콜택시, 저상버스 기준/)).toBeInTheDocument()
    expect(screen.queryByText(/장애인 콜택시, 지하철, 저상버스 기준/)).not.toBeInTheDocument()
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

    expect(screen.getByRole('button', { name: '경로검색' })).toBeEnabled()
  })

  it('keeps search disabled for whitespace-only origin or destination', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('출발지'), { target: { value: '   ' } })
    fireEvent.change(screen.getByLabelText('목적지'), { target: { value: '서울역' } })

    expect(screen.getByRole('button', { name: '경로검색' })).toBeDisabled()
  })
})
