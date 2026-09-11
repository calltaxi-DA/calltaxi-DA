import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'

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

function App() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [selectedTransportTypes, setSelectedTransportTypes] = useState<string[]>(
    transportOptions.map((option) => option.value),
  )
  const [priority, setPriority] = useState(priorityOptions[0].value)
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

  const handleTransportToggle = (transportType: string) => {
    setSelectedTransportTypes((current) =>
      current.includes(transportType)
        ? current.filter((item) => item !== transportType)
        : [...current, transportType],
    )
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSearch) {
      return
    }

    const priorityLabel =
      priorityOptions.find((option) => option.value === priority)?.label ?? '시간 최소'

    setSubmittedSummary(
      `${origin.trim()}에서 ${destination.trim()}까지 ${selectedTransportLabels.join(
        ', ',
      )} 기준으로 ${priorityLabel} 경로를 검색합니다.`,
    )
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">장애인 이동 경로 비교</p>
        <h1>출발지와 목적지를 입력해 이동 조건을 설정하세요.</h1>
        <p>
          장애인 콜택시, 지하철, 저상버스를 같은 기준으로 비교하기 위한 첫 화면입니다.
          실제 경로 계산은 이후 Phase에서 backend API와 연결합니다.
        </p>
      </section>

      <form className="search-panel" aria-label="경로 검색 조건" onSubmit={handleSubmit}>
        <div className="field-grid">
          <label>
            <span>출발지</span>
            <input
              value={origin}
              onChange={(event) => setOrigin(event.target.value)}
              placeholder="예: 서울시청"
              autoComplete="off"
            />
          </label>

          <label>
            <span>목적지</span>
            <input
              value={destination}
              onChange={(event) => setDestination(event.target.value)}
              placeholder="예: 서울역"
              autoComplete="off"
            />
          </label>
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
          <div className="option-row">
            {priorityOptions.map((option) => (
              <label className="radio-card" key={option.value}>
                <input
                  type="radio"
                  name="priority"
                  value={option.value}
                  checked={priority === option.value}
                  onChange={(event) => setPriority(event.target.value)}
                />
                <span>{option.label}</span>
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
