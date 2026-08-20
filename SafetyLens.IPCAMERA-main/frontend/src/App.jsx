import AppShell from './components/AppShell'
import About from './pages/About'
import Analytics from './pages/Analytics'
import Dashboard from './pages/Dashboard'
import Detections from './pages/Detections'
import Monitoring from './pages/Monitoring'

const routes = {
  '/': { title: 'Visão geral', component: Dashboard },
  '/monitoring': { title: 'Monitoramento', component: Monitoring },
  '/detections': { title: 'Histórico', component: Detections },
  '/analytics': { title: 'Estatísticas', component: Analytics },
  '/about': { title: 'Sobre', component: About },
}

/** Seleciona a página pela URL e a envolve no shell visual compartilhado. */
export default function App() {
  const route = routes[window.location.pathname] || routes['/']
  const Page = route.component
  return (
    <AppShell title={route.title}>
      <Page />
    </AppShell>
  )
}
