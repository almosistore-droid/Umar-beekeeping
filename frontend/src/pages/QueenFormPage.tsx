import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { hivesApi, queensApi, type QueenInput } from '../api/resources'
import { ErrorBox, Field, Select, SubmitButton, fieldError } from '../components/ui'
import { LoadingView } from '../components/StateViews'
import { haptic } from '../services/telegram'
import type { QueenOrigin, QueenStatus } from '../types/api'
import { ACTIVE_QUEEN_STATUSES, MARKING, QUEEN_ORIGIN, QUEEN_STATUS, todayIso } from '../utils/labels'

const BREEDS = ['Карника', 'Карпатка', 'Бакфаст', 'Среднерусская', 'Кавказская', 'Итальянская']
const originOpts = (Object.keys(QUEEN_ORIGIN) as QueenOrigin[]).map((k) => ({ value: k, label: QUEEN_ORIGIN[k] }))
const statusOpts = ACTIVE_QUEEN_STATUSES.map((s) => ({ value: s, label: QUEEN_STATUS[s].label }))
const markingOpts = Object.entries(MARKING).map(([k, v]) => ({ value: k, label: v.label }))

interface FormState {
  code: string; birthMode: 'date' | 'year'; birthDate: string; birthYear: string; breed: string
  origin: QueenOrigin; status: QueenStatus; egg: string; swarm: string; temper: string; marking: string; notes: string
}

const empty: FormState = {
  code: '', birthMode: 'date', birthDate: '', birthYear: '', breed: '', origin: 'UNKNOWN', status: 'ACTIVE',
  egg: '', swarm: '', temper: '', marking: '', notes: '',
}

function Score({ value, onChange, label, hint }: { value: string; onChange: (v: string) => void; label: string; hint: string }) {
  return (
    <Field label={label} hint={hint}>
      <div className="score">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" className={String(n) === value ? 'is-active' : ''}
            onClick={() => onChange(String(n) === value ? '' : String(n))}>{n}</button>
        ))}
      </div>
    </Field>
  )
}

