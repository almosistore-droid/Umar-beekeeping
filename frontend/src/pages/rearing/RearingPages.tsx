import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { hivesApi, queensApi, rearingApi, type RearingInput } from '../../api/resources'
import { Icon } from '../../components/Icon'
import { LoadingView, MessageView } from '../../components/StateViews'
import { ErrorBox, Field, Sheet, SubmitButton, fieldError } from '../../components/ui'
import { usePermissions } from '../../hooks/usePermissions'
import { haptic } from '../../services/telegram'
import type { RearingBatch, RearingStep } from '../../types/api'
import { addDaysIso, formatDate, todayIso } from '../../utils/labels'
import { tr } from '../../i18n'

const STATE_LABEL: Record<RearingStep['state'], string> = {
  done: tr("сделано"), today: tr("сегодня"), overdue: tr("пора"), upcoming: tr("впереди"), skipped: tr("не понадобилось"),
}

function useRearingMutation<T>(fn: (v: T) => Promise<RearingBatch>, onDone?: (b: RearingBatch) => void) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (b) => {
      haptic('success')
      qc.setQueryData(['rearing', b.id], b)
      for (const k of ['rearing-list', 'tasks', 'attention']) qc.invalidateQueries({ queryKey: [k] })
      onDone?.(b)
    },
    onError: () => haptic('error'),
  })
}

/** Counts in one line: «30 → 24 → 22 → … → …». */
function Funnel({ b }: { b: RearingBatch }) {
  const parts: [string, number | null][] = [
    [tr("привито"), b.cells_grafted], [tr("принято"), b.cells_accepted], [tr("запечатано"), b.cells_sealed],
    [tr("вышло"), b.queens_emerged], [tr("плодных"), b.queens_mated],
  ]
  return (
    <div className="funnel">
      {parts.map(([label, n], i) => (
        <span key={label} className={`funnel__cell${n === null ? ' funnel__cell--empty' : ''}`}>
          <b>{n ?? '—'}</b><small>{label}</small>{i < parts.length - 1 && <i aria-hidden>›</i>}
        </span>
      ))}
    </div>
  )
}

export function RearingListPage() {
  const { canWrite } = usePermissions()
  const navigate = useNavigate()
  const [adding, setAdding] = useState(false)
  const list = useQuery({ queryKey: ['rearing-list'], queryFn: rearingApi.list })
  const active = (list.data ?? []).filter((b) => b.status === 'ACTIVE')
  const closed = (list.data ?? []).filter((b) => b.status !== 'ACTIVE')
  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Вывод маток")}</h1>
        {canWrite && <button className="btn btn--primary btn--sm" onClick={() => setAdding(true)}>{tr("＋ Прививка")}</button>}
      </div>
      <ErrorBox error={list.error} />
      {list.isLoading ? <LoadingView /> : !list.data?.length ? (
        <MessageView icon="crown" title={tr("Партий пока нет")}
          text={tr("Запишите день прививки личинок — приложение распишет календарь: приём, запечатка, перенос маточников, выход, облёт и засев — и напомнит в Telegram о каждом шаге.")}
          action={canWrite ? { label: tr("Записать прививку"), onClick: () => setAdding(true) } : undefined} />
      ) : <>
        {active.map((b) => (
          <Link key={b.id} to={`/rearing/${b.id}`} className="card rearing-card">
            <div className="rearing-card__head">
              <span className="rearing-card__day"><b>{b.day}</b><small>{tr("день")}</small></span>
              <span className="rearing-card__main">
                <b>{b.label}</b>
                {b.next_step && (
                  <span className={`small ${b.next_step.state === 'overdue' || b.next_step.state === 'today' ? 'rearing-due' : 'hint'}`}>
                    {b.next_step.state === 'upcoming'
                      ? tr("Дальше: {0} — {1}", b.next_step.title, formatDate(b.next_step.date))
                      : tr("Сейчас: {0}", b.next_step.title)}
                  </span>
                )}
              </span>
              <span className="chevron">›</span>
            </div>
            <Funnel b={b} />
          </Link>
        ))}
        {closed.length > 0 && (
          <section className="card card--list">
            <h2 className="card__title">{tr("Закрытые партии")}</h2>
            {closed.map((b) => (
              <Link key={b.id} to={`/rearing/${b.id}`} className="stock-row">
                <span className="stock-row__main">
                  <b>{b.label}</b>
                  <span className="small hint">{b.status === 'DONE' ? tr("завершена") : tr("отменена")}{b.cancel_reason ? ` · ${b.cancel_reason}` : ''}</span>
                </span>
                <span className="stock-row__qty" style={{ fontSize: 17 }}>{b.queens_mated ?? '—'} / {b.cells_grafted}</span>
              </Link>
            ))}
          </section>
        )}
      </>}
      <Sheet open={adding} title={tr("Прививка личинок")} onClose={() => setAdding(false)}>
        {adding && <RearingForm onDone={(b) => { setAdding(false); navigate(`/rearing/${b.id}`) }} />}
      </Sheet>
    </div>
  )
}

