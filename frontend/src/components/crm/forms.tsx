import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { crmApi, type CustomerInput } from '../../api/resources'
import { haptic } from '../../services/telegram'
import type {
  Customer, Expense, ExpenseCategory, FeedUnit, LineInput, Order, PayMode, PaymentMethod, Sale, SaleCategory,
} from '../../types/api'
import {
  DEFAULT_SALE_UNIT, EXPENSE_CATEGORY, FEED_UNIT, PAYMENT_METHOD, SALE_CATEGORY, addDaysIso, money, num, todayIso,
} from '../../utils/labels'
import { Icon } from '../Icon'
import { Choice, ErrorBox, Field, SubmitButton, fieldError } from '../ui'

export const parseNum = (v: string) => Number(v.replace(/\s/g, '').replace(',', '.'))
const opts = <T extends string>(rec: Record<T, string>) => (Object.keys(rec) as T[]).map((k) => ({ value: k, label: rec[k] }))
const UNITS: FeedUnit[] = ['KG', 'G', 'L', 'PCS']

/** Currency label from the server settings (CURRENCY in .env). */
export function useCurrency(): string {
  const q = useQuery({ queryKey: ['crm-settings'], queryFn: crmApi.settings, staleTime: Infinity })
  return q.data?.currency ?? ''
}

/** Everything that shows money or customers is refreshed after a CRM write. */
export function useCrmInvalidate() {
  const qc = useQueryClient()
  return () => {
    for (const key of ['crm-summary', 'crm-sales', 'crm-sale', 'crm-expenses', 'crm-orders', 'crm-order', 'crm-customers',
      'crm-customer', 'crm-debts', 'dashboard', 'report']) qc.invalidateQueries({ queryKey: [key] })
  }
}

function useCrmMutation<T, R>(fn: (v: T) => Promise<R>, onDone: (r: R) => void) {
  const invalidate = useCrmInvalidate()
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => { haptic('success'); invalidate(); onDone(r) },
    onError: () => haptic('error'),
  })
}

// ---------- customer picker ----------

