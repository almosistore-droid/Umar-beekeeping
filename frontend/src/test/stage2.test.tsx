import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthGate } from '../App'
import { AuthProvider } from '../hooks/useAuth'
import { HivesPage } from '../pages/HivesPage'
import { HiveDetailsPage } from '../pages/HiveDetailsPage'
import { QueenFormPage } from '../pages/QueenFormPage'
import type { TelegramWebApp } from '../types/telegram'
import type { UserRole } from '../types/api'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const apiary = { id: 'a1', name: 'Пасека №1' }
const hiveListItem = {
  id: 'h1', apiary, hive_number: '27', hive_type: 'DADANT', status: 'STRONG', is_archived: false,
  strength: 'STRONG', queen_code: 'M-105', queen_age_label: '2 года 3 месяца', last_inspection_at: null, next_inspection_at: null,
}
const hive = {
  id: 'h1', apiary, hive_number: '27', hive_type: 'DADANT', status: 'STRONG', is_archived: false,
  installation_date: '2024-04-01', colonization_date: '2024-05-01', last_inspection_at: null, next_inspection_at: null,
  notes: null, version: 3, created_at: '', updated_at: '',
  current_family: { id: 'f1', hive_id: 'h1', strength: 'STRONG', status: 'ACTIVE', origin: 'PURCHASED', start_date: '2024-05-01', end_date: null, end_reason: null, notes: null },
  current_queen: { id: 'q1', queen_code: 'M-105', status: 'ACTIVE', birth_date: '2024-06-15', birth_year: 2024, age_months: 27, age_label: '2 года 3 месяца', breed: 'Карника', marking_color: 'GREEN', installed_at: '2026-04-10' },
}

type Handler = (url: string, init?: RequestInit) => Response | undefined

function setup(role: UserRole, handler: Handler, path: string, element: React.ReactNode, routePath: string) {
  window.Telegram = { WebApp: { initData: 'x', initDataUnsafe: {}, BackButton: { show() {}, hide() {}, onClick() {}, offClick() {} } } as unknown as TelegramWebApp }
  const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
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
            <Route path={routePath} element={element} />
            <Route path="/hives/:id" element={<div>hive page</div>} />
          </Routes>
        </MemoryRouter>
      </AuthGate></AuthProvider>
    </QueryClientProvider>,
  )
  return fetchSpy
}

describe('Hives list', () => {
  it('shows hive cards with status, strength and queen age', async () => {
    setup('BEEKEEPER', (url) => {
      if (url.includes('/api/apiaries')) return json([{ ...apiary, hive_count: 1 }])
      if (url.includes('/api/hives')) return json({ items: [hiveListItem], total: 1 })
    }, '/hives', <HivesPage />, '/hives')
    expect(await screen.findByLabelText('Улей №27')).toBeInTheDocument()
    expect(screen.getByText(/Сильный/)).toBeInTheDocument()
    expect(screen.getByText(/M-105, 2 года 3 месяца/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Улей' })).toHaveAttribute('href', '/hives/new')
  })

  it('hides the add button from viewers', async () => {
    setup('VIEWER', (url) => {
      if (url.includes('/api/apiaries')) return json([{ ...apiary, hive_count: 1 }])
      if (url.includes('/api/hives')) return json({ items: [hiveListItem], total: 1 })
    }, '/hives', <HivesPage />, '/hives')
    await screen.findByLabelText('Улей №27')
    expect(screen.queryByRole('link', { name: 'Улей' })).not.toBeInTheDocument()
  })

  it('sends the strength filter to the API', async () => {
    const spy = setup('BEEKEEPER', (url) => {
      if (url.includes('/api/apiaries')) return json([{ ...apiary, hive_count: 1 }])
      if (url.includes('/api/hives')) return json({ items: [], total: 0 })
    }, '/hives', <HivesPage />, '/hives')
    await userEvent.click(await screen.findByRole('tab', { name: 'Слабые' }))
    await waitFor(() => expect(spy.mock.calls.some(([u]) => String(u).includes('strength=WEAK&strength=VERY_WEAK'))).toBe(true))
  })
})

describe('Hive details', () => {
  it('shows the hive passport with queen age and history', async () => {
    setup('BEEKEEPER', (url) => {
      if (url.endsWith('/api/hives/h1')) return json(hive)
      if (url.endsWith('/api/hives/h1/history'))
        return json([{ id: 'e1', created_at: '2026-10-06T10:00:00Z', user_name: 'Иван', entity_type: 'hive', entity_id: 'h1', action: 'queen_replaced', old_value: { queen_code: 'M-105' }, new_value: { queen_code: 'M-205' }, comment: null }])
    }, '/hives/h1', <HiveDetailsPage />, '/hives/:id')
    expect(await screen.findByText('Улей №27')).toBeInTheDocument()
    expect(screen.getByText('2 года 3 месяца')).toBeInTheDocument()
    expect(screen.getByText('Карника')).toBeInTheDocument()
    expect(await screen.findByText('M-105 → M-205')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Заменить матку/ })).toBeInTheDocument()
  })

  it('shows a friendly message for an unknown hive', async () => {
    setup('VIEWER', (url) => {
      if (url.endsWith('/api/hives/zzz')) return json({ detail: 'Улей не найден' }, 404)
    }, '/hives/zzz', <HiveDetailsPage />, '/hives/:id')
    expect(await screen.findByText('Улей не найден')).toBeInTheDocument()
  })

  it('viewers see no management buttons', async () => {
    setup('VIEWER', (url) => {
      if (url.endsWith('/api/hives/h1')) return json(hive)
      if (url.endsWith('/history')) return json([])
    }, '/hives/h1', <HiveDetailsPage />, '/hives/:id')
    await screen.findByText('Улей №27')
    expect(screen.queryByRole('button', { name: /Заменить матку/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Изменить улей')).not.toBeInTheDocument()
  })
})

describe('Queen form', () => {
  it('creates a queen straight into a hive and shows API validation errors', async () => {
    const spy = setup('BEEKEEPER', (url, init) => {
      if (url.endsWith('/api/hives/h1')) return json(hive)
      if (url.endsWith('/api/queens') && init?.method === 'POST')
        return json({ detail: 'Проверьте введённые данные: Дата рождения матки не может быть в будущем',
          errors: [{ field: 'birth_date', message: 'Дата рождения матки не может быть в будущем' }] }, 422)
    }, '/queens/new?hive=h1', <QueenFormPage />, '/queens/new')
    expect(await screen.findByText('Будет подсажена в улей №27')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Код матки/), 'm-300')
    await userEvent.click(screen.getByRole('button', { name: 'Добавить матку' }))
    expect(await screen.findAllByText(/не может быть в будущем/)).not.toHaveLength(0)
    const post = spy.mock.calls.find(([u, i]) => String(u).endsWith('/api/queens') && i?.method === 'POST')!
    const body = JSON.parse(String(post[1]!.body))
    expect(body).toMatchObject({ queen_code: 'm-300', hive_id: 'h1' })
  })
})
