import { useCallback, useEffect, useState } from 'react'

/** Busca JSON, preserva o último resultado e oferece polling/repetição às páginas. */
export function useApi(path, { pollMs = 0 } = {}) {
  const [state, setState] = useState({ data: null, error: '', loading: true })
  const [attempt, setAttempt] = useState(0)
  const retry = useCallback(() => setAttempt((value) => value + 1), [])

  useEffect(() => {
    const controller = new AbortController()
    setState((current) => ({ ...current, error: '', loading: !current.data }))
    const load = () => fetch(path, { signal: controller.signal })
        .then(async (response) => {
          const body = await response.json()
          if (!response.ok) throw new Error(body.error || 'Não foi possível carregar os dados')
          return body
        })
        .then((data) => setState({ data, error: '', loading: false }))
        .catch((error) => {
          if (error.name !== 'AbortError') setState((current) => ({ data: current.data, error: error.message, loading: false }))
        })
    load()
    const interval = pollMs ? window.setInterval(load, pollMs) : null
    return () => { controller.abort(); if (interval) window.clearInterval(interval) }
  }, [path, attempt, pollMs])

  return { ...state, retry }
}

export function formatDate(value, withTime = true) {
  // A API usa ISO; toda apresentação humana fica centralizada em pt-BR aqui.
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    ...(withTime ? { timeStyle: 'short' } : {}),
  }).format(new Date(value))
}

export function buildQuery(values) {
  // URLSearchParams faz o escape correto e ignora filtros ainda vazios.
  const query = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => value && query.set(key, value))
  return query.toString()
}

export async function sendJson(path, method, body = {}) {
  // Único caminho para mutações mantém cabeçalhos e mensagens consistentes.
  const response = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Não foi possível concluir a ação')
  return data
}
