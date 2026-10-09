import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { hivesApi, queensApi } from '../api/resources'
import { useAuth } from '../hooks/useAuth'
import { ROLE_LABELS, type FamilyStrength, type HiveStatus } from '../types/api'

/** Stage 2 home: live counts from hives/queens. Full dashboard with charts comes in stage 6. */
export function HomePage() {
  const { user } = useAuth()
  const hives = useQuery({ queryKey: ['hives', 'home'], queryFn: () => hivesApi.list({ include_archived: false }) })
  const queens = useQuery({ queryKey: ['queens', 'home'], queryFn: () => queensApi.list({ in_hive: true }) })

  const items = hives.data?.items ?? []
  const count = (...s: HiveStatus[]) => (hives.data ? items.filter((h) => s.includes(h.status)).length : undefined)
  const strong = (s: FamilyStrength[]) => (hives.data ? items.filter((h) => h.strength && s.includes(h.strength)).length : undefined)
  const tiles = [
    { icon: '🐝', label: 'Всего ульев', value: hives.data?.total, to: '/hives' },
    { icon: '👑', label: 'Матки', value: queens.data?.total, to: '/queens' },
    { icon: '💪', label: 'Сильные семьи', value: strong(['STRONG', 'VERY_STRONG']), to: '/hives' },
    { icon: '⚠️', label: 'Слабые семьи', value: strong(['WEAK', 'VERY_WEAK']), to: '/hives' },
    { icon: '🩺', label: 'Больные', value: count('SICK', 'QUARANTINE'), to: '/hives' },
    { icon: '❗', label: 'Без матки', value: count('QUEENLESS'), to: '/hives' },
  ]

  return (
    <div className="page">
      <header className="page__header">
        <p className="hint">Добро пожаловать</p>
        <h1 className="page__title">{user?.display_name ?? 'Пчеловод'} 🐝</h1>
        {user && <span className="chip">{ROLE_LABELS[user.role]}</span>}
      </header>

      <div className="tiles">
        {tiles.map((t) => (
          <Link key={t.label} to={t.to} className="tile">
            <span className="tile__icon" aria-hidden>{t.icon}</span>
            <span className="tile__value">{t.value ?? '…'}</span>
            <span className="tile__label">{t.label}</span>
          </Link>
        ))}
      </div>

      <section className="card card--muted">
        <h2 className="card__title">Скоро здесь</h2>
        <p className="hint">Мёд за год, доходы, расходы, прибыль и графики появятся на этапах 4–7.</p>
      </section>
    </div>
  )
}
