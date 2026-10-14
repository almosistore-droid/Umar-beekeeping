import { Link } from 'react-router-dom'
import type { Order, Sale } from '../../types/api'
import { FEED_UNIT, MONTHS, ORDER_STATUS, SALE_CATEGORY, SALE_STATE, formatDate, money, num } from '../../utils/labels'
import { Icon } from '../Icon'
import { Badge, Chips } from '../ui'
import { tr } from '../../i18n'

export interface Period { year: number; month: number | null }

export function currentPeriod(): Period {
  const d = new Date()
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

/** «Этот месяц» / current year / previous year. */
export function PeriodChips({ value, onChange }: { value: Period; onChange: (p: Period) => void }) {
  const now = currentPeriod()
  const options = [
    { value: `${now.year}-${now.month}`, label: MONTHS[now.month! - 1] },
    { value: `${now.year}-`, label: String(now.year) },
    { value: `${now.year - 1}-`, label: String(now.year - 1) },
  ]
  return (
    <Chips options={options} value={`${value.year}-${value.month ?? ''}`}
      onChange={(v) => { const [y, m] = v.split('-'); onChange({ year: Number(y), month: m ? Number(m) : null }) }} />
  )
}

export const linesText = (items: Sale['items']) =>
  items.map((i) => `${SALE_CATEGORY[i.category]} ${num(i.quantity)} ${FEED_UNIT[i.unit]}`).join(', ')

export function SaleRow({ s, currency }: { s: Sale; currency: string }) {
  const st = SALE_STATE[s.state]
  return (
    <Link to={`/crm/sales/${s.id}`} className={`crm-row${s.cancelled_at ? ' is-cancelled' : ''}`}>
      <span className="crm-row__icon" aria-hidden><Icon name="cart" size={18} /></span>
      <span className="crm-row__main">
        <b>{s.customer?.name ?? tr("Без клиента")}</b>
        <span className="small hint">{formatDate(s.sale_date)} · {linesText(s.items)}</span>
      </span>
      <span className="crm-row__side">
        <b>{money(s.total, currency)}</b>
        {s.state !== 'paid' && <Badge tone={st.tone}>{s.state === 'partial' ? tr("долг {0}", money(s.debt, currency)) : st.label}</Badge>}
      </span>
    </Link>
  )
}

export function OrderRow({ o, currency }: { o: Order; currency: string }) {
  const st = ORDER_STATUS[o.status]
  return (
    <Link to={`/crm/orders/${o.id}`} className={`crm-row${o.status === 'CANCELLED' ? ' is-cancelled' : ''}`}>
      <span className="crm-row__icon" aria-hidden><Icon name="box" size={18} /></span>
      <span className="crm-row__main">
        <b>{o.customer.name}</b>
        <span className={`small ${o.overdue ? 'warn' : 'hint'}`}>
          {o.due_date ? tr("{0}к {1}", o.overdue ? tr("просрочен, ") : '', formatDate(o.due_date)) : tr("от {0}", formatDate(o.order_date))} · {linesText(o.items)}
        </span>
      </span>
      <span className="crm-row__side">
        <b>{money(o.total, currency)}</b>
        <Badge tone={st.tone}>{st.label}</Badge>
      </span>
    </Link>
  )
}

export function Money({ label, value, currency, tone, to }: { label: string; value: string | number; currency: string; tone?: 'ok' | 'bad'; to?: string }) {
  const body = <>
    <span className={`money__value${tone ? ` money__value--${tone}` : ''}`}>{money(value, currency)}</span>
    <span className="money__label">{label}</span>
  </>
  return to ? <Link to={to} className="money">{body}</Link> : <div className="money">{body}</div>
}
