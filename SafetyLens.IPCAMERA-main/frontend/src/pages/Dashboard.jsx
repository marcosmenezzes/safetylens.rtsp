import { formatDate, useApi } from '../api'
import { LineChart } from '../components/Charts'
import DetectionTable from '../components/DetectionTable'
import StatCard from '../components/StatCard'
import { ErrorState, LoadingState } from '../components/States'
import Icon from '../components/Icon'

/** Resume o estado operacional e oferece atalhos para os fluxos detalhados. */
export default function Dashboard() {
  const { data, error, loading, retry } = useApi('/api/dashboard')
  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} retry={retry} />
  const last = data.summary.lastDetection
  const topEpi = data.byEpi[0]
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'

  return (
    <section className="dashboard-canvas">
      <header className="dashboard-header">
        <div>
          <span className="eyebrow">VISÃO COMPUTACIONAL · SEGURANÇA EM TEMPO REAL</span>
          <h2>SafetyLens</h2>
          <p>{greeting}, equipe. Acompanhe as análises de segurança de hoje.</p>
        </div>
        <div className="dashboard-actions">
          <button className="icon-button" type="button" aria-label="Atualizar dados" onClick={retry}><Icon name="refresh" /></button>
          <span className="period-button">Dados mensais</span>
          <a className="button" href="/monitoring"><Icon name="camera" /> Monitorar</a>
        </div>
      </header>

      <div className="dot-divider" />
      <section className="update-strip">
        <div><span><i /> Atualização</span><small>{data.updatedAt ? formatDate(data.updatedAt) : 'agora'}</small><p>{data.summary.totalDetections} alertas registrados nos últimos 30 dias</p></div>
        <a href="/analytics">Abrir análise　→</a>
      </section>
      <div className="dot-divider" />

      <div className="overview-head"><h3>Visão geral das ocorrências</h3><h3>Resumo operacional</h3></div>
      <section className="overview-grid">
        <div className="overview-chart">
          <div className="chart-summary"><span>Total de alertas</span><strong>{data.summary.totalDetections}</strong><small>dados do período</small><span>nos últimos 30 dias</span></div>
          <LineChart title="Visão geral das ocorrências" data={data.daily} />
        </div>
        <div className="overview-stats" aria-label="Resumo do período">
          <StatCard label="EPI mais recorrente" value={topEpi?.count || '—'} detail={topEpi?.name.replaceAll('_', ' ') || 'Aguardando dados'} tone="quartz" />
          <StatCard label="Tipos monitorados" value={data.summary.monitoredEpis} detail="Classes com ocorrências" tone="violet" />
          <StatCard label="Último evento" value={last ? formatDate(last.timestamp, false) : '—'} detail={last ? formatDate(last.timestamp).split(' ')[1] || last.epi : 'Sem eventos'} tone="jade" />
          <StatCard label="Último EPI ausente" value={last?.epi.replaceAll('_', ' ') || 'Nenhum'} detail="Ocorrência mais recente" tone="citrine" />
        </div>
      </section>

      <div className="dot-divider" />
      <section className="summary-strip">
        <article><span>Alertas recentes</span><strong>{data.recent.length}</strong><small>capturas disponíveis</small><a href="/detections">Ver histórico　→</a></article>
        <article><span>Maior recorrência</span><strong>{topEpi?.name.replaceAll('_', ' ') || '—'}</strong><small>{topEpi ? `${topEpi.count} ocorrências` : 'Aguardando dados'}</small><a href="/analytics">Analisar dados　→</a></article>
        <article><span>Status da operação</span><strong>Ativo</strong><small>processamento local</small><a href="/about">Ver detalhes　→</a></article>
      </section>

      <div className="dot-divider" />
      <section className="dashboard-table">
        <div className="panel-heading"><div><h2>Detecções e ocorrências</h2></div><a className="text-link" href="/detections">Ver histórico completo →</a></div>
        <DetectionTable items={data.recent} compact />
      </section>
    </section>
  )
}
