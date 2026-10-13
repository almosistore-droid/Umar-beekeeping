import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { healthApi, hivesApi, type InspectionInput } from '../../api/resources'
import { haptic } from '../../services/telegram'
import type { FamilyStrength, FoodLevel, Hive, InspectionHealth, QueenCondition, RecordWarning } from '../../types/api'
import { FOOD_LEVEL, INSPECTION_HEALTH, QUEEN_CONDITION, STRENGTH, addDaysIso, formatDate, todayIso } from '../../utils/labels'
import { Choice, ErrorBox, Field, Stepper, SubmitButton } from '../ui'
import { useHiveRecordMutation } from './useHiveRecordMutation'

const strengthOpts = (Object.keys(STRENGTH) as FamilyStrength[]).map((k) => ({ value: k, label: STRENGTH[k].label }))
const foodOpts = (Object.keys(FOOD_LEVEL) as FoodLevel[]).map((k) => ({ value: k, label: FOOD_LEVEL[k] }))
const healthOpts = (Object.keys(INSPECTION_HEALTH) as InspectionHealth[]).map((k) => ({ value: k, label: INSPECTION_HEALTH[k] }))
const seenOpts = [{ value: true, label: 'Видна' }, { value: false, label: 'Не найдена' }]
const eggOpts = [{ value: true, label: 'Есть' }, { value: false, label: 'Нет' }]
const conditionOpts = (Object.keys(QUEEN_CONDITION) as QueenCondition[]).map((k) => ({ value: k, label: QUEEN_CONDITION[k] }))
const yesNo = [{ value: true, label: 'Да' }, { value: false, label: 'Нет' }]
const NEXT = [3, 7, 14]

/** Past days are stored at noon UTC so they stay on the same calendar day in any time zone. */
const dayToInstant = (day: string) => (day === todayIso() ? null : `${day}T12:00:00Z`)

/**
 * Inspection at the hive: only taps (chips and steppers), prefilled from the previous inspection,
 * so the beekeeper can save in one tap. Every save is a separate dated inspection record.
 * `doneActions`: always show the «saved» screen with these buttons (field flow after a QR scan).
 */
