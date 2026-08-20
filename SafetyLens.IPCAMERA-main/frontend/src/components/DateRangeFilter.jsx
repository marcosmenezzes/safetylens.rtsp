import { useState } from 'react'

/** Valida o intervalo no navegador antes de solicitar novos dados à API. */
export default function DateRangeFilter({ initial = {}, onApply }) {
  const [values, setValues] = useState({ start: initial.start || '', end: initial.end || '' })
  const [error, setError] = useState('')

  function submit(event) {
    // O backend repete esta validação porque o navegador não é fronteira confiável.
    event.preventDefault()
    if (values.start && values.end && values.start > values.end) {
      setError('A data inicial deve ser anterior à data final.')
      return
    }
    setError('')
    onApply(values)
  }

  return (
    <form className="date-filter" onSubmit={submit}>
      <label>Início<input type="datetime-local" value={values.start} onChange={(event) => setValues({ ...values, start: event.target.value })} /></label>
      <label>Fim<input type="datetime-local" value={values.end} onChange={(event) => setValues({ ...values, end: event.target.value })} /></label>
      <button className="button" type="submit">Aplicar período</button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </form>
  )
}
