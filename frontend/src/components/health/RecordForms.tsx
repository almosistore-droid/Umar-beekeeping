import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { healthApi, stockApi } from '../../api/resources'
import type { CaseStatus, DiseaseSeverity, FeedType, FeedUnit, Hive } from '../../types/api'
import { CASE_STATUS, FEED_TYPE, FEED_UNIT, SEVERITY, addDaysIso, qty as qtyText, STOCK_UNIT, todayIso } from '../../utils/labels'
import { feedingNeed } from '../../utils/stock'
import { Choice, ErrorBox, Field, SubmitButton, fieldError } from '../ui'
import { useHiveRecordMutation } from './useHiveRecordMutation'
import { tr } from '../../i18n'

const severityOpts = (Object.keys(SEVERITY) as DiseaseSeverity[]).map((k) => ({ value: k, label: SEVERITY[k] }))
const openStatusOpts = (['SUSPECTED', 'CONFIRMED', 'TREATING'] as CaseStatus[]).map((k) => ({ value: k, label: CASE_STATUS[k].label }))
const feedOpts = (Object.keys(FEED_TYPE) as FeedType[]).map((k) => ({ value: k, label: FEED_TYPE[k] }))
const unitOpts = (Object.keys(FEED_UNIT) as FeedUnit[]).map((k) => ({ value: k, label: FEED_UNIT[k] }))
const MEDICATIONS = [tr("Бипин"), tr("Апитак"), tr("Апивароль"), tr("Полоски с амитразом"), tr("Щавелевая кислота"), tr("Муравьиная кислота"), tr("Нозематом"), tr("Фумагиллин")]
const METHODS = [tr("Полив"), tr("Окуривание"), tr("Полоски"), tr("Испарение"), tr("С подкормкой"), tr("Опрыскивание")]

function NextDate({ label, value, onChange, from, presets }: {
  label: string; value: string | null; onChange: (v: string | null) => void; from: string; presets: number[]
}) {
  const base = new Date(`${from}T00:00:00`)
  return (
    <div className="choice-field">
      <span className="field__label">{label}</span>
      <div className="pills">
        <button type="button" className={`pill${value === null ? ' is-active' : ''}`} onClick={() => onChange(null)}>{tr("Не нужна")}</button>
        {presets.map((d) => {
          const iso = addDaysIso(d, base)
          return <button key={d} type="button" className={`pill${value === iso ? ' is-active' : ''}`} onClick={() => onChange(iso)}>{tr("через {0} дн.", d)}</button>
        })}
      </div>
      <input className="input" type="date" aria-label={label} min={from} value={value ?? ''} onChange={(e) => onChange(e.target.value || null)} />
    </div>
  )
}

// ---------- disease case ----------

export function DiseaseForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const diseases = useQuery({ queryKey: ['diseases'], queryFn: healthApi.diseases, staleTime: 5 * 60_000 })
  const [diseaseId, setDiseaseId] = useState<string | null>(null)
  const [status, setStatus] = useState<CaseStatus>('CONFIRMED')
  const [severity, setSeverity] = useState<DiseaseSeverity>('MODERATE')
  const [detected, setDetected] = useState(todayIso())
  const [symptoms, setSymptoms] = useState('')
  const save = useHiveRecordMutation(hive, () => healthApi.openCase(hive.id, {
    disease_id: diseaseId!, status, severity, detected_at: detected, symptoms: symptoms || null,
  }), onDone)
  const chosen = diseases.data?.find((d) => d.id === diseaseId)

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); if (diseaseId) save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Choice label={tr("Болезнь")} options={(diseases.data ?? []).map((d) => ({ value: d.id, label: d.name }))}
        value={diseaseId} onChange={setDiseaseId} />
      {chosen?.is_quarantine && <div className="warn-box">{tr("Карантинная болезнь: при подтверждении улей будет отмечен «Карантин».")}</div>}
      <Choice label={tr("Статус")} options={openStatusOpts} value={status} onChange={(v) => v && setStatus(v)} />
      <Choice label={tr("Тяжесть")} options={severityOpts} value={severity} onChange={(v) => v && setSeverity(v)} />
      <Field label={tr("Дата обнаружения")} error={fieldError(save.error, 'detected_at')}>
        <input className="input" type="date" value={detected} max={todayIso()} onChange={(e) => setDetected(e.target.value)} />
      </Field>
      <Field label={tr("Симптомы")}>
        <textarea className="input" rows={2} value={symptoms} onChange={(e) => setSymptoms(e.target.value)} placeholder={tr("Что заметили")} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{diseaseId ? tr("Записать болезнь") : tr("Выберите болезнь")}</SubmitButton></div>
    </form>
  )
}

