import { useMemo, useState } from 'react'
import { buildQuery, useApi } from '../api'
import DateRangeFilter from '../components/DateRangeFilter'
import DetectionTable from '../components/DetectionTable'
import { ErrorState, LoadingState } from '../components/States'

/** Lista evidências com filtros e paginação sincronizados com a API. */
export default function Detections() {
  const [filters, setFilters] = useState({ start: '', end: '' })
  const [page, setPage] = useState(1)
  const path = useMemo(() => `/api/detections?${buildQuery({ ...filters, page, limit: 15 })}`, [filters, page])
  const { data, error, loading, retry } = useApi(path)

  function apply(values) {
    // Um novo intervalo sempre começa na primeira página para não cair em vazio.
    setFilters(values)
    setPage(1)
  }

  return (
    <>
      <section className="section-intro"><div><span className="eyebrow">RASTREABILIDADE</span><h2>Cada alerta, uma evidência.</h2></div><p>Filtre o período e consulte as capturas associadas às ocorrências detectadas pelo modelo.</p></section>
      <DateRangeFilter initial={filters} onApply={apply} />
      <section className="panel section-panel">
        <div className="panel-heading"><div><span className="eyebrow">REGISTRO DE EVENTOS</span><h2>Ocorrências</h2></div><span className="panel-count">{data?.total ?? '—'} registros</span></div>
        {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={retry} /> : <DetectionTable items={data.items} />}
        {data && data.totalPages > 1 && (
          <nav className="pagination" aria-label="Paginação do histórico">
            <button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>← Anterior</button>
            <span>Página <strong>{page}</strong> de {data.totalPages}</span>
            <button type="button" disabled={page === data.totalPages} onClick={() => setPage((value) => value + 1)}>Próxima →</button>
          </nav>
        )}
      </section>
    </>
  )
}
