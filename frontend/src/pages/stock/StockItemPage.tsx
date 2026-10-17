import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { stockApi } from '../../api/resources'
import { CancelStockForm, ItemForm, MovementForm, useStockMutation, type MoveKind } from '../../components/stock/forms'
import { Icon } from '../../components/Icon'
import { LoadingView } from '../../components/StateViews'
import { ErrorBox, Sheet } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import type { StockMovement } from '../../types/api'
import { MOVEMENT_KIND, STOCK_CATEGORY, formatDate, qty } from '../../utils/labels'
import { tr } from '../../i18n'

const MANUAL = new Set(['RECEIPT', 'CONSUMPTION', 'INVENTORY'])

export function StockItemPage() {
  const { id = '' } = useParams()
  const { canWrite, canManage } = usePermissions()
  const data = useQuery({ queryKey: ['stock-item', id], queryFn: () => stockApi.item(id) })
  const [moving, setMoving] = useState<MoveKind | null>(null)
  const [editing, setEditing] = useState(false)
  const [cancelling, setCancelling] = useState<StockMovement | null>(null)
  const archive = useStockMutation((v: boolean) => (v ? stockApi.archive(id) : stockApi.restore(id)), () => undefined)
  if (data.isLoading) return <LoadingView />
  if (!data.data) return <div className="page"><ErrorBox error={data.error} /></div>
  const { item, movements } = data.data
  const title = moving === 'RECEIPT' ? tr("Приход") : moving === 'CONSUMPTION' ? tr("Расход") : tr("Пересчёт")
  return (
    <div className="page">
      <h1 className="page__title">{item.name}</h1>
      <ErrorBox error={archive.error} />
      <section className="card">
        <div className={`stock-row${item.low ? ' stock-row--low' : ''}`}>
          <span className="stock-row__main">
            <span className="hint small">{STOCK_CATEGORY[item.category]}{item.is_archived ? ` · ${tr("в архиве")}` : ''}</span>
            {item.min_quantity != null && <span className="hint small">{tr("Минимум {0}", qty(item.min_quantity, item.unit))}</span>}
          </span>
          <span className="stock-row__qty" style={{ fontSize: 30 }}>{qty(item.quantity, item.unit)}</span>
        </div>
        {item.notes && <p className="hint small">{item.notes}</p>}
        {!item.is_archived && canWrite && (
          <div className="stock-actions">
            <button type="button" className="btn btn--primary" onClick={() => setMoving('RECEIPT')}>{tr("＋ Приход")}</button>
            <button type="button" className="btn btn--secondary" onClick={() => setMoving('CONSUMPTION')}>{tr("− Расход")}</button>
            {canManage && <button type="button" className="btn btn--ghost" onClick={() => setMoving('INVENTORY')}>{tr("Пересчёт")}</button>}
            {canManage && <button type="button" className="btn btn--ghost" onClick={() => setEditing(true)}><Icon name="edit" size={16} />{tr("Изменить")}</button>}
          </div>
        )}
        {canManage && !item.code && (
          <button type="button" className="btn btn--ghost btn--block" disabled={archive.isPending}
            onClick={() => archive.mutate(!item.is_archived)}>
            {item.is_archived ? tr("Вернуть из архива") : tr("Убрать в архив")}
          </button>
        )}
      </section>
      <section className="card card--list">
        <h2 className="card__title">{tr("Движение")}</h2>
        {!movements.length && <p className="hint">{tr("Записей пока нет. Начните с прихода.")}</p>}
        {movements.map((m) => {
          const canCancel = canManage && !m.cancelled_at && (MANUAL.has(m.kind) || m.frame_prep_id)
          const body = <>
            <span className="stock-row__main">
              <b>{MOVEMENT_KIND[m.kind]}{m.hive_number ? ` · ${tr("улей №{0}", m.hive_number)}` : ''}</b>
              <span className="small hint">
                {formatDate(m.moved_at)}{m.note && m.kind !== 'FEEDING' && m.kind !== 'TREATMENT' ? ` · ${m.note}` : ''}
                {m.author_name ? ` · ${m.author_name}` : ''}{m.cancelled_at ? ` · ${tr("отменено")}` : ''}
              </span>
            </span>
            <span className="stock-row__qty" style={{ fontSize: 17 }}>{Number(m.quantity) > 0 ? '+' : ''}{qty(m.quantity, item.unit)}</span>
          </>
          const cls = `stock-row${m.cancelled_at ? ' stock-row--cancelled' : ''}`
          if (canCancel) return <button key={m.id} type="button" className={cls} onClick={() => setCancelling(m)}>{body}</button>
          if (m.hive_id) return <Link key={m.id} to={`/hives/${m.hive_id}`} className={cls}>{body}</Link>
          return <div key={m.id} className={cls}>{body}</div>
        })}
      </section>
      <Sheet open={moving !== null} title={title} onClose={() => setMoving(null)}>
        {moving && <MovementForm item={item} kind={moving} onDone={() => setMoving(null)} />}
      </Sheet>
      <Sheet open={editing} title={tr("Позиция склада")} onClose={() => setEditing(false)}>
        {editing && <ItemForm item={item} onDone={() => setEditing(false)} />}
      </Sheet>
      <Sheet open={cancelling !== null} title={cancelling?.frame_prep_id ? tr("Отменить подготовку рамок") : tr("Отменить запись")}
        onClose={() => setCancelling(null)}>
        {cancelling && (cancelling.frame_prep_id
          ? <CancelStockForm text={tr("Отменится вся подготовка: проволока, вощина и рамки вернутся на склад. Запись останется в истории с пометкой «отменено».")}
              cancel={(r) => stockApi.cancelFramePrep(cancelling.frame_prep_id!, r)} onDone={() => setCancelling(null)} />
          : <CancelStockForm text={tr("Запись не удаляется: она останется в истории с пометкой «отменено» и не будет учитываться в остатке.")}
              cancel={(r) => stockApi.cancelMovement(cancelling.id, r)} onDone={() => setCancelling(null)} />)}
      </Sheet>
    </div>
  )
}
