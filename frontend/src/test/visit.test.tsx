import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthGate } from '../App'
import { AuthProvider } from '../hooks/useAuth'
import { HiveCheckPage } from '../pages/HiveCheckPage'
import { HiveInspectPage } from '../pages/HiveInspectPage'
import { HiveVisitPage } from '../pages/HiveVisitPage'
import { InspectionList } from '../components/health/HealthCards'
import type { TelegramWebApp } from '../types/telegram'
import type { UserRole } from '../types/api'
import { addDaysIso } from '../utils/labels'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const hive = {
  id: 'h1', apiary: { id: 'a1', name: 'Горная' }, hive_number: '27', hive_type: 'DADANT', status: 'ACTIVE', is_archived: false,
  installation_date: null, colonization_date: null, last_inspection_at: null, next_inspection_at: null, notes: null, version: 1,
  created_at: '', updated_at: '',
  current_family: { id: 'f1', hive_id: 'h1', strength: 'MEDIUM', status: 'ACTIVE', origin: 'OWN', start_date: '2026-05-01', end_date: null, end_reason: null, notes: null },
  current_queen: null,
}

type Handler = (url: string, init?: RequestInit) => Response | undefined

function Where() {
  const l = useLocation()
  return <div data-testid="where">{l.pathname}</div>
}

function setup(role: UserRole, handler: Handler, path: string, routes: React.ReactNode) {
  window.Telegram = { WebApp: { initData: 'x', initDataUnsafe: {}, isVersionAtLeast: () => true,
    BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} } } as unknown as TelegramWebApp }
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/api/auth/telegram')) {
      return json({ access_token: 't', token_type: 'bearer', expires_in: 60, start_param: null,
        user: { id: 'u1', telegram_id: 1, username: null, first_name: 'Умар', last_name: null, display_name: 'Умар', role, is_active: true, created_at: '' } })
    }
    return handler(url, init) ?? json({ detail: 'not mocked' }, 500)
  })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}><AuthProvider><AuthGate>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          {routes}
          <Route path="*" element={<Where />} />
        </Routes>
      </MemoryRouter>
    </AuthGate></AuthProvider></QueryClientProvider>,
  )
  return spy
}

const hiveApi: Handler = (url) => (url.endsWith('/api/hives/h1') ? json(hive) : undefined)

describe('After a scan: choice', () => {
  it('offers «Осмотр» and «Проверка» and opens each', async () => {
    setup('ASSISTANT', hiveApi, '/hives/h1/visit', <Route path="/hives/:id/visit" element={<HiveVisitPage />} />)
    expect(await screen.findByRole('heading', { name: 'Улей №27' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Осмотр/ }))
    expect(await screen.findByTestId('where')).toHaveTextContent('/hives/h1/inspect')
  })

  it('lets a viewer only check', async () => {
    setup('VIEWER', hiveApi, '/hives/h1/visit', <Route path="/hives/:id/visit" element={<HiveVisitPage />} />)
    expect(await screen.findByRole('button', { name: /Осмотр/ })).toBeDisabled()
    expect(screen.getByText('Только просмотр')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Проверка/ }))
    expect(await screen.findByTestId('where')).toHaveTextContent('/hives/h1/check')
  })
})

describe('Full inspection at the hive', () => {
  it('saves with one tap as a dated record and offers the next hive', async () => {
    const spy = setup('ASSISTANT', (url, init) => {
      if (url.endsWith('/api/hives/h1')) return json(hive)
      if (url.endsWith('/inspections') && init?.method === 'POST') return json({ inspection: { id: 'i1' }, hive, warnings: [] }, 201)
      if (url.endsWith('/inspections')) return json([])
      return undefined
    }, '/hives/h1/inspect', <Route path="/hives/:id/inspect" element={<HiveInspectPage />} />)
    await screen.findByRole('button', { name: 'Сохранить осмотр' })
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Дата осмотра' })).getByRole('radio', { name: 'Вчера' }))
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Матка' })).getByRole('radio', { name: 'Видна' }))
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Состояние матки' })).getByRole('radio', { name: 'Хорошее' }))
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Признаки роения' })).getByRole('radio', { name: 'Да' }))
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить осмотр' }))
    expect(await screen.findByText('Осмотр сохранён')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Следующий улей/ })).toHaveAttribute('href', '/scan')
    const post = spy.mock.calls.find(([u, i]) => String(u).endsWith('/inspections') && i?.method === 'POST')!
    expect(JSON.parse(String(post[1]!.body))).toMatchObject({
      inspected_at: `${addDaysIso(-1)}T12:00:00Z`, queen_present: true, queen_condition: 'GOOD', swarming_signs: true, strength: 'MEDIUM',
    })
  })

  it('today is sent with the current time (kept when the record waits offline)', async () => {
    const spy = setup('BEEKEEPER', (url, init) => {
      if (url.endsWith('/api/hives/h1')) return json(hive)
      if (url.endsWith('/inspections') && init?.method === 'POST') return json({ inspection: { id: 'i1' }, hive, warnings: [] }, 201)
      if (url.endsWith('/inspections')) return json([])
      return undefined
    }, '/hives/h1/inspect', <Route path="/hives/:id/inspect" element={<HiveInspectPage />} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Сохранить осмотр' }))
    await waitFor(() => expect(spy.mock.calls.some(([u, i]) => String(u).endsWith('/inspections') && i?.method === 'POST')).toBe(true))
    const post = spy.mock.calls.find(([u, i]) => String(u).endsWith('/inspections') && i?.method === 'POST')!
    const body = JSON.parse(String(post[1]!.body))
    expect(Math.abs(Date.parse(body.inspected_at) - Date.now())).toBeLessThan(60_000)
    expect(body.client_uid).toMatch(/^[0-9a-f-]{36}$/)
  })
})

