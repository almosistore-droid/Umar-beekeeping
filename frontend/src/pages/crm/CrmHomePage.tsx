import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { crmApi } from '../../api/resources'
import { BarList } from '../../components/charts/BarList'
import { ColumnChart } from '../../components/charts/ColumnChart'
import { CustomerForm, ExpenseForm, OrderForm, SaleForm } from '../../components/crm/forms'
import { Money, PeriodChips, currentPeriod, type Period } from '../../components/crm/rows'
import { Icon, type IconName } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { ErrorBox, Sheet } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import { MONTHS, MONTHS_SHORT, num } from '../../utils/labels'
import { plural } from '../../utils/plural'
import { tr } from '../../i18n'

type SheetKind = null | 'sale' | 'expense' | 'order' | 'customer'
const TICKS = MONTHS_SHORT.map((m) => m.slice(0, 1).toUpperCase() + m.slice(1, 3))

/** CRM: money for the period, quick actions, sections. ADMIN / BEEKEEPER only. */
export function CrmHomePage() {
  const { canManage } = usePermissions()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>(currentPeriod())
  const [sheet, setSheet] = useState<SheetKind>(null)
  const summary = useQuery({ queryKey: ['crm-summary', period.year, period.month], queryFn: () => crmApi.summary(period), enabled: canManage })
  if (!canManage) return <MessageView icon="wallet" title={tr("CRM недоступна")} text={tr("Раздел с деньгами и клиентами видят администратор и пчеловод.")} />
  const s = summary.data
  const cur = s?.currency ?? ''
  const close = () => setSheet(null)
  const profitTone = s ? (Number(s.profit) >= 0 ? 'ok' : 'bad') : undefined

  const actions: { kind: SheetKind; icon: IconName; label: string }[] = [
    { kind: 'sale', icon: 'cart', label: tr("Продажа") }, { kind: 'expense', icon: 'receipt', label: tr("Расход") },
    { kind: 'order', icon: 'box', label: tr("Заказ") }, { kind: 'customer', icon: 'users', label: tr("Клиент") },
  ]
  const sections: { to: string; icon: IconName; label: string; note?: string }[] = [
    { to: '/crm/sales', icon: 'cart', label: tr("Продажи") },
    { to: '/crm/expenses', icon: 'receipt', label: tr("Расходы") },
    { to: '/crm/orders', icon: 'box', label: tr("Заказы"), note: s?.open_orders ? tr("открыто {0}", s.open_orders) : undefined },
    { to: '/crm/customers', icon: 'users', label: tr("Клиенты") },
    { to: '/crm/debts', icon: 'coins', label: tr("Долги"), note: s?.debtors ? `${s.debtors} ${plural(s.debtors, tr("должник"), tr("должника"), tr("должников"))}` : undefined },
  ]

  return (
    <div className="page">
      <h1 className="page__title">CRM</h1>
      <PeriodChips value={period} onChange={setPeriod} />
      <ErrorBox error={summary.error} />

      {!s ? <LoadingView /> : <>
        <section className="profit-hero">
          <span className="money__label">{tr("Прибыль за")}{" "}{period.month ? MONTHS[period.month - 1].toLowerCase() : tr("{0} год", period.year)}</span>
          <span className={`profit-hero__value money__value--${profitTone}`}>{num(s.profit)} <small>{cur}</small></span>
          <span className="hint small">{tr("доход минус расход")}</span>
        </section>
        <div className="money-grid">
          <Money label={tr("Доход (продажи)")} value={s.income} currency={cur} to="/crm/sales" />
          <Money label={tr("Расход")} value={s.expenses} currency={cur} to="/crm/expenses" />
          <Money label={tr("Получено денег")} value={s.received} currency={cur} />
          <Money label={tr("Долги клиентов")} value={s.debts_total} currency={cur} tone={Number(s.debts_total) > 0 ? 'bad' : undefined} to="/crm/debts" />
        </div>
        <p className="hint small stock-note"><Icon name="honey" size={16} />{" "}{tr("Мёд на складе по записям:")}{" "}<b>{tr("{0} кг", num(s.honey_stock_kg))}</b></p>
      </>}

      <div className="quick-grid quick-grid--4">
        {actions.map((a) => (
          <button key={a.label} type="button" className="quick" onClick={() => setSheet(a.kind)}>
            <span className="quick__icon"><Icon name={a.icon} /></span><span className="quick__label">＋ {a.label}</span>
          </button>
        ))}
      </div>

      <nav className="menu">
        {sections.map((x) => (
          <Link key={x.to} to={x.to} className="menu__item"><Icon name={x.icon} />{x.label}
            {x.note && <span className="menu__note">{x.note}</span>}<span className="chevron">›</span></Link>
        ))}
      </nav>

      {s && <>
        <ColumnChart title={tr("Доход по месяцам {0}, {1}", period.year, cur)} unit={cur} labelHeader={tr("Месяц")} labels={MONTHS_SHORT} shortLabels={TICKS}
          values={s.income_by_month.map(Number)} />
        <ColumnChart title={tr("Расход по месяцам {0}, {1}", period.year, cur)} unit={cur} labelHeader={tr("Месяц")} labels={MONTHS_SHORT} shortLabels={TICKS}
          values={s.expenses_by_month.map(Number)} />
        <section className="card">
          <h2 className="card__title">{tr("Доход по видам")}</h2>
          <BarList label={tr("Доход по видам продукции")} unit={cur} empty={tr("Продаж за период нет")}
            rows={s.income_by_category.map((x) => ({ key: x.key, label: x.label, value: Number(x.amount) }))} />
        </section>
        <section className="card">
          <h2 className="card__title">{tr("Расход по категориям")}</h2>
          <BarList label={tr("Расход по категориям")} unit={cur} empty={tr("Расходов за период нет")}
            rows={s.expenses_by_category.map((x) => ({ key: x.key, label: x.label, value: Number(x.amount) }))} />
        </section>
      </>}

      <Sheet open={sheet === 'sale'} title={tr("Новая продажа")} onClose={close}>{sheet === 'sale' && <SaleForm onDone={(x) => { close(); navigate(`/crm/sales/${x.id}`) }} />}</Sheet>
      <Sheet open={sheet === 'expense'} title={tr("Новый расход")} onClose={close}>{sheet === 'expense' && <ExpenseForm onDone={close} />}</Sheet>
      <Sheet open={sheet === 'order'} title={tr("Новый заказ")} onClose={close}>{sheet === 'order' && <OrderForm onDone={(o) => { close(); navigate(`/crm/orders/${o.id}`) }} />}</Sheet>
      <Sheet open={sheet === 'customer'} title={tr("Новый клиент")} onClose={close}>{sheet === 'customer' && <CustomerForm onDone={(c) => { close(); navigate(`/crm/customers/${c.id}`) }} />}</Sheet>
    </div>
  )
}
