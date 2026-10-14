import { useState, type FormEvent } from 'react'
import { HiveQrCard } from '../components/qr/HiveQr'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { hivesApi, queensApi } from '../api/resources'
import { Icon, type IconName } from '../components/Icon'
import { DiseaseForm, FeedingForm, TreatmentForm } from '../components/health/RecordForms'
import { InspectionList, OpenCasesCard, RemindersCard, Timeline } from '../components/health/HealthCards'
import { HoneyForm, MergeForm, MoveForm, SplitForm, SwarmForm, WinteringForm } from '../components/operations/OperationForms'
import { HoneyCard } from '../components/operations/HoneyCard'
import { Badge, ErrorBox, Field, InfoRow, Select, Sheet, StrengthBars, SubmitButton } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import type { FamilyOrigin, FamilyStatus, FamilyStrength, Hive, QueenStatus } from '../types/api'
import {
  FAMILY_ORIGIN, FAMILY_STATUS, HIVE_STATUS, HIVE_TYPE, MARKING, QUEEN_STATUS,
  REMOVED_QUEEN_STATUSES, STRENGTH, formatDate, todayIso,
} from '../utils/labels'
import { tr } from '../i18n'

type SheetKind = null | 'queen' | 'removeQueen' | 'family' | 'endFamily' | 'strength' | 'inspection' | 'disease' | 'treatment' | 'feeding' | 'honey' | 'move' | 'swarm' | 'split' | 'merge' | 'wintering'

// Actions arriving in later stages are shown, but disabled, so the layout is final
const OPERATIONS: { sheet: SheetKind; label: string; icon: IconName; needsFamily: boolean }[] = [
  { sheet: 'move', label: tr("Переместить"), icon: 'apiary', needsFamily: false },
  { sheet: 'swarm', label: tr("Роение"), icon: 'hive', needsFamily: true },
  { sheet: 'split', label: tr("Отводок"), icon: 'plus', needsFamily: true },
  { sheet: 'merge', label: tr("Объединить"), icon: 'hive', needsFamily: true },
  { sheet: 'wintering', label: tr("Зимовка"), icon: 'weak', needsFamily: true },
]

const QUICK_ACTIONS: { icon: IconName; label: string; sheet?: SheetKind; stage?: number }[] = [
  { icon: 'inspect', label: tr("Осмотр"), sheet: 'inspection' }, { icon: 'honey', label: tr("Мёд"), sheet: 'honey' },
  { icon: 'health', label: tr("Болезнь"), sheet: 'disease' }, { icon: 'treat', label: tr("Лечение"), sheet: 'treatment' },
  { icon: 'feed', label: tr("Подкормка"), sheet: 'feeding' }, { icon: 'photo', label: tr("Фото"), stage: 9 },
]

