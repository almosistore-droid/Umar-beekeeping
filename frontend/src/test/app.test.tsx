import userEvent from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/react'
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
    await userEvent.click(within(box.closest('form')!).getByRole('button', { name: 'Войти' }))
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    const [, init] = fetchSpy.mock.calls.find(([u]) => String(u).endsWith('/api/auth/telegram'))!
    expect(JSON.parse(String(init?.body))).toEqual({ init_data: 'signed-by-dev-script' })
  })
})

describe('BottomNav', () => {
  it('gives CRM to admin and beekeeper, queens to everyone else', () => {
    expect(navItems(true).map((i) => i.label)).toEqual(['Главная', 'Ульи', 'Сканер', 'CRM', 'Отчёты', 'Ещё'])
    expect(navItems(false).map((i) => i.label)).toEqual(['Главная', 'Ульи', 'Сканер', 'Матки', 'Отчёты', 'Ещё'])
  })
})

describe('App on the phone (outside Telegram)', () => {
  const code = { code: 'C'.repeat(32), poll_secret: 'S'.repeat(43), bot_link: `https://t.me/fayzi_bee_bot?start=login_${'C'.repeat(32)}`,
    bot_username: 'fayzi_bee_bot', expires_in: 300 }
  const session = { access_token: 'tok', token_type: 'bearer', expires_in: 60, user, start_param: null }
  afterEach(() => localStorage.clear())

  it('logs in through the bot and remembers this phone', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')
    let confirmed = false
    const fetchSpy = mockFetch((url, init) => {
      if (url.endsWith('/api/auth/login-codes')) return json(code, 201)
      if (url.endsWith('/api/auth/login-codes/poll')) {
        expect(JSON.parse(String(init?.body))).toEqual({ code: code.code, poll_secret: code.poll_secret })
        return json(confirmed ? { status: 'ok', access_token: 'tok', device_token: 'device-1', expires_in: 60, user }
          : { status: 'pending', access_token: null, device_token: null, expires_in: null, user: null })
      }
      if (url.includes('/api/dashboard')) return json(dashboard)
      return json({}, 404)
    })
    renderApp()
    const link = await screen.findByRole('link', { name: 'Войти через Telegram' })
    expect(link).toHaveAttribute('href', `tg://resolve?domain=fayzi_bee_bot&start=login_${code.code}`)
    await userEvent.click(link)
    expect(await screen.findByText('Подтвердите вход в Telegram')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Открыть Telegram ещё раз' })).toHaveAttribute('href', code.bot_link)

    confirmed = true
    window.dispatchEvent(new Event('focus'))  // back from Telegram: checks at once
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    expect(localStorage.getItem('fayzi-umar.device')).toBe('device-1')
    const dashCall = fetchSpy.mock.calls.find(([u]) => String(u).includes('/api/dashboard'))!
    expect(new Headers(dashCall[1]?.headers).get('Authorization')).toBe('Bearer tok')
  })

  it('opens straight away on a logged-in phone', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')
    localStorage.setItem('fayzi-umar.device', 'device-1')
    const fetchSpy = mockFetch((url) => {
      if (url.endsWith('/api/auth/device')) return json(session)
      if (url.includes('/api/dashboard')) return json(dashboard)
      return json({}, 404)
    })
    renderApp()
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    expect(JSON.parse(String(fetchSpy.mock.calls[0][1]?.body))).toEqual({ device_token: 'device-1' })
  })

  it('asks to log in again when the phone was logged out or the user blocked', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')
    localStorage.setItem('fayzi-umar.device', 'old')
    mockFetch((url) => {
      if (url.endsWith('/api/auth/device')) return json({ detail: 'Вход на этом устройстве больше не действует. Войдите снова.' }, 401)
      if (url.endsWith('/api/auth/login-codes')) return json(code, 201)
      return json({}, 404)
    })
    renderApp()
    expect(await screen.findByText(/Войдите снова/)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Войти через Telegram' })).toBeInTheDocument()
    expect(localStorage.getItem('fayzi-umar.device')).toBeNull()
  })

  it('offers only the password when the server has no bot', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')
    mockFetch(() => json({ detail: 'Вход вне Telegram не настроен: на сервере не указан TELEGRAM_BOT_USERNAME' }, 503))
    renderApp()
    expect(await screen.findByLabelText('Логин')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText('или')).not.toBeInTheDocument())
    expect(screen.queryByText(/TELEGRAM_BOT_USERNAME/)).not.toBeInTheDocument()
  })

  it('logs in with a login and password, then asks to replace the temporary password', async () => {
    vi.stubEnv('VITE_DEV_INIT_DATA', '')
    const temp = { ...user, telegram_id: null, login: 'karim', has_password: true, must_change_password: true }
    let changed: unknown = null
    mockFetch((url, init) => {
      if (url.endsWith('/api/auth/login-codes')) return json(code, 201)
      if (url.endsWith('/api/auth/password')) {
        const body = JSON.parse(String(init?.body))
        if (body.password !== 'k7mq-3vxe-p9ta') return json({ detail: 'Неверный логин или пароль' }, 401)
        return json({ status: 'ok', access_token: 'tok', device_token: 'device-2', expires_in: 60, user: temp })
      }
      if (url.endsWith('/api/auth/me/password')) {
        changed = JSON.parse(String(init?.body))
        return json({ ...temp, must_change_password: false })
      }
      if (url.includes('/api/dashboard')) return json(dashboard)
      return json({}, 404)
    })
    renderApp()
    await userEvent.type(await screen.findByLabelText('Логин'), 'karim')
    await userEvent.type(screen.getByLabelText('Пароль'), 'wrong')
    const loginForm = () => within(screen.getByLabelText('Логин').closest('form')!)
    await userEvent.click(loginForm().getByRole('button', { name: 'Войти' }))
    expect(await screen.findByText('Неверный логин или пароль')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Пароль'))
    await userEvent.type(screen.getByLabelText('Пароль'), 'k7mq-3vxe-p9ta')
    await userEvent.click(loginForm().getByRole('button', { name: 'Войти' }))

    expect(await screen.findByText('Придумайте свой пароль')).toBeInTheDocument()
    expect(localStorage.getItem('fayzi-umar.device')).toBe('device-2')
    await userEvent.type(screen.getByLabelText('Временный пароль'), 'k7mq-3vxe-p9ta')
    await userEvent.type(screen.getByLabelText(/^Новый пароль/), 'pchela-2026')
    await userEvent.type(screen.getByLabelText('Повторите новый пароль'), 'pchela-2025')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить пароль' }))
    expect(await screen.findByText('Пароли не совпадают')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Повторите новый пароль'))
    await userEvent.type(screen.getByLabelText('Повторите новый пароль'), 'pchela-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить пароль' }))
    expect(await screen.findByText(/Иван/)).toBeInTheDocument()
    expect(changed).toEqual({ current_password: 'k7mq-3vxe-p9ta', new_password: 'pchela-2026' })
  })
})
