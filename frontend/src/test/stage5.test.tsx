import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthGate } from '../App'
import { AuthProvider } from '../hooks/useAuth'
import { AppLayout } from '../layouts/AppLayout'
import { HiveQrCard } from '../components/qr/HiveQr'
import { HiveFormPage } from '../pages/HiveFormPage'
import { OpenQrPage } from '../pages/OpenQrPage'
import { ScanPage } from '../pages/ScanPage'
import { resetStartParamForTests } from '../services/telegram'
import type { TelegramWebApp } from '../types/telegram'
import type { UserRole } from '../types/api'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const HIVE_ID = '550e8400-e29b-41d4-a716-446655440000'
type Handler = (url: string, init?: RequestInit) => Response | undefined

function Where() {
  const l = useLocation()
  return <div data-testid="where">{l.pathname}{l.search}</div>
}

function setup(role: UserRole, handler: Handler, path: string, routes: React.ReactNode, wa: Partial<TelegramWebApp> = {}) {
  window.Telegram = {
    WebApp: {
      initData: 'x', initDataUnsafe: {}, isVersionAtLeast: () => true,
      BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} },
      HapticFeedback: { impactOccurred() {}, notificationOccurred() {}, selectionChanged() {} },
      ...wa,
    } as unknown as TelegramWebApp,
  }
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/api/auth/telegram')) {
      return json({ access_token: 't', token_type: 'bearer', expires_in: 60, start_param: null,
        user: { id: 'u1', telegram_id: 1, username: null, first_name: 'Иван', last_name: null, display_name: 'Иван', role, is_active: true, created_at: '' } })
    }
    return handler(url, init) ?? json({ detail: 'not mocked' }, 500)
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <AuthProvider><AuthGate>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            {routes}
            <Route path="/hives/:id" element={<Where />} />
            <Route path="/hives/new" element={<Where />} />
          </Routes>
        </MemoryRouter>
      </AuthGate></AuthProvider>
    </QueryClientProvider>,
  )
  return spy
}

const resolveWith = (body: object): Handler => (url) =>
  url.includes('/api/qr/resolve') ? json({ hive_id: null, hive_number: null, apiary_name: null, is_archived: false, can_register: false, ...body }) : undefined

describe('Opening a scanned code', () => {
  it('goes straight to the hive when the QR is known', async () => {
    const spy = setup('VIEWER', resolveWith({ status: 'found', hive_id: HIVE_ID }), `/open?code=hive_${HIVE_ID}`,
      <Route path="/open" element={<OpenQrPage />} />)
    expect(await screen.findByTestId('where')).toHaveTextContent(`/hives/${HIVE_ID}`)
    expect(spy.mock.calls.some(([u]) => String(u).includes(`code=hive_${HIVE_ID}`))).toBe(true)
  })

  it('offers registration of an unknown QR to a beekeeper', async () => {
    setup('BEEKEEPER', resolveWith({ status: 'unknown', hive_id: HIVE_ID, can_register: true }), `/open?code=hive_${HIVE_ID}`,
      <Route path="/open" element={<OpenQrPage />} />)
    expect(await screen.findByText('Улей не найден')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Зарегистрировать улей с этим QR' }))
    expect(await screen.findByTestId('where')).toHaveTextContent(`/hives/new?qr=${HIVE_ID}`)
  })

  it('tells a viewer to ask an administrator', async () => {
    setup('VIEWER', resolveWith({ status: 'unknown', hive_id: HIVE_ID }), '/open?code=x', <Route path="/open" element={<OpenQrPage />} />)
    expect(await screen.findByText(/Попросите администратора/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Зарегистрировать/ })).not.toBeInTheDocument()
  })

  it('explains a code that is not a hive QR', async () => {
    setup('VIEWER', resolveWith({ status: 'invalid' }), '/open?code=hello', <Route path="/open" element={<OpenQrPage />} />)
    expect(await screen.findByText('Это не QR-код улья')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Сканировать снова' })).toBeInTheDocument()
  })
})

describe('Scanner', () => {
  it('opens the Telegram camera at once and opens the scanned hive', async () => {
    let onText: ((t: string) => boolean | void) | undefined
    const showScanQrPopup = vi.fn((_p: { text?: string }, cb?: (t: string) => boolean | void) => { onText = cb })
    setup('VIEWER', resolveWith({ status: 'found', hive_id: HIVE_ID }), '/scan', <>
      <Route path="/scan" element={<ScanPage />} />
      <Route path="/open" element={<OpenQrPage />} />
    </>, { showScanQrPopup })
    await waitFor(() => expect(showScanQrPopup).toHaveBeenCalledTimes(1))
    expect(showScanQrPopup.mock.calls[0][0]).toEqual({ text: 'Наведите камеру на QR-код улья' })
    let closed: boolean | void = false
    await waitFor(() => { closed = onText!(`https://t.me/umar_bee_bot/app?startapp=hive_${HIVE_ID}`) })
    expect(closed).toBe(true)
    expect(await screen.findByTestId('where')).toHaveTextContent(`/hives/${HIVE_ID}`)
  })

  it('falls back to manual entry when the camera is not available', async () => {
    setup('VIEWER', resolveWith({ status: 'found', hive_id: HIVE_ID }), '/scan', <>
      <Route path="/scan" element={<ScanPage />} />
      <Route path="/open" element={<OpenQrPage />} />
    </>)
    expect(await screen.findByText(/Камера доступна, когда приложение открыто в Telegram/)).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Код или ссылка/), `hive_${HIVE_ID}`)
    await userEvent.click(screen.getByRole('button', { name: 'Открыть улей' }))
    expect(await screen.findByTestId('where')).toHaveTextContent(`/hives/${HIVE_ID}`)
  })
})