export function HiveDetailsPage() {
  const { id = '' } = useParams()
  const { canManage, canWrite } = usePermissions()
  const navigate = useNavigate()
  const [sheet, setSheet] = useState<SheetKind>(null)
  const [tab, setTab] = useState<'timeline' | 'inspections' | 'families' | 'queens'>('timeline')
  const hive = useQuery({ queryKey: ['hive', id], queryFn: () => hivesApi.get(id) })

  if (hive.isLoading) return <LoadingView />
  if (hive.error) {
    return hive.error instanceof ApiError && hive.error.status === 404
      ? <MessageView icon="hive" title={tr("Улей не найден")} text={tr("Возможно, ссылка или QR-код устарели.")} />
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
            <h1 className="page__title">{tr("Улей №{0}", h.hive_number)}</h1>
            <p className="hint">{h.apiary.name}, {HIVE_TYPE[h.hive_type].toLowerCase()}</p>
          </div>
        </div>
        {canManage && editable && <Link className="icon-btn" to={`/hives/${h.id}/edit`} aria-label={tr("Изменить улей")}><Icon name="edit" /></Link>}
      </header>
      <div className="row row--start">
        <Badge tone={st.tone}>{st.label}</Badge>
        {family && <StrengthBars bars={STRENGTH[family.strength].bars} label={STRENGTH[family.strength].label} />}
      </div>

      {editable && (
        <div className="quick-grid">
          {QUICK_ACTIONS.map((a) => {
            const ready = !!a.sheet && canWrite && (!!family || a.sheet === 'honey')
            return (
              <button key={a.label} type="button" className="quick" disabled={!ready}
                title={a.stage ? tr("Появится на этапе {0}", a.stage) : !family ? tr("Сначала заселите семью") : undefined}
                onClick={() => a.sheet === 'inspection' ? navigate(`/hives/${h.id}/inspect`) : a.sheet && setSheet(a.sheet)}>
                <span className="quick__icon"><Icon name={a.icon} /></span>{a.label}
                {a.stage ? <small>{tr("скоро")}</small> : !canWrite ? <small>{tr("только просмотр")}</small> : null}
              </button>
            )
          })}
        </div>
      )}

      <HiveQrCard hiveId={h.id} />
      <HoneyCard hiveId={h.id} />
      <OpenCasesCard hive={h} canWrite={canWrite && editable} />
      <RemindersCard hive={h} canWrite={canWrite && editable} />

      {/* Family */}
      <section className="card">
        <div className="card__titlebar">
          <h2 className="card__title">{tr("Пчелиная семья")}</h2>
          {canWrite && editable && family && <button className="link-btn" onClick={() => setSheet('strength')}>{tr("Сила")}</button>}
        </div>
        {family ? <>
          <InfoRow label={tr("Сила")}><StrengthBars bars={STRENGTH[family.strength].bars} label={STRENGTH[family.strength].label} /></InfoRow>
          <InfoRow label={tr("Происхождение")}>{FAMILY_ORIGIN[family.origin]}</InfoRow>
          <InfoRow label={tr("Заселена")}>{formatDate(family.start_date)}</InfoRow>
        </> : <p className="hint">{tr("В улье нет семьи")}</p>}
        {canManage && editable && (
          <div className="btn-row">
            <button className="btn btn--secondary" onClick={() => setSheet('family')}>{family ? tr("Сменить семью") : tr("Заселить семью")}</button>
            {family && <button className="btn btn--ghost" onClick={() => setSheet('endFamily')}>{tr("Семья выбыла")}</button>}
          </div>
        )}
      </section>

      {/* Queen */}
      <section className="card">
        <h2 className="card__title">{tr("Матка")}</h2>
        {queen ? <>
          <InfoRow label={tr("Код")}>
            <Link to={`/queens/${queen.id}`} className="link">
              {queen.marking_color && MARKING[queen.marking_color] && <i className="dot" style={{ background: MARKING[queen.marking_color].color }} />}
              {queen.queen_code}
            </Link>
          </InfoRow>
          <InfoRow label={tr("Рождение")}>{queen.birth_date ? formatDate(queen.birth_date) : queen.birth_year ?? '—'}</InfoRow>
          <InfoRow label={tr("Возраст")}>{queen.age_label ?? '—'}</InfoRow>
          <InfoRow label={tr("Порода")}>{queen.breed ?? '—'}</InfoRow>
          <InfoRow label={tr("В улье с")}>{formatDate(queen.installed_at)}</InfoRow>
          <InfoRow label={tr("Состояние")}><Badge tone={QUEEN_STATUS[queen.status].tone}>{QUEEN_STATUS[queen.status].label}</Badge></InfoRow>
        </> : <p className="hint">{family ? tr("Матка не записана") : tr("Нет семьи — нет матки")}</p>}
        {canManage && editable && family && (
          <div className="btn-row">
            <button className="btn btn--secondary" onClick={() => setSheet('queen')}>{queen ? tr("Заменить матку") : tr("Подсадить матку")}</button>
            {queen && <button className="btn btn--ghost" onClick={() => setSheet('removeQueen')}>{tr("Убрать")}</button>}
          </div>
        )}
      </section>

      {canManage && editable && (
        <section className="card">
          <h2 className="card__title">{tr("Операции")}</h2>
          <div className="ops-grid">
            {OPERATIONS.map((o) => (
              <button key={o.sheet} type="button" className="btn btn--secondary" disabled={o.needsFamily && !family}
                onClick={() => setSheet(o.sheet)}><Icon name={o.icon} size={18} />{o.label}</button>
            ))}
          </div>
        </section>
      )}

      <section className="card">
        <InfoRow label={tr("Установлен")}>{formatDate(h.installation_date)}</InfoRow>
        <InfoRow label={tr("Последний осмотр")}>{h.last_inspection_at ? formatDate(h.last_inspection_at) : '—'}</InfoRow>
        <InfoRow label={tr("Следующий осмотр")}>{h.next_inspection_at ? formatDate(h.next_inspection_at) : '—'}</InfoRow>
        {h.notes && <p className="notes">{h.notes}</p>}
      </section>

      {/* History */}
      <section className="card">
        <div className="segmented">
          {([['timeline', tr("Хронология")], ['inspections', tr("Осмотры")], ['families', tr("Семьи")], ['queens', tr("Матки")]] as const).map(([k, l]) => (
            <button key={k} type="button" className={tab === k ? 'is-active' : ''} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>
        {tab === 'timeline' && <Timeline hiveId={h.id} />}
        {tab === 'inspections' && <InspectionList hiveId={h.id} />}
        {tab === 'families' && <FamilyList hiveId={h.id} />}
        {tab === 'queens' && <QueenPeriods hiveId={h.id} />}
      </section>

      <Sheet open={sheet === 'queen'} title={queen ? tr("Заменить матку") : tr("Подсадить матку")} onClose={close}><AssignQueenForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'removeQueen'} title={tr("Убрать матку")} onClose={close}><RemoveQueenForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'family'} title={family ? tr("Сменить семью") : tr("Заселить семью")} onClose={close}><SettleFamilyForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'endFamily'} title={tr("Семья выбыла")} onClose={close}><EndFamilyForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'strength'} title={tr("Сила семьи")} onClose={close}><StrengthForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'disease'} title={tr("Болезнь")} onClose={close}><DiseaseForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'treatment'} title={tr("Лечение")} onClose={close}><TreatmentForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'feeding'} title={tr("Подкормка")} onClose={close}><FeedingForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'honey'} title={tr("Мёд, улей №{0}", h.hive_number)} onClose={close}><HoneyForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'move'} title={tr("Переместить улей")} onClose={close}><MoveForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'swarm'} title={tr("Роение")} onClose={close}><SwarmForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'split'} title={tr("Отводок")} onClose={close}><SplitForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'merge'} title={tr("Объединить семьи")} onClose={close}><MergeForm hive={h} onDone={close} /></Sheet>
      <Sheet open={sheet === 'wintering'} title={tr("Зимовка")} onClose={close}><WinteringForm hive={h} onDone={close} /></Sheet>
    </div>
  )
}

