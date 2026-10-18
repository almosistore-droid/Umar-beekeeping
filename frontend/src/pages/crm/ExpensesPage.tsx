import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { crmApi } from '../../api/resources'
import { CancelForm, ExpenseForm, useCurrency } from '../../components/crm/forms'
import { PeriodChips, currentPeriod, type Period } from '../../components/crm/rows'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { ErrorBox, Sheet } from '../../components/ui'
import type { Expense } from '../../types/api'
import { EXPENSE_CATEGORY, formatDate, money } from '../../utils/labels'
import { tr } from '../../i18n'

export function ExpensesPage() {
  const currency = useCurrency()
  const [period, setPeriod] = useState<Period>(currentPeriod())
  const [editing, setEditing] = useState<Expense | 'new' | null>(null)
  const [cancelling, setCancelling] = useState<Expense | null>(null)
  const list = useQuery({ queryKey: ['crm-expenses', period.year, period.month], queryFn: () => crmApi.expenses(period) })
  const total = (list.data ?? []).reduce((s, x) => s + Number(x.amount), 0)
  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Расходы")}</h1>
        <button className="btn btn--primary btn--sm" onClick={() => setEditing('new')}>{tr("＋ Расход")}</button>
      </div>
      <PeriodChips value={period} onChange={setPeriod} />
      <ErrorBox error={list.error} />
      {list.isLoading ? <LoadingView /> : !list.data?.length ? (
        <MessageView icon="receipt" title={tr("Расходов нет")} text={tr("Корм, лекарства, вощина, топливо — записывайте всё, чтобы видеть прибыль.")} />
      ) : <>
        <p className="hint">{tr("{0} · всего {1}", list.data.length, money(total, currency))}</p>
        <section className="card card--list">
          {list.data.map((e) => (
            <button key={e.id} type="button" className="crm-row" onClick={() => setEditing(e)}>
              <span className="crm-row__icon" aria-hidden><Icon name="receipt" size={18} /></span>
              <span className="crm-row__main">
                <b>{EXPENSE_CATEGORY[e.category]}</b>
                <span className="small hint">{formatDate(e.expense_date)}{e.description ? ` · ${e.description}` : ''}</span>
              </span>
              <span className="crm-row__side"><b>{money(e.amount, currency)}</b></span>
            </button>
          ))}
        </section>
      </>}
      <Sheet open={editing !== null} title={editing === 'new' ? tr("Новый расход") : tr("Расход")} onClose={() => setEditing(null)}>
        {editing && <>
          <ExpenseForm expense={editing === 'new' ? undefined : editing} onDone={() => setEditing(null)} />
          {editing !== 'new' && editing.stock_item_id && (
            <Link className="btn btn--ghost btn--block" to={`/stock/${editing.stock_item_id}`}>
              {tr("Создан приходом на склад — открыть склад")}
            </Link>
          )}
          {editing !== 'new' && !editing.stock_item_id && (
            <button type="button" className="btn btn--ghost btn--block" onClick={() => { setCancelling(editing); setEditing(null) }}>{tr("Отменить расход")}</button>
          )}
        </>}
      </Sheet>
      <Sheet open={cancelling !== null} title={tr("Отменить расход")} onClose={() => setCancelling(null)}>
        {cancelling && <CancelForm what={tr("Расход")} cancel={(r) => crmApi.cancelExpense(cancelling.id, r)} onDone={() => setCancelling(null)} />}
      </Sheet>
    </div>
  )
}