export function RearingForm({ batch, onDone }: { batch?: RearingBatch; onDone: (b: RearingBatch) => void }) {
  const queens = useQuery({ queryKey: ['queens', 'rearing'], queryFn: () => queensApi.list({ status: ['ACTIVE'] }) })
  const hives = useQuery({ queryKey: ['hives', 'rearing'], queryFn: () => hivesApi.list({ limit: 300 }) })
  const [date, setDate] = useState(batch?.grafted_at ?? todayIso())
  const [cells, setCells] = useState(String(batch?.cells_grafted ?? 30))
  const [queen, setQueen] = useState(batch?.mother_queen_id ?? '')
  const [builder, setBuilder] = useState(batch?.cell_builder_hive_id ?? '')
  const [label, setLabel] = useState(batch?.label ?? '')
  const [notes, setNotes] = useState(batch?.notes ?? '')
  const body: RearingInput = {
    grafted_at: date, cells_grafted: Number(cells), mother_queen_id: queen || null, cell_builder_hive_id: builder || null,
    label: label || null, notes: notes || null,
  }
  const save = useRearingMutation(() => (batch ? rearingApi.update(batch.id, body) : rearingApi.create(body)), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <Field label={tr("День прививки")} error={fieldError(save.error, 'grafted_at')}
        hint={tr("Матки выйдут {0}", formatDate(addDaysIso(12, new Date(`${date}T00:00:00`))))}>
        <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} required />
      </Field>
      <Field label={tr("Сколько личинок привито")} error={fieldError(save.error, 'cells_grafted')}>
        <input className="input input--big" inputMode="numeric" value={cells} onChange={(e) => setCells(e.target.value)} required />
      </Field>
      <Field label={tr("Матка-мать (от кого личинки)")}>
        <select className="input" value={queen} onChange={(e) => setQueen(e.target.value)}>
          <option value="">{tr("Не указывать")}</option>
          {(queens.data?.items ?? []).map((q) => <option key={q.id} value={q.id}>{q.queen_code}{q.breed ? ` · ${q.breed}` : ''}</option>)}
        </select>
      </Field>
      <Field label={tr("Семья-воспитательница (улей)")} hint={tr("Напоминания будут с кнопкой этого улья")}>
        <select className="input" value={builder} onChange={(e) => setBuilder(e.target.value)}>
          <option value="">{tr("Не указывать")}</option>
          {(hives.data?.items ?? []).map((h) => <option key={h.id} value={h.id}>{tr("Улей №{0}", h.hive_number)} · {h.apiary.name}</option>)}
        </select>
      </Field>
      <Field label={tr("Название партии")} hint={tr("Пусто — «Партия N · дата»")}>
        <input className="input" value={label} maxLength={80} onChange={(e) => setLabel(e.target.value)} />
      </Field>
      <Field label={tr("Заметка")}><input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{batch ? tr("Сохранить") : tr("Записать прививку")}</SubmitButton></div>
    </form>
  )
}

function StepForm({ batch, step, onDone }: { batch: RearingBatch; step: RearingStep; onDone: () => void }) {
  const prev = step.count_field ? ([batch.cells_grafted, batch.cells_accepted, batch.cells_sealed, batch.queens_emerged]
    .filter((x): x is number => x !== null).slice(-1)[0]) : null
  const [count, setCount] = useState(step.count_field && batch[step.count_field] !== null ? String(batch[step.count_field]) : String(prev ?? ''))
  const save = useRearingMutation(() => rearingApi.stepDone(batch.id, step.key, step.count_field ? Number(count) : null), onDone)
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate(undefined) }}>
      <ErrorBox error={save.error} />
      <p className="hint">{step.hint}</p>
      {step.count_field && (
        <Field label={step.count_label ?? ''} hint={prev !== null ? tr("На прошлом шаге: {0}", prev) : undefined}>
          <input className="input input--big" inputMode="numeric" value={count} onChange={(e) => setCount(e.target.value)} required autoFocus />
        </Field>
      )}
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Отметить сделанным")}</SubmitButton></div>
    </form>
  )
}

