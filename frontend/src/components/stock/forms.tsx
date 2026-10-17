import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { stockApi, type MovementInput, type NormsInput } from '../../api/resources'
import type { FramePrepResult, StockCategory, StockItem, StockNorms, StockUnit } from '../../types/api'
import { STOCK_CATEGORY, STOCK_UNIT, qty, todayIso } from '../../utils/labels'
import { frameNeed } from '../../utils/stock'
import { haptic } from '../../services/telegram'
import { Choice, ErrorBox, Field, SubmitButton, fieldError } from '../ui'
import { tr } from '../../i18n'

export const parseQty = (v: string) => Number(v.replace(/\s/g, '').replace(',', '.'))
const opts = <T extends string>(rec: Record<T, string>) => (Object.keys(rec) as T[]).map((k) => ({ value: k, label: rec[k] }))

export function useStockMutation<T, R>(fn: (v: T) => Promise<R>, onDone: (r: R) => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => {
      haptic('success')
      for (const key of ['stock', 'stock-item', 'stock-preps', 'dashboard']) qc.invalidateQueries({ queryKey: [key] })
      onDone(r)
    },
    onError: () => haptic('error'),
  })
}

// ---------- receipt / use / inventory ----------

export type MoveKind = MovementInput['kind']

export function MovementForm({ item, kind, onDone }: { item: StockItem; kind: MoveKind; onDone: () => void }) {
  const [amount, setAmount] = useState(kind === 'INVENTORY' ? String(Number(item.quantity)) : '')
  const [date, setDate] = useState(todayIso())
  const [note, setNote] = useState('')
  const save = useStockMutation(
    () => stockApi.move(item.id, { kind, quantity: parseQty(amount), moved_at: date, note: note || null }), onDone)
  const unit = STOCK_UNIT[item.unit]
  const label = kind === 'RECEIPT' ? tr("Сколько пришло, {0}", unit)
    : kind === 'CONSUMPTION' ? tr("Сколько израсходовано, {0}", unit) : tr("Сколько есть на самом деле, {0}", unit)
  const n = parseQty(amount)
  const after = kind === 'RECEIPT' ? Number(item.quantity) + n : kind === 'CONSUMPTION' ? Number(item.quantity) - n : n
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <p className="hint">{tr("Сейчас на складе: {0}", qty(item.quantity, item.unit))}</p>
      <Field label={label} error={fieldError(save.error, 'quantity')}>
        <input className="input input--big" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)}
          required autoFocus />
      </Field>
      {amount && !Number.isNaN(n) && <p className="hint small">{tr("Станет: {0}", qty(after, item.unit))}</p>}
      <Field label={tr("Дата")} error={fieldError(save.error, 'moved_at')}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <Field label={tr("Заметка")} hint={kind === 'RECEIPT' ? tr("Например: куплено на базаре") : undefined}>
        <input className="input" value={note} maxLength={255} onChange={(e) => setNote(e.target.value)} />
      </Field>
      <div className="submit-bar">
        <SubmitButton pending={save.isPending}>
          {kind === 'RECEIPT' ? tr("Записать приход") : kind === 'CONSUMPTION' ? tr("Списать") : tr("Сохранить остаток")}
        </SubmitButton>
      </div>
    </form>
  )
}

// ---------- frames ----------

