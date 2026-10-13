import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiariesApi, harvestApi, hivesApi, operationsApi, queensApi } from '../../api/resources'
import type { FamilyStrength, Hive, WinteringResult } from '../../types/api'
import { HONEY_TYPES, STRENGTH, WINTERING_RESULT, num, todayIso } from '../../utils/labels'
import { Choice, ErrorBox, Field, Select, Stepper, SubmitButton, fieldError } from '../ui'
import { useHiveRecordMutation } from '../health/useHiveRecordMutation'

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
      <Field label="Вес, кг" error={fieldError(save.error, 'weight_kg')}>
        <input className="input input--big" inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} placeholder="0" required autoFocus />
      </Field>
      <Stepper label="Рамок откачано" value={frames} max={500} onChange={setFrames} />
      <Choice label="Мёд" options={HONEY_TYPES.map((t) => ({ value: t, label: t }))} value={type} onChange={setType} allowNone />
      <Field label="Цена за кг" error={fieldError(save.error, 'price_per_kg')} hint={value ? `Сумма: ${num(value)}` : 'Можно не указывать'}>
        <input className="input" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
      </Field>
      <Field label="Дата откачки" error={fieldError(save.error, 'harvest_date')}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Записать мёд</SubmitButton></div>
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

  if (apiaries.data && !others.length) return <p className="hint">Нет другой пасеки. Сначала создайте её в разделе «Пасеки».</p>
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); if (to) save.mutate() }}>
      <ErrorBox error={save.error} />
      <Choice label="Куда" options={others.map((a) => ({ value: a.id, label: a.name }))} value={to} onChange={setTo} />
      <Field label="Причина"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Например: кочёвка на акацию" maxLength={255} /></Field>
      <Field label="Новый номер улья" hint={needsNumber ? 'Номер занят на той пасеке — укажите другой' : 'Если оставить пустым, номер не изменится'}>
        <input className="input" value={number} onChange={(e) => setNumber(e.target.value)} placeholder={hive.hive_number} maxLength={20} />
      </Field>
      <Field label="Дата"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{to ? 'Переместить' : 'Выберите пасеку'}</SubmitButton></div>
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
    <Choice label="Куда" options={[{ value: 'new', label: 'Новый улей' }, { value: 'empty', label: 'Пустой улей' }]} value={mode} onChange={(v) => v && setMode(v as 'new' | 'empty')} />
    {mode === 'new' ? (
      <Field label="Номер нового улья"><input className="input" value={number} onChange={(e) => setNumber(e.target.value)} required maxLength={20} /></Field>
    ) : (
      <Field label="Пустой улей" hint={empty.data?.items.length ? undefined : 'Пустых ульев на этой пасеке нет'}>
        <Select value={emptyId} onChange={setEmptyId} placeholder="— выберите —" options={(empty.data?.items ?? []).map((h) => ({ value: h.id, label: `№${h.hive_number}` }))} />
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
      <Stepper label="Сколько роёв" value={count} min={1} max={20} onChange={setCount} />
      <Choice label="Рой" options={[{ value: true, label: 'Пойман' }, { value: false, label: 'Улетел' }]} value={captured} onChange={(v) => setCaptured(v ?? false)} />
      {captured && <>
        <label className="switch"><input type="checkbox" checked={settle} onChange={(e) => setSettle(e.target.checked)} /><span>Посадить в улей</span></label>
        {settle && <TargetPicker apiaryId={hive.apiary.id} mode={mode} setMode={setMode} number={number} setNumber={setNumber} emptyId={emptyId} setEmptyId={setEmptyId} />}
      </>}
      <Field label="Что сделали"><textarea className="input" rows={2} value={actions} onChange={(e) => setActions(e.target.value)} placeholder="Например: снят с яблони, посажен на вощину" /></Field>
      <Field label="Дата"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Записать роение</SubmitButton></div>
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
      <p className="hint">Из улья №{hive.hive_number} будет сделан отводок. Исходный улей продолжит жить.</p>
      <TargetPicker apiaryId={hive.apiary.id} mode={mode} setMode={setMode} number={number} setNumber={setNumber} emptyId={emptyId} setEmptyId={setEmptyId} />
      <Choice label="Сила отводка" options={strengthOpts} value={strength} onChange={(v) => v && setStrength(v)} />
      <Field label="Матка" hint="Если не выбрать, отводок будет отмечен «Без матки»">
        <Select value={queenId} onChange={setQueenId} placeholder="— выведут сами —"
          options={(queens.data?.items ?? []).map((q) => ({ value: q.id, label: `${q.queen_code}${q.breed ? `, ${q.breed}` : ''}` }))} />
      </Field>
      <Field label="Дата"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Сделать отводок</SubmitButton></div>
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
    ...(hive.current_queen ? [{ value: hive.current_queen.id, label: `${hive.current_queen.queen_code} (улей №${hive.hive_number})` }] : []),
    ...candidates.filter((c) => others.includes(c.id) && c.queen_id).map((c) => ({ value: c.queen_id!, label: `${c.queen_code} (улей №${c.hive_number})` })),
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
      <span className="field__label">С какими ульями объединить улей №{hive.hive_number}</span>
      <div className="pills">
        {candidates.map((c) => (
          <button key={c.id} type="button" className={`pill${others.includes(c.id) ? ' is-active' : ''}`} onClick={() => toggle(c.id)}>№{c.hive_number}</button>
        ))}
        {!candidates.length && <span className="hint">На этой пасеке нет других ульев с семьёй</span>}
      </div>
      {others.length > 0 && <>
        <Choice label="Куда объединить" value={target} onChange={(v) => v && setTarget(v)}
          options={[...sources.map((id) => ({ value: id, label: `№${id === hive.id ? hive.hive_number : candidates.find((c) => c.id === id)?.hive_number}` })), { value: 'new', label: 'В новый улей' }]} />
        {target === 'new' && <Field label="Номер нового улья"><input className="input" value={number} onChange={(e) => setNumber(e.target.value)} required maxLength={20} /></Field>}
        <Field label="Какую матку оставить" hint="Остальные будут отмечены «Заменена»">
          <Select value={keepQueen} onChange={setKeepQueen} placeholder="— не важно / нет маток —" options={queenOptions} />
        </Field>
        <div className="warn-box">Остальные ульи уйдут в архив «Объединён». Их история сохранится.</div>
      </>}
      <Field label="Дата"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger={others.length > 0}>{others.length ? 'Объединить' : 'Выберите ульи'}</SubmitButton></div>
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
  if (list.isLoading) return <p className="hint">Загрузка…</p>
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
      <Field label="Сезон" error={fieldError(save.error, 'season')}><input className="input" value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2026/2027" /></Field>
      <Choice label="Сила перед зимой" options={strengthOpts} value={strength} onChange={(v) => v && setStrength(v)} />
      <Field label="Корма, кг"><input className="input" inputMode="decimal" value={food} onChange={(e) => setFood(e.target.value)} /></Field>
      <Stepper label="Рамок" value={frames} onChange={setFrames} />
      <Field label="Обработка перед зимой"><input className="input" value={treatment} onChange={(e) => setTreatment(e.target.value)} maxLength={255} /></Field>
      <Field label="Где зимует"><input className="input" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="На точке, в зимовнике…" maxLength={255} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>Начать зимовку</SubmitButton></div>
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
      <p className="hint">Улей зимует, сезон {season}. Отметьте, как прошла зимовка.</p>
      <Choice label="Итог" options={(Object.keys(WINTERING_RESULT) as WinteringResult[]).map((k) => ({ value: k, label: WINTERING_RESULT[k] }))} value={result} onChange={setResult} />
      {result === 'DIED' && <div className="warn-box">Семья будет отмечена погибшей, улей станет пустым. История сохранится.</div>}
      {result && result !== 'DIED' && <Choice label="Сила весной" options={strengthOpts} value={strength} onChange={setStrength} allowNone />}
      <Field label="Дата окончания"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger={result === 'DIED'}>{result ? 'Завершить зимовку' : 'Выберите итог'}</SubmitButton></div>
    </form>
  )
}