describe('Deep link', () => {
  it('opens the hive from start_param once after login', async () => {
    resetStartParamForTests()
    setup('VIEWER', (url) => resolveWith({ status: 'found', hive_id: HIVE_ID })(url) ?? (url.includes('/api/') ? json({}) : undefined), '/', <>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<div>home</div>} />
        <Route path="open" element={<OpenQrPage />} />
      </Route>
    </>, { initDataUnsafe: { start_param: `hive_${HIVE_ID}` } })
    expect(await screen.findByTestId('where')).toHaveTextContent(`/hives/${HIVE_ID}`)
  })
})

const qrInfo = {
  hive_id: HIVE_ID, hive_number: '27', apiary_name: 'Пасека', code: `hive_${HIVE_ID}`, deep_link: null,
  content: `hive_${HIVE_ID}`, deep_link_ready: false, svg_data_uri: 'data:image/svg+xml;base64,PHN2Zy8+',
  print_count: 0, last_printed_at: null,
}

describe('Hive QR card', () => {
  it('shows the QR, warns when the bot is not configured and sends the PDF to the chat', async () => {
    const spy = setup('ASSISTANT', (url, init) => {
      if (url.endsWith(`/api/hives/${HIVE_ID}/qr`)) return json(qrInfo)
      if (url.endsWith('/api/qr/labels') && init?.method === 'POST') return json({ sent: true, labels: 1 })
      return undefined
    }, '/x', <Route path="/x" element={<HiveQrCard hiveId={HIVE_ID} />} />)
    expect(await screen.findByText('Ещё не печатался')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /QR-код улья/ }))
    expect(screen.getByRole('img', { name: 'QR-код улья №27' })).toBeInTheDocument()
    expect(screen.getByText(/Укажите бота/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Отправить PDF в чат' }))
    expect(await screen.findByText(/отправлен в чат с ботом/)).toBeInTheDocument()
    const post = spy.mock.calls.find(([u, i]) => String(u).endsWith('/api/qr/labels') && i?.method === 'POST')!
    expect(JSON.parse(String(post[1]!.body))).toEqual({ hive_ids: [HIVE_ID], delivery: 'telegram' })
  })

  it('hides printing from a viewer', async () => {
    setup('VIEWER', (url) => (url.endsWith('/qr') ? json({ ...qrInfo, deep_link_ready: true, deep_link: 'https://t.me/b/a?startapp=x' }) : undefined),
      '/x', <Route path="/x" element={<HiveQrCard hiveId={HIVE_ID} />} />)
    await userEvent.click(await screen.findByRole('button', { name: /QR-код улья/ }))
    expect(screen.getByText('https://t.me/b/a?startapp=x')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /PDF/ })).not.toBeInTheDocument()
  })
})

describe('Registering a hive from a QR', () => {
  it('sends the scanned identifier as the new hive id', async () => {
    const spy = setup('BEEKEEPER', (url, init) => {
      if (url.includes('/api/apiaries')) return json([{ id: 'a1', name: 'Пасека', is_archived: false }])
      if (url.includes('/api/queens')) return json({ items: [], total: 0 })
      if (url.endsWith('/api/hives') && init?.method === 'POST') return json({ id: HIVE_ID }, 201)
      return undefined
    }, `/hives/new?qr=${HIVE_ID}`, <Route path="/hives/new" element={<HiveFormPage />} />)
    expect(await screen.findByText(/привязан к отсканированному QR-коду/)).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Номер/), '40')
    await userEvent.click(screen.getByRole('button', { name: /Создать|Сохранить/ }))
    await waitFor(() => expect(spy.mock.calls.some(([u, i]) => String(u).endsWith('/api/hives') && i?.method === 'POST')).toBe(true))
    const post = spy.mock.calls.find(([u, i]) => String(u).endsWith('/api/hives') && i?.method === 'POST')!
    expect(JSON.parse(String(post[1]!.body))).toMatchObject({ id: HIVE_ID, apiary_id: 'a1', hive_number: '40' })
  })
})
