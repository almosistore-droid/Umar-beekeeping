import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import { BottomNav } from '../components/BottomNav'
import { ExpenseForm, SaleForm } from '../components/crm/forms'
import { CrmHomePage } from '../pages/crm/CrmHomePage'
import { DebtsPage } from '../pages/crm/DebtsPage'
import { OrderDetailsPage } from '../pages/crm/OrdersPages'

const auth = vi.hoisted(() => ({ role: 'BEEKEEPER' }))
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'u1', first_name: 'Умар', display_name: 'Умар', role: auth.role } }),
}))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

type Handler = (url: string, init?: RequestInit) => unknown
function mockApi(handler: Handler) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input)
    if (url.endsWith('/api/crm/settings')) return json({ currency: 'смн' })
    const body = handler(url, init)
    return body instanceof Response ? body : json(body ?? { detail: 'not mocked' }, body ? 200 : 500)
  })
}
const posts = (spy: ReturnType<typeof mockApi>, end: string) =>
  spy.mock.calls.filter(([u, i]) => String(u).includes(end) && i?.method === 'POST').map(([, i]) => JSON.parse(String(i!.body)))

function wrap(ui: React.ReactNode, path = '/', route = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}>
    <Routes><Route path={route} element={ui} /><Route path="*" element={<div>other page</div>} /></Routes>
  </MemoryRouter></QueryClientProvider>)
}

const customers = [{ id: 'c1', name: 'Фарход', phone: '+992901112233', city: 'Душанбе', notes: null, is_archived: false, created_at: '',
  bought: '0', paid: '0', debt: '0', sales_count: 0, last_purchase: null }]
const summary = {
  year: 2026, month: 10, currency: 'смн', income: '12500', expenses: '9600', profit: '2900', received: '10800',
  debts_total: '1700', debtors: 2, open_orders: 2, honey_stock_kg: '120.5',
  income_by_month: Array(12).fill('0'), expenses_by_month: Array(12).fill('0'),
  income_by_category: [{ key: 'HONEY', label: 'Мёд', amount: '11000' }], expenses_by_category: [{ key: 'FEED', label: 'Корм', amount: '1900' }],
}
const sale = (over: object = {}) => ({
  id: 's1', sale_date: '2026-10-01', customer: { id: 'c1', name: 'Фарход', phone: '+992901112233' }, order_id: null, notes: null,
  items: [{ id: 'i1', category: 'HONEY', quantity: '10', unit: 'KG', price_per_unit: '100', total: '1000', description: null }],
  payments: [], total: '1000', paid: '300', debt: '700', state: 'partial', cancelled_at: null, cancel_reason: null, author: 'Умар', created_at: '',
  ...over,
})

beforeEach(() => { auth.role = 'BEEKEEPER' })

describe('Navigation', () => {
  it('shows CRM to a beekeeper and «Матки» to an assistant', () => {
    const { unmount } = wrap(<BottomNav />)
    expect(screen.getByText('CRM').closest('a')).toHaveAttribute('href', '/crm')
    expect(screen.queryByText('Матки')).not.toBeInTheDocument()
    unmount()
    auth.role = 'ASSISTANT'
    wrap(<BottomNav />)
    expect(screen.queryByText('CRM')).not.toBeInTheDocument()
    expect(screen.getByText('Матки')).toBeInTheDocument()
  })
})