export function RearingBatchPage() {
  const { id = '' } = useParams()
  const { canWrite, canManage } = usePermissions()
  const data = useQuery({ queryKey: ['rearing', id], queryFn: () => rearingApi.get(id) })
  const [step, setStep] = useState<RearingStep | null>(null)
  const [editing, setEditing] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [reason, setReason] = useState('')
  const finish = useRearingMutation(() => rearingApi.finish(id))
  const cancel = useRearingMutation(() => rearingApi.cancel(id, reason), () => setCancelling(false))
  if (data.isLoading) return <LoadingView />
  if (!data.data) return <div className="page"><ErrorBox error={data.error} /></div>
  const b = data.data
  const open = b.status === 'ACTIVE'
  return (
    <div className="page">
      <h1 className="page__title">{b.label}</h1>
      <p className="hint">
        {tr("Прививка {0}", formatDate(b.grafted_at))}{open ? ` · ${tr("сегодня {0}-й день", b.day)}` : ''}
        {b.mother_queen_code ? ` · ${tr("мать {0}", b.mother_queen_code)}` : ''}
        {b.cell_builder_number ? ` · ${tr("воспитательница — улей №{0}", b.cell_builder_number)}` : ''}
      </p>
      {!open && <p className="warn-box small">{b.status === 'DONE' ? tr("Партия завершена.") : tr("Партия отменена: {0}", b.cancel_reason ?? '')}</p>}
      <ErrorBox error={finish.error ?? cancel.error} />
      <section className="card"><Funnel b={b} /></section>
      <ol className="rearing-steps">
        {b.steps.map((s) => (
          <li key={s.key} className={`rearing-step rearing-step--${s.state}`}>
            <span className="rearing-step__day" aria-hidden>{s.day}</span>
            <div className="rearing-step__body">
              <div className="rearing-step__top">
                <b>{s.title}</b>
                <span className={`rearing-step__chip rearing-step__chip--${s.state}`}>{STATE_LABEL[s.state]}</span>
              </div>
              <span className="small hint">{tr("{0}-й день · {1}", s.day, formatDate(s.date))}
                {s.count_field && b[s.count_field] !== null ? ` · ${s.count_label}: ${b[s.count_field]}` : ''}</span>
              {(s.state === 'today' || s.state === 'overdue') && <p className="small">{s.hint}</p>}
              {open && canWrite && s.key !== 'graft' && s.state !== 'done' && (
                <button type="button" className="btn btn--secondary btn--sm" onClick={() => setStep(s)}>
                  {s.count_field ? tr("Записать: {0}", (s.count_label ?? '').toLowerCase()) : tr("Сделано")}
                </button>
              )}
              {open && canWrite && s.state === 'done' && s.count_field && (
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => setStep(s)}>{tr("Исправить")}</button>
              )}
            </div>
          </li>
        ))}
      </ol>
      {b.queens_mated !== null && b.queens_mated > 0 && canManage && (
        <Link to="/queens/new" className="btn btn--secondary btn--block"><Icon name="crown" size={18} />{tr("Добавить маток в «Матки»")}</Link>
      )}
      {open && canWrite && <>
        <button type="button" className="btn btn--ghost btn--block" onClick={() => setEditing(true)}><Icon name="edit" size={16} />{tr("Изменить партию")}</button>
        <button type="button" className="btn btn--ghost btn--block" disabled={finish.isPending} onClick={() => finish.mutate(undefined)}>{tr("Завершить партию")}</button>
        {canManage && <button type="button" className="btn btn--ghost btn--block" onClick={() => setCancelling(true)}>{tr("Отменить партию")}</button>}
      </>}
      <Sheet open={step !== null} title={step?.title ?? ''} onClose={() => setStep(null)}>
        {step && <StepForm batch={b} step={step} onDone={() => setStep(null)} />}
      </Sheet>
      <Sheet open={editing} title={tr("Изменить партию")} onClose={() => setEditing(false)}>
        {editing && <RearingForm batch={b} onDone={() => setEditing(false)} />}
      </Sheet>
      <Sheet open={cancelling} title={tr("Отменить партию")} onClose={() => setCancelling(false)}>
        {cancelling && (
          <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); cancel.mutate(undefined) }}>
            <ErrorBox error={cancel.error} />
            <p className="hint">{tr("Партия останется в истории с пометкой «отменена», напоминания по ней закроются.")}</p>
            <Field label={tr("Причина")}><input className="input" value={reason} onChange={(e) => setReason(e.target.value)} required autoFocus
              placeholder={tr("Например: похолодание, личинки не приняты")} /></Field>
            <div className="submit-bar"><SubmitButton pending={cancel.isPending} danger>{tr("Отменить партию")}</SubmitButton></div>
          </form>
        )}
      </Sheet>
    </div>
  )
}
