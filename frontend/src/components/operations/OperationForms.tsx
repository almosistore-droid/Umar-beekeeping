import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiariesApi, harvestApi, hivesApi, operationsApi, queensApi } from '../../api/resources'
import type { FamilyStrength, Hive, WinteringResult } from '../../types/api'
import { HONEY_TYPES, STRENGTH, WINTERING_RESULT, num, todayIso } from '../../utils/labels'
import { Choice, ErrorBox, Field, Select, Stepper, SubmitButton, fieldError } from '../ui'
import { useHiveRecordMutation } from '../health/useHiveRecordMutation'
import { tr } from '../../i18n'

const strengthOpts = (Object.keys(STRENGTH) as FamilyStrength[]).map((k) => ({ value: k, label: STRENGTH[k].label }))
const decimal = (v: string) => (v.trim() === '' ? null : Number(v.replace(',', '.')))

// ---------- honey ----------

export function HoneyForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const [weight, setWeight] = useState('')
  const [frames, setFrames] = useState(4)
  const [type, setType] = useState<string | null>(null)
  const [price, setPrice] = useState('')
  const [date, setDate] = useState(todayIso())
  const save = useHiveRecordMutation(hive, async () => {
    await harvestApi.harvest(hive.id, {
      weight_kg: decimal(weight) ?? 0, frames_count: frames, honey_type: type, price_per_kg: decimal(price), harvest_date: date,
    })
    return hive
  }, onDone)
  const w = decimal(weight), p = decimal(price)
  const value = w && p ? w * p : null

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Field label={tr("Вес, кг")} error={fieldError(save.error, 'weight_kg')}>
        <input className="input input--big" inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="0" required autoFocus />
      </Field>
      <Stepper label={tr("Рамок откачано")} value={frames} max={500} onChange={setFrames} />
      <Choice label={tr("Мёд")} options={HONEY_TYPES.map((t) => ({ value: t, label: t }))} value={type} onChange={setType} allowNone />
      <Field label={tr("Цена за кг")} error={fieldError(save.error, 'price_per_kg')} hint={value ? tr("Сумма: {0}", num(value)) : tr("Можно не указывать")}>
        <input className="input" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
      </Field>
      <Field label={tr("Дата откачки")} error={fieldError(save.error, 'harvest_date')}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Записать мёд")}</SubmitButton></div>
    </form>
  )
}

// ---------- move ----------

export function MoveForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const apiaries = useQuery({ queryKey: ['apiaries'], queryFn: () => apiariesApi.list() })
  const others = (apiaries.data ?? []).filter((a) => a.id !== hive.apiary.id)
  const [to, setTo] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [number, setNumber] = useState('')
  const [date, setDate] = useState(todayIso())
  const save = useHiveRecordMutation(hive, () => operationsApi.move(hive.id, {
    to_apiary_id: to!, reason: reason || null, new_hive_number: number || null, movement_date: date,
  }), onDone)
  const needsNumber = save.error && /новый номер/.test(String((save.error as Error).message))

  if (apiaries.data && !others.length) return <p className="hint">{tr("Нет другой пасеки. Сначала создайте её в разделе «Пасеки».")}</p>
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); if (to) save.mutate() }}>
      <ErrorBox error={save.error} />
      <Choice label={tr("Куда")} options={others.map((a) => ({ value: a.id, label: a.name }))} value={to} onChange={setTo} />
      <Field label={tr("Причина")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder={tr("Например: кочёвка на акацию")} maxLength={255} /></Field>
      <Field label={tr("Новый номер улья")} hint={needsNumber ? tr("Номер занят на той пасеке — укажите другой") : tr("Если оставить пустым, номер не изменится")}>
        <input className="input" value={number} onChange={(e) => setNumber(e.target.value)} placeholder={hive.hive_number} maxLength={20} />
      </Field>
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{to ? tr("Переместить") : tr("Выберите пасеку")}</SubmitButton></div>
    </form>
  )
}

// ---------- helpers for "new or empty hive" targets ----------

