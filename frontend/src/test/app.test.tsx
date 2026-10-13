import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthGate } from '../App'
import { AuthProvider } from '../hooks/useAuth'
import { navItems } from '../components/BottomNav'
import { HomePage } from '../pages/HomePage'
import type { TelegramWebApp } from '../types/telegram'

const user = {
  id: 'u1', telegram_id: 1000, username: 'ivan', first_name: 'Иван', last_name: null,
  display_name: 'Иван', role: 'BEEKEEPER', is_active: true, created_at: '2026-10-06T00:00:00Z',
}

function fakeTelegram(initData = 'user=%7B%7D&hash=abc') {
  window.Telegram = {
    WebApp: { initData, initDataUnsafe: {}, BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} } } as unknown as TelegramWebApp,
  }
}

function mockFetch(handler: (url: string, init?: RequestInit) => Response) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => handler(String(input), init))
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const dashboard = {
  year: 2026, finance_ready: false, honey_by_month: Array(12).fill('0'), honey_by_hive: [], strength: [], diseases: [], queen_ages: [],
  tiles: { hives: 4, queens_in_hives: 3, strong: 0, weak: 0, sick: 0, queenless: 0, needs_inspection: 0, open_tasks: 0, overdue_tasks: 0, honey_year_kg: '0', best_hive: null },
}

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <AuthGate>
          <MemoryRouter>
            <Routes><Route path="/" element={<HomePage />} /></Routes>
          </MemoryRouter>
        </AuthGate>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('Telegram authentication', () => {
  it('shows "open in Telegram" when there is no initData', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')  // a developer's .env.local must not affect this test
    renderApp()
    expect(await screen.findByText('Откройте в Telegram')).toBeInTheDocument()
  })

  it('sends raw initData to the backend and shows the user', async () => {
    fakeTelegram('signed-init-data')
    const fetchSpy = mockFetch((url) => {
      if (url.endsWith('/api/auth/telegram'))
        return json({ access_token: 'tok', token_type: 'bearer', expires_in: 60, user, start_param: null })
      if (url.includes('/api/dashboard')) return json(dashboard)
      return json({}, 404)
    })
    renderApp()
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    expect(screen.getByText('Пчеловод')).toBeInTheDocument()

    const [, init] = fetchSpy.mock.calls[0]
    expect(JSON.parse(String(init?.body))).toEqual({ init_data: 'signed-init-data' })

    // Subsequent calls carry the bearer token
    await waitFor(() => expect(screen.getByText('4')).toBeInTheDocument())
    const dashCall = fetchSpy.mock.calls.find(([u]) => String(u).includes('/api/dashboard'))!
    expect(new Headers(dashCall[1]?.headers).get('Authorization')).toBe('Bearer tok')
  })

  it('shows a readable error when the backend rejects initData', async () => {
    fakeTelegram()
    mockFetch(() => json({ detail: 'Не удалось подтвердить вход через Telegram: initData signature is invalid' }, 401))
    renderApp()
    expect(await screen.findByText('Не удалось войти')).toBeInTheDocument()
    expect(screen.getByText(/signature is invalid/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Повторить' })).toBeInTheDocument()
  })

  it('shows a network error message when the server is unreachable', async () => {
    fakeTelegram()
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    renderApp()
    expect(await screen.findByText(/Нет соединения с сервером/)).toBeInTheDocument()
  })
})

describe('Local dev login', () => {
  it('logs in with a pasted signed initData when opened outside Telegram', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')
    const fetchSpy = mockFetch((url) => {
      if (url.endsWith('/api/auth/telegram'))
        return json({ access_token: 'tok', token_type: 'bearer', expires_in: 60, user, start_param: null })
      if (url.includes('/api/hives')) return json({ items: [], total: 0 })
      if (url.includes('/api/queens')) return json({ items: [], total: 0 })
      return json({}, 404)
    })
    renderApp()
    const box = await screen.findByLabelText('Строка входа')
    await userEvent.type(box, 'signed-by-dev-script')
    await userEvent.click(screen.getByRole('button', { name: 'Войти' }))
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    const [, init] = fetchSpy.mock.calls[0]
    expect(JSON.parse(String(init?.body))).toEqual({ init_data: 'signed-by-dev-script' })
  })
})

describe('BottomNav', () => {
  it('gives CRM to admin and beekeeper, queens to everyone else', () => {
    expect(navItems(true).map((i) => i.label)).toEqual(['Главная', 'Ульи', 'Сканер', 'CRM', 'Отчёты', 'Ещё'])
    expect(navItems(false).map((i) => i.label)).toEqual(['Главная', 'Ульи', 'Сканер', 'Матки', 'Отчёты', 'Ещё'])
  })
})
