import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { healthApi } from '../api/resources'
import { Icon } from '../components/Icon'
import { LoadingView } from '../components/StateViews'
import { Badge, ErrorBox, InfoRow, StrengthBars } from '../components/ui'
import { HiveMiniHead } from '../components/visit/HiveMiniHead'
import { usePermissions } from '../hooks/usePermissions'
import { FOOD_LEVEL, HIVE_STATUS, INSPECTION_HEALTH, STRENGTH, daysAgoLabel, formatDate, num } from '../utils/labels'

const yesNo = (v: boolean | null, yes: string, no: string) => (v === null ? '—' : v ? yes : no)

/** «Проверка улья»: the current state in one screen; nothing is saved. */
export function HiveCheckPage() {
  const { id = '' } = useParams()
  const { canWrite } = usePermissions()
  const check = useQuery({ queryKey: ['hive-check', id], queryFn: () => healthApi.check(id), staleTime: 0 })

  if (check.isLoading) return <LoadingView text="Собираем итог…" />
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
        <h2 className="card__title">Семья и матка</h2>
        <InfoRow label="Статус"><Badge tone={st.tone}>{st.label}</Badge></InfoRow>
        <InfoRow label="Сила">{c.strength ? <StrengthBars bars={STRENGTH[c.strength].bars} label={STRENGTH[c.strength].label} /> : 'нет семьи'}</InfoRow>
        <InfoRow label="Матка">{c.queen ? <Link className="link" to={`/queens/${c.queen.id}`}>{c.queen.queen_code}</Link> : '—'}</InfoRow>
        {c.queen?.age_label && <InfoRow label="Возраст матки">{c.queen.age_label}</InfoRow>}
      </section>

      <section className="card">
        <h2 className="card__title">Последний осмотр</h2>
        {li ? <>
          <InfoRow label="Когда">{formatDate(li.inspected_at)}, {daysAgoLabel(li.days_ago)}</InfoRow>
          {li.user_name && <InfoRow label="Кто">{li.user_name}</InfoRow>}
          <InfoRow label="Рамки">{li.frames_total} (расплод {li.brood_frames}, мёд {li.honey_frames}, перга {li.pollen_frames})</InfoRow>
          <InfoRow label="Матка / яйца">{yesNo(li.queen_present, 'видна', 'не найдена')} / {yesNo(li.egg_laying, 'есть', 'нет')}</InfoRow>
          {(li.queen_cells > 0 || li.swarming_signs) && <InfoRow label="Роение">{li.swarming_signs ? 'есть признаки' : 'нет признаков'}, маточников {li.queen_cells}</InfoRow>}
          <InfoRow label="Корм">{li.food_level ? FOOD_LEVEL[li.food_level] : '—'}</InfoRow>
          <InfoRow label="Здоровье">{INSPECTION_HEALTH[li.health_status]}</InfoRow>
        </> : <p className="hint">Осмотров ещё не было</p>}
        <InfoRow label="Следующий осмотр">{c.next_inspection_at ? formatDate(c.next_inspection_at) : '—'}</InfoRow>
      </section>

      {(c.open_cases.length > 0 || c.open_tasks.length > 0) && (
        <section className="card">
          <h2 className="card__title">Болезни и напоминания</h2>
          {c.open_cases.map((d) => <InfoRow key={d.disease_name} label={d.disease_name}>{d.status}</InfoRow>)}
          {c.open_tasks.map((t) => (
            <InfoRow key={t.title + t.due_date} label={t.title}><span className={t.overdue ? 'warn' : undefined}>{formatDate(t.due_date)}</span></InfoRow>
          ))}
        </section>
      )}

      <section className="card">
        <InfoRow label={`Мёд за ${new Date().getFullYear()}`}>{num(c.honey_year_kg)} кг</InfoRow>
      </section>

      {canInspect && <Link className="btn btn--primary btn--block" to={`/hives/${c.hive_id}/inspect`} replace><Icon name="inspect" size={18} />Провести осмотр</Link>}
      <Link className="btn btn--ghost btn--block" to={`/hives/${c.hive_id}`}>Паспорт улья</Link>
    </div>
  )
}
