import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { vi } from 'vitest'
import { MorePage } from '../pages/MorePage'
import { AppLayout, START_SCREENS } from '../layouts/AppLayout'
import type { TelegramWebApp } from '../types/telegram'

let role = 'BEEKEEPER'
let telegramId: number | null = 3000
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'me', telegram_id: telegramId, display_name: 'Умар', role }, onDevice: false, logout: vi.fn() }),
}))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function wrap(ui: React.ReactNode, path = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter></QueryClientProvider>)
}

describe('Reminders in «Ещё»', () => {
  beforeEach(() => { role = 'BEEKEEPER'; telegramId = 3000 })

  it('turns groups on and off and sends a test message', async () => {
    let state = { field: true, crm: true, crm_available: true, telegram: true, hours: '7:00–21:00' }
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u, init) => {
      const url = String(u)
      if (url.endsWith('/api/notifications/settings') && init?.method === 'PUT') {
        state = { ...state, ...JSON.parse(String(init.body)) }
        return json(state)
      }
      if (url.endsWith('/api/notifications/settings')) return json(state)
      if (url.endsWith('/api/notifications/test')) return json({ sent: true })
      return json({})
    })
    wrap(<MorePage />)
    expect(await screen.findByText('Напоминания в Telegram')).toBeInTheDocument()
    expect(screen.getByText(/в 7:00–21:00/)).toBeInTheDocument()
    const crm = screen.getByRole('checkbox', { name: /CRM: долги клиентов и заказы/ })
    await userEvent.click(crm)
    await waitFor(() => expect(crm).not.toBeChecked())
    const put = spy.mock.calls.find(([u, i]) => String(u).endsWith('/settings') && i?.method === 'PUT')!
    expect(JSON.parse(String(put[1]?.body))).toEqual({ crm: false })
    await userEvent.click(screen.getByRole('button', { name: /Прислать пробное сообщение/ }))
    expect(await screen.findByText('Отправлено — проверьте чат с ботом.')).toBeInTheDocument()
  })

  it('explains that people without Telegram see reminders in the app', async () => {
    telegramId = null
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      json({ field: true, crm: true, crm_available: false, telegram: false, hours: '7:00–21:00' }))
    wrap(<MorePage />)
    expect(await screen.findByText(/у вас вход без Telegram/)).toBeInTheDocument()
    expect(screen.queryByRole('checkbox', { name: /Работа на пасеке/ })).not.toBeInTheDocument()
  })
})

describe('Reminder buttons open their screen', () => {
  function Where() { return <p data-testid="where">{useLocation().pathname}</p> }

  it.each(Object.entries(START_SCREENS))('%s → %s', async (param, path) => {
    window.Telegram = { WebApp: { initData: 'x', initDataUnsafe: { start_param: param },
      BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} } } as unknown as TelegramWebApp }
    const { resetStartParamForTests } = await import('../services/telegram')
    resetStartParamForTests()
    wrap(<Routes><Route element={<AppLayout />}><Route path="*" element={<Where />} /></Route></Routes>)
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(path))
  })
})
