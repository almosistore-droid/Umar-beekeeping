import { useQuery } from '@tanstack/react-query'
import { healthApi } from '../../api/resources'
import type { Hive, TimelineItem } from '../../types/api'
import { CASE_STATUS, SEVERITY, describeAudit, formatDate, formatDateTime, todayIso } from '../../utils/labels'
import { Icon, type IconName } from '../Icon'
import { Badge, ErrorBox } from '../ui'
import { useHiveRecordMutation } from './useHiveRecordMutation'

/** Open disease cases with a one-tap «Вылечено». Hidden when there are none. */
export function OpenCasesCard({ hive, canWrite }: { hive: Hive; canWrite: boolean }) {
  const cases = useQuery({ queryKey: ['hive-cases', hive.id], queryFn: () => healthApi.cases(hive.id) })
  const resolve = useHiveRecordMutation(hive, (id: string) => healthApi.updateCase(id, { status: 'RESOLVED', resolved_at: todayIso() }), () => {})
  const open = (cases.data ?? []).filter((c) => c.status !== 'RESOLVED')
  if (!open.length) return null
  return (
    <section className="card">
      <h2 className="card__title">Болезни</h2>
      <ErrorBox error={resolve.error} />
      {open.map((c) => (
        <div key={c.id} className="case-row">
          <div>
            <b>{c.disease.name}</b>
            <div className="small hint">с {formatDate(c.detected_at)}, {SEVERITY[c.severity].toLowerCase()}</div>
          </div>
          <Badge tone={CASE_STATUS[c.status].tone}>{CASE_STATUS[c.status].label}</Badge>
          {canWrite && (
            <button type="button" className="btn btn--secondary btn--sm" disabled={resolve.isPending}
              onClick={() => resolve.mutate(c.id)}>Вылечено</button>
          )}
        </div>
      ))}
    </section>
  )
}

/** Open reminders for this hive (repeat treatment, next feeding). */
export function RemindersCard({ hive, canWrite }: { hive: Hive; canWrite: boolean }) {
  const tasks = useQuery({ queryKey: ['hive-tasks', hive.id], queryFn: () => healthApi.tasks({ hive_id: hive.id }) })
  const done = useHiveRecordMutation(hive, async (id: string) => { await healthApi.completeTask(id); return hive }, () => {})
  if (!tasks.data?.length) return null
  const today = todayIso()
  return (
    <section className="card">
      <h2 className="card__title">Напоминания</h2>
      {tasks.data.map((t) => (
        <div key={t.id} className="reminder">
          <div className="reminder__body">
            <div>{t.title}</div>
            <div className={`reminder__due${t.due_date < today ? ' is-overdue' : ''}`}>
              {t.due_date < today ? 'Просрочено: ' : t.due_date === today ? 'Сегодня: ' : 'К '}{formatDate(t.due_date)}
            </div>
          </div>
          {canWrite && <button type="button" className="btn btn--ghost btn--sm" onClick={() => done.mutate(t.id)}>Готово</button>}
        </div>
      ))}
    </section>
  )
}

const KIND_ICON: Record<TimelineItem['kind'], IconName> = {
  inspection: 'inspect', disease_opened: 'health', disease_resolved: 'health', treatment: 'treat', feeding: 'feed', event: 'edit',
}

/** Unified hive timeline: records of stage 3 plus history events. */
export function Timeline({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-timeline', hiveId], queryFn: () => healthApi.timeline(hiveId) })
  if (q.isLoading) return <p className="hint">Загрузка…</p>
  if (q.error) return <ErrorBox error={q.error} />
  if (!q.data?.length) return <p className="hint">Записей пока нет. Начните с осмотра.</p>
  return (
    <ol className="timeline">
      {q.data.map((item, i) => {
        let icon = KIND_ICON[item.kind]
        let title = item.title
        let details = item.details
        if (item.kind === 'event') {
          const d = describeAudit(item.action ?? '', item.old_value ?? null, item.new_value ?? null)
          icon = d.icon
          title = d.title
          details = d.details.filter(Boolean)
        }
        return (
          <li key={`${item.kind}-${item.ref_id}-${i}`}>
            <span className={`timeline__icon timeline__icon--${item.kind}`} aria-hidden><Icon name={icon} size={16} /></span>
            <div>
              <div className="timeline__title">{title}</div>
              {details.map((x, j) => <div key={j} className="small">{x}</div>)}
              {item.comment && <div className="small hint">«{item.comment}»</div>}
              <div className="small hint">
                {item.kind === 'event' || item.kind === 'inspection' ? formatDateTime(item.at) : formatDate(item.at)}
                {item.author && `, ${item.author}`}
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
