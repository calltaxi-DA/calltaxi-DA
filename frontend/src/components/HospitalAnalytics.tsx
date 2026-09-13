import type { HospitalAnalyticsResponse } from '../api/hospitalAnalytics'
import { hospitalChartUrl } from '../api/hospitalAnalytics'

function HospitalAnalytics({ result }: { result: HospitalAnalyticsResponse }) {
  const regions = result.analyses.find((item) => item.analysis_id === 'medical_destination_top_regions')
  const districtTop5 = regions?.values.district_top5 ?? []
  const limitations = [...new Set(result.analyses.flatMap((item) => item.limitations))]
  return (
    <section className="hospital-analytics" aria-label="병원 이동 분석정보">
      <header>
        <p className="result-kicker">{result.source_period.start_date}~{result.source_period.end_date} {result.source_period.basis} 기준</p>
        <h2>의료목적콜 이동 분석</h2>
        <p>개별 병원 방문량이 아닌 의료목적으로 기록된 이동의 지역 집계입니다.</p>
      </header>
      <h3>도착이 많은 자치구</h3>
      <ol>{districtTop5.map((item) => <li key={item.name}><span>{item.name}</span><strong>{item.count.toLocaleString()}건</strong></li>)}</ol>
      {result.charts.map((chart) => (
        <figure key={chart.chart_id}>
          <img src={hospitalChartUrl(chart.asset_url)} alt={chart.alt_text} />
          <figcaption>{chart.title}</figcaption>
        </figure>
      ))}
      <details><summary>분석 기준과 한계</summary><ul>{limitations.map((text) => <li key={text}>{text}</li>)}</ul></details>
    </section>
  )
}

export default HospitalAnalytics