// ---------- history lists ----------

function FamilyList({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-families', hiveId], queryFn: () => hivesApi.families(hiveId) })
  if (!q.data?.length) return <p className="hint">{q.isLoading ? tr("Загрузка…") : tr("Семей не было")}</p>
  return (
    <ul className="plain-list">
      {q.data.map((f) => (
        <li key={f.id}>
          <div className="row"><b>{FAMILY_ORIGIN[f.origin]}</b><span className="small">{FAMILY_STATUS[f.status]}</span></div>
          <div className="small hint">{formatDate(f.start_date)} — {f.end_date ? formatDate(f.end_date) : tr("сейчас")} · {STRENGTH[f.strength].label}</div>
          {f.end_reason && <div className="small hint">{f.end_reason}</div>}
        </li>
      ))}
    </ul>
  )
}

function QueenPeriods({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-queens', hiveId], queryFn: () => hivesApi.queens(hiveId) })
  if (!q.data?.length) return <p className="hint">{q.isLoading ? tr("Загрузка…") : tr("Маток не было")}</p>
  return (
    <ul className="plain-list">
      {q.data.map((a) => (
        <li key={a.id}>
          <Link to={`/queens/${a.queen_id}`} className="link"><b>{a.queen_code}</b></Link>
          <div className="small hint">{formatDate(a.installed_at)} — {a.removed_at ? formatDate(a.removed_at) : tr("сейчас")}</div>
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
        <p className="hint">{tr("Свободных маток нет.")}{" "}<Link className="link" to={`/queens/new?hive=${hive.id}`}>{tr("Добавить новую матку сразу в этот улей →")}</Link></p>
      ) : <>
        <Field label={tr("Матка")}>
          <Select value={queenId} onChange={setQueenId} placeholder={tr("— выберите —")}
            options={(free.data?.items ?? []).map((q) => ({ value: q.id, label: `${q.queen_code}${q.breed ? ` · ${q.breed}` : ''}${q.age_label ? ` · ${q.age_label}` : ''}` }))} />
        </Field>
        <p className="small"><Link className="link" to={`/queens/new?hive=${hive.id}`}>{tr("или добавить новую матку →")}</Link></p>
        <Field label={tr("Дата подсадки")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
        {hive.current_queen && <>
          <Field label={tr("Что с маткой {0}?", hive.current_queen.queen_code)}><Select value={prev} onChange={setPrev} options={removedOpts} /></Field>
          <Field label={tr("Причина замены")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} placeholder={tr("Например: плохая яйценоскость")} /></Field>
        </>}
        <SubmitButton pending={m.isPending}>{tr("Подсадить")}</SubmitButton>
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
      <p className="hint">{tr("Улей будет отмечен «Без матки».")}</p>
      <Field label={tr("Что случилось")}><Select value={status} onChange={setStatus} options={removedOpts} /></Field>
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <Field label={tr("Причина")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} /></Field>
      <SubmitButton pending={m.isPending} danger>{tr("Убрать матку")}</SubmitButton>
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
        <div className="warn-box">{tr("Текущая семья будет закрыта и останется в истории")}{hive.current_queen ? tr(", матка {0} — отмечена заменённой", hive.current_queen.queen_code) : ''}.</div>
        <Field label={tr("Что с прежней семьёй")}><Select value={prev} onChange={setPrev} options={endOpts} /></Field>
        <Field label={tr("Причина")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} /></Field>
      </>}
      <Field label={tr("Происхождение новой семьи")}><Select value={origin} onChange={setOrigin} options={originOpts} /></Field>
      <Field label={tr("Сила")}><Select value={strength} onChange={setStrength} options={strengthOpts} /></Field>
      <Field label={tr("Дата заселения")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <SubmitButton pending={m.isPending}>{tr("Заселить")}</SubmitButton>
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
      <p className="hint">{tr("Улей станет пустым. Семья")}{hive.current_queen ? tr(" и матка") : ''}{" "}{tr("останутся в истории.")}</p>
      <Field label={tr("Что случилось")}><Select value={status} onChange={setStatus} options={endOpts} /></Field>
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <Field label={tr("Причина")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={255} placeholder={tr("Например: варроатоз, слёт, продажа")} /></Field>
      <SubmitButton pending={m.isPending} danger>{tr("Подтвердить")}</SubmitButton>
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

