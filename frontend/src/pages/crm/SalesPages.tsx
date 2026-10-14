import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { crmApi } from '../../api/resources'
import { CancelForm, PaymentForm, SaleForm, useCurrency } from '../../components/crm/forms'
import { PeriodChips, SaleRow, currentPeriod, type Period } from '../../components/crm/rows'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { Badge, Chips, ErrorBox, InfoRow, Sheet } from '../../components/ui'
import { FEED_UNIT, PAYMENT_METHOD, SALE_CATEGORY, SALE_STATE, formatDate, money, num } from '../../utils/labels'
import { tr } from '../../i18n'

export function SalesPage() {
  const currency = useCurrency()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>(currentPeriod())
  const [filter, setFilter] = useState<'all' | 'debt'>('all')
  const [open, setOpen] = useState(false)
  const sales = useQuery({
    queryKey: ['crm-sales', period.year, period.month, filter],
    queryFn: () => crmApi.sales({ ...period, unpaid: filter === 'debt' }),
  })
  const total = (sales.data ?? []).reduce((s, x) => s + Number(x.total), 0)
  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Продажи")}</h1>
        <button className="btn btn--primary btn--sm" onClick={() => setOpen(true)}>{tr("＋ Продажа")}</button>
      </div>
      <PeriodChips value={period} onChange={setPeriod} />
      <Chips options={[{ value: 'all', label: tr("Все") }, { value: 'debt', label: tr("С долгом") }]} value={filter} onChange={setFilter} />
      <ErrorBox error={sales.error} />
      {sales.isLoading ? <LoadingView /> : !sales.data?.length ? (
        <MessageView icon="cart" title={tr("Продаж нет")} text={tr("Нажмите «＋ Продажа», чтобы записать первую.")} />
      ) : <>
        <p className="hint">{tr("{0} · на {1}", sales.data.length, money(total, currency))}</p>
        <section className="card card--list">{sales.data.map((s) => <SaleRow key={s.id} s={s} currency={currency} />)}</section>
      </>}
      <Sheet open={open} title={tr("Новая продажа")} onClose={() => setOpen(false)}>
        {open && <SaleForm onDone={(s) => { setOpen(false); navigate(`/crm/sales/${s.id}`) }} />}
      </Sheet>
    </div>
  )
}

export function SaleDetailsPage() {
  const { id = '' } = useParams()
  const currency = useCurrency()
  const [sheet, setSheet] = useState<null | 'pay' | 'cancel'>(null)
  const sale = useQuery({ queryKey: ['crm-sale', id], queryFn: () => crmApi.sale(id) })
  if (sale.isLoading) return <LoadingView />
  if (sale.error || !sale.data) return <div className="page"><ErrorBox error={sale.error} /></div>
  const s = sale.data
  const st = SALE_STATE[s.state]
  const close = () => setSheet(null)
  return (
    <div className="page">
      <header className="page__titlebar">
        <div>
          <h1 className="page__title">{tr("Продажа")}</h1>
          <p className="hint">{formatDate(s.sale_date)}{s.author ? tr(" · записал {0}", s.author) : ''}</p>
        </div>
        <Badge tone={st.tone}>{st.label}</Badge>
      </header>
      {s.cancelled_at && <p className="warn-box">{tr("Отменена: {0}", s.cancel_reason)}</p>}

      <section className="profit-hero">
        <span className="money__label">{tr("Сумма")}</span>
        <span className="profit-hero__value">{num(s.total)} <small>{currency}</small></span>
        {Number(s.debt) > 0 && <span className="money__value--bad"><b>{tr("Долг {0}", money(s.debt, currency))}</b>{" "}{tr("· оплачено {0}", money(s.paid, currency))}</span>}
      </section>

      <section className="card">
        <h2 className="card__title">{tr("Клиент")}</h2>
        {s.customer ? <>
          <InfoRow label={tr("Имя")}><Link className="link" to={`/crm/customers/${s.customer.id}`}>{s.customer.name}</Link></InfoRow>
          {s.customer.phone && <InfoRow label={tr("Телефон")}><a className="link" href={`tel:${s.customer.phone}`}><Icon name="phone" size={14} /> {s.customer.phone}</a></InfoRow>}
        </> : <p className="hint">{tr("Без клиента")}</p>}
        {s.order_id && <InfoRow label={tr("По заказу")}><Link className="link" to={`/crm/orders/${s.order_id}`}>{tr("открыть заказ")}</Link></InfoRow>}
      </section>

      <section className="card">
        <h2 className="card__title">{tr("Что продано")}</h2>
        {s.items.map((i) => (
          <InfoRow key={i.id} label={`${SALE_CATEGORY[i.category]}, ${num(i.quantity)} ${FEED_UNIT[i.unit]} × ${num(i.price_per_unit)}`}>{money(i.total, currency)}</InfoRow>
        ))}
        {s.notes && <p className="notes">{s.notes}</p>}
      </section>

      <section className="card">
        <h2 className="card__title">{tr("Оплаты")}</h2>
        {!s.payments.length ? <p className="hint">{tr("Оплат пока не было")}</p> : s.payments.map((p) => (
          <InfoRow key={p.id} label={`${formatDate(p.paid_at)}, ${PAYMENT_METHOD[p.method].toLowerCase()}`}>{money(p.amount, currency)}</InfoRow>
        ))}
        {Number(s.debt) > 0 && <button type="button" className="btn btn--primary btn--block" onClick={() => setSheet('pay')}><Icon name="coins" size={18} />{tr("Принять оплату")}</button>}
      </section>

      {!s.cancelled_at && !s.order_id && !s.payments.length && (
        <button type="button" className="btn btn--ghost btn--block" onClick={() => setSheet('cancel')}>{tr("Отменить продажу")}</button>
      )}

      <Sheet open={sheet === 'pay'} title={tr("Оплата")} onClose={close}>{sheet === 'pay' && <PaymentForm sale={s} onDone={close} />}</Sheet>
      <Sheet open={sheet === 'cancel'} title={tr("Отменить продажу")} onClose={close}>
        {sheet === 'cancel' && <CancelForm what={tr("Продажа")} cancel={(r) => crmApi.cancelSale(s.id, r)} onDone={close} />}
      </Sheet>
    </div>
  )
}
