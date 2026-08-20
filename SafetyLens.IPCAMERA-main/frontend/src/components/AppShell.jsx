import { useEffect, useState } from 'react'
import Icon from './Icon'

const links = [
  ['/', 'dashboard', 'Visão geral'],
  ['/monitoring', 'camera', 'Monitoramento'],
  ['/detections', 'history', 'Histórico'],
  ['/analytics', 'chart', 'Estatísticas'],
  ['/about', 'info', 'Sobre'],
]

/** Mantém navegação, tema e estrutura responsiva iguais em todas as páginas. */
export default function AppShell({ title, children }) {
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('safetylens-sidebar-collapsed') === 'true' }
    catch { return false }
  })
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('safetylens-climate-theme') || 'dark' }
    catch { return 'dark' }
  })

  useEffect(() => {
    // Escape fecha o drawer mobile, padrão esperado de teclado.
    const close = (event) => event.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [])

  useEffect(() => {
    // O atributo no HTML ativa os tokens do tema antes de qualquer componente.
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('safetylens-climate-theme', theme) }
    catch { /* Preferência continua válida durante a sessão. */ }
  }, [theme])

  useEffect(() => {
    // A preferência evita reabrir a barra após cada recarregamento.
    try { localStorage.setItem('safetylens-sidebar-collapsed', String(collapsed)) }
    catch { /* Preferência continua válida durante a sessão. */ }
  }, [collapsed])

  return (
    <div className={collapsed ? 'app-shell app-shell--collapsed' : 'app-shell'}>
      <aside className={open ? 'sidebar sidebar--open' : 'sidebar'}>
        <div className="sidebar-brand-row">
          <a className="brand" href="/" aria-label="SafetyLens — início"><span>SafetyLens</span></a>
          <button className="collapse-button" type="button" aria-label={collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'} onClick={() => setCollapsed((value) => !value)}><Icon name="chevron" /></button>
        </div>
        <nav id="main-navigation" className="nav" aria-label="Navegação principal">
          <span className="nav-label">MENU</span>
          {links.map(([href, icon, label]) => (
            <a key={href} href={href} aria-label={label} title={collapsed ? label : undefined} aria-current={window.location.pathname === href ? 'page' : undefined}>
              <span><Icon name={icon} /></span><b>{label}</b>
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="system-status"><span /><b>Sistema local ativo</b></div>
          <button className="theme-button" type="button" aria-label={theme === 'light' ? 'Ativar tema escuro' : 'Ativar tema claro'} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
            <Icon name="sun" /><b>{theme === 'light' ? 'Tema escuro' : 'Tema claro'}</b>
          </button>
        </div>
      </aside>
      {open && <button className="sidebar-backdrop" type="button" aria-label="Fechar menu" onClick={() => setOpen(false)} />}
      <div className="workspace">
        <header className="topbar">
          <button
            className="menu-button"
            type="button"
            aria-label="Alternar menu"
            aria-controls="main-navigation"
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            <span /><span /><span />
          </button>
          <div className="page-heading"><span>Dashboard</span><b>/</b><h1>{title}</h1></div>
          <div className="topbar-actions"><span className="live-dot" /> Monitoramento ativo</div>
          <button className="top-theme-button" type="button" aria-label={theme === 'light' ? 'Ativar tema escuro' : 'Ativar tema claro'} onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}><Icon name="sun" /></button>
        </header>
        <main>{children}</main>
        <footer><span>SafetyLens · visão computacional aplicada à segurança</span><span>Dados processados localmente</span></footer>
      </div>
    </div>
  )
}