describe('CRM home', () => {
  it('shows profit, money and sections', async () => {
    mockApi((u) => (u.includes('/api/crm/summary') ? summary : undefined))
    wrap(<CrmHomePage />)
    expect(await screen.findByText(/Прибыль за октябрь/)).toBeInTheDocument()
    expect(screen.getByText('12 500 смн')).toBeInTheDocument()
    expect(screen.getByText('1 700 смн').closest('a')).toHaveAttribute('href', '/crm/debts')
    expect(screen.getByText('120,5 кг')).toBeInTheDocument()
    expect(screen.getByText('открыто 2')).toBeInTheDocument()
    expect(screen.getByText('2 должника')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Расход по категориям' })).getByText('Корм')).toBeInTheDocument()
  })

  it('is closed for an assistant', () => {
    auth.role = 'ASSISTANT'
    const spy = mockApi(() => summary)
    wrap(<CrmHomePage />)
    expect(screen.getByText('CRM недоступна')).toBeInTheDocument()
    expect(spy.mock.calls.some(([u]) => String(u).includes('/summary'))).toBe(false)
  })
})

describe('Sale form', () => {
  it('records a partly paid sale for a customer and shows the remaining debt', async () => {
    const spy = mockApi((u, i) => {
      if (u.includes('/api/crm/customers')) return customers
      if (u.includes('/api/crm/summary')) return summary
      if (u.endsWith('/api/crm/sales') && i?.method === 'POST') return json(sale(), 201)
    })
    const done = vi.fn()
    wrap(<SaleForm onDone={done} />)
    await screen.findByRole('option', { name: /Фарход/ })
    await userEvent.selectOptions(screen.getByLabelText(/Клиент/), 'c1')
    await userEvent.type(screen.getByLabelText('Количество'), '10')
    await userEvent.type(screen.getByLabelText('Цена за кг'), '100')
    expect(screen.getByText('1 000 смн', { selector: 'b' })).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Оплата' })).getByRole('radio', { name: 'Частично' }))
    await userEvent.type(screen.getByLabelText('Сколько заплатили сейчас'), '300')
    expect(screen.getByText('700 смн')).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Как платили' })).getByRole('radio', { name: 'Перевод' }))
    await userEvent.click(screen.getByRole('button', { name: /Записать продажу/ }))
    await waitFor(() => expect(done).toHaveBeenCalled())
    expect(posts(spy, '/api/crm/sales')[0]).toMatchObject({
      customer_id: 'c1', payment: 'partial', paid_amount: 300, method: 'TRANSFER',
      items: [{ category: 'HONEY', quantity: 10, unit: 'KG', price_per_unit: 100 }],
    })
  })

  it('warns when more honey is sold than recorded in stock and asks for a customer for credit', async () => {
    mockApi((u) => (u.includes('/customers') ? customers : u.includes('/summary') ? { ...summary, honey_stock_kg: '5' } : undefined))
    wrap(<SaleForm onDone={vi.fn()} />)
    await userEvent.type(await screen.findByLabelText('Количество'), '8')
    expect(await screen.findByText(/На складе по записям 5 кг/)).toBeInTheDocument()
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Оплата' })).getByRole('radio', { name: 'В долг' }))
    expect(screen.getByText('Для продажи в долг выберите клиента.')).toBeInTheDocument()
  })
})

describe('Expense form', () => {
  it('records an expense with a category and amount', async () => {
    const spy = mockApi((_u, i) => (i?.method === 'POST' ? json({ id: 'e1' }, 201) : undefined))
    const done = vi.fn()
    wrap(<ExpenseForm onDone={done} />)
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Категория' })).getByRole('radio', { name: 'Топливо' }))
    await userEvent.type(screen.getByLabelText(/Сумма/), '450,5')
    await userEvent.type(screen.getByLabelText(/На что/), 'Бензин')
    await userEvent.click(screen.getByRole('button', { name: 'Записать расход' }))
    await waitFor(() => expect(done).toHaveBeenCalled())
    expect(posts(spy, '/api/crm/expenses')[0]).toMatchObject({ category: 'FUEL', amount: 450.5, description: 'Бензин' })
  })
})

describe('Debts', () => {
  it('lists debtors and takes a payment with the whole debt prefilled', async () => {
    const spy = mockApi((u, i) => {
      if (u.endsWith('/api/crm/debts')) return [{ customer: sale().customer, debt: '700', sales: [sale()] }]
      if (u.endsWith('/payments') && i?.method === 'POST') return json(sale({ debt: '0', state: 'paid' }), 201)
    })
    wrap(<DebtsPage />)
    expect(await screen.findByText('Вам должны')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /700 смн · Принять/ }))
    expect(screen.getByLabelText('Сумма оплаты')).toHaveValue('700')
    await userEvent.click(screen.getByRole('button', { name: 'Принять оплату' }))
    await waitFor(() => expect(posts(spy, '/payments')).toHaveLength(1))
    expect(posts(spy, '/payments')[0]).toMatchObject({ amount: 700, method: 'CASH' })
  })
})

describe('Order', () => {
  it('is delivered on credit and becomes a sale', async () => {
    const order = { id: 'o1', customer: sale().customer, order_date: '2026-10-10', due_date: '2026-10-12', status: 'READY', notes: null,
      cancel_reason: null, items: sale().items, total: '1000', overdue: true, sale_id: null, sale_state: null, sale_debt: null, created_at: '' }
    const spy = mockApi((u, i) => {
      if (u.endsWith('/api/crm/orders/o1')) return order
      if (u.endsWith('/deliver') && i?.method === 'POST') return sale({ id: 's9', order_id: 'o1', paid: '0', debt: '1000', state: 'unpaid' })
    })
    wrap(<OrderDetailsPage />, '/crm/orders/o1', '/crm/orders/:id')
    expect(await screen.findByText('Срок выдачи прошёл')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Собран' })).not.toBeInTheDocument()  // already READY
    await userEvent.click(screen.getByRole('button', { name: /Выдать заказ/ }))
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Оплата' })).getByRole('radio', { name: 'В долг' }))
    const dialog = screen.getByRole('dialog', { name: 'Выдать заказ' })
    expect(within(dialog).getByText(/Останется долг/)).toHaveTextContent('1 000 смн')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Выдать заказ' }))
    expect(await screen.findByText('other page')).toBeInTheDocument()
    expect(posts(spy, '/deliver')[0]).toMatchObject({ payment: 'credit' })
  })
})
