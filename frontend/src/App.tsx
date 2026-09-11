import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'

type LocationRole = 'origin' | 'destination'

type PlaceSelection = {
  id: string
  name: string
  address: string
  lat: number
  lng: number
}

type KakaoPlace = {
  id: string
  place_name: string
  address_name: string
  road_address_name: string
  x: string
  y: string
}

type KakaoMap = {
  setCenter: (latLng: KakaoLatLng) => void
}

type KakaoLatLng = unknown

type KakaoMarker = {
  setMap: (map: KakaoMap | null) => void
}

type KakaoPlaces = {
  keywordSearch: (
    keyword: string,
    callback: (results: KakaoPlace[], status: string) => void,
  ) => void
}

declare global {
  interface Window {
    kakao?: {
      maps: {
        load: (callback: () => void) => void
        Map: new (container: HTMLElement, options: { center: KakaoLatLng; level: number }) => KakaoMap
        LatLng: new (lat: number, lng: number) => KakaoLatLng
        Marker: new (options: { map: KakaoMap; position: KakaoLatLng }) => KakaoMarker
        services: {
          Places: new () => KakaoPlaces
          Status: {
            OK: string
          }
        }
      }
    }
  }
}

const transportOptions = [
  { value: 'calltaxi', label: '장애인 콜택시' },
  { value: 'subway', label: '지하철' },
  { value: 'low_floor_bus', label: '저상버스' },
]

const priorityOptions = [
  { value: 'time', label: '시간 최소' },
  { value: 'cost', label: '비용 최소' },
  { value: 'walk', label: '도보 최소' },
]

const defaultPriorityOrder = priorityOptions.map((option) => option.value)
const defaultCenter = { lat: 37.566826, lng: 126.9786567 }

function getPlaceAddress(place: KakaoPlace) {
  return place.road_address_name || place.address_name || '주소 정보 없음'
}

function toPlaceSelection(place: KakaoPlace): PlaceSelection {
  return {
    id: place.id,
    name: place.place_name,
    address: getPlaceAddress(place),
    lat: Number(place.y),
    lng: Number(place.x),
  }
}

function getLocationLabel(role: LocationRole) {
  return role === 'origin' ? '출발지' : '목적지'
}

