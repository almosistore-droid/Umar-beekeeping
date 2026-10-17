import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { stockApi } from '../../api/resources'
import { FramePrepForm, ItemForm } from '../../components/stock/forms'
import { Icon } from '../../components/Icon'
import { LoadingView } from '../../components/StateViews'
import { ErrorBox, Sheet } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import type { FramePrepResult, StockCategory, StockItem } from '../../types/api'
import { STOCK_CATEGORY, num, qty } from '../../utils/labels'
import { tr } from '../../i18n'

const ORDER: StockCategory[] = ['FRAMES', 'FEED', 'MEDICINE', 'OTHER']

export function StockRow({ item }: { item: StockItem }) {
  return (
    <Link to={`/stock/${item.id}`} className={`stock-row${item.low ? ' stock-row--low' : ''}`}>
      <span className="stock-row__main">
        <b>{item.name}</b>
        {item.low ? <span className="small" style={{ color: 'var(--ember)' }}>
          {Number(item.quantity) < 0 ? tr("Не хватает — запишите приход") : tr("Меньше минимума ({0})", qty(item.min_quantity ?? 0, item.unit))}
        </span> : item.min_quantity != null && <span className="small hint">{tr("Минимум {0}", qty(item.min_quantity, item.unit))}</span>}
      </span>
      <span className="stock-row__qty">{qty(item.quantity, item.unit)}</span>
    </Link>
  )
}

export function StockPage() {
  const { canWrite, canManage } = usePermissions()
  const [archived, setArchived] = useState(false)
  const [adding, setAdding] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const [prepared, setPrepared] = useState<FramePrepResult | null>(null)
  const data = useQuery({ queryKey: ['stock', archived], queryFn: () => stockApi.overview(archived) })
  const items = data.data?.items ?? []
  const low = items.filter((i) => i.low)
  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Склад")}</h1>
        {canManage && <button className="btn btn--primary btn--sm" onClick={() => setAdding(true)}>{tr("＋ Позиция")}</button>}
      </div>
      <ErrorBox error={data.error} />
      <div className="stock-actions">
        {canWrite && (
          <button type="button" className="btn btn--secondary" onClick={() => { setPrepared(null); setPreparing(true) }}>
            <Icon name="hive" size={18} />{tr("Подготовить рамки")}
          </button>
        )}
        <Link to="/stock/norms" className="btn btn--ghost"><Icon name="edit" size={18} />{tr("Нормы расхода")}</Link>
      </div>
      {prepared && (
        <div className="ok-box small" role="status">
          <b>{tr("Подготовлено рамок: {0}", prepared.prep.frames)}</b>
          {prepared.lines.map((l) => (
            <div key={l.item_id}>{l.name}: {Number(l.quantity) > 0 ? '+' : ''}{qty(l.quantity, l.unit)} · {tr("осталось {0}", qty(l.balance_after, l.unit))}</div>
          ))}
        </div>
      )}
      {data.isLoading ? <LoadingView /> : <>
        {low.length > 0 && !archived && (
          <p className="warn-box small">{tr("Заканчивается: {0}", low.map((i) => i.name).join(', '))}</p>
        )}
        {!archived && (
          <Link to="/honey" className="card stock-honey">
            <span className="stock-row">
              <span className="stock-row__main"><b>{tr("Мёд")}</b><span className="small hint">{tr("Собрано − продано − скормлено пчёлам")}</span></span>
              <span className="stock-row__qty">{tr("{0} кг", num(data.data?.honey_kg ?? 0))}</span>
            </span>
          </Link>
        )}
        {ORDER.map((cat) => {
          const list = items.filter((i) => i.category === cat && i.is_archived === archived)
          if (!list.length) return null
          return (
            <section key={cat} className="card card--list">
              <h2 className="card__title">{STOCK_CATEGORY[cat]}</h2>
              {list.map((i) => <StockRow key={i.id} item={i} />)}
            </section>
          )
        })}
        {archived && !items.some((i) => i.is_archived) && <p className="hint">{tr("В архиве пусто.")}</p>}
        <button type="button" className="btn btn--ghost btn--block" onClick={() => setArchived(!archived)}>
          {archived ? tr("← Склад") : tr("Архив склада")}
        </button>
      </>}
      <Sheet open={preparing} title={tr("Подготовка рамок")} onClose={() => setPreparing(false)}>
        {preparing && <FramePrepForm onDone={(r) => { setPreparing(false); setPrepared(r) }} />}
      </Sheet>
      <Sheet open={adding} title={tr("Новая позиция склада")} onClose={() => setAdding(false)}>
        {adding && <ItemForm onDone={() => setAdding(false)} />}
      </Sheet>
    </div>
  )
}
