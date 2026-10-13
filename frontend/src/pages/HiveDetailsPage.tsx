import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { hivesApi, queensApi } from '../api/resources'
import { Icon, type IconName } from '../components/Icon'
import { InspectionForm } from '../components/health/InspectionForm'
import { DiseaseForm, FeedingForm, TreatmentForm } from '../components/health/RecordForms'
import { OpenCasesCard, RemindersCard, Timeline } from '../components/health/HealthCards'
import { Badge, ErrorBox, Field, InfoRow, Select, Sheet, StrengthBars, SubmitButton } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import type { FamilyOrigin, FamilyStatus, FamilyStrength, Hive, QueenStatus } from '../types/api'
import {
  FAMILY_ORIGIN, FAMILY_STATUS, HIVE_STATUS, HIVE_TYPE, MARKING, QUEEN_STATUS,
  REMOVED_QUEEN_STATUSES, STRENGTH, formatDate, todayIso,
} from '../utils/labels'

type SheetKind = null | 'queen' | 'removeQueen' | 'family' | 'endFamily' | 'strength' | 'inspection' | 'disease' | 'treatment' | 'feeding'

// Actions arriving in later stages are shown, but disabled, so the layout is final
const QUICK_ACTIONS: { icon: IconName; label: string; sheet?: SheetKind; stage?: number }[] = [
  { icon: 'inspect', label: 'Осмотр', sheet: 'inspection' }, { icon: 'honey', label: 'Мёд', stage: 4 },
  { icon: 'health', label: 'Болезнь', sheet: 'disease' }, { icon: 'treat', label: 'Лечение', sheet: 'treatment' },
  { icon: 'feed', label: 'Подкормка', sheet: 'feeding' }, { icon: 'photo', label: 'Фото', stage: 9 },
]

