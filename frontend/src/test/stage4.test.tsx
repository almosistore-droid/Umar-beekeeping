import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { HoneyForm, WinteringForm } from '../components/operations/OperationForms'
import { HoneyPage } from '../pages/HoneyPage'
import type { Hive } from '../types/api'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

const hive = {
  id: 'h1', apiary: { id: 'a1', name: 'Пасека' }, hive_number: '27', hive_type: 'DADANT', status: 'ACTIVE',
  is_archived: false, version: 1,
  current_family: { id: 'f1', hive_id: 'h1', strength: 'STRONG', status: 'ACTIVE', origin: 'OWN', start_date: '2026-05-01', end_date: null, end_reason: null, notes: null },
  current_queen: null,
} as unknown as Hive

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

describe('Honey form', () => {
  it('shows the computed sum and sends weight, frames and price', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json({ id: 'x' }, 201))
    const done = vi.fn()
    wrap(<HoneyForm hive={hive} onDone={done} />)
    await userEvent.type(screen.getByLabelText(/Вес, кг/), '12,5')
    await userEvent.type(screen.getByLabelText(/Цена за кг/), '80')
    expect(screen.getByText('Сумма: 1 000')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: 'Акация' }))
    await userEvent.click(screen.getByRole('button', { name: 'Записать мёд' }))
    await waitFor(() => expect(done).toHaveBeenCalled())
    const body = JSON.parse(String(spy.mock.calls[0][1]!.body))
    expect(body).toMatchObject({ weight_kg: 12.5, price_per_kg: 80, frames_count: 4, honey_type: 'Акация' })
  })
})

describe('Honey page', () => {
  it('shows year totals, the best hives and a table view of months', async () => {
    const byMonth = Array(12).fill('0'); byMonth[5] = '20'; byMonth[7] = '25'
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json({
      year: 2026, month_kg: '0', year_kg: '45', season_kg: '45', all_time_kg: '52', year_value: '1600',
      producing_hives: 2, avg_per_hive_kg: '22.5', best_hive: null, by_month: byMonth,
      by_hive: [
        { hive_id: 'h1', hive_number: '1', apiary_name: 'Пасека', kg: '35', harvests: 2 },
        { hive_id: 'h2', hive_number: '2', apiary_name: 'Горная', kg: '10', harvests: 1 },
      ],
    }))
    wrap(<HoneyPage />)
    expect(await screen.findByText('45')).toBeInTheDocument()
    expect(screen.getByText('22,5 кг')).toBeInTheDocument()
    expect(screen.getByText('35 кг')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /июн 20 кг, авг 25 кг/ })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Таблица' }))
    expect(screen.getByRole('table')).toHaveTextContent('авг25')
  })
})

describe('Wintering form', () => {
  it('offers to finish an open wintering and warns when the colony died', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json([
      { id: 'w1', hive_id: 'h1', season: '2025/2026', start_date: '2025-10-25', end_date: null, result: null },
    ]))
    wrap(<WinteringForm hive={hive} onDone={vi.fn()} />)
    expect(await screen.findByText(/сезон 2025\/2026/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('radio', { name: 'Погибла' }))
    expect(screen.getByText(/Семья будет отмечена погибшей/)).toBeInTheDocument()
  })
})
