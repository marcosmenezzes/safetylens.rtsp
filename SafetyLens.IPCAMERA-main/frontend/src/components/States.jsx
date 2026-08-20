/** Mantém a geometria do conteúdo enquanto uma requisição está em andamento. */
export function LoadingState() {
  return <div className="state-card" aria-live="polite"><span className="loader" /> Carregando dados…</div>
}

/** Explica a falha e oferece nova tentativa sem recarregar toda a aplicação. */
export function ErrorState({ message, retry }) {
  return (
    <div className="state-card state-card--error" role="alert">
      <div><strong>Não foi possível carregar.</strong><p>{message}</p></div>
      <button className="button button--secondary" type="button" onClick={retry}>Tentar novamente</button>
    </div>
  )
}

/** Comunica ausência legítima de dados, diferente de carregamento ou erro. */
export function EmptyState({ children = 'Nenhuma detecção encontrada neste período.' }) {
  return <div className="empty-state"><p>{children}</p></div>
}
