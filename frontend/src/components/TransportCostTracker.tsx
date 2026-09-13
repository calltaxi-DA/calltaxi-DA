import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import type { RecommendationResponse, TransportType } from '../api/recommendation'
import {
  createTransportCostRecord,
  fetchDailyTransportCosts,
  fetchMonthlyTransportCosts,
} from '../api/transportCosts'
import type { DailyTransportCostResponse, MonthlyTransportCostResponse } from '../api/transportCosts'

type DailyTransportCostSummary = MonthlyTransportCostResponse['daily_summaries'][number]

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

function hasCostTotals(value: unknown): value is { actual_cost_won: number; recommended_cost_won: number; potential_savings_won: number } {
  if (!value || typeof value !== 'object') return false
  const totals = value as Record<string, unknown>
  return typeof totals.actual_cost_won === 'number'
    && typeof totals.recommended_cost_won === 'number'
    && typeof totals.potential_savings_won === 'number'
}

function isMonthlyTransportCostResponse(value: unknown): value is MonthlyTransportCostResponse {
  if (!value || typeof value !== 'object') return false
  const response = value as Record<string, unknown>
  return typeof response.month === 'string'
    && Array.isArray(response.daily_summaries)
    && hasCostTotals(response.totals)
}

function isDailyTransportCostResponse(value: unknown): value is DailyTransportCostResponse {
  if (!value || typeof value !== 'object') return false
  const response = value as Record<string, unknown>
  return typeof response.date === 'string'
    && Array.isArray(response.records)
    && hasCostTotals(response.totals)
}

function daysInMonth(month: string) {
  const [year, monthNumber] = month.split('-').map(Number)
  if (!year || !monthNumber) return []
  const lastDay = new Date(year, monthNumber, 0).getDate()
  return Array.from({ length: lastDay }, (_, index) => `${month}-${String(index + 1).padStart(2, '0')}`)
}

