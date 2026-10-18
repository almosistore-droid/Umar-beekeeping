import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { RearingBatchPage, RearingListPage } from '../pages/rearing/RearingPages'
import type { RearingBatch } from '../types/api'

let role = 'BEEKEEPER'
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: { id: 'me', role } }) }))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const step = (key: string, day: number, title: string, state: string, count_field: string | null = null, count_label: string | null = null) =>
  ({ key, day, date: `2026-10-${String(12 + day).padStart(2, '0')}`, title, hint: `Подсказка ${key}`, count_field, count_label, state, task_id: null })
const batch: RearingBatch = {
  id: 'r1', label: 'Партия 1 · 12.10', grafted_at: '2026-10-12', day: 6, cells_grafted: 30, cells_accepted: 24, cells_sealed: null,
  queens_emerged: null, queens_mated: null, mother_queen_id: null, mother_queen_code: 'M-7', cell_builder_hive_id: 'h1',
  cell_builder_number: '3', status: 'ACTIVE', finished_at: null, cancel_reason: null, notes: null,
  next_step: null, steps: [
    step('graft', 0, 'Прививка личинок', 'done'),
    step('acceptance', 1, 'Проверить приём личинок', 'done', 'cells_accepted', 'Принято'),
    step('sealed', 5, 'Маточники запечатаны', 'overdue', 'cells_sealed', 'Запечатано'),
    step('move', 10, 'Разнести маточники по нуклеусам', 'upcoming'),
  ],
} as unknown as RearingBatch
batch.next_step = batch.steps[2]

function wrap(ui: React.ReactNode, path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}><Routes>{ui}</Routes></MemoryRouter></QueryClientProvider>)
}

describe('Queen rearing', () => {
  beforeEach(() => { role = 'BEEKEEPER' })

  it('list shows the day, the step due now and the counts', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json([batch]))
    wrap(<Route path="/rearing" element={<RearingListPage />} />, '/rearing')
    expect(await screen.findByText('Партия 1 · 12.10')).toBeInTheDocument()
    expect(screen.getByText('Сейчас: Маточники запечатаны')).toBeInTheDocument()
    expect(screen.getByText('24')).toBeInTheDocument()
  })

  it('records the count of a step', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      if (String(u).includes('/steps/sealed/done')) return json({ ...batch, cells_sealed: 22 })
      return json(batch)
    })
    wrap(<Route path="/rearing/:id" element={<RearingBatchPage />} />, '/rearing/r1')
    expect(await screen.findByText(/сегодня 6-й день/)).toBeInTheDocument()
    expect(screen.getByText('Подсказка sealed')).toBeInTheDocument() // overdue step shows what to do
    await userEvent.click(screen.getByRole('button', { name: 'Записать: запечатано' }))
    const input = await screen.findByLabelText(/Запечатано/)
    expect(input).toHaveValue('24') // starts from the previous step
    await userEvent.clear(input)
    await userEvent.type(input, '22')
    await userEvent.click(screen.getByRole('button', { name: 'Отметить сделанным' }))
    await waitFor(() => expect(spy.mock.calls.some(([u]) => String(u).includes('/steps/sealed/done'))).toBe(true))
    const call = spy.mock.calls.find(([u]) => String(u).includes('/steps/sealed/done'))!
    expect(JSON.parse(String(call[1]?.body))).toEqual({ count: 22 })
  })

  it('a viewer only looks', async () => {
    role = 'VIEWER'
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json(batch))
    wrap(<Route path="/rearing/:id" element={<RearingBatchPage />} />, '/rearing/r1')
    expect(await screen.findByText('Маточники запечатаны')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Записать/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Завершить партию' })).not.toBeInTheDocument()
  })
})
