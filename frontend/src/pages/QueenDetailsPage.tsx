import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '../api/client'
import { queensApi } from '../api/resources'
import { Badge, ErrorBox, InfoRow } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { MARKING, QUEEN_ORIGIN, QUEEN_STATUS, formatDate } from '../utils/labels'

const stars = (n: number | null) => (n ? '★'.repeat(n) + '☆'.repeat(5 - n) : '—')

export function QueenDetailsPage() {
  const { id = '' } = useParams()
  const { canManage } = usePermissions()
  const queen = useQuery({ queryKey: ['queen', id], queryFn: () => queensApi.get(id) })
  const history = useQuery({ queryKey: ['queen-history', id], queryFn: () => queensApi.history(id) })

  if (queen.isLoading) return <LoadingView />
  if (queen.error) {
    return queen.error instanceof ApiError && queen.error.status === 404
      ? <MessageView icon="❌" title="Матка не найдена" />
      : <div className="page"><ErrorBox error={queen.error} /></div>
  }
  const q = queen.data!
  const mark = q.marking_color ? MARKING[q.marking_color] : undefined

  return (
    <div className="page">
      <header className="hive-head">
        <div>
          <p className="hint">{q.breed ?? 'Порода не указана'}</p>
          <h1 className="page__title">👑 {q.queen_code}</h1>
        </div>
        {canManage && <Link className="icon-btn" to={`/queens/${q.id}/edit`} aria-label="Изменить матку">✏️</Link>}
      </header>
      <div className="row row--start"><Badge tone={QUEEN_STATUS[q.status].tone}>{QUEEN_STATUS[q.status].label}</Badge></div>

      <section className="card">
        <InfoRow label="Возраст"><b>{q.age_label ?? '—'}</b></InfoRow>
        <InfoRow label="Рождение">{q.birth_date ? formatDate(q.birth_date) : q.birth_year ?? '—'}</InfoRow>
        <InfoRow label="Происхождение">{QUEEN_ORIGIN[q.origin]}</InfoRow>
        <InfoRow label="Метка">{mark ? <><i className="dot" style={{ background: mark.color }} />{mark.label}</> : '—'}</InfoRow>
        <InfoRow label="Улей">
          {q.current_hive ? <Link className="link" to={`/hives/${q.current_hive.id}`}>№{q.current_hive.hive_number} · {q.current_hive.apiary_name}</Link> : 'не в улье'}
        </InfoRow>
        {q.current_hive && <InfoRow label="Подсажена">{formatDate(q.installed_at)}</InfoRow>}
        {q.removed_at && <InfoRow label="Выбыла">{formatDate(q.removed_at)}</InfoRow>}
        {q.removal_reason && <InfoRow label="Причина">{q.removal_reason}</InfoRow>}
      </section>

      <section className="card">
        <h2 className="card__title">Оценка</h2>
        <InfoRow label="Яйценоскость"><span className="stars">{stars(q.egg_laying_quality)}</span></InfoRow>
        <InfoRow label="Ройливость"><span className="stars">{stars(q.swarming_tendency)}</span></InfoRow>
        <InfoRow label="Миролюбие"><span className="stars">{stars(q.temperament)}</span></InfoRow>
        {q.notes && <p className="notes">{q.notes}</p>}
      </section>

      <section className="card">
        <h2 className="card__title">📜 Где жила</h2>
        {!history.data?.length ? <p className="hint">Ещё не была в улье</p> : (
          <ul className="plain-list">
            {history.data.map((a) => (
              <li key={a.id}>
                <Link to={`/hives/${a.hive_id}`} className="link"><b>Улей №{a.hive_number}</b></Link>
                <div className="small hint">{formatDate(a.installed_at)} — {a.removed_at ? formatDate(a.removed_at) : 'сейчас'}</div>
                {a.removal_reason && <div className="small hint">{a.removal_reason}</div>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