function TransportCostTracker({ result }: { result: RecommendationResponse }) {
  const initialDate = localDateString()
  const availableTypes = result.recommendations.map((item) => item.route.transport_type)
  const [travelDate, setTravelDate] = useState(initialDate)
  const [month, setMonth] = useState(initialDate.slice(0, 7))
  const [selectedDate, setSelectedDate] = useState(initialDate)
  const [actualCost, setActualCost] = useState('')
  const [selectedTransport, setSelectedTransport] = useState<TransportType | ''>(availableTypes[0] ?? '')
  const [summary, setSummary] = useState<MonthlyTransportCostResponse | null>(null)
  const [dailyDetail, setDailyDetail] = useState<DailyTransportCostResponse | null>(null)
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [queryStatus, setQueryStatus] = useState<'idle' | 'loading' | 'error'>('idle')

  const summaryByDate = useMemo(() => {
    const entries: Array<[string, DailyTransportCostSummary]> = (summary?.daily_summaries ?? [])
      .map((day) => [day.date, day])
    return new Map<string, DailyTransportCostSummary>(entries)
  }, [summary])

  async function refreshMonthlySummary(targetMonth: string) {
    const monthly = await fetchMonthlyTransportCosts(targetMonth)
    if (!isMonthlyTransportCostResponse(monthly)) throw new Error('Invalid monthly transport cost response')
    setSummary(monthly)
    return monthly
  }

  async function refreshDailyDetail(targetDate: string) {
    const daily = await fetchDailyTransportCosts(targetDate)
    if (!isDailyTransportCostResponse(daily)) throw new Error('Invalid daily transport cost response')
    setDailyDetail(daily)
  }

  async function refreshCalendar(targetMonth: string, targetDate = selectedDate) {
    setQueryStatus('loading')
    try {
      await refreshMonthlySummary(targetMonth)
      const dateForDetail = targetDate.startsWith(targetMonth) ? targetDate : `${targetMonth}-01`
      setSelectedDate(dateForDetail)
      await refreshDailyDetail(dateForDetail)
      setQueryStatus('idle')
    } catch {
      setSummary(null)
      setDailyDetail(null)
      setQueryStatus('error')
    }
  }

  async function handleMonthlyQuery() {
    await refreshCalendar(month)
  }

  async function handleDateSelect(date: string) {
    setSelectedDate(date)
    setTravelDate(date)
    try {
      await refreshDailyDetail(date)
      setQueryStatus('idle')
    } catch {
      setDailyDetail(null)
      setQueryStatus('error')
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
      setSelectedDate(travelDate)
      await refreshMonthlySummary(recordMonth)
      await refreshDailyDetail(travelDate)
      setActualCost('')
      setStatus('saved')
    } catch {
      setStatus('error')
    }
  }

  useEffect(() => {
    void refreshCalendar(month)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section className="transport-cost-tracker" aria-labelledby="transport-cost-title">
      <h2 id="transport-cost-title">교통비 기록</h2>
      <p>실제 이용금액을 기록하면 Backend가 같은 경로의 금액 우선 추천과 비교해 절약 가능 금액을 계산합니다.</p>
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
        <button type="button" onClick={handleMonthlyQuery} disabled={queryStatus === 'loading'}>
          {queryStatus === 'loading' ? '조회 중…' : '월별 조회'}
        </button>
        {queryStatus === 'error' ? <p role="alert">교통비 내역을 불러오지 못했습니다.</p> : null}
        {summary ? <>
          <dl aria-label={`${summary.month} 월 누적 교통비`}>
            <div><dt>실제 교통비</dt><dd>{won(summary.totals.actual_cost_won)}</dd></div>
            <div><dt>금액 우선 기준</dt><dd>{won(summary.totals.recommended_cost_won)}</dd></div>
            <div><dt>절약 가능 금액</dt><dd>{won(summary.totals.potential_savings_won)}</dd></div>
          </dl>
          <div className="cost-calendar" role="grid" aria-label={`${summary.month} 교통비 캘린더`}>
            {daysInMonth(summary.month).map((date) => {
              const day = summaryByDate.get(date)
              return (
                <button
                  key={date}
                  type="button"
                  className={`cost-calendar-day${day ? ' has-record' : ''}${date === selectedDate ? ' selected' : ''}`}
                  onClick={() => void handleDateSelect(date)}
                  aria-label={`${date} 교통비 ${day ? `실제 ${won(day.actual_cost_won)}, 절약 가능 ${won(day.potential_savings_won)}` : '기록 없음'}`}
                >
                  <strong>{Number(date.slice(-2))}</strong>
                  {day ? <span>{won(day.actual_cost_won)}</span> : <span>-</span>}
                </button>
              )
            })}
          </div>
          <section className="daily-cost-detail" aria-labelledby="daily-cost-title">
            <h3 id="daily-cost-title">{selectedDate} 이용 기록</h3>
            {dailyDetail ? <>
              <dl>
                <div><dt>실제 이용금액</dt><dd>{won(dailyDetail.totals.actual_cost_won)}</dd></div>
                <div><dt>금액 우선 추천</dt><dd>{won(dailyDetail.totals.recommended_cost_won)}</dd></div>
                <div><dt>절약 가능</dt><dd>{won(dailyDetail.totals.potential_savings_won)}</dd></div>
              </dl>
              {dailyDetail.records.length ? (
                <ul>
                  {dailyDetail.records.map((record) => (
                    <li key={record.id}>
                      {transportLabels[record.selected_transport_type]} 실제 {won(record.actual_cost_won)}
                      {' / '}금액 우선 {transportLabels[record.recommended_transport_type]} {won(record.recommended_cost_won)}
                      {' / '}절약 가능 {won(record.potential_savings_won)}
                    </li>
                  ))}
                </ul>
              ) : <p>선택한 날짜의 교통비 기록이 없습니다.</p>}
            </> : <p>날짜를 선택하면 상세 기록이 표시됩니다.</p>}
          </section>
        </> : <p>조회할 월을 선택해주세요.</p>}
      </div>
    </section>
  )
}

export default TransportCostTracker
