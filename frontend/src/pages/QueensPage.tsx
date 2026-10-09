import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { queensApi, type QueenFilters } from '../api/resources'
import { Badge, Chips, ErrorBox, Fab } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { MARKING, QUEEN_STATUS, REMOVED_QUEEN_STATUSES } from '../utils/labels'

type Filter = 'all' | 'in_hive' | 'free' | 'removed'
const FILTERS: { value: Filter; label: string; params: QueenFilters }[] = [
  { value: 'all', label: 'Работают', params: {} },
  { value: 'in_hive', label: '🐝 В ульях', params: { in_hive: true } },
  { value: 'free', label: '📦 Свободные', params: { in_hive: false } },
  { value: 'removed', label: '🗄 Выбывшие', params: { status: REMOVED_QUEEN_STATUSES } },
]

export function QueensPage() {
  const { canManage } = usePermissions()
  const [filter, setFilter] = useState<Filter>('all')
  const [q, setQ] = useState('')
  const params = FILTERS.find((f) => f.value === filter)!.params
  const queens = useQuery({ queryKey: ['queens', filter, q], queryFn: () => queensApi.list({ ...params, q: q || undefined }) })

  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">Матки</h1>
        {queens.data && <span className="hint">{queens.data.total}</span>}
      </div>
      <input className="input input--search" type="search" placeholder="🔎 Код или порода" value={q} onChange={(e) => setQ(e.target.value)} />
      <Chips options={FILTERS} value={filter} onChange={setFilter} />
      <ErrorBox error={queens.error} />
      {queens.isLoading ? <LoadingView /> : queens.data?.items.length === 0 ? (
        <MessageView icon="👑" title="Маток не найдено" />
      ) : (
        <ul className="list">
          {queens.data?.items.map((m) => (
            <li key={m.id}>
              <Link to={`/queens/${m.id}`} className="hive-card">
                <div className="hive-card__num queen-num">
                  {m.marking_color && MARKING[m.marking_color] && <i className="dot dot--lg" style={{ background: MARKING[m.marking_color].color }} />}
                  👑
                </div>
                <div className="hive-card__body">
                  <div className="hive-card__top">
                    <b>{m.queen_code}</b>
                    <Badge tone={QUEEN_STATUS[m.status].tone}>{QUEEN_STATUS[m.status].label}</Badge>
                  </div>
                  <div className="small">{[m.breed, m.age_label].filter(Boolean).join(' · ') || '—'}</div>
                  <div className="small hint">{m.current_hive ? `Улей №${m.current_hive.hive_number} · ${m.current_hive.apiary_name}` : 'Не в улье'}</div>
                </div>
                <span className="chevron" aria-hidden>›</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {canManage && <Fab to="/queens/new" label="Матка" />}
    </div>
  )
}
