import { expect, test } from '@playwright/test'

const detection = { id: 42, timestamp: '2026-08-17T14:30:00', epi: 'Sem_Capacete', imageUrl: '/image/42' }
const dashboard = {
  updatedAt: '2026-08-17T15:00:00',
  summary: { totalDetections: 128, monitoredEpis: 4, lastDetection: detection },
  byEpi: [{ name: 'Sem_Capacete', count: 72 }, { name: 'Sem_Luva', count: 36 }, { name: 'Sem_Oculos', count: 20 }],
  daily: [{ date: '2026-08-15', count: 28 }, { date: '2026-08-16', count: 44 }, { date: '2026-08-17', count: 56 }],
  recent: [detection],
}
const detections = { items: [detection], page: 1, limit: 15, total: 16, totalPages: 2 }
const analytics = {
  updatedAt: '2026-08-17T15:00:00',
  summary: { periodTotal: 128, overallTotal: 512, periodShare: 25, mostMissing: 'Sem_Capacete' },
  trend: dashboard.daily,
  byEpi: dashboard.byEpi.map((item, index) => ({ ...item, percentage: [56.2, 28.1, 15.7][index], trend: [12, -8, 0][index] })),
  monthly: [{ month: '2026-06', count: 98 }, { month: '2026-07', count: 110 }, { month: '2026-08', count: 128 }],
}
const camera = {
  source: { name: 'Câmera nativa', type: 'native' },
  settings: { brightness: 100, contrast: 100, sharpness: 2, grayscale: false, minConfidence: .5, delayTime: 30 },
  status: { state: 'online', message: 'Monitoramento ativo', fps: 24.8, resolution: '1080x1920', missingEpis: [], updatedAt: '2026-08-17T15:00:00' },
  streamUrl: '/api/camera/stream',
}

test.beforeEach(async ({ page }) => {
  await page.route('**/api/dashboard**', (route) => route.fulfill({ json: dashboard }))
  await page.route('**/api/detections**', (route) => route.fulfill({ json: detections }))
  await page.route('**/api/analytics**', (route) => route.fulfill({ json: analytics }))
  await page.route('**/image/42', (route) => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="100%" height="100%" fill="#171717"/></svg>' }))
  await page.route(/\/api\/camera\/stream(?:\?.*)?$/, (route) => route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><rect width="100%" height="100%" fill="#111"/></svg>' }))
  await page.route(/\/api\/cameras\/192\.168\.15\.6\/connect$/, (route) => route.fulfill({ status: 202, json: { camera: { name: 'celular', ip: '192.168.15.6', port: 4747 } } }))
  await page.route(/\/api\/cameras\/192\.168\.15\.6$/, (route) => route.fulfill({ json: { deleted: { name: 'celular', ip: '192.168.15.6' }, active: 'Câmera nativa' } }))
  await page.route(/\/api\/cameras(?:\?.*)?$/, (route) => route.fulfill({ json: { active: 'celular', items: [{ name: 'celular', ip: '192.168.15.6', port: 4747, active: true }] } }))
  await page.route(/\/api\/camera(?:\?.*)?$/, (route) => route.fulfill({ json: camera }))
})

for (const [path, heading] of [['/', 'Visão geral'], ['/monitoring', 'Monitoramento'], ['/detections', 'Histórico'], ['/analytics', 'Estatísticas'], ['/about', 'Sobre']]) {
  test(`${heading} renderiza sem overflow`, async ({ page }, testInfo) => {
    const consoleErrors = []
    page.on('console', (message) => message.type() === 'error' && consoleErrors.push(message.text()))
    await page.goto(path)
    await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)
    expect(overflow).toBe(false)
    expect(consoleErrors).toEqual([])
    await page.screenshot({ path: testInfo.outputPath(`${heading.toLowerCase().replaceAll(' ', '-')}.png`), fullPage: true })
  })
}

test('monitoramento exibe vídeo, controles e cadastro de câmera', async ({ page }) => {
  await page.goto('/monitoring')
  await expect(page.getByText('Central de monitoramento')).toBeVisible()
  await expect(page.getByText('24.8 FPS')).toBeVisible()
  await page.getByRole('tab', { name: 'Câmeras' }).click()
  await expect(page.getByLabel('Nome')).toBeVisible()
  await expect(page.getByLabel('Endereço IPv4')).toBeVisible()
  await expect(page.getByLabel('Porta')).toHaveValue('554')
  await expect(page.getByRole('button', { name: /Cadastrar e conectar/ })).toBeVisible()
  await page.getByRole('button', { name: 'Conectar celular' }).click()
  await expect(page.getByText('Reconectando celular…')).toBeVisible()
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Apagar celular' }).click()
  await expect(page.getByText('celular foi apagada.')).toBeVisible()
})

test('dashboard apresenta métricas e evento recente', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('128', { exact: true })).toBeVisible()
  await expect(page.getByText('Sem Capacete').first()).toBeVisible()
  await expect(page.locator('.chart-line')).toHaveAttribute('d', / C /)
  await expect(page.locator('.chart-point')).toHaveCount(3)
  await expect(page.getByRole('link', { name: /Ver histórico completo/ })).toHaveAttribute('href', '/detections')
})

test('tema escuro é padrão e a preferência persiste', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('button', { name: 'Ativar tema claro' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await expect(page.getByRole('button', { name: 'Ativar tema escuro' })).toBeVisible()
})

test('sidebar desktop pode ser recolhida e persiste', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'Fluxo específico de desktop')
  await page.goto('/')
  await page.getByRole('button', { name: 'Recolher menu lateral' }).click()
  await expect(page.locator('.app-shell')).toHaveClass(/app-shell--collapsed/)
  await expect(page.getByRole('link', { name: 'Monitoramento' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('button', { name: 'Expandir menu lateral' })).toBeVisible()
})

test('histórico aplica período e pagina', async ({ page }) => {
  let requestedUrl = ''
  await page.route('**/api/detections**', (route) => { requestedUrl = route.request().url(); return route.fulfill({ json: detections }) })
  await page.goto('/detections')
  await page.getByRole('textbox', { name: 'Início' }).fill('2026-08-01T00:00')
  await page.getByRole('textbox', { name: 'Fim' }).fill('2026-08-17T23:59')
  await page.getByRole('button', { name: 'Aplicar período' }).click()
  await expect.poll(() => requestedUrl).toContain('start=2026-08-01T00%3A00')
  await page.getByRole('button', { name: /Próxima/ }).click()
  await expect.poll(() => requestedUrl).toContain('page=2')
})

test('histórico abre a captura em diálogo e mantém a página', async ({ page }) => {
  await page.goto('/detections')
  const historyUrl = page.url()
  const trigger = page.getByRole('button', { name: 'Ver captura' })
  await trigger.click()
  const dialog = page.getByRole('dialog', { name: 'Captura #42' })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByText('17/08/2026, 14:30')).toBeVisible()
  await expect(dialog.locator('img')).toHaveAttribute('src', '/image/42')
  expect(page.url()).toBe(historyUrl)
  await page.keyboard.press('Escape')
  await expect(dialog).not.toBeVisible()
  await expect(trigger).toBeFocused()
})

test('menu mobile expõe a navegação', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile', 'Fluxo específico de mobile')
  await page.goto('/')
  const button = page.getByRole('button', { name: 'Alternar menu' })
  await button.click()
  await expect(button).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('link', { name: 'Estatísticas', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(button).toHaveAttribute('aria-expanded', 'false')
})