export function CustomerPicker({ value, onChange, required }: { value: string | null; onChange: (id: string | null) => void; required?: boolean }) {
  const customers = useQuery({ queryKey: ['crm-customers', ''], queryFn: () => crmApi.customers() })
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const create = useCrmMutation((b: CustomerInput) => crmApi.createCustomer(b), (c: Customer) => {
    onChange(c.id); setAdding(false); setName(''); setPhone('')
  })
  return (
    <div className="customer-picker">
      <Field label={required ? 'Клиент' : 'Клиент (можно без клиента)'}>
        <select className="input" value={value ?? ''} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">{required ? 'Выберите клиента' : '— без клиента —'}</option>
          {(customers.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}{c.phone ? ` · ${c.phone}` : ''}</option>)}
        </select>
      </Field>
      {!adding ? (
        <button type="button" className="link-btn small" onClick={() => setAdding(true)}>＋ Новый клиент</button>
      ) : (
        <div className="inline-card">
          <ErrorBox error={create.error} />
          <Field label="Имя нового клиента" error={fieldError(create.error, 'name')}>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </Field>
          <Field label="Телефон" error={fieldError(create.error, 'phone')}>
            <input className="input" type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+992…" />
          </Field>
          <div className="btn-row">
            <button type="button" className="btn btn--secondary" disabled={create.isPending || name.trim().length < 2}
              onClick={() => create.mutate({ name, phone: phone || null })}>Добавить</button>
            <button type="button" className="btn btn--ghost" onClick={() => setAdding(false)}>Отмена</button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------- lines ----------

interface DraftLine { category: SaleCategory; quantity: string; unit: FeedUnit; price: string }
const newLine = (category: SaleCategory = 'HONEY'): DraftLine => ({ category, quantity: '', unit: DEFAULT_SALE_UNIT[category], price: '' })
export const toLines = (lines: DraftLine[]): LineInput[] =>
  lines.map((l) => ({ category: l.category, quantity: parseNum(l.quantity), unit: l.unit, price_per_unit: parseNum(l.price || '0') }))
export const fromLines = (items: Order['items']): DraftLine[] =>
  items.map((i) => ({ category: i.category, quantity: String(Number(i.quantity)), unit: i.unit, price: String(Number(i.price_per_unit)) }))
const lineTotal = (l: DraftLine) => (parseNum(l.quantity) || 0) * (parseNum(l.price) || 0)
export const linesTotal = (lines: DraftLine[]) => lines.reduce((s, l) => s + lineTotal(l), 0)

export function useLines(initial?: DraftLine[]) {
  return useState<DraftLine[]>(initial ?? [newLine()])
}

export function ItemsEditor({ lines, setLines, currency, error }: {
  lines: DraftLine[]; setLines: (l: DraftLine[]) => void; currency: string; error?: unknown
}) {
  const set = (i: number, patch: Partial<DraftLine>) => setLines(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)))
  return (
    <div className="lines">
      {lines.map((l, i) => (
        <div key={i} className="line">
          <div className="line__head">
            <span className="form-section-title">Позиция {lines.length > 1 ? i + 1 : ''}</span>
            {lines.length > 1 && <button type="button" className="link-btn small" onClick={() => setLines(lines.filter((_, j) => j !== i))}>Убрать</button>}
          </div>
          <Choice label={`Что продаём${lines.length > 1 ? ` (${i + 1})` : ''}`} options={opts(SALE_CATEGORY)} value={l.category}
            onChange={(v) => v && set(i, { category: v, unit: DEFAULT_SALE_UNIT[v] })} />
          <div className="line__nums">
            <Field label="Количество" error={fieldError(error, `items.${i}.quantity`)}>
              <input className="input input--big" inputMode="decimal" value={l.quantity} onChange={(e) => set(i, { quantity: e.target.value })} />
            </Field>
            <Field label={`Цена за ${FEED_UNIT[l.unit]}`} error={fieldError(error, `items.${i}.price_per_unit`)}>
              <input className="input input--big" inputMode="decimal" value={l.price} onChange={(e) => set(i, { price: e.target.value })} />
            </Field>
          </div>
          <div className="pills" role="radiogroup" aria-label={`Единица (${i + 1})`}>
            {UNITS.map((u) => (
              <button key={u} type="button" role="radio" aria-checked={l.unit === u} className={`pill${l.unit === u ? ' is-active' : ''}`}
                onClick={() => set(i, { unit: u })}>{FEED_UNIT[u]}</button>
            ))}
          </div>
          {lineTotal(l) > 0 && <p className="hint small">= {money(lineTotal(l), currency)}</p>}
        </div>
      ))}
      <button type="button" className="btn btn--ghost" onClick={() => setLines([...lines, newLine('WAX')])}><Icon name="plus" size={18} />Ещё позиция</button>
      <div className="lines__total">Итого: <b>{money(linesTotal(lines), currency)}</b></div>
    </div>
  )
}

// ---------- payment now ----------

const PAY_MODES: { value: PayMode; label: string }[] = [
  { value: 'full', label: 'Оплачено полностью' }, { value: 'partial', label: 'Частично' }, { value: 'credit', label: 'В долг' },
]

export function PayNowFields({ mode, setMode, amount, setAmount, method, setMethod, total, currency, error }: {
  mode: PayMode; setMode: (m: PayMode) => void; amount: string; setAmount: (v: string) => void
  method: PaymentMethod; setMethod: (m: PaymentMethod) => void; total: number; currency: string; error?: unknown
}) {
  const paid = mode === 'full' ? total : mode === 'credit' ? 0 : parseNum(amount) || 0
  return (
    <div className="form">
      <Choice label="Оплата" options={PAY_MODES} value={mode} onChange={(v) => v && setMode(v)} />
      {mode === 'partial' && (
        <Field label="Сколько заплатили сейчас" error={fieldError(error, 'paid_amount')}>
          <input className="input input--big" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Field>
      )}
      {mode !== 'credit' && <Choice label="Как платили" options={opts(PAYMENT_METHOD)} value={method} onChange={(v) => v && setMethod(v)} />}
      {mode !== 'full' && total > 0 && <p className="warn-box small">Останется долг: <b>{money(Math.max(total - paid, 0), currency)}</b></p>}
    </div>
  )
}

function usePayNow() {
  const [mode, setMode] = useState<PayMode>('full')
  const [amount, setAmount] = useState('')
  const [method, setMethod] = useState<PaymentMethod>('CASH')
  const body = { payment: mode, paid_amount: mode === 'partial' ? parseNum(amount) || null : null, method }
  return { mode, setMode, amount, setAmount, method, setMethod, body }
}

// ---------- sale ----------

export function SaleForm({ customerId, onDone }: { customerId?: string | null; onDone: (s: Sale) => void }) {
  const currency = useCurrency()
  const [customer, setCustomer] = useState<string | null>(customerId ?? null)
  const [lines, setLines] = useLines()
  const [date, setDate] = useState(todayIso())
  const [notes, setNotes] = useState('')
  const pay = usePayNow()
  const stock = useQuery({ queryKey: ['crm-summary', 'stock'], queryFn: () => crmApi.summary({}) })
  const save = useCrmMutation(() => crmApi.createSale({
    sale_date: date, customer_id: customer, items: toLines(lines), notes: notes || null, ...pay.body,
  }), onDone)
  const honeyKg = lines.filter((l) => l.category === 'HONEY' && l.unit === 'KG').reduce((s, l) => s + (parseNum(l.quantity) || 0), 0)
  const stockKg = stock.data ? Number(stock.data.honey_stock_kg) : null
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <CustomerPicker value={customer} onChange={setCustomer} />
      <ItemsEditor lines={lines} setLines={setLines} currency={currency} error={save.error} />
      {stockKg !== null && honeyKg > 0 && honeyKg > stockKg && (
        <p className="warn-box small">На складе по записям {num(stockKg)} кг мёда, а продаётся {num(honeyKg)} кг. Сохранить можно — проверьте откачки.</p>
      )}
      <PayNowFields {...pay} total={linesTotal(lines)} currency={currency} error={save.error} />
      {pay.mode !== 'full' && !customer && <p className="warn-box small">Для продажи в долг выберите клиента.</p>}
      <Field label="Дата продажи"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <Field label="Заметка" hint="Можно не заполнять"><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Записать продажу · {money(linesTotal(lines), currency)}</SubmitButton></div>
    </form>
  )
}

