/** Gera uma curva cúbica suave sem depender de biblioteca de gráficos. */
function smoothPath(points, height) {
  if (points.length < 2) return ''
  return points.slice(0, -1).reduce((path, point, index) => {
    const previous = points[index - 1] || point
    const next = points[index + 1]
    const after = points[index + 2] || next
    const clamp = (value) => Math.max(0, Math.min(height, value))
    const first = [point[0] + (next[0] - previous[0]) / 6, clamp(point[1] + (next[1] - previous[1]) / 6)]
    const second = [next[0] - (after[0] - point[0]) / 6, clamp(next[1] - (after[1] - point[1]) / 6)]
    return `${path} C ${first.join(',')} ${second.join(',')} ${next.join(',')}`
  }, `M ${points[0].join(',')}`)
}

export function BarChart({ title, data }) {
  // Barras são melhores para comparar categorias de EPI.
  const max = Math.max(...data.map((item) => item.count), 1)
  return (
    <figure className="chart" aria-label={title}>
      <figcaption>{title}<span>{data.reduce((sum, item) => sum + item.count, 0)} eventos</span></figcaption>
      <div className="bar-chart">
        {data.length ? data.map((item, index) => (
          <div className="bar-row" key={item.name}>
            <span>{item.name.replaceAll('_', ' ')}</span>
            <div><i style={{ width: `${(item.count / max) * 100}%`, '--index': index }} /></div>
            <strong>{item.count}</strong>
          </div>
        )) : <p className="chart-empty">Aguardando detecções</p>}
      </div>
    </figure>
  )
}

export function LineChart({ title, data, labelKey = 'date' }) {
  // A série temporal usa SVG para continuar leve, responsiva e acessível.
  const width = 720
  const height = 250
  const max = Math.max(...data.map((item) => item.count), 1)
  const plotData = data.length === 1 ? [data[0], data[0]] : data
  const points = plotData.map((item, index) => {
    const x = index * (width / (plotData.length - 1))
    const y = height - (item.count / max) * (height - 24) - 12
    return [x, y]
  })
  const line = smoothPath(points, height)
  const area = `${line} L ${width},${height} L 0,${height} Z`
  return (
    <figure className="chart" aria-label={title}>
      <figcaption>{title}<span>{data.length} períodos</span></figcaption>
      {data.length ? (
        <>
          <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}: ${data.map((item) => `${item[labelKey]} ${item.count}`).join(', ')}`}>
            <defs><linearGradient id={`area-${labelKey}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="var(--chart-primary)" stopOpacity=".5"/><stop offset="1" stopColor="var(--chart-primary)" stopOpacity=".03"/></linearGradient></defs>
            <path key={`area-${line}`} className="chart-area" d={area} fill={`url(#area-${labelKey})`} />
            <path key={line} className="chart-line" d={line} fill="none" stroke="var(--chart-primary)" strokeWidth="4" pathLength="1" vectorEffect="non-scaling-stroke" />
            {points.map(([x, y], index) => <circle className="chart-point" key={`${plotData[index]?.[labelKey]}-${x}`} cx={x} cy={y} r="7" fill="var(--chart-secondary)" stroke="var(--surface)" strokeWidth="3" style={{ '--index': index }}><title>{plotData[index]?.[labelKey]}: {plotData[index]?.count}</title></circle>)}
          </svg>
          <div className="chart-axis"><span>{data[0]?.[labelKey]}</span><span>{data.at(-1)?.[labelKey]}</span></div>
        </>
      ) : <p className="chart-empty">Aguardando detecções</p>}
    </figure>
  )
}
