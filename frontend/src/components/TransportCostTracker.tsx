import { useState } from 'react'
import type { FormEvent } from 'react'

import type { RecommendationResponse, TransportType } from '../api/recommendation'
import {
  createTransportCostRecord,
  fetchMonthlyTransportCosts,
} from '../api/transportCosts'
import type { MonthlyTransportCostResponse } from '../api/transportCosts'

const transportLabels: Record<TransportType, string> = {
  calltaxi: '장애인 콜택시',
  subway: '지하철',
  low_floor_bus: '저상버스',
}

function localDateString() {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60_000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

function won(value: number) {
  return `${value.toLocaleString('ko-KR')}원`
}

function TransportCostTracker({ result }: { result: RecommendationResponse }) {
  const initialDate = localDateString()
  const availableTypes = result.recommendations.map((item) => item.route.transport_type)
  const [travelDate, setTravelDate] = useState(initialDate)
  const [month, setMonth] = useState(initialDate.slice(0, 7))
  const [actualCost, setActualCost] = useState('')
  const [selectedTransport, setSelectedTransport] = useState<TransportType | ''>(availableTypes[0] ?? '')
  const [summary, setSummary] = useState<MonthlyTransportCostResponse | null>(null)
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [queryError, setQueryError] = useState(false)

  async function refreshMonthlySummary(targetMonth: string) {
    setSummary(await fetchMonthlyTransportCosts(targetMonth))
  }

  async function handleMonthlyQuery() {
    try {
      await refreshMonthlySummary(month)
      setQueryError(false)
    } catch {
      setSummary(null)
      setQueryError(true)
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const parsedCost = Number(actualCost)
    if (!selectedTransport || !Number.isInteger(parsedCost) || parsedCost < 0) return
    setStatus('saving')
    try {
      await createTransportCostRecord(result, travelDate, parsedCost, selectedTransport)
      const recordMonth = travelDate.slice(0, 7)
      setMonth(recordMonth)
      await refreshMonthlySummary(recordMonth)
      setActualCost('')
      setStatus('saved')
    } catch {
      setStatus('error')
    }
  }

  return (
    <section className="transport-cost-tracker" aria-labelledby="transport-cost-title">
      <h2 id="transport-cost-title">교통비 기록</h2>
      <p>실제 이용금액을 기록하면 Backend가 같은 경로의 금액 우선 추천과 비교합니다.</p>
      <form className="transport-cost-form" onSubmit={handleSubmit}>
        <label>이용 날짜<input type="date" value={travelDate} onChange={(event) => setTravelDate(event.target.value)} required /></label>
        <label>실제 이용수단<select value={selectedTransport} onChange={(event) => setSelectedTransport(event.target.value as TransportType)}>
          {availableTypes.map((type) => <option key={type} value={type}>{transportLabels[type]}</option>)}
        </select></label>
        <label>실제 이용금액(원)<input type="number" min="0" step="1" value={actualCost} onChange={(event) => setActualCost(event.target.value)} required /></label>
        <button type="submit" disabled={status === 'saving'}>{status === 'saving' ? '저장 중…' : '교통비 저장'}</button>
      </form>
      {status === 'saved' ? <p role="status">교통비를 저장했습니다.</p> : null}
      {status === 'error' ? <p role="alert">교통비를 저장하지 못했습니다.</p> : null}

      <div className="monthly-cost-summary">
        <label>조회 월<input type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label>
        <button type="button" onClick={handleMonthlyQuery}>월별 조회</button>
        {queryError ? <p role="alert">월별 교통비를 불러오지 못했습니다.</p> : null}
        {summary ? <>
          <dl>
            <div><dt>실제 교통비</dt><dd>{won(summary.totals.actual_cost_won)}</dd></div>
            <div><dt>금액 우선 기준</dt><dd>{won(summary.totals.recommended_cost_won)}</dd></div>
            <div><dt>절약 가능 금액</dt><dd>{won(summary.totals.potential_savings_won)}</dd></div>
          </dl>
          {summary.daily_summaries.length ? <ul>{summary.daily_summaries.map((day) => (
            <li key={day.date}>{day.date}: 실제 {won(day.actual_cost_won)} / 절약 가능 {won(day.potential_savings_won)}</li>
          ))}</ul> : <p>이 달의 교통비 기록이 없습니다.</p>}
        </> : <p>조회할 월을 선택해주세요.</p>}
      </div>
    </section>
  )
}

export default TransportCostTracker
