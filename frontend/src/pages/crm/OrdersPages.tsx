import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { crmApi } from '../../api/resources'
import { CancelForm, DeliverForm, OrderForm, useCrmInvalidate, useCurrency } from '../../components/crm/forms'
import { OrderRow } from '../../components/crm/rows'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { Badge, Chips, ErrorBox, InfoRow, Sheet } from '../../components/ui'
import { haptic } from '../../services/telegram'
import type { OrderStatus } from '../../types/api'
import { FEED_UNIT, ORDER_STATUS, SALE_CATEGORY, SALE_STATE, formatDate, money, num } from '../../utils/labels'

type Filter = 'open' | 'DELIVERED' | 'CANCELLED'

export function OrdersPage() {
  const currency = useCurrency()
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('open')
  const [open, setOpen] = useState(false)
  const orders = useQuery({
    queryKey: ['crm-orders', filter],
    queryFn: () => crmApi.orders(filter === 'open' ? { open_only: true } : { status: filter as OrderStatus }),
  })
  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">Заказы</h1>
        <button className="btn btn--primary btn--sm" onClick={() => setOpen(true)}>＋ Заказ</button>
      </div>
      <Chips options={[{ value: 'open', label: 'Открытые' }, { value: 'DELIVERED', label: 'Выданные' }, { value: 'CANCELLED', label: 'Отменённые' }]}
        value={filter} onChange={setFilter} />
      <ErrorBox error={orders.error} />
      {orders.isLoading ? <LoadingView /> : !orders.data?.length ? (
        <MessageView icon="box" title={filter === 'open' ? 'Открытых заказов нет' : 'Заказов нет'} />
      ) : <section className="card card--list">{orders.data.map((o) => <OrderRow key={o.id} o={o} currency={currency} />)}</section>}
      <Sheet open={open} title="Новый заказ" onClose={() => setOpen(false)}>
        {open && <OrderForm onDone={(o) => { setOpen(false); navigate(`/crm/orders/${o.id}`) }} />}
      </Sheet>
    </div>
  )
}

const STEPS: OrderStatus[] = ['NEW', 'READY', 'DELIVERED']

export function OrderDetailsPage() {
  const { id = '' } = useParams()
  const currency = useCurrency()
  const navigate = useNavigate()
  const invalidate = useCrmInvalidate()
  const [sheet, setSheet] = useState<null | 'edit' | 'deliver' | 'cancel'>(null)
  const order = useQuery({ queryKey: ['crm-order', id], queryFn: () => crmApi.order(id) })
  const ready = useMutation({
    mutationFn: () => crmApi.updateOrder(id, { status: 'READY' }),
    onSuccess: () => { haptic('success'); invalidate() }, onError: () => haptic('error'),
  })
  if (order.isLoading) return <LoadingView />
  if (order.error || !order.data) return <div className="page"><ErrorBox error={order.error} /></div>
  const o = order.data
  const isOpen = o.status === 'NEW' || o.status === 'READY'
  const close = () => setSheet(null)
  return (
    <div className="page">
      <header className="page__titlebar">
        <div>
          <h1 className="page__title">Заказ</h1>
          <p className="hint">от {formatDate(o.order_date)}{o.due_date ? ` · отдать ${formatDate(o.due_date)}` : ''}</p>
        </div>
        <Badge tone={ORDER_STATUS[o.status].tone}>{ORDER_STATUS[o.status].label}</Badge>
      </header>
      {o.overdue && <p className="warn-box">Срок выдачи прошёл</p>}
      {o.status === 'CANCELLED' && <p className="warn-box">Отменён: {o.cancel_reason}</p>}

      {o.status !== 'CANCELLED' && (
        <ol className="steps" aria-label="Статус заказа">
          {STEPS.map((st, i) => (
            <li key={st} className={STEPS.indexOf(o.status) >= i ? 'is-done' : ''}>{ORDER_STATUS[st].label}</li>
          ))}
        </ol>
      )}

      <section className="card">
        <InfoRow label="Клиент"><Link className="link" to={`/crm/customers/${o.customer.id}`}>{o.customer.name}</Link></InfoRow>
        {o.customer.phone && <InfoRow label="Телефон"><a className="link" href={`tel:${o.customer.phone}`}><Icon name="phone" size={14} /> {o.customer.phone}</a></InfoRow>}
        {o.items.map((i) => (
          <InfoRow key={i.id} label={`${SALE_CATEGORY[i.category]}, ${num(i.quantity)} ${FEED_UNIT[i.unit]} × ${num(i.price_per_unit)}`}>{money(i.total, currency)}</InfoRow>
        ))}
        <InfoRow label="Итого"><b>{money(o.total, currency)}</b></InfoRow>
        {o.notes && <p className="notes">{o.notes}</p>}
      </section>

      {o.sale_id && o.sale_state && (
        <section className="card">
          <InfoRow label="Продажа"><Link className="link" to={`/crm/sales/${o.sale_id}`}>{SALE_STATE[o.sale_state].label}</Link></InfoRow>
          {o.sale_debt && Number(o.sale_debt) > 0 && <InfoRow label="Долг"><span className="warn">{money(o.sale_debt, currency)}</span></InfoRow>}
        </section>
      )}

      <ErrorBox error={ready.error} />
      {isOpen && <>
        <button type="button" className="btn btn--primary btn--block" onClick={() => setSheet('deliver')}><Icon name="cart" size={18} />Выдать заказ</button>
        <div className="btn-row">
          {o.status === 'NEW' && <button type="button" className="btn btn--secondary" disabled={ready.isPending} onClick={() => ready.mutate()}>Собран</button>}
          <button type="button" className="btn btn--secondary" onClick={() => setSheet('edit')}>Изменить</button>
        </div>
      </>}
      {o.status !== 'CANCELLED' && (!o.sale_id || o.sale_state === 'unpaid') && (
        <button type="button" className="btn btn--ghost btn--block" onClick={() => setSheet('cancel')}>Отменить заказ</button>
      )}

      <Sheet open={sheet === 'edit'} title="Изменить заказ" onClose={close}>{sheet === 'edit' && <OrderForm order={o} onDone={close} />}</Sheet>
      <Sheet open={sheet === 'deliver'} title="Выдать заказ" onClose={close}>
        {sheet === 'deliver' && <DeliverForm order={o} onDone={(s) => { close(); navigate(`/crm/sales/${s.id}`) }} />}
      </Sheet>
      <Sheet open={sheet === 'cancel'} title="Отменить заказ" onClose={close}>
        {sheet === 'cancel' && <CancelForm what="Заказ" cancel={(r) => crmApi.cancelOrder(o.id, r)} onDone={close} />}
      </Sheet>
    </div>
  )
}
