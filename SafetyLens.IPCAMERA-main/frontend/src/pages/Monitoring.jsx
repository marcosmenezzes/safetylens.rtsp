import { useEffect, useState } from 'react'
import { sendJson, useApi } from '../api'
import Icon from '../components/Icon'
import { ErrorState, LoadingState } from '../components/States'

const tabs = [
  ['image', 'image', 'Imagem'],
  ['detection', 'target', 'Detecção'],
  ['alerts', 'bell', 'Alertas'],
  ['cameras', 'camera', 'Câmeras'],
]

const fields = {
  image: [
    ['brightness', 'Brilho', 0, 200, '%', 'sun'],
    ['contrast', 'Contraste', 0, 200, '%', 'contrast'],
    ['sharpness', 'Nitidez', 0, 10, '', 'focus'],
  ],
  detection: [
    ['minConfidence', 'Confiança mínima', 0, 1, '', 'target', .01],
  ],
  alerts: [
    ['delayTime', 'Intervalo entre alertas', 0, 300, ' s', 'history'],
  ],
}

/** Renderiza um controle deslizante a partir da definição declarativa do campo. */
function RangeField({ field, value, onChange }) {
  const [name, label, min, max, unit, icon, step = 1] = field
  const shown = name === 'minConfidence' ? `${Math.round(value * 100)}%` : `${value}${unit}`
  return (
    <label className="control-field">
      <span><span className="control-label"><Icon name={icon} />{label}</span><output>{shown}</output></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(name, Number(event.target.value))} />
    </label>
  )
}