export function QueenFormPage() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const hiveId = params.get('hive')
  const navigate = useNavigate()
  const qc = useQueryClient()
  const existing = useQuery({ queryKey: ['queen', id], queryFn: () => queensApi.get(id!), enabled: !!id })
  const targetHive = useQuery({ queryKey: ['hive', hiveId], queryFn: () => hivesApi.get(hiveId!), enabled: !!hiveId })
  const [f, setF] = useState<FormState | null>(id ? null : empty)
  const [installDate, setInstallDate] = useState(todayIso())

  useEffect(() => {
    const q = existing.data
    if (q && !f) setF({
      code: q.queen_code, birthMode: q.birth_date || !q.birth_year ? 'date' : 'year', birthDate: q.birth_date ?? '',
      birthYear: q.birth_year ? String(q.birth_year) : '', breed: q.breed ?? '', origin: q.origin, status: q.status,
      egg: q.egg_laying_quality ? String(q.egg_laying_quality) : '', swarm: q.swarming_tendency ? String(q.swarming_tendency) : '',
      temper: q.temperament ? String(q.temperament) : '', marking: q.marking_color ?? '', notes: q.notes ?? '',
    })
  }, [existing.data, f])

  const save = useMutation({
    mutationFn: () => {
      const s = f!
      const num = (v: string) => (v ? Number(v) : null)
      const body: QueenInput = {
        queen_code: s.code,
        birth_date: s.birthMode === 'date' ? s.birthDate || null : null,
        birth_year: s.birthMode === 'year' ? num(s.birthYear) : s.birthDate ? Number(s.birthDate.slice(0, 4)) : null,
        breed: s.breed || null, origin: s.origin, status: s.status,
        egg_laying_quality: num(s.egg), swarming_tendency: num(s.swarm), temperament: num(s.temper),
        marking_color: s.marking || null, notes: s.notes || null,
      }
      if (id) return queensApi.update(id, body)
      return queensApi.create({ ...body, hive_id: hiveId, installed_at: hiveId ? installDate : null })
    },
    onSuccess: (queen) => {
      haptic('success')
      qc.invalidateQueries({ queryKey: ['queens'] })
      qc.invalidateQueries({ queryKey: ['queen', queen.id] })
      if (hiveId) {
        for (const k of ['hive', 'hives', 'hive-history', 'hive-queens']) qc.invalidateQueries({ queryKey: [k] })
        navigate(`/hives/${hiveId}`, { replace: true })
      } else navigate(`/queens/${queen.id}`, { replace: true })
    },
    onError: () => haptic('error'),
  })

  if (!f) return <LoadingView />
  const set = (p: Partial<FormState>) => setF({ ...f, ...p })
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate() }
  const removed = id && existing.data && !ACTIVE_QUEEN_STATUSES.includes(existing.data.status)

  return (
    <form className="page form" onSubmit={submit}>
      <h1 className="page__title">{id ? `Матка ${existing.data?.queen_code}` : 'Новая матка'}</h1>
      {targetHive.data && <p className="hint">Будет подсажена в улей №{targetHive.data.hive_number}</p>}
      <ErrorBox error={save.error} />
      <section className="card">
        <Field label="Код матки" error={fieldError(save.error, 'queen_code')} hint="Например M-105">
          <input className="input" value={f.code} onChange={(e) => set({ code: e.target.value })} required maxLength={40} autoFocus={!id} />
        </Field>
        <div className="segmented">
          <button type="button" className={f.birthMode === 'date' ? 'is-active' : ''} onClick={() => set({ birthMode: 'date' })}>Дата рождения</button>
          <button type="button" className={f.birthMode === 'year' ? 'is-active' : ''} onClick={() => set({ birthMode: 'year' })}>Только год</button>
        </div>
        {f.birthMode === 'date' ? (
          <Field label="Дата рождения" error={fieldError(save.error, 'birth_date')}>
            <input className="input" type="date" value={f.birthDate} max={todayIso()} onChange={(e) => set({ birthDate: e.target.value })} />
          </Field>
        ) : (
          <Field label="Год рождения" error={fieldError(save.error, 'birth_year')}>
            <input className="input" type="number" inputMode="numeric" min={1990} max={new Date().getFullYear()} value={f.birthYear} onChange={(e) => set({ birthYear: e.target.value })} />
          </Field>
        )}
        <Field label="Порода">
          <input className="input" list="breeds" value={f.breed} onChange={(e) => set({ breed: e.target.value })} maxLength={80} />
          <datalist id="breeds">{BREEDS.map((b) => <option key={b} value={b} />)}</datalist>
        </Field>
        <Field label="Происхождение"><Select value={f.origin} onChange={(v) => set({ origin: v })} options={originOpts} /></Field>
        {!removed && <Field label="Состояние"><Select value={f.status} onChange={(v) => set({ status: v })} options={statusOpts} /></Field>}
        <Field label="Метка" hint="Если не выбрать — цвет подставится по году рождения">
          <Select value={f.marking} onChange={(v) => set({ marking: v })} options={markingOpts} placeholder="— авто —" />
        </Field>
      </section>
      <section className="card">
        <h2 className="card__title">Оценка (1–5)</h2>
        <Score label="Яйценоскость" hint="5 — отличная" value={f.egg} onChange={(v) => set({ egg: v })} />
        <Score label="Ройливость" hint="5 — очень ройливая" value={f.swarm} onChange={(v) => set({ swarm: v })} />
        <Score label="Миролюбие" hint="5 — очень спокойная" value={f.temper} onChange={(v) => set({ temper: v })} />
      </section>
      {hiveId && (
        <section className="card">
          <Field label="Дата подсадки"><input className="input" type="date" value={installDate} max={todayIso()} onChange={(e) => setInstallDate(e.target.value)} /></Field>
        </section>
      )}
      <section className="card">
        <Field label="Заметки"><textarea className="input" rows={3} value={f.notes} onChange={(e) => set({ notes: e.target.value })} /></Field>
      </section>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{id ? 'Сохранить' : 'Добавить матку'}</SubmitButton></div>
    </form>
  )
}
