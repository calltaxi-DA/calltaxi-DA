import type { RecommendationResponse, TransportType } from './recommendation'

export type TransportCostRecord = {
  id: number
  travel_date: string
  actual_cost_won: number
  recommended_cost_won: number
  potential_savings_won: number
  selected_transport_type: TransportType
  recommended_transport_type: TransportType
  created_at: string
}

export type MonthlyTransportCostResponse = {
  month: string
  daily_summaries: Array<{
    date: string
    record_count: number
    actual_cost_won: number
    recommended_cost_won: number
    potential_savings_won: number
  }>
  totals: {
    actual_cost_won: number
    recommended_cost_won: number
    potential_savings_won: number
  }
}

export type DailyTransportCostResponse = {
  date: string
  records: TransportCostRecord[]
  totals: {
    actual_cost_won: number
    recommended_cost_won: number
    potential_savings_won: number
  }
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '')
  || 'http://127.0.0.1:8000'

export async function createTransportCostRecord(
  result: RecommendationResponse,
  travelDate: string,
  actualCostWon: number,
  selectedTransportType: TransportType,
): Promise<TransportCostRecord> {
  const response = await fetch(`${apiBaseUrl}/transport-cost-records`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      travel_date: travelDate,
      actual_cost_won: actualCostWon,
      selected_transport_type: selectedTransportType,
      origin: result.origin,
      destination: result.destination,
      transport_types: result.transport_types,
    }),
  })
  if (!response.ok) throw new Error(`Transport cost request failed with status ${response.status}`)
  return (await response.json()) as TransportCostRecord
}

export async function fetchMonthlyTransportCosts(
  month: string,
  signal?: AbortSignal,
): Promise<MonthlyTransportCostResponse> {
  const response = await fetch(
    `${apiBaseUrl}/transport-cost-records/monthly?month=${encodeURIComponent(month)}`,
    { signal },
  )
  if (!response.ok) throw new Error(`Monthly transport cost request failed with status ${response.status}`)
  return (await response.json()) as MonthlyTransportCostResponse
}

export async function fetchDailyTransportCosts(
  date: string,
  signal?: AbortSignal,
): Promise<DailyTransportCostResponse> {
  const response = await fetch(
    `${apiBaseUrl}/transport-cost-records/daily?date=${encodeURIComponent(date)}`,
    { signal },
  )
  if (!response.ok) throw new Error(`Daily transport cost request failed with status ${response.status}`)
  return (await response.json()) as DailyTransportCostResponse
}