/** «Prepared N frames»: shows by the norms how much wire and foundation it takes, then writes it off. */
export function FramePrepForm({ onDone }: { onDone: (r: FramePrepResult) => void }) {
  const stock = useQuery({ queryKey: ['stock'], queryFn: () => stockApi.overview() })
  const [frames, setFrames] = useState('10')
  const [date, setDate] = useState(todayIso())
  const [notes, setNotes] = useState('')
  const n = Math.floor(parseQty(frames))
  const save = useStockMutation(() => stockApi.prepareFrames({ frames: n, prepared_at: date, notes: notes || null }), onDone)
  const data = stock.data
  const byCode = (code: string) => data?.items.find((i) => i.code === code)
  const need = data ? frameNeed(data.norms, n) : []
  const short = need.filter((x) => { const it = byCode(x.code); return it && Number(it.quantity) < x.quantity })
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error ?? stock.error} />
      <Field label={tr("Сколько рамок подготовлено")} error={fieldError(save.error, 'frames')}>
        <input className="input input--big" inputMode="numeric" value={frames} onChange={(e) => setFrames(e.target.value)} required />
      </Field>
      {data && (
        <div className="calc" aria-label={tr("Расчёт")}>
          <div className="calc__row hint small">
            <span>{tr("Норма на 1 рамку: {0} проволоки, {1} вощины",
              qty(data.norms.wire_m_per_frame, 'M'), qty(data.norms.foundation_g_per_frame, 'G'))}</span>
          </div>
          {need.map((x) => {
            const it = byCode(x.code)
            if (!it) return null
            const bad = Number(it.quantity) < x.quantity
            return (
              <div key={x.code} className={`calc__row${bad ? ' calc__row--bad' : ''}`}>
                <span>{it.name}</span>
                <b>{tr("−{0} (есть {1})", qty(x.quantity, x.unit), qty(it.quantity, it.unit))}</b>
              </div>
            )
          })}
          {n > 0 && byCode('frames_ready') && (
            <div className="calc__row"><span>{byCode('frames_ready')!.name}</span><b>+{qty(n, 'PCS')}</b></div>
          )}
        </div>
      )}
      {short.length > 0 && (
        <p className="warn-box small">{tr("На складе меньше, чем нужно — остаток станет отрицательным. Запишите приход, если материал уже куплен.")}</p>
      )}
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <Field label={tr("Заметка")}><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Списать на рамки")}</SubmitButton></div>
    </form>
  )
}

// ---------- item ----------

export function ItemForm({ item, onDone }: { item?: StockItem; onDone: (i: StockItem) => void }) {
  const [name, setName] = useState(item?.name ?? '')
  const [category, setCategory] = useState<StockCategory>(item?.category ?? 'MEDICINE')
  const [unit, setUnit] = useState<StockUnit>(item?.unit ?? 'PCS')
  const [min, setMin] = useState(item?.min_quantity != null ? String(Number(item.min_quantity)) : '')
  const [initial, setInitial] = useState('')
  const [notes, setNotes] = useState(item?.notes ?? '')
  const system = !!item?.code
  const body = {
    name, category, unit, min_quantity: min ? parseQty(min) : null, notes: notes || null,
    ...(item ? {} : { initial_quantity: initial ? parseQty(initial) : null }),
  }
  const save = useStockMutation(() => item ? stockApi.updateItem(item.id, body) : stockApi.createItem(body), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Field label={tr("Название")} error={fieldError(save.error, 'name')}>
        <input className="input" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} required
          placeholder={tr("Например: Бипин, банки 1 л, сетка")} />
      </Field>
      {system ? (
        <p className="hint small">{tr("Раздел и единица этой позиции не меняются: по ней считаются нормы.")}</p>
      ) : <>
        <Choice label={tr("Раздел")} options={opts(STOCK_CATEGORY)} value={category} onChange={(v) => v && setCategory(v)} />
        <Choice label={tr("Единица")} options={opts(STOCK_UNIT)} value={unit} onChange={(v) => v && setUnit(v)} />
      </>}
      <Field label={tr("Предупредить, когда меньше, {0}", STOCK_UNIT[unit])} error={fieldError(save.error, 'min_quantity')}
        hint={tr("Пусто — без предупреждения")}>
        <input className="input" inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value)} />
      </Field>
      {!item && (
        <Field label={tr("Сейчас есть, {0}", STOCK_UNIT[unit])} error={fieldError(save.error, 'initial_quantity')}>
          <input className="input" inputMode="decimal" value={initial} onChange={(e) => setInitial(e.target.value)} />
        </Field>
      )}
      <Field label={tr("Заметка")}><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{item ? tr("Сохранить") : tr("Добавить на склад")}</SubmitButton></div>
    </form>
  )
}