function useEmptyHives(apiaryId: string) {
  return useQuery({ queryKey: ['hives', 'empty', apiaryId], queryFn: () => hivesApi.list({ apiary_id: apiaryId, status: ['EMPTY'] }) })
}
function useFreeQueens() {
  return useQuery({ queryKey: ['queens', 'free'], queryFn: () => queensApi.list({ in_hive: false }) })
}

function TargetPicker({ apiaryId, mode, setMode, number, setNumber, emptyId, setEmptyId }: {
  apiaryId: string; mode: 'new' | 'empty'; setMode: (m: 'new' | 'empty') => void
  number: string; setNumber: (v: string) => void; emptyId: string; setEmptyId: (v: string) => void
}) {
  const empty = useEmptyHives(apiaryId)
  return <>
    <Choice label={tr("Куда")} options={[{ value: 'new', label: tr("Новый улей") }, { value: 'empty', label: tr("Пустой улей") }]} value={mode} onChange={(v) => v && setMode(v as 'new' | 'empty')} />
    {mode === 'new' ? (
      <Field label={tr("Номер нового улья")}><input className="input" value={number} onChange={(e) => setNumber(e.target.value)} required maxLength={20} /></Field>
    ) : (
      <Field label={tr("Пустой улей")} hint={empty.data?.items.length ? undefined : tr("Пустых ульев на этой пасеке нет")}>
        <Select value={emptyId} onChange={setEmptyId} placeholder={tr("— выберите —")} options={(empty.data?.items ?? []).map((h) => ({ value: h.id, label: `№${h.hive_number}` }))} />
      </Field>
    )}
  </>
}

// ---------- swarm ----------

export function SwarmForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const navigate = useNavigate()
  const [count, setCount] = useState(1)
  const [captured, setCaptured] = useState(true)
  const [settle, setSettle] = useState(true)
  const [mode, setMode] = useState<'new' | 'empty'>('new')
  const [number, setNumber] = useState('')
  const [emptyId, setEmptyId] = useState('')
  const [actions, setActions] = useState('')
  const [date, setDate] = useState(todayIso())
  const save = useHiveRecordMutation(hive, () => operationsApi.swarm(hive.id, {
    swarm_count: count, captured, swarm_date: date, actions: actions || null,
    new_hive_number: captured && settle && mode === 'new' ? number : null,
    settle_into_hive_id: captured && settle && mode === 'empty' ? emptyId || null : null,
  }), (res) => { onDone(); if (res.new_hive) navigate(`/hives/${res.new_hive.id}`) })

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Stepper label={tr("Сколько роёв")} value={count} min={1} max={20} onChange={setCount} />
      <Choice label={tr("Рой")} options={[{ value: true, label: tr("Пойман") }, { value: false, label: tr("Улетел") }]} value={captured} onChange={(v) => setCaptured(v ?? false)} />
      {captured && <>
        <label className="switch"><input type="checkbox" checked={settle} onChange={(e) => setSettle(e.target.checked)} /><span>{tr("Посадить в улей")}</span></label>
        {settle && <TargetPicker apiaryId={hive.apiary.id} mode={mode} setMode={setMode} number={number} setNumber={setNumber} emptyId={emptyId} setEmptyId={setEmptyId} />}
      </>}
      <Field label={tr("Что сделали")}><textarea className="input" rows={2} value={actions} onChange={(e) => setActions(e.target.value)} placeholder={tr("Например: снят с яблони, посажен на вощину")} /></Field>
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Записать роение")}</SubmitButton></div>
    </form>
  )
}

// ---------- split ----------

