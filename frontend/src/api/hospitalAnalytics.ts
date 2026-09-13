export type SourcePeriod = { start_date: string; end_date: string; basis: string; timezone: string }
export type HospitalAnalysis = {
  analysis_id: string
  title: string
  population_definition: string
  aggregation_unit: string
  values: Record<string, unknown>
  limitations: string[]
}
export type HospitalChart = { chart_id: string; title: string; alt_text: string; asset_url: string; analysis_ids: string[] }
export type HospitalAnalyticsResponse = {
  schema_version: string
  source_period: SourcePeriod
  analyses: HospitalAnalysis[]
  charts: HospitalChart[]
}

function apiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://127.0.0.1:8000'
}

export function hospitalChartUrl(assetUrl: string) {
  return `${apiBaseUrl()}${assetUrl}`
}

export async function fetchHospitalAnalytics(): Promise<HospitalAnalyticsResponse> {
  const response = await fetch(`${apiBaseUrl()}/analytics/hospital`)
  if (!response.ok) throw new Error(`Hospital analytics request failed with status ${response.status}`)
  return (await response.json()) as HospitalAnalyticsResponse
}