/** Opera o stream, ajustes do detector e cadastro das fontes de vídeo. */
export default function Monitoring() {
  const { data, error, loading, retry } = useApi('/api/camera', { pollMs: 2000 })
  const cameras = useApi('/api/cameras')
  const [tab, setTab] = useState('image')
  const [settings, setSettings] = useState(null)
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [cameraForm, setCameraForm] = useState({ name: '', ip: '', port: 554 })
  const [streamKey, setStreamKey] = useState(0)

  useEffect(() => { if (data) setSettings((current) => current || data.settings) }, [data])

  async function saveSettings() {
    // Envia todos os ajustes juntos para gerar apenas uma gravação no YAML.
    setSaving(true)
    setMessage('')
    try {
      const result = await sendJson('/api/camera/settings', 'PATCH', settings)
      setSettings(result.settings)
      setMessage('Ajustes salvos e aplicados.')
    } catch (requestError) {
      setMessage(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  async function registerCamera(event) {
    // O backend valida rede privada e escolhe o caminho RTSP/HTTP apropriado.
    event.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await sendJson('/api/cameras', 'POST', cameraForm)
      setCameraForm({ name: '', ip: '', port: 554 })
      setMessage('Câmera cadastrada. Conexão iniciada.')
      cameras.retry()
      retry()
      setStreamKey((value) => value + 1)
    } catch (requestError) {
      setMessage(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  async function useNativeCamera() {
    // Recarregar a chave força o navegador a abandonar o stream MJPEG anterior.
    setSaving(true)
    try {
      await sendJson('/api/cameras/native', 'POST')
      setMessage('Câmera nativa selecionada.')
      cameras.retry()
      retry()
      setStreamKey((value) => value + 1)
    } catch (requestError) {
      setMessage(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  async function reconnectCamera(camera) {
    // Reutiliza o cadastro persistido para testar novamente seus caminhos de vídeo.
    setSaving(true)
    setMessage('')
    try {
      await sendJson(`/api/cameras/${camera.ip}/connect`, 'POST')
      setMessage(`Reconectando ${camera.name}…`)
      setStreamKey((value) => value + 1)
      cameras.retry()
      retry()
    } catch (requestError) {
      setMessage(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  async function deleteCamera(camera) {
    // Confirma localmente porque a remoção não possui desfazer no YAML.
    if (!window.confirm(`Apagar a câmera ${camera.name}?`)) return
    setSaving(true)
    setMessage('')
    try {
      await sendJson(`/api/cameras/${camera.ip}`, 'DELETE')
      setMessage(`${camera.name} foi apagada.`)
      setStreamKey((value) => value + 1)
      cameras.retry()
      retry()
    } catch (requestError) {
      setMessage(requestError.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading || !data || !settings) return <LoadingState />
  if (error) return <ErrorState message={error} retry={retry} />

  const status = data.status
  const online = status.state === 'online'
  return (
    <section className="monitor-page">
      <header className="monitor-header">
        <div><span className="eyebrow">OPERAÇÃO EM TEMPO REAL</span><h2>Central de monitoramento</h2><p>Visualize a análise e ajuste o modelo sem interromper o painel.</p></div>
        <div className={`camera-state camera-state--${status.state}`}><i /><span>{online ? 'Sistema online' : status.message}</span></div>
      </header>

      <div className="monitor-grid">
        <article className="live-panel">
          <div className="panel-title"><div><Icon name="camera" /><span>Monitor ao vivo</span></div><span className="source-chip">{data.source.name}</span></div>
          <div className="camera-viewport">
            <img src={`${data.streamUrl}?v=${encodeURIComponent(data.source.name)}-${streamKey}`} alt={`Transmissão ao vivo de ${data.source.name}`} />
            {!online && <div className="camera-overlay"><Icon name="camera" size={30} /><strong>{status.state === 'connecting' ? 'Conectando…' : 'Preparando transmissão'}</strong><span>{status.message}</span></div>}
            <div className="live-label"><i /> AO VIVO</div>
          </div>
          <footer className="camera-meta">
            <div><span>Status</span><strong>{status.message}</strong></div>
            <div><span>Resolução</span><strong>{status.resolution || '—'}</strong></div>
            <div><span>Processamento</span><strong>{status.fps ? `${status.fps} FPS` : '—'}</strong></div>
          </footer>
          <div className={status.missingEpis?.length ? 'detection-banner detection-banner--alert' : 'detection-banner'}>
            <Icon name="target" />
            <div><span>Leitura atual</span><strong>{status.missingEpis?.length ? `EPIs ausentes: ${status.missingEpis.join(', ').replaceAll('_', ' ')}` : 'Nenhum alerta no frame mais recente'}</strong></div>
          </div>
        </article>

        <aside className="control-panel">
          <div className="panel-title"><div><Icon name="settings" /><span>Painel de controle</span></div></div>
          <div className="control-tabs" role="tablist" aria-label="Configurações da câmera">
            {tabs.map(([id, icon, label]) => <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => { setTab(id); setMessage('') }}><Icon name={icon} />{label}</button>)}
          </div>

          <div className="control-content" role="tabpanel">
            {fields[tab] && <>
              <div className="control-section-heading"><div><span className="eyebrow">CONFIGURAÇÃO</span><h3>{tabs.find(([id]) => id === tab)[2]}</h3></div><span>Alterações locais</span></div>
              <div className="control-fields">{fields[tab].map((field) => <RangeField key={field[0]} field={field} value={settings[field[0]]} onChange={(name, value) => setSettings((current) => ({ ...current, [name]: value }))} />)}</div>
              {tab === 'image' && <label className="switch-field"><span><strong>Escala de cinza</strong><small>Remove as cores antes da inferência</small></span><input type="checkbox" checked={settings.grayscale} onChange={(event) => setSettings((current) => ({ ...current, grayscale: event.target.checked }))} /><i /></label>}
              {tab === 'detection' && <div className="system-note"><i /><div><strong>Modelo carregado</strong><span>A confiança mínima filtra detecções fracas.</span></div></div>}
              <button className="button control-save" type="button" disabled={saving} onClick={saveSettings}>{saving ? 'Salvando…' : 'Salvar ajustes'}</button>
            </>}

            {tab === 'cameras' && <>
              <div className="control-section-heading"><div><span className="eyebrow">FONTES DE VÍDEO</span><h3>Câmeras</h3></div><button className="button button--secondary native-button" type="button" disabled={saving} onClick={useNativeCamera}>Usar nativa</button></div>
              <form className="camera-form" onSubmit={registerCamera}>
                <label>Nome<input required maxLength="64" value={cameraForm.name} onChange={(event) => setCameraForm({ ...cameraForm, name: event.target.value })} placeholder="Entrada principal" /></label>
                <label>Endereço IPv4<input required inputMode="decimal" value={cameraForm.ip} onChange={(event) => setCameraForm({ ...cameraForm, ip: event.target.value })} placeholder="192.168.1.20" /></label>
                <label>Porta<input required type="number" min="1" max="65535" value={cameraForm.port} onChange={(event) => setCameraForm({ ...cameraForm, port: Number(event.target.value) })} /></label>
                <button className="button" type="submit" disabled={saving}><Icon name="plus" />Cadastrar e conectar</button>
              </form>
              <div className="camera-list"><div className="camera-list-heading"><span>Câmeras cadastradas</span><small>{cameras.data?.items?.length || 0}</small></div>{cameras.data?.items?.length ? cameras.data.items.map((camera) => <article key={camera.ip}><span className="camera-list-icon"><Icon name="camera" /></span><div className="camera-list-data"><strong>{camera.name}</strong><span>{camera.ip}:{camera.port}</span></div><div className="camera-list-actions"><b>{camera.active ? 'Selecionada' : 'Salva'}</b><button type="button" disabled={saving} onClick={() => reconnectCamera(camera)} aria-label={`Conectar ${camera.name}`}><Icon name="refresh" />{camera.active ? 'Tentar novamente' : 'Conectar'}</button><button className="camera-delete" type="button" disabled={saving} onClick={() => deleteCamera(camera)} aria-label={`Apagar ${camera.name}`}><Icon name="trash" />Apagar</button></div></article>) : <div className="camera-list-empty">Nenhuma câmera de rede cadastrada.</div>}</div>
            </>}
            {message && <p className="control-message" role="status">{message}</p>}
          </div>
        </aside>
      </div>
    </section>
  )
}