export function InspectionForm({ hive, onDone, doneActions }: { hive: Hive; onDone: () => void; doneActions?: ReactNode }) {
  const previous = useQuery({ queryKey: ['hive-inspections', hive.id], queryFn: () => healthApi.inspections(hive.id) })
  const [f, setF] = useState<InspectionInput>({
    strength: hive.current_family?.strength ?? 'MEDIUM', frames_total: 10, brood_frames: 0, honey_frames: 0,
    pollen_frames: 0, queen_present: null, egg_laying: null, queen_cells: 0, swarming_signs: false,
    food_level: null, aggressiveness: null, health_status: 'HEALTHY', next_inspection_at: addDaysIso(7), notes: null,
  })
  const [prefilled, setPrefilled] = useState(false)
  const [warnings, setWarnings] = useState<RecordWarning[] | null>(null)
  const [day, setDay] = useState(todayIso())

  useEffect(() => {
    const last = previous.data?.[0]
    if (last && !prefilled) {
      setF((s) => ({ ...s, frames_total: last.frames_total, brood_frames: last.brood_frames, honey_frames: last.honey_frames, pollen_frames: last.pollen_frames }))
      setPrefilled(true)
    }
  }, [previous.data, prefilled])

  const save = useHiveRecordMutation(hive, () => healthApi.inspect(hive.id, { ...f, inspected_at: dayToInstant(day) }), (res) => {
    if (res.warnings.length || doneActions) setWarnings(res.warnings)
    else onDone()
  })
  const markQueenless = useHiveRecordMutation(hive, () => hivesApi.update(hive.id, { status: 'QUEENLESS', comment: 'По результатам осмотра' }), onDone)

  const set = (patch: Partial<InspectionInput>) => setF((s) => ({ ...s, ...patch }))
  const used = f.brood_frames + f.honey_frames + f.pollen_frames
  const overflow = used > f.frames_total

  if (warnings) {
    const canMarkQueenless = warnings.some((w) => w.code === 'possible_queenless') && !hive.current_queen && hive.status !== 'QUEENLESS'
    return (
      <div className="form">
        <div className="result-ok"><span className="result-ok__mark" aria-hidden>✓</span><b>Осмотр сохранён</b>
          <span className="hint small">{day === todayIso() ? 'Сегодня' : formatDate(day)}, улей №{hive.hive_number}</span></div>
        {warnings.map((w) => <div key={w.code} className="warn-box">{w.message}</div>)}
        <ErrorBox error={markQueenless.error} />
        {canMarkQueenless && (
          <button type="button" className="btn btn--secondary btn--block" disabled={markQueenless.isPending} onClick={() => markQueenless.mutate(undefined)}>
            Отметить «Без матки»
          </button>
        )}
        {doneActions ?? <button type="button" className="btn btn--primary btn--block" onClick={onDone}>Готово</button>}
      </div>
    )
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (overflow) { haptic('error'); return }
    save.mutate(undefined)
  }

  return (
    <form className="form" onSubmit={submit}>
      <ErrorBox error={save.error} />
      <Choice label="Дата осмотра" value={day === todayIso() ? 'today' : day === addDaysIso(-1) ? 'yesterday' : null}
        options={[{ value: 'today', label: 'Сегодня' }, { value: 'yesterday', label: 'Вчера' }]}
        onChange={(v) => v && setDay(v === 'today' ? todayIso() : addDaysIso(-1))} />
      {day !== todayIso() && day !== addDaysIso(-1) && <p className="hint small">Дата: {formatDate(day)}</p>}
      <input className="input" type="date" aria-label="Другая дата осмотра" max={todayIso()} value={day}
        onChange={(e) => e.target.value && setDay(e.target.value)} />
      <Choice label="Сила семьи" options={strengthOpts} value={f.strength} onChange={(v) => v && set({ strength: v })} />

      <span className="form-section-title">Рамки</span>
      <div className="frames-grid">
        <Stepper label="Всего" value={f.frames_total} onChange={(v) => set({ frames_total: v })} />
        <Stepper label="Расплод" value={f.brood_frames} onChange={(v) => set({ brood_frames: v })} />
        <Stepper label="Мёд" value={f.honey_frames} onChange={(v) => set({ honey_frames: v })} />
        <Stepper label="Перга" value={f.pollen_frames} onChange={(v) => set({ pollen_frames: v })} />
      </div>
      <p className={`frames-note${overflow ? ' is-bad' : ''}`} role={overflow ? 'alert' : undefined}>
        {overflow ? `Занято ${used} из ${f.frames_total} — больше, чем всего рамок` : `Занято ${used} из ${f.frames_total}`}
      </p>

      <span className="form-section-title">Матка</span>
      <Choice label="Матка" options={seenOpts} value={f.queen_present}
        onChange={(v) => set({ queen_present: v, queen_condition: v === false ? 'NOT_SEEN' : v ? f.queen_condition === 'NOT_SEEN' ? null : f.queen_condition : null })} allowNone />
      {f.queen_present && (
        <Choice label="Состояние матки" options={conditionOpts.filter((o) => o.value !== 'NOT_SEEN')} value={f.queen_condition ?? null}
          onChange={(v) => set({ queen_condition: v })} allowNone />
      )}
      <Choice label="Яйца" options={eggOpts} value={f.egg_laying} onChange={(v) => set({ egg_laying: v })} allowNone />
      <Stepper label="Маточники" value={f.queen_cells} max={100} onChange={(v) => set({ queen_cells: v })} />
      <Choice label="Признаки роения" options={yesNo} value={f.swarming_signs} onChange={(v) => v !== null && set({ swarming_signs: v })} />

      <span className="form-section-title">Состояние</span>
      <Choice label="Корм" options={foodOpts} value={f.food_level} onChange={(v) => set({ food_level: v })} allowNone />
      <Choice label="Агрессивность (1 — спокойные)" value={f.aggressiveness === null ? null : String(f.aggressiveness)}
        options={['1', '2', '3', '4', '5'].map((v) => ({ value: v, label: v }))}
        onChange={(v) => set({ aggressiveness: v === null ? null : Number(v) })} allowNone />
      <Choice label="Здоровье" options={healthOpts} value={f.health_status} onChange={(v) => v && set({ health_status: v })} />

      <span className="form-section-title">Следующий осмотр</span>
      <div className="pills">
        {NEXT.map((d) => (
          <button key={d} type="button" className={`pill${f.next_inspection_at === addDaysIso(d) ? ' is-active' : ''}`}
            onClick={() => set({ next_inspection_at: addDaysIso(d) })}>через {d} дн.</button>
        ))}
      </div>
      <input className="input" type="date" aria-label="Дата следующего осмотра" min={todayIso()}
        value={f.next_inspection_at ?? ''} onChange={(e) => set({ next_inspection_at: e.target.value || null })} />

      <Field label="Заметки" hint="Можно не заполнять">
        <textarea className="input" rows={2} value={f.notes ?? ''} onChange={(e) => set({ notes: e.target.value || null })} maxLength={5000} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Сохранить осмотр</SubmitButton></div>
    </form>
  )
}
