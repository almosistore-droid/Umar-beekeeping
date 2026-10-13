import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'
import { InspectionForm } from '../components/health/InspectionForm'
import { Timeline } from '../components/health/HealthCards'
import type { Hive } from '../types/api'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const hive = {
  id: 'h1', apiary: { id: 'a1', name: 'Пасека' }, hive_number: '27', hive_type: 'DADANT', status: 'ACTIVE',
  is_archived: false, installation_date: null, colonization_date: null, last_inspection_at: null,
  next_inspection_at: null, notes: null, version: 1, created_at: '', updated_at: '',
  current_family: { id: 'f1', hive_id: 'h1', strength: 'MEDIUM', status: 'ACTIVE', origin: 'OWN', start_date: '2026-05-01', end_date: null, end_reason: null, notes: null },
  current_queen: null,
} as unknown as Hive

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('Inspection form', () => {
  it('prefills frames from the previous inspection and sends the observations', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.endsWith('/inspections') && (!init?.method || init.method === 'GET'))
        return json([{ frames_total: 12, brood_frames: 5, honey_frames: 4, pollen_frames: 1 }])
      if (url.endsWith('/inspections') && init?.method === 'POST')
        return json({ inspection: {}, hive, warnings: [] }, 201)
      return json({}, 404)
    })
    const done = vi.fn()
    wrap(<InspectionForm hive={hive} onDone={done} />)
    await waitFor(() => expect(screen.getByLabelText('Всего')).toHaveTextContent('12'))
    await userEvent.click(screen.getByRole('radio', { name: 'Сильная' }))
    await userEvent.click(screen.getByLabelText('Расплод: больше'))
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Матка' })).getByRole('radio', { name: 'Видна' }))
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить осмотр' }))
    await waitFor(() => expect(done).toHaveBeenCalled())
    const post = spy.mock.calls.find(([, i]) => i?.method === 'POST')!
    expect(JSON.parse(String(post[1]!.body))).toMatchObject({
      strength: 'STRONG', frames_total: 12, brood_frames: 6, honey_frames: 4, pollen_frames: 1, queen_present: true,
    })
  })

  it('blocks saving when occupied frames exceed the total', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json([]))
    wrap(<InspectionForm hive={hive} onDone={vi.fn()} />)
    for (let i = 0; i < 11; i++) await userEvent.click(screen.getByLabelText('Мёд: больше'))
    expect(screen.getByRole('alert')).toHaveTextContent('больше, чем всего рамок')
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить осмотр' }))
    expect(spy.mock.calls.some(([, i]) => i?.method === 'POST')).toBe(false)
  })

  it('shows warnings after saving and offers to mark the hive queenless', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (_input, init) =>
      init?.method === 'POST'
        ? json({ inspection: {}, hive, warnings: [{ code: 'possible_queenless', message: 'Матка не найдена и яиц нет' }] }, 201)
        : json([]))
    wrap(<InspectionForm hive={hive} onDone={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: 'Сохранить осмотр' }))
    expect(await screen.findByText('Осмотр сохранён')).toBeInTheDocument()
    expect(screen.getByText('Матка не найдена и яиц нет')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Отметить «Без матки»' })).toBeInTheDocument()
  })
})

describe('Timeline', () => {
  it('renders records and history events with readable summaries', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json([
      { kind: 'inspection', at: '2026-10-05T09:30:00Z', title: 'Осмотр', details: ['Сила: сильная', 'Рамки: 10 (расплод 6, мёд 3, перга 1)'], author: 'Умар', ref_id: 'i1' },
      { kind: 'treatment', at: '2026-09-20T12:00:00Z', title: 'Обработка: Варроатоз', details: ['Бипин 1 мл'], author: 'Умар', ref_id: 't1' },
      { kind: 'event', at: '2026-04-10T08:00:00Z', title: 'queen_replaced', details: [], author: 'Умар', ref_id: 'h1',
        action: 'queen_replaced', old_value: { queen_code: 'M-105' }, new_value: { queen_code: 'M-205' } },
    ]))
    wrap(<Timeline hiveId="h1" />)
    expect(await screen.findByText('Осмотр')).toBeInTheDocument()
    expect(screen.getByText('Рамки: 10 (расплод 6, мёд 3, перга 1)')).toBeInTheDocument()
    expect(screen.getByText('Обработка: Варроатоз')).toBeInTheDocument()
    expect(screen.getByText('Замена матки')).toBeInTheDocument()
    expect(screen.getByText('M-105 → M-205')).toBeInTheDocument()
  })
})
