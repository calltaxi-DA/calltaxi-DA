export type RouteLocation = {
  name: string
  latitude: number
  longitude: number
  address: string
}

type SubwayRouteBase = {
  transport_type: 'subway'
  warnings: string[]
}

type AvailableSubwayRouteResult = SubwayRouteBase & {
  status: 'available'
  total_time_seconds: number
  total_distance_meters: number
  total_cost_won: number
  walking_distance_meters: number
  walking_time_seconds: number
  unavailable_reason: null
  summary: string | null
}

type UnavailableSubwayRouteResult = SubwayRouteBase & {
  status: 'unavailable'
  total_time_seconds: null
  total_distance_meters: null
  total_cost_won: null
  walking_distance_meters: null
  walking_time_seconds: null
  unavailable_reason: string
  summary: string | null
}

export type SubwayRouteResult = AvailableSubwayRouteResult | UnavailableSubwayRouteResult

type SubwayRouteRequest = {
  origin: RouteLocation
  destination: RouteLocation
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export async function fetchSubwayRoute(
  request: SubwayRouteRequest,
  signal?: AbortSignal,
): Promise<SubwayRouteResult> {
  const response = await fetch(`${apiBaseUrl}/routes/subway`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Subway route request failed with status ${response.status}`)
  }

  return (await response.json()) as SubwayRouteResult
}
