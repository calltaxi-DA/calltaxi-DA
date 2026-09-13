import type { RouteLocation } from './subway'

type LowFloorBusRouteBase = {
  transport_type: 'low_floor_bus'
  warnings: string[]
}

type AvailableLowFloorBusRouteResult = LowFloorBusRouteBase & {
  status: 'available'
  total_time_seconds: number
  total_distance_meters: number
  total_cost_won: number
  walking_distance_meters: number
  walking_time_seconds: number
  unavailable_reason: null
  summary: string | null
}

type UnavailableLowFloorBusRouteResult = LowFloorBusRouteBase & {
  status: 'unavailable'
  total_time_seconds: null
  total_distance_meters: null
  total_cost_won: null
  walking_distance_meters: null
  walking_time_seconds: null
  unavailable_reason: string
  summary: string | null
}

export type LowFloorBusRouteResult =
  | AvailableLowFloorBusRouteResult
  | UnavailableLowFloorBusRouteResult

type LowFloorBusRouteRequest = {
  origin: RouteLocation
  destination: RouteLocation
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export async function fetchLowFloorBusRoute(
  request: LowFloorBusRouteRequest,
  signal?: AbortSignal,
): Promise<LowFloorBusRouteResult> {
  const response = await fetch(`${apiBaseUrl}/routes/bus`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Low-floor bus route request failed with status ${response.status}`)
  }

  return (await response.json()) as LowFloorBusRouteResult
}
