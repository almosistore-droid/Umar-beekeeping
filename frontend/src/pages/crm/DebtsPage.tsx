import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { crmApi } from '../../api/resources'
import { PaymentForm, useCurrency } from '../../components/crm/forms'
import { linesText } from '../../components/crm/rows'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { ErrorBox, Sheet } from '../../components/ui'
import type { Sale } from '../../types/api'
import { formatDate, money, num } from '../../utils/labels'
import { tr } from '../../i18n'

/** Who owes money: one card per customer with the unpaid sales and «Принять оплату». */
export function DebtsPage() {
  const currency = useCurrency()
  const [paying, setPaying] = useState<Sale | null>(null)
  const debts = useQuery({ queryKey: ['crm-debts'], queryFn: crmApi.debts })
  const total = (debts.data ?? []).reduce((s, d) => s + Number(d.debt), 0)
  return (
    <div className="page">
      <h1 className="page__title">{tr("Долги")}</h1>
      <ErrorBox error={debts.error} />
      {debts.isLoading ? <LoadingView /> : !debts.data?.length ? (
        <MessageView icon="coins" title={tr("Долгов нет")} text={tr("Все продажи оплачены.")} />
      ) : <>
        <section className="profit-hero">
          <span className="money__label">{tr("Вам должны")}</span>
          <span className="profit-hero__value money__value--bad">{num(total)} <small>{currency}</small></span>
        </section>
        {debts.data.map((d) => (
          <section key={d.customer?.id ?? 'none'} className="card">
            <div className="card__titlebar">
              <h2 className="card__title">{d.customer ? <Link to={`/crm/customers/${d.customer.id}`}>{d.customer.name}</Link> : tr("Без клиента")}</h2>
              <b className="warn">{money(d.debt, currency)}</b>
            </div>
            {d.customer?.phone && <a className="link small" href={`tel:${d.customer.phone}`}><Icon name="phone" size={14} /> {d.customer.phone}</a>}
            {d.sales.map((s) => (
              <div key={s.id} className="debt-row">
                <Link to={`/crm/sales/${s.id}`} className="debt-row__main">
                  <span>{formatDate(s.sale_date)} · {linesText(s.items)}</span>
                  <span className="small hint">{tr("из {0} оплачено {1}", money(s.total, currency), money(s.paid, currency))}</span>
                </Link>
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => setPaying(s)}>{tr("{0} · Принять", money(s.debt, currency))}</button>
              </div>
            ))}
          </section>
        ))}
      </>}
      <Sheet open={paying !== null} title={tr("Оплата долга")} onClose={() => setPaying(null)}>
        {paying && <PaymentForm sale={paying} onDone={() => setPaying(null)} />}
      </Sheet>
    </div>
  )
}
