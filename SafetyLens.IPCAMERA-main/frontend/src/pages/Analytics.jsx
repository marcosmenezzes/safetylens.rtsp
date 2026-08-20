import { useMemo, useState } from 'react'
import { buildQuery, useApi } from '../api'
import { LineChart } from '../components/Charts'
import DateRangeFilter from '../components/DateRangeFilter'
import StatCard from '../components/StatCard'
import { ErrorState, LoadingState } from '../components/States'

/** Transforma as agregações da API em análises visuais do período escolhido. */
export default function Analytics() {
  const [filters, setFilters] = useState({ start: '', end: '' })
  const path = useMemo(() => `/api/analytics?${buildQuery(filters)}`, [filters])
  const { data, error, loading, retry } = useApi(path)
  const top = data?.byEpi[0]
  const riskColors = ['var(--chart-primary)', 'var(--chart-secondary)', 'var(--expressive-purple)', 'var(--jade)']
  let riskOffset = 0
  const riskSegments = data?.byEpi.map((item, index) => {
    const start = riskOffset
    riskOffset = Math.min(100, riskOffset + item.percentage)
    return `${riskColors[index % riskColors.length]} ${start}% ${riskOffset}%`
  }) || []
  if (riskOffset < 100) riskSegments.push(`var(--grid) ${riskOffset}% 100%`)

  return (
    <div className="analytics-page">
      <DateRangeFilter initial={filters} onApply={setFilters} />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={retry} /> : (
        <section className="analytics-canvas">
          <section className="analytics-hero">
            <div className="analytics-intro"><span className="eyebrow">INTELIGÊNCIA OPERACIONAL</span><h2>Do alerta ao padrão.</h2><p>Uma leitura aprofundada dos riscos detectados para orientar inspeções e próximos treinamentos.</p><a className="button" href="/detections">Ver relatório completo　→</a></div>
            <aside className="key-insight"><h3>Insight principal</h3><strong>{data.summary.periodTotal}</strong><p><b>{data.summary.periodShare}%</b> da base histórica</p><div className="signal-bars" aria-hidden="true">{Array.from({ length: 30 }, (_, index) => <i className={index < Math.ceil(data.summary.periodShare * .3) ? 'active' : ''} key={index} />)}</div><small>Maior recorrência　·　{data.summary.mostMissing.replaceAll('_', ' ')}</small></aside>
          </section>

          <div className="dot-divider" />
          <section className="analytics-overview">
            <div className="analytics-trend"><header><h3>Evolução das ocorrências</h3><span>período selecionado</span></header><LineChart title="Tendência diária" data={data.trend} /></div>
            <aside className="risk-distribution"><h3>Distribuição de risco</h3><div className="risk-ring" style={{ '--risk-gradient': `conic-gradient(${riskSegments.join(', ')})` }}><div><small>MAIOR ÍNDICE</small><strong>{top?.percentage || 0}%</strong></div></div><ul>{data.byEpi.map((item, index) => <li key={item.name}><i style={{ background: riskColors[index % riskColors.length] }} /><span>{item.name.replaceAll('_', ' ')}</span><strong>{item.count}</strong></li>)}</ul></aside>
          </section>

          <div className="dot-divider" />
          <section className="analytics-metrics">
            <StatCard label="Eventos no período" value={data.summary.periodTotal} detail="Intervalo selecionado" tone="quartz" />
            <StatCard label="Base histórica" value={data.summary.overallTotal} detail="Todos os registros" tone="violet" />
            <StatCard label="Participação no histórico" value={`${data.summary.periodShare}%`} detail="Fatia do período" tone="jade" />
          </section>

          <div className="dot-divider" />
          <section className="analytics-history"><header><h3>Comparativo mensal</h3><span>Visão histórica</span></header><LineChart title="Comparativo mensal" data={data.monthly} labelKey="month" /></section>

          <div className="dot-divider" />
          <section className="analytics-table">
            <div className="panel-heading"><div><h2>Resumo por EPI</h2></div></div>
            <div className="table-scroll"><table className="data-table"><caption className="sr-only">Resumo estatístico por EPI</caption><thead><tr><th scope="col">EPI ausente</th><th scope="col">Eventos</th><th scope="col">Participação</th><th scope="col">Tendência</th></tr></thead><tbody>{data.byEpi.map((item) => <tr key={item.name}><td>{item.name.replaceAll('_', ' ')}</td><td>{item.count}</td><td>{item.percentage}%</td><td><span className={item.trend > 0 ? 'trend trend--up' : 'trend'}>{item.trend > 0 ? '↑' : item.trend < 0 ? '↓' : '—'} {Math.abs(item.trend)}%</span></td></tr>)}</tbody></table></div>
          </section>
        </section>
      )}
    </div>
  )
}
