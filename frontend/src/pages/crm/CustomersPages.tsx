import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { crmApi } from '../../api/resources'
import { CustomerForm, OrderForm, SaleForm, useCrmInvalidate, useCurrency } from '../../components/crm/forms'
import { Money, OrderRow, SaleRow } from '../../components/crm/rows'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { Badge, ErrorBox, Sheet } from '../../components/ui'
import { haptic } from '../../services/telegram'
import { formatDate, money } from '../../utils/labels'
import { tr } from '../../i18n'

export function CustomersPage() {
  const currency = useCurrency()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const list = useQuery({ queryKey: ['crm-customers', q], queryFn: () => crmApi.customers(q || undefined) })
  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Клиенты")}</h1>
        <button className="btn btn--primary btn--sm" onClick={() => setOpen(true)}>{tr("＋ Клиент")}</button>
      </div>
      <input className="input" type="search" placeholder={tr("Имя, телефон или город")} aria-label={tr("Поиск клиентов")} value={q} onChange={(e) => setQ(e.target.value)} />
      <ErrorBox error={list.error} />
      {list.isLoading ? <LoadingView /> : !list.data?.length ? (
        <MessageView icon="users" title={q ? tr("Никого не нашли") : tr("Клиентов пока нет")} />
      ) : (
        <section className="card card--list">
          {list.data.map((c) => (
            <Link key={c.id} to={`/crm/customers/${c.id}`} className="crm-row">
              <span className="crm-row__icon" aria-hidden><Icon name="users" size={18} /></span>
              <span className="crm-row__main">
                <b>{c.name}</b>
                <span className="small hint">{[c.phone, c.city].filter(Boolean).join(' · ') || '—'}</span>
              </span>
              <span className="crm-row__side">
                <span className="small hint">{tr("куплено {0}", money(c.bought, currency))}</span>
                {Number(c.debt) > 0 && <Badge tone="bad">{tr("долг {0}", money(c.debt, currency))}</Badge>}
              </span>
            </Link>
          ))}
        </section>
      )}
      <Sheet open={open} title={tr("Новый клиент")} onClose={() => setOpen(false)}>
        {open && <CustomerForm onDone={(c) => { setOpen(false); navigate(`/crm/customers/${c.id}`) }} />}
      </Sheet>
    </div>
  )
}

export function CustomerDetailsPage() {
  const { id = '' } = useParams()
  const currency = useCurrency()
  const navigate = useNavigate()
  const invalidate = useCrmInvalidate()
  const [sheet, setSheet] = useState<null | 'edit' | 'sale' | 'order'>(null)
  const [tab, setTab] = useState<'sales' | 'orders'>('sales')
  const c = useQuery({ queryKey: ['crm-customer', id], queryFn: () => crmApi.customer(id) })
  const archive = useMutation({
    mutationFn: (v: boolean) => crmApi.updateCustomer(id, { is_archived: v }),
    onSuccess: () => { haptic('success'); invalidate() }, onError: () => haptic('error'),
  })
  if (c.isLoading) return <LoadingView />
  if (c.error || !c.data) return <div className="page"><ErrorBox error={c.error} /></div>
  const x = c.data
  const close = () => setSheet(null)
  return (
    <div className="page">
      <header className="page__titlebar">
        <div>
          <h1 className="page__title">{x.name}</h1>
          <p className="hint">{x.city ?? ''}{x.last_purchase ? tr(" · последняя покупка {0}", formatDate(x.last_purchase)) : ''}</p>
        </div>
        <button className="icon-btn" aria-label={tr("Изменить клиента")} onClick={() => setSheet('edit')}><Icon name="edit" /></button>
      </header>
      {x.is_archived && <p className="warn-box">{tr("Клиент в архиве")}</p>}
      {x.phone && <a className="btn btn--secondary btn--block" href={`tel:${x.phone}`}><Icon name="phone" size={18} />{tr("Позвонить {0}", x.phone)}</a>}

      <div className="money-grid">
        <Money label={tr("Куплено")} value={x.bought} currency={currency} />
        <Money label={tr("Оплачено")} value={x.paid} currency={currency} />
        <Money label={tr("Долг")} value={x.debt} currency={currency} tone={Number(x.debt) > 0 ? 'bad' : undefined} />
      </div>
      {x.notes && <p className="notes">{x.notes}</p>}

      {!x.is_archived && (
        <div className="btn-row">
          <button className="btn btn--primary" onClick={() => setSheet('sale')}>{tr("＋ Продажа")}</button>
          <button className="btn btn--secondary" onClick={() => setSheet('order')}>{tr("＋ Заказ")}</button>
        </div>
      )}

      <section className="card">
        <div className="segmented">
          <button type="button" className={tab === 'sales' ? 'is-active' : ''} onClick={() => setTab('sales')}>{tr("Покупки ({0})", x.sales.length)}</button>
          <button type="button" className={tab === 'orders' ? 'is-active' : ''} onClick={() => setTab('orders')}>{tr("Заказы ({0})", x.orders.length)}</button>
        </div>
        {tab === 'sales' && (x.sales.length ? x.sales.map((s) => <SaleRow key={s.id} s={s} currency={currency} />) : <p className="hint">{tr("Покупок нет")}</p>)}
        {tab === 'orders' && (x.orders.length ? x.orders.map((o) => <OrderRow key={o.id} o={o} currency={currency} />) : <p className="hint">{tr("Заказов нет")}</p>)}
      </section>

      <ErrorBox error={archive.error} />
      <button type="button" className="btn btn--ghost btn--block" disabled={archive.isPending} onClick={() => archive.mutate(!x.is_archived)}>
        {x.is_archived ? tr("Вернуть из архива") : tr("Убрать в архив")}
      </button>
      {!x.is_archived && Number(x.debt) > 0 && <p className="hint small">{tr("У клиента есть долг — в архиве он останется в «Долгах».")}</p>}

      <Sheet open={sheet === 'edit'} title={tr("Клиент")} onClose={close}>{sheet === 'edit' && <CustomerForm customer={x} onDone={close} />}</Sheet>
      <Sheet open={sheet === 'sale'} title={tr("Продажа: {0}", x.name)} onClose={close}>
        {sheet === 'sale' && <SaleForm customerId={x.id} onDone={(s) => { close(); navigate(`/crm/sales/${s.id}`) }} />}
      </Sheet>
      <Sheet open={sheet === 'order'} title={tr("Заказ: {0}", x.name)} onClose={close}>
        {sheet === 'order' && <OrderForm customerId={x.id} onDone={(o) => { close(); navigate(`/crm/orders/${o.id}`) }} />}
      </Sheet>
    </div>
  )
}
