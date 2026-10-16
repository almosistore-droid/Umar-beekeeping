import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AdminPage } from '../pages/admin/AdminPage'
import { AuditLogPage } from '../pages/admin/AuditLogPage'
import { UsersPage } from '../pages/UsersPage'
import type { TelegramWebApp } from '../types/telegram'

let role = 'ADMIN'
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'me', first_name: 'Умар', display_name: 'Умар', role } }),
}))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

const users = [
  { id: 'me', telegram_id: 1000, username: 'umar', first_name: 'Умар', last_name: null, display_name: 'Умар', role: 'ADMIN', is_active: true, last_seen_at: new Date().toISOString(), created_at: '' },
  { id: 'u2', telegram_id: 2000, username: 'karim', first_name: 'Карим', last_name: null, display_name: 'Карим', role: 'ASSISTANT', is_active: false, last_seen_at: null, created_at: '' },
]
const invite = { id: 'i1', telegram_id: null, username: 'new_guy', role: 'BEEKEEPER', note: 'Сосед', status: 'PENDING', expired: false,
  expires_at: '2026-11-13T00:00:00Z', created_at: '', created_by_name: 'Умар', used_by_name: null, used_at: null }

beforeEach(() => { role = 'ADMIN' })

describe('Users and access', () => {
  it('lists users with last visit and blocked state, and pending invitations with revoke', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u, init) => {
      const url = String(u)
      if (url.endsWith('/api/users')) return json(users)
      if (url.endsWith('/revoke')) return json({ ...invite, status: 'REVOKED' })
      if (url.endsWith('/api/admin/invites') && !init?.method) return json([invite])
      return json({})
    })
    wrap(<UsersPage />)
    expect(await screen.findByText('Карим')).toBeInTheDocument()
    expect(screen.getByText('был(а): только что')).toBeInTheDocument()
    expect(screen.getByText('был(а): ещё не входил(а)')).toBeInTheDocument()
    expect(screen.getByText('заблокирован')).toBeInTheDocument()
    expect(await screen.findByText('Сосед')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Отозвать' }))
    await waitFor(() => expect(spy.mock.calls.some(([u, i]) => String(u).endsWith('/api/admin/invites/i1/revoke') && i?.method === 'POST')).toBe(true))
  })

  it('adds a person by @username and shares the invitation through Telegram', async () => {
    const openTelegramLink = vi.fn()
    window.Telegram = { WebApp: { initData: 'x', initDataUnsafe: {}, openTelegramLink, HapticFeedback: { impactOccurred() {}, notificationOccurred() {} } } as unknown as TelegramWebApp }
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u, init) => {
      const url = String(u)
      if (url.endsWith('/api/admin/invites') && init?.method === 'POST')
        return json({ kind: 'invited', invite, user: null, share_text: 'Вас добавили в учёт пасеки Fayzi Umar (пчеловод). Откройте бота: https://t.me/umar_bot' }, 201)
      if (url.endsWith('/api/users')) return json(users)
      return json([])
    })
    wrap(<UsersPage />)
    await userEvent.click(await screen.findByRole('button', { name: '＋ Добавить' }))
    await userEvent.type(screen.getByLabelText(/Имя пользователя в Telegram/), '@New_Guy')
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Роль' })).getByRole('radio', { name: 'Пчеловод' }))
    await userEvent.type(screen.getByLabelText(/Кто это/), 'Сосед')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить' }))
    expect(await screen.findByText('Приглашение создано')).toBeInTheDocument()
    const post = spy.mock.calls.find(([, i]) => i?.method === 'POST')!
    expect(JSON.parse(String(post[1]!.body))).toEqual({ username: '@New_Guy', role: 'BEEKEEPER', note: 'Сосед' })
    await userEvent.click(screen.getByRole('button', { name: /Отправить приглашение/ }))
    expect(openTelegramLink).toHaveBeenCalledWith(expect.stringContaining('https://t.me/share/url?url=%D0%92%D0%B0%D1%81'))
  })

  it('by Telegram ID keeps digits only; an existing user gets the role at once', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u, init) => {
      if (init?.method === 'POST') return json({ kind: 'updated', invite: null, user: { ...users[1], role: 'BEEKEEPER', is_active: true }, share_text: null }, 201)
      return json(String(u).endsWith('/api/users') ? users : [])
    })
    wrap(<UsersPage />)
    await userEvent.click(await screen.findByRole('button', { name: '＋ Добавить' }))
    await userEvent.click(screen.getByRole('radio', { name: 'По Telegram ID' }))
    await userEvent.type(screen.getByLabelText(/Telegram ID/), '20a00')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить' }))
    expect(await screen.findByText('Карим уже пользуется приложением')).toBeInTheDocument()
    const post = spy.mock.calls.find(([, i]) => i?.method === 'POST')!
    expect(JSON.parse(String(post[1]!.body))).toMatchObject({ telegram_id: 2000, role: 'ASSISTANT' })
  })

  it('creates a login and password for someone without Telegram and resets a password', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      const url = String(u)
      if (url.endsWith('/api/admin/accounts'))
        return json({ user: { ...users[1], id: 'u3', telegram_id: null, login: 'aziz', display_name: 'Азиз' }, login: 'aziz', temporary_password: 'k7mq-3vxe-p9ta' }, 201)
      if (url.endsWith('/api/admin/users/u2/password'))
        return json({ user: { ...users[1], login: 'karim' }, login: 'karim', temporary_password: 'abcd-efgh-jkmn' })
      if (url.endsWith('/api/users')) return json(users)
      return json([])
    })
    wrap(<UsersPage />)
    await userEvent.click(await screen.findByRole('button', { name: '＋ Добавить' }))
    await userEvent.click(screen.getByRole('radio', { name: 'Логин и пароль' }))
    await userEvent.type(screen.getByLabelText('Имя'), 'Азиз')
    await userEvent.type(screen.getByLabelText(/^Логин/), 'Aziz')
    await userEvent.click(screen.getByRole('button', { name: 'Создать вход' }))
    expect(await screen.findByText('k7mq-3vxe-p9ta')).toBeInTheDocument()
    const [, init] = spy.mock.calls.find(([u]) => String(u).endsWith('/api/admin/accounts'))!
    expect(JSON.parse(String(init?.body))).toEqual({ first_name: 'Азиз', last_name: null, login: 'aziz', role: 'ASSISTANT' })
    await userEvent.click(screen.getByRole('button', { name: 'Готово' }))

    // a Telegram user without a login gets one together with a temporary password
    await userEvent.click(screen.getByRole('button', { name: 'Вход по паролю' }))
    await userEvent.type(screen.getByLabelText(/^Логин/), 'karim')
    await userEvent.click(screen.getByRole('button', { name: 'Создать временный пароль' }))
    expect(await screen.findByText('abcd-efgh-jkmn')).toBeInTheDocument()
  })

  it('is closed to other roles', async () => {
    role = 'BEEKEEPER'
    wrap(<UsersPage />)
    expect(screen.getByText('Только для администратора')).toBeInTheDocument()
  })
})