// ---------- payment ----------

export function PaymentForm({ sale, onDone }: { sale: Sale; onDone: () => void }) {
  const currency = useCurrency()
  const [amount, setAmount] = useState(String(Number(sale.debt)))
  const [method, setMethod] = useState<PaymentMethod>('CASH')
  const [date, setDate] = useState(todayIso())
  const save = useCrmMutation(() => crmApi.pay(sale.id, { amount: parseNum(amount), method, paid_at: date }), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <p className="hint">Долг по продаже от {sale.sale_date.split('-').reverse().join('.')}: <b>{money(sale.debt, currency)}</b></p>
      <Field label="Сумма оплаты" error={fieldError(save.error, 'amount')}>
        <input className="input input--big" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} autoFocus />
      </Field>
      <div className="pills">
        <button type="button" className="pill" onClick={() => setAmount(String(Number(sale.debt)))}>Весь долг</button>
        <button type="button" className="pill" onClick={() => setAmount(String(Math.round(Number(sale.debt) / 2)))}>Половина</button>
      </div>
      <Choice label="Как платили" options={opts(PAYMENT_METHOD)} value={method} onChange={(v) => v && setMethod(v)} />
      <Field label="Дата оплаты"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Принять оплату</SubmitButton></div>
    </form>
  )
}

// ---------- cancel ----------

export function CancelForm({ what, cancel, onDone }: { what: string; cancel: (reason: string) => Promise<unknown>; onDone: () => void }) {
  const [reason, setReason] = useState('')
  const save = useCrmMutation(() => cancel(reason), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <p className="hint">{what} не удаляется: запись останется в истории с пометкой «отменено» и не будет учитываться в суммах.</p>
      <Field label="Причина отмены" error={fieldError(save.error, 'reason')}>
        <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} autoFocus />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger>Отменить</SubmitButton></div>
    </form>
  )
}

// ---------- expense ----------

export function ExpenseForm({ expense, onDone }: { expense?: Expense; onDone: () => void }) {
  const currency = useCurrency()
  const [category, setCategory] = useState<ExpenseCategory>(expense?.category ?? 'FEED')
  const [amount, setAmount] = useState(expense ? String(Number(expense.amount)) : '')
  const [date, setDate] = useState(expense?.expense_date ?? todayIso())
  const [description, setDescription] = useState(expense?.description ?? '')
  const body = { category, amount: parseNum(amount), expense_date: date, description: description || null }
  const save = useCrmMutation(() => expense ? crmApi.updateExpense(expense.id, body) : crmApi.createExpense(body), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Choice label="Категория" options={opts(EXPENSE_CATEGORY)} value={category} onChange={(v) => v && setCategory(v)} />
      <Field label={`Сумма, ${currency}`} error={fieldError(save.error, 'amount')}>
        <input className="input input--big" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
      </Field>
      <Field label="На что" hint="Например: сахар 50 кг"><input className="input" value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
      <Field label="Дата" error={fieldError(save.error, 'expense_date')}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{expense ? 'Сохранить' : 'Записать расход'}</SubmitButton></div>
    </form>
  )
}

