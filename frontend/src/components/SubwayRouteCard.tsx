import type { SubwayRouteResult } from '../api/subway'

type SubwayRouteCardProps = {
  route: SubwayRouteResult
}

function formatDuration(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.ceil((totalSeconds % 3600) / 60)

  if (hours === 0) {
    return `${minutes}분`
  }
  if (minutes === 0) {
    return `${hours}시간`
  }
  return `${hours}시간 ${minutes}분`
}

function formatDistance(meters: number) {
  if (meters < 1000) {
    return `${meters.toLocaleString('ko-KR')}m`
  }
  return `${(meters / 1000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}km`
}

function SubwayRouteCard({ route }: SubwayRouteCardProps) {
  if (route.status === 'unavailable') {
    return (
      <section className="subway-result-card unavailable" aria-labelledby="subway-result-title">
        <div className="result-heading">
          <span className="transport-badge" aria-hidden="true">지하철</span>
          <div>
            <p className="result-kicker">경로를 찾지 못했어요</p>
            <h2 id="subway-result-title">지하철 경로</h2>
          </div>
        </div>
        <p className="result-message">{route.unavailable_reason ?? '이용 가능한 지하철 경로가 없습니다.'}</p>
      </section>
    )
  }

  const metrics = [
    { label: '총 예상시간', value: formatDuration(route.total_time_seconds), emphasis: true },
    { label: '예상비용', value: `${route.total_cost_won.toLocaleString('ko-KR')}원` },
    { label: '도보거리', value: formatDistance(route.walking_distance_meters) },
    { label: '도보시간', value: formatDuration(route.walking_time_seconds) },
  ]

  return (
    <section className="subway-result-card" aria-labelledby="subway-result-title">
      <div className="result-heading">
        <span className="transport-badge" aria-hidden="true">지하철</span>
        <div>
          <p className="result-kicker">접근성 안내가 포함된 경로</p>
          <h2 id="subway-result-title">{route.summary ?? '지하철 경로'}</h2>
        </div>
      </div>

      <dl className="route-metrics">
        {metrics.map((metric) => (
          <div className={metric.emphasis ? 'metric emphasis' : 'metric'} key={metric.label}>
            <dt>{metric.label}</dt>
            <dd>{metric.value}</dd>
          </div>
        ))}
      </dl>

      <div className="accessibility-note">
        <h3>엘리베이터·접근성 안내</h3>
        {route.warnings.length > 0 ? (
          <ul>
            {route.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        ) : (
          <p>현재 경로에서 별도의 접근성 주의사항이 확인되지 않았습니다.</p>
        )}
      </div>
    </section>
  )
}

export default SubwayRouteCard