// ---------- treatment ----------

export function TreatmentForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const cases = useQuery({ queryKey: ['hive-cases', hive.id], queryFn: () => healthApi.cases(hive.id) })
  const diseases = useQuery({ queryKey: ['diseases'], queryFn: healthApi.diseases, staleTime: 5 * 60_000 })
  const openCases = (cases.data ?? []).filter((c) => c.status !== 'RESOLVED')
  const [target, setTarget] = useState<string | null>(null) // "case:<id>" | "disease:<id>" | null
  const [date, setDate] = useState(todayIso())
  const [medication, setMedication] = useState('')
  const [dosage, setDosage] = useState('')
  const [method, setMethod] = useState<string | null>(null)
  const [result, setResult] = useState('')
  const [next, setNext] = useState<string | null>(null)
  const stock = useQuery({ queryKey: ['stock'], queryFn: () => stockApi.overview() })
  const medicines = (stock.data?.items ?? []).filter((i) => i.category === 'MEDICINE' || i.category === 'OTHER')
  const [stockItem, setStockItem] = useState('')
  const [stockQty, setStockQty] = useState('')
  const picked = medicines.find((i) => i.id === stockItem)

  const save = useHiveRecordMutation(hive, () => healthApi.treat(hive.id, {
    treated_at: date, medication, dosage: dosage || null, method, result: result || null, next_treatment_date: next,
    hive_disease_id: target?.startsWith('case:') ? target.slice(5) : null,
    disease_id: target?.startsWith('disease:') ? target.slice(8) : null,
    stock_item_id: picked ? picked.id : null,
    stock_quantity: picked ? Number(stockQty.replace(',', '.')) : null,
  }), onDone)

  const targetOpts = [
    ...openCases.map((c) => ({ value: `case:${c.id}`, label: `${c.disease.name} (${CASE_STATUS[c.status].label.toLowerCase()})` })),
    ...(diseases.data ?? []).filter((d) => !openCases.some((c) => c.disease.id === d.id))
      .map((d) => ({ value: `disease:${d.id}`, label: d.name })),
  ]

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Choice label={tr("От чего")} options={targetOpts} value={target} onChange={setTarget} allowNone />
      <Field label={tr("Препарат")} error={fieldError(save.error, 'medication')}>
        <input className="input" list="medications" value={medication} onChange={(e) => setMedication(e.target.value)} required maxLength={120} />
        <datalist id="medications">{MEDICATIONS.map((m) => <option key={m} value={m} />)}</datalist>
      </Field>
      {medicines.some((i) => i.category === 'MEDICINE') && (
        <Field label={tr("Списать со склада")} error={fieldError(save.error, 'stock_quantity')}
          hint={picked ? tr("На складе: {0}", qtyText(picked.quantity, picked.unit)) : undefined}>
          <select className="input" value={stockItem} aria-label={tr("Препарат со склада")} onChange={(e) => {
            setStockItem(e.target.value)
            const item = medicines.find((i) => i.id === e.target.value)
            if (item && !medication.trim()) setMedication(item.name)
          }}>
            <option value="">{tr("Не списывать")}</option>
            {medicines.map((i) => <option key={i.id} value={i.id}>{i.name} · {qtyText(i.quantity, i.unit)}</option>)}
          </select>
          {picked && (
            <div className="input-unit">
              <input className="input" inputMode="decimal" value={stockQty} required aria-label={tr("Сколько списать")}
                placeholder={tr("Сколько")} onChange={(e) => setStockQty(e.target.value)} />
              <span>{STOCK_UNIT[picked.unit]}</span>
            </div>
          )}
        </Field>
      )}
      <Field label={tr("Доза")}><input className="input" value={dosage} onChange={(e) => setDosage(e.target.value)} maxLength={120} placeholder={tr("Например: 1 мл на улочку")} /></Field>
      <Choice label={tr("Способ")} options={METHODS.map((m) => ({ value: m, label: m }))} value={method} onChange={setMethod} allowNone />
      <Field label={tr("Дата обработки")} error={fieldError(save.error, 'treated_at')}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <NextDate label={tr("Повторная обработка")} value={next} onChange={setNext} from={date} presets={[7, 14, 21]} />
      <Field label={tr("Результат")}><input className="input" value={result} onChange={(e) => setResult(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Записать обработку")}</SubmitButton></div>
    </form>
  )
}