export function SplitForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const navigate = useNavigate()
  const queens = useFreeQueens()
  const [mode, setMode] = useState<'new' | 'empty'>('new')
  const [number, setNumber] = useState('')
  const [emptyId, setEmptyId] = useState('')
  const [queenId, setQueenId] = useState('')
  const [strength, setStrength] = useState<FamilyStrength>('WEAK')
  const [date, setDate] = useState(todayIso())
  const save = useHiveRecordMutation(hive, async () => {
    const r = await operationsApi.split(hive.id, {
      split_date: date, strength, queen_id: queenId || null,
      new_hive_number: mode === 'new' ? number : null, target_hive_id: mode === 'empty' ? emptyId || null : null,
    })
    return { hive: r.source, newHive: r.new_hive }
  }, (res) => { onDone(); navigate(`/hives/${res.newHive.id}`) })

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <p className="hint">{tr("Из улья №{0} будет сделан отводок. Исходный улей продолжит жить.", hive.hive_number)}</p>
      <TargetPicker apiaryId={hive.apiary.id} mode={mode} setMode={setMode} number={number} setNumber={setNumber} emptyId={emptyId} setEmptyId={setEmptyId} />
      <Choice label={tr("Сила отводка")} options={strengthOpts} value={strength} onChange={(v) => v && setStrength(v)} />
      <Field label={tr("Матка")} hint={tr("Если не выбрать, отводок будет отмечен «Без матки»")}>
        <Select value={queenId} onChange={setQueenId} placeholder={tr("— выведут сами —")}
          options={(queens.data?.items ?? []).map((q) => ({ value: q.id, label: `${q.queen_code}${q.breed ? `, ${q.breed}` : ''}` }))} />
      </Field>
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Сделать отводок")}</SubmitButton></div>
    </form>
  )
}

// ---------- merge ----------

export function MergeForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const navigate = useNavigate()
  const hives = useQuery({ queryKey: ['hives', 'merge', hive.apiary.id], queryFn: () => hivesApi.list({ apiary_id: hive.apiary.id }) })
  const candidates = (hives.data?.items ?? []).filter((h) => h.id !== hive.id && h.strength)
  const [others, setOthers] = useState<string[]>([])
  const [target, setTarget] = useState<string>(hive.id) // a source id or "new"
  const [number, setNumber] = useState('')
  const [keepQueen, setKeepQueen] = useState<string>('')
  const [date, setDate] = useState(todayIso())
  const sources = [hive.id, ...others]
  const queenOptions = [
    ...(hive.current_queen ? [{ value: hive.current_queen.id, label: tr("{0} (улей №{1})", hive.current_queen.queen_code, hive.hive_number) }] : []),
    ...candidates.filter((c) => others.includes(c.id) && c.queen_id).map((c) => ({ value: c.queen_id!, label: tr("{0} (улей №{1})", c.queen_code, c.hive_number) })),
  ]

  const save = useHiveRecordMutation(hive, async () => {
    const t = await operationsApi.merge({
      source_hive_ids: sources, target_hive_id: target === 'new' ? null : target, new_hive_number: target === 'new' ? number : null,
      keep_queen_id: keepQueen || null, merge_date: date,
    })
    return { hive: t.id === hive.id ? t : { ...hive, status: 'MERGED' as const, is_archived: true }, target: t }
  }, (res) => { onDone(); if (res.target.id !== hive.id) navigate(`/hives/${res.target.id}`) })

  const toggle = (id: string) => setOthers((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); if (others.length) save.mutate() }}>
      <ErrorBox error={save.error} />
      <span className="field__label">{tr("С какими ульями объединить улей №{0}", hive.hive_number)}</span>
      <div className="pills">
        {candidates.map((c) => (
          <button key={c.id} type="button" className={`pill${others.includes(c.id) ? ' is-active' : ''}`} onClick={() => toggle(c.id)}>№{c.hive_number}</button>
        ))}
        {!candidates.length && <span className="hint">{tr("На этой пасеке нет других ульев с семьёй")}</span>}
      </div>
      {others.length > 0 && <>
        <Choice label={tr("Куда объединить")} value={target} onChange={(v) => v && setTarget(v)}
          options={[...sources.map((id) => ({ value: id, label: `№${id === hive.id ? hive.hive_number : candidates.find((c) => c.id === id)?.hive_number}` })), { value: 'new', label: tr("В новый улей") }]} />
        {target === 'new' && <Field label={tr("Номер нового улья")}><input className="input" value={number} onChange={(e) => setNumber(e.target.value)} required maxLength={20} /></Field>}
        <Field label={tr("Какую матку оставить")} hint={tr("Остальные будут отмечены «Заменена»")}>
          <Select value={keepQueen} onChange={setKeepQueen} placeholder={tr("— не важно / нет маток —")} options={queenOptions} />
        </Field>
        <div className="warn-box">{tr("Остальные ульи уйдут в архив «Объединён». Их история сохранится.")}</div>
      </>}
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger={others.length > 0}>{others.length ? tr("Объединить") : tr("Выберите ульи")}</SubmitButton></div>
    </form>
  )
}

