import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { hivesApi, queensApi } from '../api/resources'
import { Icon, type IconName } from '../components/Icon'
import { LOGO_SRC } from '../components/StateViews'
import { useAuth } from '../hooks/useAuth'
import { ROLE_LABELS, type FamilyStrength, type HiveStatus } from '../types/api'
import { plural } from '../utils/plural'

/** Live counts from hives/queens. The full dashboard with charts arrives in stage 6. */
export function HomePage() {
  const { user } = useAuth()
  const hives = useQuery({ queryKey: ['hives', 'home'], queryFn: () => hivesApi.list({ include_archived: false }) })
  const queens = useQuery({ queryKey: ['queens', 'home'], queryFn: () => queensApi.list({ in_hive: true }) })

  const items = hives.data?.items ?? []
  const count = (...s: HiveStatus[]) => (hives.data ? items.filter((h) => s.includes(h.status)).length : undefined)
  const strong = (s: FamilyStrength[]) => (hives.data ? items.filter((h) => h.strength && s.includes(h.strength)).length : undefined)
  const total = hives.data?.total

  const tiles: { icon: IconName; label: string; value: number | undefined; alert?: boolean }[] = [
    { icon: 'crown', label: 'Маток в ульях', value: queens.data?.total },
    { icon: 'strong', label: 'Сильные семьи', value: strong(['STRONG', 'VERY_STRONG']) },
    { icon: 'weak', label: 'Слабые семьи', value: strong(['WEAK', 'VERY_WEAK']), alert: true },
    { icon: 'sick', label: 'Больные', value: count('SICK', 'QUARANTINE'), alert: true },
    { icon: 'queenless', label: 'Без матки', value: count('QUEENLESS'), alert: true },
  ]

  return (
    <div className="page">
      <header className="brand-hero">
        <img className="brand-hero__logo" src={LOGO_SRC} alt="Fayzi Umar" width={76} height={76} />
        <div className="brand-hero__text">
          <span className="brand-hero__name">Fayzi Umar</span>
          <span className="brand-hero__sub">Учёт пасеки</span>
        </div>
      </header>

      <div className="greeting">
        <span className="greeting__name">Салом, {user?.first_name ?? user?.display_name ?? 'пчеловод'}</span>
        {user && <span className="chip">{ROLE_LABELS[user.role]}</span>}
      </div>

      <div className="tiles">
        <Link to="/hives" className="tile tile--lead">
          <span className="tile__icon"><Icon name="hive" /></span>
          <span>
            <span className="tile__value" style={{ display: 'block' }}>{total ?? '…'}</span>
            <span className="tile__label">{total === undefined ? 'ульев' : `${plural(total, 'улей', 'улья', 'ульев')} на пасеках`}</span>
          </span>
        </Link>
        {tiles.map((t) => (
          <Link key={t.label} to={t.label.includes('Мат') ? '/queens' : '/hives'}
            className={`tile${t.alert && t.value ? ' tile--alert' : ''}`}>
            <span className="tile__icon"><Icon name={t.icon} /></span>
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
