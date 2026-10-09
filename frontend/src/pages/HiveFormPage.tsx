import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiariesApi, hivesApi, queensApi } from '../api/resources'
import { ErrorBox, Field, Select, SubmitButton, fieldError } from '../components/ui'
import { LoadingView } from '../components/StateViews'
import { haptic } from '../services/telegram'
import type { FamilyOrigin, FamilyStrength, HiveStatus, HiveType } from '../types/api'
import { EDITABLE_HIVE_STATUSES, FAMILY_ORIGIN, HIVE_STATUS, HIVE_TYPE, STRENGTH, todayIso } from '../utils/labels'

const opts = <T extends string>(rec: Record<T, string>) => (Object.keys(rec) as T[]).map((k) => ({ value: k, label: rec[k] }))
const strengthOpts = (Object.keys(STRENGTH) as FamilyStrength[]).map((k) => ({ value: k, label: STRENGTH[k].label }))

export function HiveFormPage() {
  const { id } = useParams()
  return id ? <EditHive id={id} /> : <CreateHive />
}

function CreateHive() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [params] = useSearchParams()
  const apiaries = useQuery({ queryKey: ['apiaries'], queryFn: () => apiariesApi.list() })
  const freeQueens = useQuery({ queryKey: ['queens', 'free'], queryFn: () => queensApi.list({ in_hive: false }) })

  const [apiaryId, setApiaryId] = useState(params.get('apiary') ?? '')
  const [number, setNumber] = useState('')
  const [type, setType] = useState<HiveType>('DADANT')
  const [populated, setPopulated] = useState(true)
  const [strength, setStrength] = useState<FamilyStrength>('MEDIUM')
  const [origin, setOrigin] = useState<FamilyOrigin>('OWN')
  const [startDate, setStartDate] = useState(todayIso())
  const [queenId, setQueenId] = useState('')
  const [installDate, setInstallDate] = useState(todayIso())
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (!apiaryId && apiaries.data?.length) setApiaryId(apiaries.data[0].id)
  }, [apiaries.data, apiaryId])

  const create = useMutation({
    mutationFn: () => hivesApi.create({
      apiary_id: apiaryId, hive_number: number, hive_type: type, installation_date: installDate, notes: notes || null,
      family: populated ? { strength, origin, start_date: startDate } : null,
      queen_id: populated && queenId ? queenId : null,
    }),
    onSuccess: (hive) => {
      haptic('success')
      qc.invalidateQueries({ queryKey: ['hives'] })
      qc.invalidateQueries({ queryKey: ['queens'] })
      qc.invalidateQueries({ queryKey: ['apiaries'] })
      navigate(`/hives/${hive.id}`, { replace: true })
    },
    onError: () => haptic('error'),
  })

  if (apiaries.isLoading) return <LoadingView />
  const submit = (e: FormEvent) => { e.preventDefault(); create.mutate() }

  return (
    <form className="page form" onSubmit={submit}>
      <h1 className="page__title">Новый улей</h1>
      <ErrorBox error={create.error} />
      <section className="card">
        <Field label="Пасека" error={fieldError(create.error, 'apiary_id')}>
          <Select value={apiaryId} onChange={setApiaryId} options={(apiaries.data ?? []).map((a) => ({ value: a.id, label: a.name }))} />
        </Field>
        <Field label="Номер улья" error={fieldError(create.error, 'hive_number')} hint="Например 27 или А-12">
          <input className="input" inputMode="text" value={number} onChange={(e) => setNumber(e.target.value)} required maxLength={20} autoFocus />
        </Field>
        <Field label="Тип улья">
          <Select value={type} onChange={setType} options={opts(HIVE_TYPE)} />
        </Field>
        <Field label="Дата установки" error={fieldError(create.error, 'installation_date')}>
          <input className="input" type="date" value={installDate} max={todayIso()} onChange={(e) => setInstallDate(e.target.value)} />
        </Field>
      </section>

      <section className="card">
        <label className="switch">
          <input type="checkbox" checked={populated} onChange={(e) => setPopulated(e.target.checked)} />
          <span>🐝 В улье живёт семья</span>
        </label>
        {populated && <>
          <Field label="Сила семьи"><Select value={strength} onChange={setStrength} options={strengthOpts} /></Field>
          <Field label="Происхождение"><Select value={origin} onChange={setOrigin} options={opts(FAMILY_ORIGIN)} /></Field>
          <Field label="Дата заселения" error={fieldError(create.error, 'start_date')}>
            <input className="input" type="date" value={startDate} max={todayIso()} onChange={(e) => setStartDate(e.target.value)} />
          </Field>
          <Field label="Матка" hint={freeQueens.data?.items.length ? 'Свободные матки из реестра' : 'Свободных маток нет — можно добавить позже'}>
            <Select value={queenId} onChange={setQueenId} placeholder="— не указывать —"
              options={(freeQueens.data?.items ?? []).map((q) => ({ value: q.id, label: `${q.queen_code}${q.age_label ? ` · ${q.age_label}` : ''}` }))} />
          </Field>
        </>}
      </section>

      <section className="card">
        <Field label="Заметки">
          <textarea className="input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={5000} />
        </Field>
      </section>
      <div className="submit-bar"><SubmitButton pending={create.isPending}>Создать улей</SubmitButton></div>
    </form>
  )
}