// ---------- wintering ----------

function defaultSeason(): string {
  const d = new Date()
  const y = d.getMonth() >= 6 ? d.getFullYear() : d.getFullYear() - 1
  return `${y}/${y + 1}`
}

export function WinteringForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const list = useQuery({ queryKey: ['hive-winterings', hive.id], queryFn: () => operationsApi.winterings(hive.id) })
  const open = list.data?.find((w) => !w.end_date)
  if (list.isLoading) return <p className="hint">{tr("Загрузка…")}</p>
  return open ? <FinishWintering hive={hive} id={open.id} season={open.season} onDone={onDone} /> : <StartWintering hive={hive} onDone={onDone} />
}

function StartWintering({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const [season, setSeason] = useState(defaultSeason())
  const [strength, setStrength] = useState<FamilyStrength>(hive.current_family?.strength ?? 'MEDIUM')
  const [food, setFood] = useState('')
  const [frames, setFrames] = useState(8)
  const [treatment, setTreatment] = useState('')
  const [location, setLocation] = useState('')
  const save = useHiveRecordMutation(hive, async () => {
    await operationsApi.startWintering(hive.id, { season, pre_winter_strength: strength, food_kg: decimal(food), frames_count: frames,
      pre_winter_treatment: treatment || null, winter_location: location || null })
    return hive
  }, onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Field label={tr("Сезон")} error={fieldError(save.error, 'season')}><input className="input" value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2026/2027" /></Field>
      <Choice label={tr("Сила перед зимой")} options={strengthOpts} value={strength} onChange={(v) => v && setStrength(v)} />
      <Field label={tr("Корма, кг")}><input className="input" inputMode="decimal" value={food} onChange={(e) => setFood(e.target.value)} /></Field>
      <Stepper label={tr("Рамок")} value={frames} onChange={setFrames} />
      <Field label={tr("Обработка перед зимой")}><input className="input" value={treatment} onChange={(e) => setTreatment(e.target.value)} maxLength={255} /></Field>
      <Field label={tr("Где зимует")}><input className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder={tr("На точке, в зимовнике…")} maxLength={255} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Начать зимовку")}</SubmitButton></div>
    </form>
  )
}

function FinishWintering({ hive, id, season, onDone }: { hive: Hive; id: string; season: string; onDone: () => void }) {
  const [result, setResult] = useState<WinteringResult | null>(null)
  const [strength, setStrength] = useState<FamilyStrength | null>(null)
  const [date, setDate] = useState(todayIso())
  const save = useHiveRecordMutation(hive, () => operationsApi.finishWintering(id, { result: result!, spring_strength: strength, end_date: date }), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); if (result) save.mutate() }}>
      <ErrorBox error={save.error} />
      <p className="hint">{tr("Улей зимует, сезон {0}. Отметьте, как прошла зимовка.", season)}</p>
      <Choice label={tr("Итог")} options={(Object.keys(WINTERING_RESULT) as WinteringResult[]).map((k) => ({ value: k, label: WINTERING_RESULT[k] }))} value={result} onChange={setResult} />
      {result === 'DIED' && <div className="warn-box">{tr("Семья будет отмечена погибшей, улей станет пустым. История сохранится.")}</div>}
      {result && result !== 'DIED' && <Choice label={tr("Сила весной")} options={strengthOpts} value={strength} onChange={setStrength} allowNone />}
      <Field label={tr("Дата окончания")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger={result === 'DIED'}>{result ? tr("Завершить зимовку") : tr("Выберите итог")}</SubmitButton></div>
    </form>
  )
}
