import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { HomePage } from '../pages/HomePage'
import { ReportsPage } from '../pages/ReportsPage'
import type { TelegramWebApp } from '../types/telegram'

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'u1', first_name: 'Умар', display_name: 'Умар', role: 'ADMIN' } }),
}))

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

const months = Array(12).fill('0')
months[6] = '40'; months[7] = '85.9'
const rank = (n: string, kg: string) => ({ hive_id: `h${n}`, hive_number: n, apiary_name: 'Горная', kg, harvests: 2 })

const dashboard = {
  year: 2026, finance_ready: false, honey_by_month: months,
  honey_by_hive: [rank('7', '30.9'), rank('3', '20')],
  strength: [
    { key: 'VERY_WEAK', label: 'Очень слабая', count: 0 }, { key: 'WEAK', label: 'Слабая', count: 3 },
    { key: 'MEDIUM', label: 'Средняя', count: 1 }, { key: 'STRONG', label: 'Сильная', count: 4 },
    { key: 'VERY_STRONG', label: 'Очень сильная', count: 1 },
  ],
  diseases: [{ name: 'Варроатоз', cases: 2, resolved: 1, open: 1 }],
  queen_ages: [{ key: 'lt1', label: 'до 1 года', count: 3 }, { key: 'unknown', label: 'неизвестно', count: 0 }],
  tiles: { hives: 11, queens_in_hives: 8, strong: 5, weak: 3, sick: 1, queenless: 2, needs_inspection: 4, open_tasks: 5, overdue_tasks: 1, honey_year_kg: '219', best_hive: rank('7', '30.9') },
}

describe('Dashboard', () => {
  it('shows counters, finance placeholders and the charts from one request', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json(dashboard))
    wrap(<HomePage />)
    expect(await screen.findByText('11')).toBeInTheDocument()
    expect(spy).toHaveBeenCalledTimes(1)
    expect(String(spy.mock.calls[0][0])).toContain('/api/dashboard?year=')
    expect(screen.getByText('Напоминания, просрочено 1')).toBeInTheDocument()
    expect(screen.getByText(/лучший улей №7/)).toBeInTheDocument()
    expect(screen.getByLabelText('Финансы появятся на этапе 7')).toHaveTextContent(/Доход.*Расход.*Прибыль.*этап 7/)
    expect(screen.getByRole('img', { name: /Мёд по месяцам, кг: июл 40 кг, авг 85,9 кг/ })).toBeInTheDocument()
    const strength = screen.getByRole('list', { name: 'Сила семей, число семей' })
    expect(within(strength).getByText('Сильная').closest('a')).toHaveAttribute('href', '/hives?filter=strong')
    expect(within(screen.getByRole('list', { name: 'Случаи болезней' })).getByText('2 случая')).toBeInTheDocument()
    expect(screen.queryByText('неизвестно')).not.toBeInTheDocument()  // empty "unknown" bucket hidden
    expect(screen.getByText('Без матки').closest('a')).toHaveAttribute('href', '/hives?filter=queenless')
  })
})

const report = {
  year: 2026, period_end: '2026-10-13', is_partial: true, available_years: [2026, 2025],
  hives: { at_start: 10, at_end: 11, new: 2, lost: 0, sold: 1, merged: 0, split: 1 },
  queens: { in_hives: 8, new: 3, replaced: 1, avg_age_months: '16.5', age_unknown: 0,
    best_families: [{ hive_id: 'h7', hive_number: '7', apiary_name: 'Горная', kg: '30.9', queen_code: 'M-107' }] },
  honey: { total_kg: '219', avg_per_hive_kg: '24.33', producing_hives: 9, best_hive: rank('7', '30.9'), worst_hive: rank('8', '14.8'),
    by_month: months, by_hive: [], value: '17257', products: [{ product_type: 'WAX', unit: 'KG', quantity: '3.5', value: '525' }] },
  diseases: { cases: 2, resolved: 1, open: 1, by_disease: [{ name: 'Варроатоз', cases: 2, resolved: 1, open: 1 }], treatments: 2,
    medications: [{ medication: 'Бипин', count: 2 }] },
  finance: { production_value: '18262', ready: false },
}

describe('Yearly report', () => {
  it('shows every section and switches year', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) =>
      json({ ...report, year: String(u).includes('2025') ? 2025 : 2026, is_partial: !String(u).includes('2025') }))
    wrap(<ReportsPage />)
    expect(await screen.findByText('На начало года')).toBeInTheDocument()
    expect(screen.getByText(/год ещё не закончился/)).toBeInTheDocument()
    expect(screen.getByText('1,4 года')).toBeInTheDocument()
    expect(screen.getByText('№7 — 30,9 кг')).toBeInTheDocument()
    expect(screen.getByText('№8 — 14,8 кг')).toBeInTheDocument()
    expect(screen.getByText('3,5 кг')).toBeInTheDocument()
    expect(screen.getByText('2 раза')).toBeInTheDocument()
    expect(screen.getByText('18 262')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: '2025' }))
    await waitFor(() => expect(spy.mock.calls.some(([u]) => String(u).endsWith('/api/reports/yearly/2025'))).toBe(true))
    await waitFor(() => expect(screen.queryByText(/год ещё не закончился/)).not.toBeInTheDocument())
  })

  it('sends the chosen format to the Telegram chat', async () => {
    window.Telegram = { WebApp: { initData: 'x', initDataUnsafe: {}, HapticFeedback: { impactOccurred() {}, notificationOccurred() {} } } as unknown as TelegramWebApp }
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_u, init) => json(init?.method === 'POST' ? { sent: true, labels: 1 } : report))
    wrap(<ReportsPage />)
    await screen.findByText('На начало года')
    await userEvent.click(within(screen.getByRole('radiogroup', { name: 'Формат' })).getByRole('radio', { name: 'Excel' }))
    await userEvent.click(screen.getByRole('button', { name: 'Отправить Excel в чат' }))
    expect(await screen.findByText('Отчёт (Excel) отправлен в чат с ботом.')).toBeInTheDocument()
    const post = spy.mock.calls.find(([, i]) => i?.method === 'POST')!
    expect(String(post[0])).toContain('/api/reports/yearly/2026/send?format=xlsx')
  })

  it('downloads in a browser', async () => {
    const created: string[] = []
    URL.createObjectURL = vi.fn(() => { created.push('blob'); return 'blob:x' })
    URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (u) => String(u).includes('/export')
      ? new Response(new Blob(['%PDF']), { status: 200, headers: { 'Content-Disposition': 'attachment; filename="godovoy-otchet-2026.pdf"' } })
      : json(report))
    wrap(<ReportsPage />)
    await screen.findByText('На начало года')
    await userEvent.click(screen.getByRole('button', { name: 'Скачать PDF' }))
    await waitFor(() => expect(created).toHaveLength(1))
  })
})
