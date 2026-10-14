import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { healthApi } from '../api/resources'
import { Icon } from '../components/Icon'
import { LoadingView } from '../components/StateViews'
import { Badge, ErrorBox, InfoRow, StrengthBars } from '../components/ui'
import { HiveMiniHead } from '../components/visit/HiveMiniHead'
import { usePermissions } from '../hooks/usePermissions'
import { FOOD_LEVEL, HIVE_STATUS, INSPECTION_HEALTH, STRENGTH, daysAgoLabel, formatDate, num } from '../utils/labels'
import { tr } from '../i18n'

const yesNo = (v: boolean | null, yes: string, no: string) => (v === null ? '—' : v ? yes : no)

/** «Проверка улья»: the current state in one screen; nothing is saved. */
export function HiveCheckPage() {
  const { id = '' } = useParams()
  const { canWrite } = usePermissions()
  const check = useQuery({ queryKey: ['hive-check', id], queryFn: () => healthApi.check(id), staleTime: 0 })

  if (check.isLoading) return <LoadingView text={tr("Собираем итог…")} />
  if (check.error) return <div className="page"><ErrorBox error={check.error} /></div>
  const c = check.data!
  const li = c.last_inspection
  const st = HIVE_STATUS[c.status]
  const canInspect = canWrite && !c.is_archived && !!c.strength

  return (
    <div className="page">
      <HiveMiniHead number={c.hive_number} apiary={c.apiary.name} />

      <section className={`verdict verdict--${c.verdict}`} aria-live="polite">
        <span className="verdict__mark" aria-hidden><Icon name={c.verdict === 'ok' ? 'strong' : 'weak'} size={26} /></span>
        <div>
          <h2 className="verdict__title">{c.headline}</h2>
          {c.issues.length > 0 && (
            <ul className="verdict__issues">
              {c.issues.map((i) => <li key={i.code + i.message} className={`is-${i.level}`}>{i.message}</li>)}
            </ul>
          )}
        </div>
      </section>

      <section className="card">
        <h2 className="card__title">{tr("Семья и матка")}</h2>
        <InfoRow label={tr("Статус")}><Badge tone={st.tone}>{st.label}</Badge></InfoRow>
        <InfoRow label={tr("Сила")}>{c.strength ? <StrengthBars bars={STRENGTH[c.strength].bars} label={STRENGTH[c.strength].label} /> : tr("нет семьи")}</InfoRow>
        <InfoRow label={tr("Матка")}>{c.queen ? <Link className="link" to={`/queens/${c.queen.id}`}>{c.queen.queen_code}</Link> : '—'}</InfoRow>
        {c.queen?.age_label && <InfoRow label={tr("Возраст матки")}>{c.queen.age_label}</InfoRow>}
      </section>

      <section className="card">
        <h2 className="card__title">{tr("Последний осмотр")}</h2>
        {li ? <>
          <InfoRow label={tr("Когда")}>{formatDate(li.inspected_at)}, {daysAgoLabel(li.days_ago)}</InfoRow>
          {li.user_name && <InfoRow label={tr("Кто")}>{li.user_name}</InfoRow>}
          <InfoRow label={tr("Рамки")}>{tr("{0} (расплод {1}, мёд {2}, перга {3})", li.frames_total, li.brood_frames, li.honey_frames, li.pollen_frames)}</InfoRow>
          <InfoRow label={tr("Матка / яйца")}>{yesNo(li.queen_present, tr("видна"), tr("не найдена"))} / {yesNo(li.egg_laying, tr("есть"), tr("нет"))}</InfoRow>
          {(li.queen_cells > 0 || li.swarming_signs) && <InfoRow label={tr("Роение")}>{li.swarming_signs ? tr("есть признаки") : tr("нет признаков")}{tr(", маточников {0}", li.queen_cells)}</InfoRow>}
          <InfoRow label={tr("Корм")}>{li.food_level ? FOOD_LEVEL[li.food_level] : '—'}</InfoRow>
          <InfoRow label={tr("Здоровье")}>{INSPECTION_HEALTH[li.health_status]}</InfoRow>
        </> : <p className="hint">{tr("Осмотров ещё не было")}</p>}
        <InfoRow label={tr("Следующий осмотр")}>{c.next_inspection_at ? formatDate(c.next_inspection_at) : '—'}</InfoRow>
      </section>

      {(c.open_cases.length > 0 || c.open_tasks.length > 0) && (
        <section className="card">
          <h2 className="card__title">{tr("Болезни и напоминания")}</h2>
          {c.open_cases.map((d) => <InfoRow key={d.disease_name} label={d.disease_name}>{d.status}</InfoRow>)}
          {c.open_tasks.map((t) => (
            <InfoRow key={t.title + t.due_date} label={t.title}><span className={t.overdue ? 'warn' : undefined}>{formatDate(t.due_date)}</span></InfoRow>
          ))}
        </section>
      )}

      <section className="card">
        <InfoRow label={tr("Мёд за {0}", new Date().getFullYear())}>{tr("{0} кг", num(c.honey_year_kg))}</InfoRow>
      </section>

      {canInspect && <Link className="btn btn--primary btn--block" to={`/hives/${c.hive_id}/inspect`} replace><Icon name="inspect" size={18} />{tr("Провести осмотр")}</Link>}
      <Link className="btn btn--ghost btn--block" to={`/hives/${c.hive_id}`}>{tr("Паспорт улья")}</Link>
    </div>
  )
}