// ---------- order ----------

const DUE = [{ d: 0, label: 'Сегодня' }, { d: 1, label: 'Завтра' }, { d: 3, label: 'Через 3 дня' }, { d: 7, label: 'Через неделю' }]

export function OrderForm({ order, customerId, onDone }: { order?: Order; customerId?: string | null; onDone: (o: Order) => void }) {
  const currency = useCurrency()
  const [customer, setCustomer] = useState<string | null>(order?.customer.id ?? customerId ?? null)
  const [lines, setLines] = useLines(order ? fromLines(order.items) : undefined)
  const [due, setDue] = useState<string>(order?.due_date ?? addDaysIso(3))
  const [notes, setNotes] = useState(order?.notes ?? '')
  const save = useCrmMutation(() => order
    ? crmApi.updateOrder(order.id, { items: toLines(lines), due_date: due || null, notes: notes || null })
    : crmApi.createOrder({ customer_id: customer!, items: toLines(lines), due_date: due || null, notes: notes || null }), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      {!order && <CustomerPicker value={customer} onChange={setCustomer} required />}
      <ItemsEditor lines={lines} setLines={setLines} currency={currency} error={save.error} />
      <span className="field__label">Когда отдать</span>
      <div className="pills">
        {DUE.map((x) => (
          <button key={x.d} type="button" className={`pill${due === addDaysIso(x.d) ? ' is-active' : ''}`} onClick={() => setDue(addDaysIso(x.d))}>{x.label}</button>
        ))}
      </div>
      <input className="input" type="date" aria-label="Дата выдачи" value={due} min={todayIso()} onChange={(e) => setDue(e.target.value)} />
      <Field label="Заметка" hint="Тара, адрес, сорт…"><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div className="submit-bar">
        <button type="submit" className="btn btn--block btn--primary" disabled={save.isPending || (!order && !customer)}>
          {save.isPending ? 'Сохранение…' : !order && !customer ? 'Выберите клиента' : order ? 'Сохранить заказ' : `Записать заказ · ${money(linesTotal(lines), currency)}`}
        </button>
      </div>
    </form>
  )
}

export function DeliverForm({ order, onDone }: { order: Order; onDone: (s: Sale) => void }) {
  const currency = useCurrency()
  const pay = usePayNow()
  const [date, setDate] = useState(todayIso())
  const save = useCrmMutation(() => crmApi.deliver(order.id, { sale_date: date, ...pay.body }), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <p className="hint">Заказ на <b>{money(order.total, currency)}</b> станет продажей клиенту «{order.customer.name}».</p>
      <PayNowFields {...pay} total={Number(order.total)} currency={currency} error={save.error} />
      <Field label="Дата выдачи"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Выдать заказ</SubmitButton></div>
    </form>
  )
}

// ---------- customer ----------

export function CustomerForm({ customer, onDone }: { customer?: Customer; onDone: (c: Customer) => void }) {
  const [f, setF] = useState<CustomerInput>({ name: customer?.name ?? '', phone: customer?.phone ?? '', city: customer?.city ?? '', notes: customer?.notes ?? '' })
  useEffect(() => { if (customer) setF({ name: customer.name, phone: customer.phone ?? '', city: customer.city ?? '', notes: customer.notes ?? '' }) }, [customer])
  const body = { name: f.name, phone: f.phone || null, city: f.city || null, notes: f.notes || null }
  const save = useCrmMutation(() => customer ? crmApi.updateCustomer(customer.id, body) : crmApi.createCustomer(body), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Field label="Имя или название" error={fieldError(save.error, 'name')}>
        <input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
      </Field>
      <Field label="Телефон" error={fieldError(save.error, 'phone')}>
        <input className="input" type="tel" inputMode="tel" placeholder="+992…" value={f.phone ?? ''} onChange={(e) => setF({ ...f, phone: e.target.value })} />
      </Field>
      <Field label="Город"><input className="input" value={f.city ?? ''} onChange={(e) => setF({ ...f, city: e.target.value })} /></Field>
      <Field label="Заметки"><textarea className="input" rows={2} value={f.notes ?? ''} onChange={(e) => setF({ ...f, notes: e.target.value })} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{customer ? 'Сохранить' : 'Добавить клиента'}</SubmitButton></div>
    </form>
  )
}
