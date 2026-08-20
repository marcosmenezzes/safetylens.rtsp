import { useEffect, useRef, useState } from 'react'
import { formatDate } from '../api'
import Icon from './Icon'
import { EmptyState } from './States'

/** Exibe ocorrências e abre a evidência no diálogo nativo sem sair da página. */
export default function DetectionTable({ items, compact = false }) {
  const [selected, setSelected] = useState(null)
  const dialogRef = useRef(null)
  const triggerRef = useRef(null)

  useEffect(() => {
    // showModal cria top layer, prende o foco e habilita fechamento por Escape.
    if (selected && !dialogRef.current.open) dialogRef.current.showModal()
  }, [selected])

  function closeCapture() {
    // Centraliza todos os caminhos de fechamento no comportamento nativo.
    dialogRef.current?.close()
  }

  if (!items.length) return <EmptyState />
  return (
    <div className="table-scroll">
      <table className={compact ? 'data-table data-table--compact' : 'data-table'}>
        <caption className="sr-only">Ocorrências de equipamentos de proteção ausentes</caption>
        <thead><tr><th scope="col">Evento</th><th scope="col">Data e hora</th><th scope="col">EPI ausente</th><th scope="col">Evidência</th></tr></thead>
        <tbody>{items.map((item) => (
          <tr key={item.id}>
            <td><span className="event-id">#{item.id}</span></td>
            <td>{formatDate(item.timestamp)}</td>
            <td><span className="risk-pill">{item.epi.replaceAll('_', ' ')}</span></td>
            <td>{item.imageUrl ? <button className="text-link capture-trigger" type="button" onClick={(event) => { triggerRef.current = event.currentTarget; setSelected(item) }}>Ver captura</button> : <span className="muted">Sem imagem</span>}</td>
          </tr>
        ))}</tbody>
      </table>
      {selected && (
        <dialog
          ref={dialogRef}
          className="capture-dialog"
          aria-labelledby="capture-title"
          onClick={(event) => event.target === event.currentTarget && closeCapture()}
          onClose={() => { setSelected(null); triggerRef.current?.focus() }}
        >
          <article className="capture-modal">
            <header className="capture-modal__header">
              <div>
                <p className="eyebrow">EVIDÊNCIA DO EVENTO</p>
                <h2 id="capture-title">Captura #{selected.id}</h2>
              </div>
              <button className="capture-close" type="button" aria-label="Fechar captura" onClick={closeCapture}><Icon name="close" /></button>
            </header>
            <div className="capture-image">
              <img src={selected.imageUrl} alt={`Captura do evento ${selected.id}, registrada em ${formatDate(selected.timestamp)}`} />
            </div>
            <footer className="capture-meta">
              <div><span>Data e hora</span><strong>{formatDate(selected.timestamp)}</strong></div>
              <div><span>EPI ausente</span><strong>{selected.epi.replaceAll('_', ' ')}</strong></div>
            </footer>
          </article>
        </dialog>
      )}
    </div>
  )
}
