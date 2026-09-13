import type {
  AccessibilityStatus,
  RecommendationResponse,
  RouteResult,
  TransportType,
} from '../api/recommendation'

const transportLabels: Record<TransportType, string> = {
  calltaxi: '장애인 콜택시',
  subway: '지하철',
  low_floor_bus: '저상버스',
}

const accessibilityLabels: Record<AccessibilityStatus, string> = {
  verified_available: '접근성 확인됨',
  verified_unavailable: '접근성 조건 미충족',
  not_verified: '접근성 미확인',
}

function duration(value: number | null, available = true) {
  if (!available || value === null) return '비교 불가'
  const hours = Math.floor(value / 3600)
  const minutes = Math.ceil((value % 3600) / 60)
  if (!hours) return `${minutes}분`
  return minutes ? `${hours}시간 ${minutes}분` : `${hours}시간`
}

function distance(value: number | null, available = true) {
  if (!available || value === null) return '비교 불가'
  return value < 1000 ? `${value.toLocaleString('ko-KR')}m` : `${(value / 1000).toFixed(1)}km`
}

function RouteMetrics({ route }: { route: RouteResult }) {
  const metrics = [
    ['총 예상시간', duration(route.total_time_seconds, route.metric_availability.total_time_seconds === 'available')],
    ['이동거리', distance(route.total_distance_meters, route.metric_availability.total_distance_meters === 'available')],
    ['예상요금', route.metric_availability.total_cost_won === 'available' && route.total_cost_won !== null ? `${route.total_cost_won.toLocaleString('ko-KR')}원` : '비교 불가'],
    ['도보거리', distance(route.walking_distance_meters, route.metric_availability.walking_distance_meters === 'available')],
    ['도보시간', duration(route.walking_time_seconds, route.metric_availability.walking_time_seconds === 'available')],
  ]
  return <dl className="route-metrics">{metrics.map(([label, value]) => (
    <div className="metric" key={label}><dt>{label}</dt><dd>{value}</dd></div>
  ))}</dl>
}

function CalltaxiTimeBreakdown({ route }: { route: RouteResult }) {
  if (route.transport_type !== 'calltaxi' || route.status !== 'available') return null

  const items = [
    ['예상 대기시간', duration(route.predicted_waiting_time_seconds ?? null, route.predicted_waiting_time_seconds !== null && route.predicted_waiting_time_seconds !== undefined)],
    ['차량 이동시간', duration(route.vehicle_time_seconds ?? null, route.vehicle_time_seconds !== null && route.vehicle_time_seconds !== undefined)],
    ['총 예상시간', duration(route.total_time_seconds, route.metric_availability.total_time_seconds === 'available')],
  ]

  return (
    <section className="calltaxi-time-breakdown" aria-label="장애인 콜택시 시간 구성">
      <h4>장애인 콜택시 시간 구성</h4>
      <dl className="component-metrics">
        {items.map(([label, value]) => (
          <div className="component-metric" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function RecommendationResults({ result }: { result: RecommendationResponse }) {
  return (
    <section className="recommendation-results" aria-labelledby="recommendation-title">
      <header className="recommendation-heading">
        <p className="result-kicker">선택한 우선순위로 Backend가 계산한 결과</p>
        <h2 id="recommendation-title">추천 경로 최대 TOP 3</h2>
      </header>

      {result.recommendations.length ? result.recommendations.map(({ rank, route }) => (
        <article className="route-result-card recommendation-card" key={route.transport_type}>
          <div className="result-heading">
            <strong className="rank-badge">{rank}위</strong>
            <div>
              <p className="result-kicker">{transportLabels[route.transport_type]}</p>
              <h3>{route.summary ?? `${transportLabels[route.transport_type]} 경로`}</h3>
            </div>
          </div>
          <RouteMetrics route={route} />
          <CalltaxiTimeBreakdown route={route} />
          <div className={`accessibility-status ${route.accessibility_status}`}>
            <strong>{accessibilityLabels[route.accessibility_status]}</strong>
            {route.warnings.length ? <ul>{route.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
          </div>
        </article>
      )) : <p className="empty-recommendation">현재 추천 가능한 경로가 없습니다.</p>}

      {result.excluded_routes.length ? (
        <div className="excluded-routes">
          <h3>추천에서 제외된 이동수단</h3>
          <ul>{result.excluded_routes.map((item) => (
            <li key={item.transport_type}><strong>{transportLabels[item.transport_type]}</strong>: {item.reason}</li>
          ))}</ul>
        </div>
      ) : null}
    </section>
  )
}

export default RecommendationResults