function EditHive({ id }: { id: string }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const hive = useQuery({ queryKey: ['hive', id], queryFn: () => hivesApi.get(id) })
  const [form, setForm] = useState<{ number: string; type: HiveType; status: HiveStatus; installation: string; notes: string; comment: string } | null>(null)

  useEffect(() => {
    if (hive.data && !form) {
      const h = hive.data
      setForm({ number: h.hive_number, type: h.hive_type, status: h.status, installation: h.installation_date ?? '', notes: h.notes ?? '', comment: '' })
    }
  }, [hive.data, form])

  const save = useMutation({
    mutationFn: () => {
      const h = hive.data!, f = form!
      return hivesApi.update(id, {
        version: h.version,
        ...(f.number !== h.hive_number && { hive_number: f.number }),
        ...(f.type !== h.hive_type && { hive_type: f.type }),
        ...(f.status !== h.status && { status: f.status }),
        ...(f.installation !== (h.installation_date ?? '') && { installation_date: f.installation || null }),
        ...(f.notes !== (h.notes ?? '') && { notes: f.notes || null }),
        comment: f.comment || null,
      })
    },
    onSuccess: (updated) => {
      haptic('success')
      qc.setQueryData(['hive', id], updated)
      qc.invalidateQueries({ queryKey: ['hives'] })
      qc.invalidateQueries({ queryKey: ['hive-history', id] })
      navigate(-1)
    },
    onError: () => haptic('error'),
  })

  if (hive.isLoading || !form) return <LoadingView />
  const set = (patch: Partial<typeof form>) => setForm({ ...form, ...patch })
  const archiving = (form.status === 'SOLD' || form.status === 'LOST') && form.status !== hive.data?.status

  return (
    <form className="page form" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <h1 className="page__title">Улей №{hive.data?.hive_number}</h1>
      <ErrorBox error={save.error} />
      <section className="card">
        <Field label="Номер улья" error={fieldError(save.error, 'hive_number')} hint="QR-код не изменится">
          <input className="input" value={form.number} onChange={(e) => set({ number: e.target.value })} required maxLength={20} />
        </Field>
        <Field label="Тип улья"><Select value={form.type} onChange={(v) => set({ type: v })} options={opts(HIVE_TYPE)} /></Field>
        <Field label="Статус">
          <Select value={form.status} onChange={(v) => set({ status: v })}
            options={EDITABLE_HIVE_STATUSES.map((s) => ({ value: s, label: `${HIVE_STATUS[s].icon} ${HIVE_STATUS[s].label}` }))} />
        </Field>
        {archiving && <div className="warn-box">Улей уйдёт в архив. Семья и матка будут отмечены как {form.status === 'SOLD' ? 'проданные' : 'погибшие'}. История сохранится.</div>}
        <Field label="Дата установки">
          <input className="input" type="date" value={form.installation} max={todayIso()} onChange={(e) => set({ installation: e.target.value })} />
        </Field>
        <Field label="Заметки">
          <textarea className="input" rows={3} value={form.notes} onChange={(e) => set({ notes: e.target.value })} />
        </Field>
        <Field label="Комментарий к изменению" hint="Попадёт в историю улья">
          <input className="input" value={form.comment} onChange={(e) => set({ comment: e.target.value })} maxLength={1000} />
        </Field>
      </section>
      <div className="submit-bar"><SubmitButton pending={save.isPending} danger={archiving}>Сохранить</SubmitButton></div>
    </form>
  )
}