const check = {
  hive_id: 'h1', hive_number: '27', apiary: { id: 'a1', name: 'Горная' }, status: 'ACTIVE', is_archived: false,
  verdict: 'attention', headline: 'Требует внимания',
  issues: [{ code: 'inspection_overdue', level: 'attention', message: 'Осмотр просрочен на 5 дней' }],
  strength: 'STRONG', queen: { id: 'q1', queen_code: 'M-105', age_label: '1 год', status: 'ACTIVE' },
  last_inspection: { id: 'i1', inspected_at: '2026-10-01T09:00:00Z', days_ago: 12, user_name: 'Умар', strength: 'STRONG',
    frames_total: 10, brood_frames: 6, honey_frames: 3, pollen_frames: 1, queen_present: true, egg_laying: true,
    queen_cells: 0, swarming_signs: false, food_level: 'NORMAL', health_status: 'HEALTHY' },
  next_inspection_at: '2026-10-08T12:00:00Z', open_cases: [], open_tasks: [], honey_year_kg: '30.9',
}

describe('Hive check', () => {
  it('shows the verdict, the issues and the last inspection', async () => {
    setup('BEEKEEPER', (url) => (url.endsWith('/api/hives/h1/check') ? json(check) : undefined), '/hives/h1/check',
      <Route path="/hives/:id/check" element={<HiveCheckPage />} />)
    expect(await screen.findByRole('heading', { name: 'Требует внимания' })).toBeInTheDocument()
    expect(screen.getByText('Осмотр просрочен на 5 дней')).toBeInTheDocument()
    expect(screen.getByText('M-105')).toBeInTheDocument()
    expect(screen.getByText(/01\.10\.2026, 12 дней назад/)).toBeInTheDocument()
    expect(screen.getByText('10 (расплод 6, мёд 3, перга 1)')).toBeInTheDocument()
    expect(screen.getByText('30,9 кг')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Провести осмотр/ })).toHaveAttribute('href', '/hives/h1/inspect')
  })

  it('says all is well and hides inspection from a viewer', async () => {
    setup('VIEWER', (url) => (url.endsWith('/check') ? json({ ...check, verdict: 'ok', headline: 'Всё в порядке', issues: [] }) : undefined),
      '/hives/h1/check', <Route path="/hives/:id/check" element={<HiveCheckPage />} />)
    expect(await screen.findByRole('heading', { name: 'Всё в порядке' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Провести осмотр/ })).not.toBeInTheDocument()
  })
})

describe('Inspections by date', () => {
  it('lists every inspection as its own dated record', async () => {
    window.Telegram = undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json([
      { ...check.last_inspection, hive_id: 'h1', inspected_at: '2026-10-12T09:00:00Z', queen_condition: null, aggressiveness: null, next_inspection_at: null, notes: 'Добавил рамку' },
      { ...check.last_inspection, hive_id: 'h1', id: 'i0', inspected_at: '2026-10-01T09:00:00Z', queen_condition: null, aggressiveness: null, next_inspection_at: null, notes: null, food_level: 'LOW' },
    ]))
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={qc}><InspectionList hiveId="h1" /></QueryClientProvider>)
    expect(await screen.findByText('Осмотр 12.10.2026')).toBeInTheDocument()
    expect(screen.getByText('Осмотр 01.10.2026')).toBeInTheDocument()
    expect(screen.getByText('Добавил рамку')).toBeInTheDocument()
    expect(screen.getByText('Корм: мало')).toBeInTheDocument()
  })
})