// ---------- norms ----------

const toInput = (n: StockNorms) => ({
  wire: String(Number(n.wire_m_per_frame)), foundation: String(Number(n.foundation_g_per_frame)),
  sugarL: String(Number(n.sugar_kg_per_l_syrup)), sugarKg: String(Number(n.sugar_kg_per_kg_syrup)),
})

export function NormsForm({ norms, canEdit, onDone }: { norms: StockNorms; canEdit: boolean; onDone: () => void }) {
  const [v, setV] = useState(toInput(norms))
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) => setV({ ...v, [k]: e.target.value })
  const body: NormsInput = {
    wire_m_per_frame: parseQty(v.wire), foundation_g_per_frame: parseQty(v.foundation),
    sugar_kg_per_l_syrup: parseQty(v.sugarL), sugar_kg_per_kg_syrup: parseQty(v.sugarKg),
  }
  const save = useStockMutation(() => stockApi.saveNorms(body), onDone)
  const frames10 = frameNeed({ ...norms, wire_m_per_frame: String(body.wire_m_per_frame), foundation_g_per_frame: String(body.foundation_g_per_frame) }, 10)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <h2 className="card__title">{tr("Подготовка рамок")}</h2>
      <Field label={tr("Проволока на 1 рамку, м")} error={fieldError(save.error, 'wire_m_per_frame')}>
        <input className="input" inputMode="decimal" value={v.wire} onChange={set('wire')} disabled={!canEdit} />
      </Field>
      <Field label={tr("Вощина на 1 рамку, г")} error={fieldError(save.error, 'foundation_g_per_frame')}
        hint={tr("Лист вощины для рамки Дадан ≈ 100–120 г, Рут ≈ 70–80 г")}>
        <input className="input" inputMode="decimal" value={v.foundation} onChange={set('foundation')} disabled={!canEdit} />
      </Field>
      {frames10.length > 0 && (
        <p className="hint small">{tr("На 10 рамок: {0} проволоки, {1} вощины",
          qty(frames10.find((x) => x.code === 'wire')?.quantity ?? 0, 'M'),
          qty(frames10.find((x) => x.code === 'foundation')?.quantity ?? 0, 'KG'))}</p>
      )}
      <h2 className="card__title">{tr("Корм")}</h2>
      <Field label={tr("Сахар на 1 л сиропа, кг")} error={fieldError(save.error, 'sugar_kg_per_l_syrup')}
        hint={tr("Сироп 1:1 ≈ 0,63 кг, 3:2 ≈ 0,8 кг, 2:1 ≈ 0,9 кг")}>
        <input className="input" inputMode="decimal" value={v.sugarL} onChange={set('sugarL')} disabled={!canEdit} />
      </Field>
      <Field label={tr("Сахар на 1 кг сиропа, кг")} error={fieldError(save.error, 'sugar_kg_per_kg_syrup')}
        hint={tr("Сироп 1:1 = 0,5 кг")}>
        <input className="input" inputMode="decimal" value={v.sugarKg} onChange={set('sugarKg')} disabled={!canEdit} />
      </Field>
      <p className="hint small">{tr("Канди и белковый корм списываются по весу подкормки, мёд — из запаса мёда. Лекарства — тем количеством, что указано в обработке.")}</p>
      {canEdit && <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Сохранить нормы")}</SubmitButton></div>}
    </form>
  )
}

// ---------- cancel ----------

export function CancelStockForm({ text, cancel, onDone }: { text: string; cancel: (reason: string) => Promise<unknown>; onDone: () => void }) {
  const [reason, setReason] = useState('')
  const save = useStockMutation(() => cancel(reason), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <p className="hint">{text}</p>
      <Field label={tr("Причина отмены")} error={fieldError(save.error, 'reason')}>
        <input className="input" value={reason} onChange={(e) => setReason(e.target.value)} required autoFocus />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger>{tr("Отменить")}</SubmitButton></div>
    </form>
  )
}
