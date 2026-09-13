export type SourcePeriod = { start_date: string; end_date: string; basis: string; timezone: string }
type HospitalAnalysisBase = {
  title: string
  population_definition: string
  aggregation_unit: string
  limitations: string[]
}
type RegionCount = { name: string; count: number }
type HospitalAnalysis = HospitalAnalysisBase & (
  | {
      analysis_id: 'medical_destination_top_regions'
      values: {
        district_top5: RegionCount[]
        neighborhood_top5: Array<RegionCount & { district: string }>
      }
    }
  | {
      analysis_id: 'medical_trip_scope'
      values: {
        same_district: { count: number; percentage: number }
        different_district: { count: number; percentage: number }
      }
    }
  | {
      analysis_id: 'medical_trip_distance_coverage'
      values: {
        same_district_within_5km_percentage: number
        different_district_within_5km_percentage: number
        overall_within_5km_percentage: number
      }
    }
  | {
      analysis_id: 'medical_net_flow_by_district'
      values: { net_inflow_top5: RegionCount[]; net_outflow_top5: RegionCount[] }
    }
)
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