// ---------- feeding ----------

export function FeedingForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const [type, setType] = useState<FeedType>('SUGAR_SYRUP')
  const [qty, setQty] = useState('2')
  const [unit, setUnit] = useState<FeedUnit>('L')
  const [date, setDate] = useState(todayIso())
  const [reason, setReason] = useState('')
  const [next, setNext] = useState<string | null>(null)
  const stock = useQuery({ queryKey: ['stock'], queryFn: () => stockApi.overview() })
  const amount = Number(qty.replace(',', '.'))
  const need = stock.data ? feedingNeed(stock.data.norms, type, amount, unit) : null
  const needItem = need ? stock.data?.items.find((i) => i.code === need.code) : undefined
  const save = useHiveRecordMutation(hive, () => healthApi.feed(hive.id, {
    feed_type: type, quantity: Number(qty.replace(',', '.')), unit, fed_at: date, reason: reason || null, next_feeding_date: next,
  }), onDone)

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Choice label={tr("Корм")} options={feedOpts} value={type} onChange={(v) => {
        if (!v) return
        setType(v)
        setUnit(v === 'SUGAR_SYRUP' || v === 'MEDICATED' ? 'L' : 'KG')
      }} />
      <div className="input-group">
        <Field label={tr("Количество")} error={fieldError(save.error, 'quantity')}>
          <input className="input" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} required />
        </Field>
      </div>
      <Choice label={tr("Единица")} options={unitOpts} value={unit} onChange={(v) => v && setUnit(v)} />
      {need && needItem && (() => {
        const left = Number(needItem.quantity) - need.quantity
        return (
          <p className={`${left < 0 ? 'warn-box' : 'ok-box'} small`} role="status">
            {tr("Со склада спишется: {0} {1}", needItem.name, qtyText(need.quantity, needItem.unit))}{" · "}
            {left < 0 ? tr("на складе только {0}", qtyText(needItem.quantity, needItem.unit))
              : tr("останется {0}", qtyText(left, needItem.unit))}
          </p>
        )
      })()}
      {type === 'HONEY' && amount > 0 && (unit === 'KG' || unit === 'G') && (
        <p className="hint small">{tr("Мёд спишется из запаса мёда на складе.")}</p>
      )}
      <Field label={tr("Дата")} error={fieldError(save.error, 'fed_at')}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <Field label={tr("Причина")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder={tr("Например: весенняя стимуляция")} maxLength={255} /></Field>
      <NextDate label={tr("Следующая подкормка")} value={next} onChange={setNext} from={date} presets={[3, 7, 14]} />
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Записать подкормку")}</SubmitButton></div>
    </form>
  )
}
