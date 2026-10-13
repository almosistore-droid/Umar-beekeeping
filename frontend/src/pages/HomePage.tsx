import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '../api/resources'
import { BarList } from '../components/charts/BarList'
import { ColumnChart } from '../components/charts/ColumnChart'
import { Icon, type IconName } from '../components/Icon'
import { LOGO_SRC } from '../components/StateViews'
import { ErrorBox } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { ROLE_LABELS } from '../types/api'
import { plural } from '../utils/plural'
import { MONTHS_SHORT, num } from '../utils/labels'

const STRENGTH_FILTER: Record<string, string | undefined> = {
  VERY_WEAK: '/hives?filter=weak', WEAK: '/hives?filter=weak', STRONG: '/hives?filter=strong', VERY_STRONG: '/hives?filter=strong',
}
const MONTH_TICKS = MONTHS_SHORT.map((m) => m.slice(0, 1).toUpperCase() + m.slice(1, 3))

/** Dashboard: counters and charts from one request (GET /api/dashboard). */
export function HomePage() {
  const { user } = useAuth()
  const year = new Date().getFullYear()
  const dash = useQuery({ queryKey: ['dashboard', year], queryFn: () => reportsApi.dashboard(year) })
  const d = dash.data
  const t = d?.tiles

  const tiles: { icon: IconName; label: string; value: number | undefined; alert?: boolean; to?: string }[] = [
    { icon: 'inspect', label: 'Требуют осмотра', value: t?.needs_inspection, alert: true, to: '/hives?filter=inspection' },
    { icon: 'treat', label: t?.overdue_tasks ? `Напоминания, просрочено ${t.overdue_tasks}` : 'Напоминания', value: t?.open_tasks, alert: !!t?.overdue_tasks, to: '/tasks' },
    { icon: 'strong', label: 'Сильные семьи', value: t?.strong, to: '/hives?filter=strong' },
    { icon: 'weak', label: 'Слабые семьи', value: t?.weak, alert: true, to: '/hives?filter=weak' },
    { icon: 'sick', label: 'Больные', value: t?.sick, alert: true, to: '/hives?filter=sick' },
    { icon: 'queenless', label: 'Без матки', value: t?.queenless, alert: true, to: '/hives?filter=queenless' },
    { icon: 'crown', label: 'Маток в ульях', value: t?.queens_in_hives, to: '/queens' },
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
      <ErrorBox error={dash.error} />

      <div className="tiles">
        <Link to="/hives" className="tile tile--lead">
          <span className="tile__icon"><Icon name="hive" /></span>
          <span>
            <span className="tile__value" style={{ display: 'block' }}>{t?.hives ?? '…'}</span>
            <span className="tile__label">{t === undefined ? 'ульев' : `${plural(t.hives, 'улей', 'улья', 'ульев')} на пасеках`}</span>
          </span>
        </Link>
        {tiles.map((x) => (
          <Link key={x.icon} to={x.to ?? '/hives'} className={`tile${x.alert && x.value ? ' tile--alert' : ''}`}>
            <span className="tile__icon"><Icon name={x.icon} /></span>
            <span className="tile__value">{x.value ?? '…'}</span>
            <span className="tile__label">{x.label}</span>
          </Link>
        ))}
      </div>

      <Link to="/honey" className="tile tile--honey">
        <span className="tile__icon"><Icon name="honey" /></span>
        <span>
          <span className="tile__value" style={{ display: 'block' }}>{t ? num(t.honey_year_kg) : '…'} <small>кг</small></span>
          <span className="tile__label">мёда за {year} год{t?.best_hive ? `, лучший улей №${t.best_hive.hive_number}` : ''}</span>
        </span>
      </Link>

      {d?.finance && (
        <Link to="/crm" className="finance-strip" aria-label="Финансы за год">
          {[['Доход', d.finance.income], ['Расход', d.finance.expenses], ['Прибыль', d.finance.profit]].map(([label, v]) => (
            <span key={label} className="finance-strip__item">
              <span className={`finance-strip__value${label === 'Прибыль' ? (Number(v) >= 0 ? ' money__value--ok' : ' money__value--bad') : ''}`}>{num(v)}</span>
              <span className="tile__label">{label}, {d.finance!.currency}</span>
            </span>
          ))}
          {Number(d.finance.debts_total) > 0 && <span className="tile__soon finance-strip__note">долги {num(d.finance.debts_total)}</span>}
        </Link>
      )}

      {d && <>
        <h2 className="section-title">Графики {year}</h2>
        <ColumnChart title="Мёд по месяцам, кг" unit="кг" labelHeader="Месяц" labels={MONTHS_SHORT}
          shortLabels={MONTH_TICKS} values={d.honey_by_month.map(Number)} />

        {d.finance && <>
          <ColumnChart title={`Доход по месяцам, ${d.finance.currency}`} unit={d.finance.currency} labelHeader="Месяц" labels={MONTHS_SHORT}
            shortLabels={MONTH_TICKS} values={d.finance.income_by_month.map(Number)} />
          <ColumnChart title={`Расход по месяцам, ${d.finance.currency}`} unit={d.finance.currency} labelHeader="Месяц" labels={MONTHS_SHORT}
            shortLabels={MONTH_TICKS} values={d.finance.expenses_by_month.map(Number)} />
        </>}

        <section className="card">
          <div className="card__titlebar">
            <h2 className="card__title">Мёд по ульям, кг</h2>
            <Link to="/honey" className="link-btn small">Все</Link>
          </div>
          <BarList label="Мёд по ульям" ranked unit="кг" empty={`В ${year} году откачек не было`}
            rows={d.honey_by_hive.map((h) => ({ key: h.hive_id, label: `№${h.hive_number}`, sub: h.apiary_name, value: Number(h.kg), to: `/hives/${h.hive_id}` }))} />
        </section>

        <section className="card">
          <h2 className="card__title">Сила семей</h2>
          <BarList label="Сила семей, число семей" empty="Семей пока нет"
            rows={d.strength.map((b) => ({ key: b.key, label: b.label, value: b.count, to: b.count ? STRENGTH_FILTER[b.key] : undefined }))} />
        </section>

        <section className="card">
          <h2 className="card__title">Болезни за {year} год</h2>
          <BarList label="Случаи болезней" empty="Болезней не было"
            rows={d.diseases.map((x) => ({ key: x.name, label: x.name, sub: x.open ? `не вылечено: ${x.open}` : 'все вылечены', value: x.cases,
              valueText: `${x.cases} ${plural(x.cases, 'случай', 'случая', 'случаев')}` }))} />
        </section>

        <section className="card">
          <h2 className="card__title">Возраст маток</h2>
          <BarList label="Возраст маток в ульях" empty="Маток в ульях нет"
            rows={d.queen_ages.filter((b) => b.key !== 'unknown' || b.count).map((b) => ({ key: b.key, label: b.label, value: b.count }))} />
        </section>

        <Link to="/reports" className="btn btn--secondary btn--block"><Icon name="chart" size={18} />Годовой отчёт</Link>
      </>}
    </div>
  )
}
