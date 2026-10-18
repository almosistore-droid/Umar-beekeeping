import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { StockPage } from '../pages/stock/StockPage'
import { FeedingForm } from '../components/health/RecordForms'
import { feedingNeed, frameNeed } from '../utils/stock'
import type { Hive, StockItem, StockOverview } from '../types/api'

let role = 'BEEKEEPER'
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'me', telegram_id: 3000, display_name: 'Умар', role } }),
}))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

const norms = { wire_m_per_frame: '3', foundation_g_per_frame: '110', sugar_kg_per_l_syrup: '0.63', sugar_kg_per_kg_syrup: '0.5' }
const item = (code: string | null, name: string, category: StockItem['category'], unit: StockItem['unit'], quantity: string,
  extra: Partial<StockItem> = {}): StockItem =>
  ({ id: code ?? name, code, name, category, unit, quantity, min_quantity: null, notes: null, is_archived: false, low: false, ...extra })
const overview: StockOverview = {
  honey_kg: '120.5', norms,
  items: [
    item('frames_empty', 'Рамки пустые', 'FRAMES', 'PCS', '40'),
    item('frames_ready', 'Рамки с вощиной', 'FRAMES', 'PCS', '20'),
    item('foundation', 'Вощина', 'FRAMES', 'KG', '1.5'),
    item('wire', 'Проволока', 'FRAMES', 'M', '150'),
    item('sugar', 'Сахар', 'FEED', 'KG', '8', { min_quantity: '25', low: true }),
    item(null, 'Бипин', 'MEDICINE', 'ML', '20'),
  ],
}

describe('consumption rules (same as the server)', () => {
  it('syrup, candy, protein, honey', () => {
    expect(feedingNeed(norms, 'SUGAR_SYRUP', 2, 'L')).toEqual({ code: 'sugar', quantity: 1.26, unit: 'KG' })
    expect(feedingNeed(norms, 'SUGAR_SYRUP', 3000, 'ML')?.quantity).toBe(1.89)
    expect(feedingNeed(norms, 'SUGAR_SYRUP', 4, 'KG')?.quantity).toBe(2)
    expect(feedingNeed(norms, 'CANDY', 500, 'G')).toEqual({ code: 'candy', quantity: 0.5, unit: 'KG' })
    expect(feedingNeed(norms, 'POLLEN_SUBSTITUTE', 1, 'KG')?.code).toBe('protein')
    expect(feedingNeed(norms, 'HONEY', 1, 'KG')).toBeNull()
    expect(feedingNeed(norms, 'MEDICATED', 1, 'L')).toBeNull()
    expect(feedingNeed(norms, 'CANDY', 2, 'PCS')).toBeNull()
  })

  it('frames: wire and foundation per frame', () => {
    expect(frameNeed(norms, 20)).toEqual([
      { code: 'wire', quantity: 60, unit: 'M' },
      { code: 'foundation', quantity: 2.2, unit: 'KG' },
      { code: 'frames_empty', quantity: 20, unit: 'PCS' },
    ])
    expect(frameNeed(norms, 0)).toEqual([])
  })
})

describe('Warehouse screen', () => {
  beforeEach(() => { role = 'BEEKEEPER' })

  it('shows sections, honey, the low item and prepares frames with the calculation', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u, init) => {
      const url = String(u)
      if (url.endsWith('/api/stock/frame-preps') && init?.method === 'POST') {
        return json({ prep: { id: 'p1', prepared_at: '2026-10-17', frames: 20, wire_m_per_frame: '3', foundation_g_per_frame: '110', notes: null, cancelled_at: null, created_at: '' },
          lines: [{ item_id: 'wire', name: 'Проволока', unit: 'M', quantity: '-60', balance_after: '90' }] }, 201)
      }
      return json(overview)
    })
    wrap(<StockPage />)
    expect(await screen.findByText('Рамки и вощина')).toBeInTheDocument()
    expect(screen.getByText('Лекарства')).toBeInTheDocument()
    expect(screen.getByText('120,5 кг')).toBeInTheDocument()
    expect(screen.getByText('Заканчивается: Сахар')).toBeInTheDocument()
    expect(screen.getByText('Меньше минимума (25 кг)')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Подготовить рамки/ }))
    const field = await screen.findByLabelText('Сколько рамок подготовлено')
    await userEvent.clear(field)
    await userEvent.type(field, '20')
    const calc = screen.getByLabelText('Расчёт')
    expect(within(calc).getByText('−60 м (есть 150 м)')).toBeInTheDocument()
    expect(within(calc).getByText('−2,2 кг (есть 1,5 кг)')).toBeInTheDocument()
    expect(within(calc).getByText('+20 шт')).toBeInTheDocument()
    expect(screen.getByText(/остаток станет отрицательным/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Списать на рамки' }))
    expect(await screen.findByText('Подготовлено рамок: 20')).toBeInTheDocument()
    const post = spy.mock.calls.find(([u, i]) => String(u).endsWith('/frame-preps') && i?.method === 'POST')!
    expect(JSON.parse(String(post[1]?.body))).toMatchObject({ frames: 20 })
  })

  it('a viewer sees the stock but cannot add or prepare', async () => {
    role = 'VIEWER'
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json(overview))
    wrap(<StockPage />)
    expect(await screen.findByText('Рамки и вощина')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Подготовить рамки/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Позиция/ })).not.toBeInTheDocument()
  })
})

describe('Feeding form', () => {
  it('shows how much sugar will be written off', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json(overview))
    wrap(<FeedingForm hive={{ id: 'h1' } as Hive} onDone={() => undefined} />)
    expect(await screen.findByText(/Со склада спишется: Сахар 1,26 кг/)).toBeInTheDocument()
    expect(screen.getByText(/останется 6,74 кг/)).toBeInTheDocument()
    const amount = screen.getByLabelText('Количество')
    await userEvent.clear(amount)
    await userEvent.type(amount, '20')
    await waitFor(() => expect(screen.getByText(/на складе только 8 кг/)).toBeInTheDocument())
  })
})

describe('Receipt with a price', () => {
  it('sends the sum and shows the price per unit', async () => {
    role = 'BEEKEEPER'
    const { MovementForm } = await import('../components/stock/forms')
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => {
      const url = String(u)
      if (url.endsWith('/api/crm/settings')) return json({ currency: 'смн' })
      return json(overview.items[4], 201)
    })
    const done = vi.fn()
    wrap(<MovementForm item={overview.items[4]} kind="RECEIPT" onDone={done} />)
    await userEvent.type(screen.getByLabelText('Сколько пришло, кг'), '50')
    await userEvent.type(await screen.findByLabelText(/Сколько заплатили, смн/), '650')
    expect(screen.getByText('13 смн за 1 кг · сумма попадёт в расходы CRM')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Записать приход' }))
    await waitFor(() => expect(done).toHaveBeenCalled())
    const post = spy.mock.calls.find(([u, i]) => String(u).includes('/movements') && i?.method === 'POST')!
    expect(JSON.parse(String(post[1]?.body))).toMatchObject({ kind: 'RECEIPT', quantity: 50, amount: 650 })
  })

  it('an assistant records the receipt without a price', async () => {
    role = 'ASSISTANT'
    const { MovementForm } = await import('../components/stock/forms')
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json({}))
    wrap(<MovementForm item={overview.items[4]} kind="RECEIPT" onDone={() => undefined} />)
    expect(screen.queryByLabelText(/Сколько заплатили/)).not.toBeInTheDocument()
  })
})
