import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthGate } from '../App'
import { AuthProvider } from '../hooks/useAuth'
import { BottomNav } from '../components/BottomNav'
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
    renderApp()
    expect(await screen.findByText('Откройте в Telegram')).toBeInTheDocument()
  })

  it('sends raw initData to the backend and shows the user', async () => {
    fakeTelegram('signed-init-data')
    const fetchSpy = mockFetch((url) => {
      if (url.endsWith('/api/auth/telegram'))
        return json({ access_token: 'tok', token_type: 'bearer', expires_in: 60, user, start_param: null })
      if (url.includes('/api/hives')) return json({ items: [], total: 4 })
      if (url.includes('/api/queens')) return json({ items: [], total: 3 })
      return json({}, 404)
    })
    renderApp()
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    expect(screen.getByText('Пчеловод')).toBeInTheDocument()

    const [, init] = fetchSpy.mock.calls[0]
    expect(JSON.parse(String(init?.body))).toEqual({ init_data: 'signed-init-data' })

    // Subsequent calls carry the bearer token
    await waitFor(() => expect(screen.getByText('4')).toBeInTheDocument())
    const hivesCall = fetchSpy.mock.calls.find(([u]) => String(u).includes('/api/hives'))!
    expect(new Headers(hivesCall[1]?.headers).get('Authorization')).toBe('Bearer tok')
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

describe('BottomNav', () => {
  it('renders the six main sections and marks the active one', () => {
    render(<MemoryRouter initialEntries={['/queens']}><BottomNav /></MemoryRouter>)
    for (const label of ['Главная', 'Ульи', 'Сканер', 'Матки', 'Отчёты', 'Ещё'])
      expect(screen.getByText(label)).toBeInTheDocument()
    expect(screen.getByText('Матки').closest('a')).toHaveClass('is-active')
    expect(screen.getByText('Главная').closest('a')).not.toHaveClass('is-active')
  })
})
