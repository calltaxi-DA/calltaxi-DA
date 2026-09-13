import type { RouteLocation } from './subway'

export type RecommendationPriority = 'time' | 'cost' | 'walk'
export type TransportType = 'calltaxi' | 'subway' | 'low_floor_bus'
export type MetricAvailability = 'available' | 'not_available'
export type AccessibilityStatus = 'verified_available' | 'verified_unavailable' | 'not_verified'

export type RouteResult = {
  transport_type: TransportType
  status: 'available' | 'unavailable'
  total_time_seconds: number | null
  total_distance_meters: number | null
  total_cost_won: number | null
  walking_distance_meters: number | null
  walking_time_seconds: number | null
  metric_availability: Record<
    | 'total_time_seconds'
    | 'total_distance_meters'
    | 'total_cost_won'
    | 'walking_distance_meters'
    | 'walking_time_seconds',
    MetricAvailability
  >
  accessibility_status: AccessibilityStatus
  unavailable_reason: string | null
  summary: string | null
  warnings: string[]
}

export type RecommendationResponse = {
  origin: RouteLocation
  destination: RouteLocation
  transport_types: TransportType[]
  priorities: RecommendationPriority[]
  recommendations: Array<{ rank: number; route: RouteResult }>
  excluded_routes: Array<{ transport_type: TransportType; reason: string }>
}

type RecommendationRequest = {
  origin: RouteLocation
  destination: RouteLocation
  transport_types: TransportType[]
  priorities: RecommendationPriority[]
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export async function fetchRecommendations(
  request: RecommendationRequest,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  const response = await fetch(`${apiBaseUrl}/routes/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) throw new Error(`Recommendation request failed with status ${response.status}`)
  return (await response.json()) as RecommendationResponse
}