export function HiveDetailsPage() {
  const { id = '' } = useParams()
  const { canManage, canWrite } = usePermissions()
  const [sheet, setSheet] = useState<SheetKind>(null)
  const [tab, setTab] = useState<'timeline' | 'families' | 'queens'>('timeline')
  const hive = useQuery({ queryKey: ['hive', id], queryFn: () => hivesApi.get(id) })

  if (hive.isLoading) return <LoadingView />
  if (hive.error) {
    return hive.error instanceof ApiError && hive.error.status === 404
      ? <MessageView icon="hive" title="Улей не найден" text="Возможно, ссылка или QR-код устарели." />
      : <div className="page"><ErrorBox error={hive.error} /></div>
  }
  const h = hive.data!
  const st = HIVE_STATUS[h.status]
  const family = h.current_family
  const queen = h.current_queen
  const editable = !h.is_archived
  const close = () => setSheet(null)

  return (
    <div className="page">
      <header className="hive-head">
        <div className="hive-head__title">
          <span className={`hive-head__badge${h.hive_number.length > 3 ? ' hive-head__badge--long' : ''}`} aria-hidden>{h.hive_number}</span>
          <div>
            <h1 className="page__title">Улей №{h.hive_number}</h1>
            <p className="hint">{h.apiary.name}, {HIVE_TYPE[h.hive_type].toLowerCase()}</p>
          </div>
        </div>
        {canManage && editable && <Link className="icon-btn" to={`/hives/${h.id}/edit`} aria-label="Изменить улей"><Icon name="edit" /></Link>}
      </header>
      <div className="row row--start">
        <Badge tone={st.tone}>{st.label}</Badge>
        {family && <StrengthBars bars={STRENGTH[family.strength].bars} label={STRENGTH[family.strength].label} />}
      </div>

      {editable && (
        <div className="quick-grid">
          {QUICK_ACTIONS.map((a) => {
            const ready = !!a.sheet && canWrite && !!family
            return (
              <button key={a.label} type="button" className="quick" disabled={!ready}
                title={a.stage ? `Появится на этапе ${a.stage}` : !family ? 'Сначала заселите семью' : undefined}
                onClick={() => a.sheet && setSheet(a.sheet)}>
                <span className="quick__icon"><Icon name={a.icon} /></span>{a.label}
                {a.stage ? <small>скоро</small> : !canWrite ? <small>только просмотр</small> : null}
              </button>
            )
          })}
        </div>
      )}

      <OpenCasesCard hive={h} canWrite={canWrite && editable} />
      <RemindersCard hive={h} canWrite={canWrite && editable} />

      {/* Family */}
      <section className="card">
        <div className="card__titlebar">
          <h2 className="card__title">Пчелиная семья</h2>
          {canWrite && editable && family && <button className="link-btn" onClick={() => setSheet('strength')}>Сила</button>}
        </div>
        {family ? <>
          <InfoRow label="Сила"><StrengthBars bars={STRENGTH[family.strength].bars} label={STRENGTH[family.strength].label} /></InfoRow>
          <InfoRow label="Происхождение">{FAMILY_ORIGIN[family.origin]}</InfoRow>
          <InfoRow label="Заселена">{formatDate(family.start_date)}</InfoRow>
        </> : <p className="hint">В улье нет семьи</p>}
        {canManage && editable && (
          <div className="btn-row">
            <button className="btn btn--secondary" onClick={() => setSheet('family')}>{family ? 'Сменить семью' : 'Заселить семью'}</button>
            {family && <button className="btn btn--ghost" onClick={() => setSheet('endFamily')}>Семья выбыла</button>}
          </div>
        )}
      </section>

      {/* Queen */}
      <section className="card">
        <h2 className="card__title">Матка</h2>
        {queen ? <>
          <InfoRow label="Код">
            <Link to={`/queens/${queen.id}`} className="link">
              {queen.marking_color && MARKING[queen.marking_color] && <i className="dot" style={{ background: MARKING[queen.marking_color].color }} />}
              {queen.queen_code}
            </Link>
          </InfoRow>
          <InfoRow label="Рождение">{queen.birth_date ? formatDate(queen.birth_date) : queen.birth_year ?? '—'}</InfoRow>
          <InfoRow label="Возраст">{queen.age_label ?? '—'}</InfoRow>
          <InfoRow label="Порода">{queen.breed ?? '—'}</InfoRow>
          <InfoRow label="В улье с">{formatDate(queen.installed_at)}</InfoRow>
          <InfoRow label="Состояние"><Badge tone={QUEEN_STATUS[queen.status].tone}>{QUEEN_STATUS[queen.status].label}</Badge></InfoRow>
        </> : <p className="hint">{family ? 'Матка не записана' : 'Нет семьи — нет матки'}</p>}
        {canManage && editable && family && (
          <div className="btn-row">
            <button className="btn btn--secondary" onClick={() => setSheet('queen')}>{queen ? 'Заменить матку' : 'Подсадить матку'}</button>
            {queen && <button className="btn btn--ghost" onClick={() => setSheet('removeQueen')}>Убрать</button>}
          </div>
        )}
      </section>

      <section className="card">
        <InfoRow label="Установлен">{formatDate(h.installation_date)}</InfoRow>
        <InfoRow label="Последний осмотр">{h.last_inspection_at ? formatDate(h.last_inspection_at) : '—'}</InfoRow>
        <InfoRow label="Следующий осмотр">{h.next_inspection_at ? formatDate(h.next_inspection_at) : '—'}</InfoRow>
        {h.notes && <p className="notes">{h.notes}</p>}
      </section>

      {/* History */}
      <section className="card">
        <div className="segmented">
          {([['timeline', 'Хронология'], ['families', 'Семьи'], ['queens', 'Матки']] as const).map(([k, l]) => (
            <button key={k} type="button" className={tab === k ? 'is-active' : ''} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>
        {tab === 'timeline' && <Timeline hiveId={h.id} />}
        {tab === 'families' && <FamilyList hiveId={h.id} />}
        {tab === 'queens' && <QueenPeriods hiveId={h.id} />}
      </section>

      <Sheet open={sheet === 'queen'} title={queen ? 'Заменить матку' : 'Подсадить матку'} onClose={close}><AssignQueenForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'removeQueen'} title="Убрать матку" onClose={close}><RemoveQueenForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'family'} title={family ? 'Сменить семью' : 'Заселить семью'} onClose={close}><SettleFamilyForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'endFamily'} title="Семья выбыла" onClose={close}><EndFamilyForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'strength'} title="Сила семьи" onClose={close}><StrengthForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'inspection'} title={`Осмотр улья №${h.hive_number}`} onClose={close}><InspectionForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'disease'} title="Болезнь" onClose={close}><DiseaseForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'treatment'} title="Лечение" onClose={close}><TreatmentForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'feeding'} title="Подкормка" onClose={close}><FeedingForm hive={h} onDone={close} /></Sheet>
    </div>
  )
}

