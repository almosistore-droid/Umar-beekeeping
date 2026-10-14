import { useQuery } from '@tanstack/react-query'
import { healthApi } from '../../api/resources'
import type { Hive, Inspection, TimelineItem } from '../../types/api'
import { CASE_STATUS, FOOD_LEVEL, INSPECTION_HEALTH, SEVERITY, STRENGTH, describeAudit, formatDate, formatDateTime, todayIso } from '../../utils/labels'
import { Icon, type IconName } from '../Icon'
import { Badge, ErrorBox } from '../ui'
import { useHiveRecordMutation } from './useHiveRecordMutation'
import { tr } from '../../i18n'

/** Open disease cases with a one-tap «Вылечено». Hidden when there are none. */
export function OpenCasesCard({ hive, canWrite }: { hive: Hive; canWrite: boolean }) {
  const cases = useQuery({ queryKey: ['hive-cases', hive.id], queryFn: () => healthApi.cases(hive.id) })
  const resolve = useHiveRecordMutation(hive, (id: string) => healthApi.updateCase(id, { status: 'RESOLVED', resolved_at: todayIso() }), () => {})
  const open = (cases.data ?? []).filter((c) => c.status !== 'RESOLVED')
  if (!open.length) return null
  return (
    <section className="card">
      <h2 className="card__title">{tr("Болезни")}</h2>
      <ErrorBox error={resolve.error} />
      {open.map((c) => (
        <div key={c.id} className="case-row">
          <div>
            <b>{c.disease.name}</b>
            <div className="small hint">{tr("с {0}, {1}", formatDate(c.detected_at), SEVERITY[c.severity].toLowerCase())}</div>
          </div>
          <Badge tone={CASE_STATUS[c.status].tone}>{CASE_STATUS[c.status].label}</Badge>
          {canWrite && (
            <button type="button" className="btn btn--secondary btn--sm" disabled={resolve.isPending}
              onClick={() => resolve.mutate(c.id)}>{tr("Вылечено")}</button>
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
      <h2 className="card__title">{tr("Напоминания")}</h2>
      {tasks.data.map((t) => (
        <div key={t.id} className="reminder">
          <div className="reminder__body">
            <div>{t.title}</div>
            <div className={`reminder__due${t.due_date < today ? ' is-overdue' : ''}`}>
              {t.due_date < today ? tr("Просрочено: ") : t.due_date === today ? tr("Сегодня: ") : tr("К ")}{formatDate(t.due_date)}
            </div>
          </div>
          {canWrite && <button type="button" className="btn btn--ghost btn--sm" onClick={() => done.mutate(t.id)}>{tr("Готово")}</button>}
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
  if (q.isLoading) return <p className="hint">{tr("Загрузка…")}</p>
  if (q.error) return <ErrorBox error={q.error} />
  if (!q.data?.length) return <p className="hint">{tr("Записей пока нет. Начните с осмотра.")}</p>
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

function inspectionSummary(i: Inspection): string[] {
  const out = [tr("Сила: {0}", STRENGTH[i.strength].label.toLowerCase()),
    tr("Рамки {0}: расплод {1}, мёд {2}, перга {3}", i.frames_total, i.brood_frames, i.honey_frames, i.pollen_frames)]
  const queen = i.queen_present === null ? null : i.queen_present ? tr("матка видна") : tr("матка не найдена")
  const eggs = i.egg_laying === null ? null : i.egg_laying ? tr("яйца есть") : tr("яиц нет")
  if (queen || eggs) out.push([queen, eggs].filter(Boolean).join(', '))
  if (i.swarming_signs || i.queen_cells) out.push(tr("Роение: {0}, маточников {1}", i.swarming_signs ? tr("есть признаки") : tr("нет"), i.queen_cells))
  if (i.food_level) out.push(tr("Корм: {0}", FOOD_LEVEL[i.food_level].toLowerCase()))
  out.push(tr("Здоровье: {0}", INSPECTION_HEALTH[i.health_status].toLowerCase()))
  if (i.notes) out.push(i.notes)
  return out
}

/** Every inspection as its own dated record, newest first. */
export function InspectionList({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-inspections', hiveId], queryFn: () => healthApi.inspections(hiveId) })
  if (q.error) return <ErrorBox error={q.error} />
  if (!q.data) return <p className="hint">{tr("Загрузка…")}</p>
  if (!q.data.length) return <p className="hint">{tr("Осмотров ещё не было")}</p>
  return (
    <ol className="timeline">
      {q.data.map((i) => (
        <li key={i.id}>
          <span className="timeline__icon timeline__icon--inspection" aria-hidden><Icon name="inspect" size={16} /></span>
          <div>
            <div className="timeline__title">{tr("Осмотр {0}", formatDate(i.inspected_at))}</div>
            {inspectionSummary(i).map((d) => <div key={d} className="small">{d}</div>)}
            {i.user_name && <div className="small hint">{i.user_name}</div>}
          </div>
        </li>
      ))}
    </ol>
  )
}