function loadKakaoMapSdk(appKey: string) {
  if (window.kakao?.maps) {
    return new Promise<void>((resolve) => window.kakao?.maps.load(resolve))
  }

  return new Promise<void>((resolve, reject) => {
    const existingScript = document.querySelector<HTMLScriptElement>('script[data-kakao-map-sdk]')

    if (existingScript) {
      existingScript.addEventListener('load', () => window.kakao?.maps.load(resolve), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('Kakao Maps SDK load failed')), {
        once: true,
      })
      return
    }

    const script = document.createElement('script')
    script.dataset.kakaoMapSdk = 'true'
    script.async = true
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${appKey}&libraries=services&autoload=false`
    script.onload = () => window.kakao?.maps.load(resolve)
    script.onerror = () => reject(new Error('Kakao Maps SDK load failed'))
    document.head.appendChild(script)
  })
}

function App() {
  const kakaoMapAppKey = import.meta.env.VITE_KAKAO_MAP_APP_KEY as string | undefined
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<KakaoMap | null>(null)
  const placesRef = useRef<KakaoPlaces | null>(null)
  const markersRef = useRef<Record<LocationRole, KakaoMarker | null>>({
    origin: null,
    destination: null,
  })

  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [selectedPlaces, setSelectedPlaces] = useState<Record<LocationRole, PlaceSelection | null>>({
    origin: null,
    destination: null,
  })
  const [searchResults, setSearchResults] = useState<Record<LocationRole, PlaceSelection[]>>({
    origin: [],
    destination: [],
  })
  const [placeSearchMessage, setPlaceSearchMessage] = useState<Record<LocationRole, string>>({
    origin: '',
    destination: '',
  })
  const [mapStatus, setMapStatus] = useState(
    kakaoMapAppKey ? '지도를 불러오는 중입니다.' : 'Kakao Maps 앱 키를 설정하면 지도와 장소검색을 사용할 수 있습니다.',
  )
  const [isMapReady, setIsMapReady] = useState(false)
  const [selectedTransportTypes, setSelectedTransportTypes] = useState<string[]>(
    transportOptions.map((option) => option.value),
  )
  const [priorityOrder, setPriorityOrder] = useState(defaultPriorityOrder)
  const [submittedSummary, setSubmittedSummary] = useState<string | null>(null)

  const selectedTransportLabels = useMemo(
    () =>
      transportOptions
        .filter((option) => selectedTransportTypes.includes(option.value))
        .map((option) => option.label),
    [selectedTransportTypes],
  )

  const canSearch =
    origin.trim().length > 0 && destination.trim().length > 0 && selectedTransportTypes.length > 0

  useEffect(() => {
    let ignore = false

    if (!kakaoMapAppKey || !mapContainerRef.current) {
      return
    }

    loadKakaoMapSdk(kakaoMapAppKey)
      .then(() => {
        if (ignore || !window.kakao?.maps || !mapContainerRef.current) {
          return
        }

        const center = new window.kakao.maps.LatLng(defaultCenter.lat, defaultCenter.lng)
        mapRef.current = new window.kakao.maps.Map(mapContainerRef.current, {
          center,
          level: 5,
        })
        placesRef.current = new window.kakao.maps.services.Places()
        setIsMapReady(true)
        setMapStatus('장소를 검색하고 출발지·목적지를 선택하세요.')
      })
      .catch(() => {
        if (!ignore) {
          setMapStatus('Kakao Maps SDK를 불러오지 못했습니다. 앱 키와 도메인 설정을 확인하세요.')
        }
      })

    return () => {
      ignore = true
    }
  }, [kakaoMapAppKey])

  const updatePlaceQuery = (role: LocationRole, nextValue: string) => {
    if (role === 'origin') {
      setOrigin(nextValue)
    } else {
      setDestination(nextValue)
    }

    setSelectedPlaces((current) => ({ ...current, [role]: null }))
    setSearchResults((current) => ({ ...current, [role]: [] }))
    setPlaceSearchMessage((current) => ({ ...current, [role]: '' }))
  }

  const handleTransportToggle = (transportType: string) => {
    setSelectedTransportTypes((current) =>
      current.includes(transportType)
        ? current.filter((item) => item !== transportType)
        : [...current, transportType],
    )
  }

  const handlePriorityChange = (rankIndex: number, nextPriority: string) => {
    setPriorityOrder((current) => {
      const updated = [...current]
      const previousIndex = updated.indexOf(nextPriority)
      const currentPriority = updated[rankIndex]

      updated[rankIndex] = nextPriority
      if (previousIndex >= 0 && previousIndex !== rankIndex) {
        updated[previousIndex] = currentPriority
      }
      return updated
    })
  }

  const searchPlaces = (role: LocationRole) => {
    const keyword = (role === 'origin' ? origin : destination).trim()

    if (!keyword) {
      setPlaceSearchMessage((current) => ({
        ...current,
        [role]: `${getLocationLabel(role)} 검색어를 입력하세요.`,
      }))
      return
    }

    if (!placesRef.current || !window.kakao?.maps) {
      setPlaceSearchMessage((current) => ({
        ...current,
        [role]: '지도 서비스가 준비된 뒤 다시 검색하세요.',
      }))
      return
    }

    placesRef.current.keywordSearch(keyword, (results, status) => {
      if (status !== window.kakao?.maps.services.Status.OK || results.length === 0) {
        setSearchResults((current) => ({ ...current, [role]: [] }))
        setPlaceSearchMessage((current) => ({
          ...current,
          [role]: `${keyword} 검색 결과가 없습니다.`,
        }))
        return
      }

      const nextResults = results.slice(0, 5).map(toPlaceSelection)
      setSearchResults((current) => ({ ...current, [role]: nextResults }))
      setPlaceSearchMessage((current) => ({
        ...current,
        [role]: `${nextResults.length}개 장소 중 하나를 선택하세요.`,
      }))
    })
  }

  const moveMapToPlace = (role: LocationRole, place: PlaceSelection) => {
    if (!mapRef.current || !window.kakao?.maps) {
      return
    }

    markersRef.current[role]?.setMap(null)

    const position = new window.kakao.maps.LatLng(place.lat, place.lng)
    markersRef.current[role] = new window.kakao.maps.Marker({
      map: mapRef.current,
      position,
    })
    mapRef.current.setCenter(position)
  }

  const selectPlace = (role: LocationRole, place: PlaceSelection) => {
    if (role === 'origin') {
      setOrigin(place.name)
    } else {
      setDestination(place.name)
    }

    setSelectedPlaces((current) => ({ ...current, [role]: place }))
    setSearchResults((current) => ({ ...current, [role]: [] }))
    setPlaceSearchMessage((current) => ({
      ...current,
      [role]: `${place.name} 위치를 선택했습니다.`,
    }))
    moveMapToPlace(role, place)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSearch) {
      return
    }

    // TODO: 경로검색 Backend API가 구현되면 입력 조건과 선택 좌표를 요청 모델로 변환해 API 호출로 대체한다.
    const priorityLabels = priorityOrder.map(
      (priority) => priorityOptions.find((option) => option.value === priority)?.label ?? priority,
    )
    const originLabel = selectedPlaces.origin
      ? `${selectedPlaces.origin.name}(${selectedPlaces.origin.lat.toFixed(6)}, ${selectedPlaces.origin.lng.toFixed(6)})`
      : origin.trim()
    const destinationLabel = selectedPlaces.destination
      ? `${selectedPlaces.destination.name}(${selectedPlaces.destination.lat.toFixed(6)}, ${selectedPlaces.destination.lng.toFixed(6)})`
      : destination.trim()

    setSubmittedSummary(
      `${originLabel}에서 ${destinationLabel}까지 ${selectedTransportLabels.join(
        ', ',
      )} 기준으로 ${priorityLabels
        .map((label, index) => `${index + 1}순위 ${label}`)
        .join(', ')} 경로를 검색합니다.`,
    )
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">장애인 이동 경로 비교</p>
        <h1>출발지와 목적지를 검색하고 지도에서 위치를 확인하세요.</h1>
        <p>
          Kakao 장소검색으로 실제 출발지와 목적지를 선택하고, 장애인 콜택시·지하철·저상버스
          비교 조건을 함께 설정합니다. 실제 경로 계산은 이후 Phase에서 backend API와 연결합니다.
        </p>
      </section>

      <section className="map-card" aria-label="지도 위치 확인">
        <div className="map-toolbar">
          <div>
            <h2>지도</h2>
            <p>{mapStatus}</p>
          </div>
          <span className={isMapReady ? 'status-pill ready' : 'status-pill'} aria-live="polite">
            {isMapReady ? '지도 준비 완료' : '지도 대기'}
          </span>
        </div>
        <div className="map-canvas" ref={mapContainerRef} role="img" aria-label="선택한 장소가 표시되는 지도" />
      </section>

      <form className="search-panel" aria-label="경로 검색 조건" onSubmit={handleSubmit}>
        <div className="field-grid">
          {(['origin', 'destination'] as const).map((role) => (
            <div className="place-search" key={role}>
              <label>
                <span>{getLocationLabel(role)}</span>
                <input
                  value={role === 'origin' ? origin : destination}
                  onChange={(event) => updatePlaceQuery(role, event.target.value)}
                  placeholder={role === 'origin' ? '예: 서울시청' : '예: 서울역'}
                  autoComplete="off"
                />
              </label>
              <button className="secondary-button" type="button" onClick={() => searchPlaces(role)}>
                {getLocationLabel(role)} 장소검색
              </button>
              {placeSearchMessage[role] ? (
                <p className="field-hint" role="status">
                  {placeSearchMessage[role]}
                </p>
              ) : null}
              {selectedPlaces[role] ? (
                <p className="selected-place">
                  선택 위치: {selectedPlaces[role]?.address}
                  <br />
                  좌표: {selectedPlaces[role]?.lat.toFixed(6)}, {selectedPlaces[role]?.lng.toFixed(6)}
                </p>
              ) : null}
              {searchResults[role].length > 0 ? (
                <ul className="place-results" aria-label={`${getLocationLabel(role)} 검색 결과`}>
                  {searchResults[role].map((place) => (
                    <li key={place.id}>
                      <button type="button" onClick={() => selectPlace(role, place)}>
                        <strong>{place.name}</strong>
                        <span>{place.address}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>

        <fieldset>
          <legend>이동수단 선택</legend>
          <div className="option-row">
            {transportOptions.map((option) => (
              <label className="check-card" key={option.value}>
                <input
                  type="checkbox"
                  checked={selectedTransportTypes.includes(option.value)}
                  onChange={() => handleTransportToggle(option.value)}
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend>우선순위 선택</legend>
          <p className="field-hint">시간·비용·도보 기준을 1순위부터 3순위까지 정해주세요.</p>
          <div className="priority-grid">
            {priorityOrder.map((selectedPriority, index) => (
              <label key={`${index + 1}-priority`}>
                <span>{index + 1}순위</span>
                <select
                  value={selectedPriority}
                  onChange={(event) => handlePriorityChange(index, event.target.value)}
                >
                  {priorityOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        </fieldset>

        <button type="submit" disabled={!canSearch}>
          경로검색
        </button>
      </form>

      <section className="summary-card" aria-live="polite">
        <h2>입력 조건 요약</h2>
        {submittedSummary ? (
          <p>{submittedSummary}</p>
        ) : (
          <p>출발지·목적지와 이동 조건을 입력하면 이곳에 검색 조건이 표시됩니다.</p>
        )}
      </section>
    </main>
  )
}

export default App