// ---------- history lists ----------

function FamilyList({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-families', hiveId], queryFn: () => hivesApi.families(hiveId) })
  if (!q.data?.length) return <p className="hint">{q.isLoading ? 'Загрузка…' : 'Семей не было'}</p>
  return (
    <ul className="plain-list">
      {q.data.map((f) => (
        <li key={f.id}>
          <div className="row"><b>{FAMILY_ORIGIN[f.origin]}</b><span className="small">{FAMILY_STATUS[f.status]}</span></div>
          <div className="small hint">{formatDate(f.start_date)} — {f.end_date ? formatDate(f.end_date) : 'сейчас'} · {STRENGTH[f.strength].label}</div>
          {f.end_reason && <div className="small hint">{f.end_reason}</div>}
        </li>
      ))}
    </ul>
  )
}

function QueenPeriods({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-queens', hiveId], queryFn: () => hivesApi.queens(hiveId) })
  if (!q.data?.length) return <p className="hint">{q.isLoading ? 'Загрузка…' : 'Маток не было'}</p>
  return (
    <ul className="plain-list">
      {q.data.map((a) => (
        <li key={a.id}>
          <Link to={`/queens/${a.queen_id}`} className="link"><b>{a.queen_code}</b></Link>
          <div className="small hint">{formatDate(a.installed_at)} — {a.removed_at ? formatDate(a.removed_at) : 'сейчас'}</div>
          {a.removal_reason && <div className="small hint">{a.removal_reason}</div>}
        </li>
      ))}
    </ul>
  )
}

// ---------- action forms ----------

function useHiveMutation<T>(hive: Hive, fn: (v: T) => Promise<Hive>, onDone: () => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (updated) => {
      haptic('success')
      qc.setQueryData(['hive', hive.id], updated)
      for (const k of ['hives', 'queens', 'hive-history', 'hive-families', 'hive-queens']) qc.invalidateQueries({ queryKey: [k] })
      onDone()
    },
    onError: () => haptic('error'),
  })
}

const removedOpts = REMOVED_QUEEN_STATUSES.map((s) => ({ value: s, label: QUEEN_STATUS[s].label }))

function AssignQueenForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const free = useQuery({ queryKey: ['queens', 'free'], queryFn: () => queensApi.list({ in_hive: false }) })
  const [queenId, setQueenId] = useState('')
  const [date, setDate] = useState(todayIso())
  const [prev, setPrev] = useState<QueenStatus>('REPLACED')
  const [reason, setReason] = useState('')
  const m = useHiveMutation(hive, () => hivesApi.assignQueen(hive.id, {
    queen_id: queenId, installed_at: date, previous_queen_status: prev, removal_reason: reason || null,
  }), onDone)
  const submit = (e: FormEvent) => { e.preventDefault(); m.mutate(undefined) }

  return (
    <form className="form" onSubmit={submit}>
      <ErrorBox error={m.error} />
      {free.data && free.data.items.length === 0 ? (
        <p className="hint">Свободных маток нет. <Link className="link" to={`/queens/new?hive=${hive.id}`}>Добавить новую матку сразу в этот улей →</Link></p>
      ) : <>
        <Field label="Матка">
          <Select value={queenId} onChange={setQueenId} placeholder="— выберите —"
            options={(free.data?.items ?? []).map((q) => ({ value: q.id, label: `${q.queen_code}${q.breed ? ` · ${q.breed}` : ''}${q.age_label ? ` · ${q.age_label}` : ''}` }))} />
        </Field>
        <p className="small"><Link className="link" to={`/queens/new?hive=${hive.id}`}>или добавить новую матку →</Link></p>
        <Field label="Дата подсадки"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
        {hive.current_queen && <>
          <Field label={`Что с маткой ${hive.current_queen.queen_code}?`}><Select value={prev} onChange={setPrev} options={removedOpts} /></Field>
          <Field label="Причина замены"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} placeholder="Например: плохая яйценоскость" /></Field>
        </>}
        <SubmitButton pending={m.isPending}>Подсадить</SubmitButton>
      </>}
    </form>
  )
}

function RemoveQueenForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const [status, setStatus] = useState<QueenStatus>('DEAD')
  const [date, setDate] = useState(todayIso())
  const [reason, setReason] = useState('')
  const m = useHiveMutation(hive, () => hivesApi.removeQueen(hive.id, { status, removed_at: date, reason: reason || null }), onDone)
  return (
    <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(undefined) }}>
      <ErrorBox error={m.error} />
      <p className="hint">Улей будет отмечен «Без матки».</p>
      <Field label="Что случилось"><Select value={status} onChange={setStatus} options={removedOpts} /></Field>
      <Field label="Дата"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <Field label="Причина"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} /></Field>
      <SubmitButton pending={m.isPending} danger>Убрать матку</SubmitButton>
    </form>
  )
}

const strengthOpts = (Object.keys(STRENGTH) as FamilyStrength[]).map((k) => ({ value: k, label: STRENGTH[k].label }))
const originOpts = (Object.keys(FAMILY_ORIGIN) as FamilyOrigin[]).map((k) => ({ value: k, label: FAMILY_ORIGIN[k] }))
const endOpts = (['DEAD', 'ABSCONDED', 'SOLD', 'REPLACED'] as FamilyStatus[]).map((k) => ({ value: k, label: FAMILY_STATUS[k] }))

function SettleFamilyForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const [strength, setStrength] = useState<FamilyStrength>('MEDIUM')
  const [origin, setOrigin] = useState<FamilyOrigin>('SWARM')
  const [date, setDate] = useState(todayIso())
  const [prev, setPrev] = useState<FamilyStatus>('REPLACED')
  const [reason, setReason] = useState('')
  const m = useHiveMutation(hive, () => hivesApi.settleFamily(hive.id, {
    strength, origin, start_date: date, previous_status: prev, end_reason: reason || null,
  }), onDone)
  return (
    <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(undefined) }}>
      <ErrorBox error={m.error} />
      {hive.current_family && <>
        <div className="warn-box">Текущая семья будет закрыта и останется в истории{hive.current_queen ? `, матка ${hive.current_queen.queen_code} — отмечена заменённой` : ''}.</div>
        <Field label="Что с прежней семьёй"><Select value={prev} onChange={setPrev} options={endOpts} /></Field>
        <Field label="Причина"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} /></Field>
      </>}
      <Field label="Происхождение новой семьи"><Select value={origin} onChange={setOrigin} options={originOpts} /></Field>
      <Field label="Сила"><Select value={strength} onChange={setStrength} options={strengthOpts} /></Field>
      <Field label="Дата заселения"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <SubmitButton pending={m.isPending}>Заселить</SubmitButton>
    </form>
  )
}

function EndFamilyForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const [status, setStatus] = useState<FamilyStatus>('DEAD')
  const [date, setDate] = useState(todayIso())
  const [reason, setReason] = useState('')
  const m = useHiveMutation(hive, () => hivesApi.endFamily(hive.id, { status, end_date: date, end_reason: reason || null }), onDone)
  return (
    <form className="form" onSubmit={(e) => { e.preventDefault(); m.mutate(undefined) }}>
      <ErrorBox error={m.error} />
      <p className="hint">Улей станет пустым. Семья{hive.current_queen ? ' и матка' : ''} останутся в истории.</p>
      <Field label="Что случилось"><Select value={status} onChange={setStatus} options={endOpts} /></Field>
      <Field label="Дата"><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <Field label="Причина"><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} placeholder="Например: варроатоз, слёт, продажа" /></Field>
      <SubmitButton pending={m.isPending} danger>Подтвердить</SubmitButton>
    </form>
  )
}

function StrengthForm({ hive, onDone }: { hive: Hive; onDone: () => void }) {
  const m = useHiveMutation(hive, (s: FamilyStrength) => hivesApi.updateFamily(hive.id, { strength: s }), onDone)
  return (
    <div className="form">
      <ErrorBox error={m.error} />
      <div className="choice-list">
        {strengthOpts.map((o) => (
          <button key={o.value} type="button" disabled={m.isPending}
            className={`choice${hive.current_family?.strength === o.value ? ' is-active' : ''}`}
            onClick={() => m.mutate(o.value)}>
            <StrengthBars bars={STRENGTH[o.value].bars} /> {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}