describe('Admin overview', () => {
  it('shows users by role, every count and the system state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json({
      system: { environment: 'development', timezone: 'Asia/Dushanbe', currency: 'смн', server_time: '2026-10-14T00:30:00Z', bot_configured: true,
        bot_username: 'umar_bot', deep_links_ready: false, database_ok: true, database_size_mb: 12.4, migration: '0007' },
      users: { ADMIN: 1, BEEKEEPER: 2, ASSISTANT: 1, VIEWER: 3, blocked: 1, pending_invites: 2, seen_7_days: 5 },
      counts: [{ section: 'Пасека', label: 'Ульи (на пасеках / в архиве)', value: '11 / 2' }, { section: 'CRM', label: 'Клиенты', value: '4' }],
    }))
    wrap(<AdminPage />)
    expect(await screen.findByText('11 / 2')).toBeInTheDocument()
    expect(screen.getByText('ждут входа: 2')).toBeInTheDocument()
    expect(screen.getByText('@umar_bot')).toBeInTheDocument()
    expect(screen.getByText('нет TELEGRAM_BOT_USERNAME')).toBeInTheDocument()
    expect(screen.getByText('12.4 МБ')).toBeInTheDocument()
    expect(screen.getByText('проверка на ноутбуке')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Журнал действий/ })).toHaveAttribute('href', '/admin/log')
  })
})

describe('Activity log', () => {
  const entry = (id: string, extra = {}) => ({ id, created_at: '2026-10-14T00:10:00Z', user_id: 'u2', user_name: 'Карим', entity_type: 'hive', entity_id: 'h1',
    hive_id: 'h1', hive_number: '27', action: 'created', old_value: null, new_value: null, comment: null, ...extra })

  it('describes entries, filters by person and loads more', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      const url = String(u)
      if (url.endsWith('/api/users')) return json(users)
      if (url.includes('offset=50')) return json({ items: [entry('e3', { hive_id: null, hive_number: null, entity_type: 'user', action: 'updated', new_value: { is_active: false } })], next_offset: null, entity_types: ['hive', 'user'] })
      return json({ items: [entry('e1'), entry('e2', { entity_type: 'sale', hive_id: null, hive_number: null, action: 'payment', new_value: { amount: '600', debt_left: '450.00' } })], next_offset: 50, entity_types: ['hive', 'sale', 'user'] })
    })
    wrap(<AuditLogPage />)
    expect(await screen.findByRole('link', { name: 'улей №27' })).toHaveAttribute('href', '/hives/h1')
    expect(screen.getByText('Улей создан')).toBeInTheDocument()
    expect(screen.getByText('Продажа — принята оплата')).toBeInTheDocument()
    expect(screen.getByText('600 · осталось 450')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Показать ещё' }))
    expect(await screen.findByText('Пользователь: доступ закрыт')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getAllByRole('combobox')[0], 'u2')
    await waitFor(() => expect(spy.mock.calls.some(([u]) => String(u).includes('user_id=u2'))).toBe(true))
  })
})
