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
import { tr } from '../i18n'

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
    { icon: 'inspect', label: tr("Требуют осмотра"), value: t?.needs_inspection, alert: true, to: '/hives?filter=inspection' },
    { icon: 'treat', label: t?.overdue_tasks ? tr("Напоминания, просрочено {0}", t.overdue_tasks) : tr("Напоминания"), value: t?.open_tasks, alert: !!t?.overdue_tasks, to: '/tasks' },
    { icon: 'strong', label: tr("Сильные семьи"), value: t?.strong, to: '/hives?filter=strong' },
    { icon: 'weak', label: tr("Слабые семьи"), value: t?.weak, alert: true, to: '/hives?filter=weak' },
    { icon: 'sick', label: tr("Больные"), value: t?.sick, alert: true, to: '/hives?filter=sick' },
    { icon: 'queenless', label: tr("Без матки"), value: t?.queenless, alert: true, to: '/hives?filter=queenless' },
    { icon: 'crown', label: tr("Маток в ульях"), value: t?.queens_in_hives, to: '/queens' },
  ]

  return (
    <div className="page">
      <header className="brand-hero">
        <img className="brand-hero__logo" src={LOGO_SRC} alt="Fayzi Umar" width={76} height={76} />
        <div className="brand-hero__text">
          <span className="brand-hero__name">Fayzi Umar</span>
          <span className="brand-hero__sub">{tr("Учёт пасеки")}</span>
        </div>
      </header>

      <div className="greeting">
        <span className="greeting__name">{tr("Салом,")}{" "}{user?.first_name ?? user?.display_name ?? tr("пчеловод")}</span>
        {user && <span className="chip">{ROLE_LABELS[user.role]}</span>}
      </div>
      <ErrorBox error={dash.error} />

      <div className="tiles">
        <Link to="/hives" className="tile tile--lead">
          <span className="tile__icon"><Icon name="hive" /></span>
          <span>
            <span className="tile__value" style={{ display: 'block' }}>{t?.hives ?? '…'}</span>
            <span className="tile__label">{t === undefined ? tr("ульев") : tr("{0} на пасеках", plural(t.hives, tr("улей"), tr("улья"), tr("ульев")))}</span>
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
          <span className="tile__value" style={{ display: 'block' }}>{t ? num(t.honey_year_kg) : '…'} <small>{tr("кг")}</small></span>
          <span className="tile__label">{tr("мёда за {0} год", year)}{t?.best_hive ? tr(", лучший улей №{0}", t.best_hive.hive_number) : ''}</span>
        </span>
      </Link>

      {d?.finance && (
        <Link to="/crm" className="finance-strip" aria-label={tr("Финансы за год")}>
          {[[tr("Доход"), d.finance.income], [tr("Расход"), d.finance.expenses], [tr("Прибыль"), d.finance.profit]].map(([label, v]) => (
            <span key={label} className="finance-strip__item">
              <span className={`finance-strip__value${label === tr("Прибыль") ? (Number(v) >= 0 ? ' money__value--ok' : ' money__value--bad') : ''}`}>{num(v)}</span>
              <span className="tile__label">{label}, {d.finance!.currency}</span>
            </span>
          ))}
          {Number(d.finance.debts_total) > 0 && <span className="tile__soon finance-strip__note">{tr("долги {0}", num(d.finance.debts_total))}</span>}
        </Link>
      )}

      {d && <>
        <h2 className="section-title">{tr("Графики {0}", year)}</h2>
        <ColumnChart title={tr("Мёд по месяцам, кг")} unit={tr("кг")} labelHeader={tr("Месяц")} labels={MONTHS_SHORT}
          shortLabels={MONTH_TICKS} values={d.honey_by_month.map(Number)} />

        {d.finance && <>
          <ColumnChart title={tr("Доход по месяцам, {0}", d.finance.currency)} unit={d.finance.currency} labelHeader={tr("Месяц")} labels={MONTHS_SHORT}
            shortLabels={MONTH_TICKS} values={d.finance.income_by_month.map(Number)} />
          <ColumnChart title={tr("Расход по месяцам, {0}", d.finance.currency)} unit={d.finance.currency} labelHeader={tr("Месяц")} labels={MONTHS_SHORT}
            shortLabels={MONTH_TICKS} values={d.finance.expenses_by_month.map(Number)} />
        </>}

        <section className="card">
          <div className="card__titlebar">
            <h2 className="card__title">{tr("Мёд по ульям, кг")}</h2>
            <Link to="/honey" className="link-btn small">{tr("Все")}</Link>
          </div>
          <BarList label={tr("Мёд по ульям")} ranked unit={tr("кг")} empty={tr("В {0} году откачек не было", year)}
            rows={d.honey_by_hive.map((h) => ({ key: h.hive_id, label: `№${h.hive_number}`, sub: h.apiary_name, value: Number(h.kg), to: `/hives/${h.hive_id}` }))} />
        </section>

        <section className="card">
          <h2 className="card__title">{tr("Сила семей")}</h2>
          <BarList label={tr("Сила семей, число семей")} empty={tr("Семей пока нет")}
            rows={d.strength.map((b) => ({ key: b.key, label: b.label, value: b.count, to: b.count ? STRENGTH_FILTER[b.key] : undefined }))} />
        </section>

        <section className="card">
          <h2 className="card__title">{tr("Болезни за {0} год", year)}</h2>
          <BarList label={tr("Случаи болезней")} empty={tr("Болезней не было")}
            rows={d.diseases.map((x) => ({ key: x.name, label: x.name, sub: x.open ? tr("не вылечено: {0}", x.open) : tr("все вылечены"), value: x.cases,
              valueText: `${x.cases} ${plural(x.cases, tr("случай"), tr("случая"), tr("случаев"))}` }))} />
        </section>

        <section className="card">
          <h2 className="card__title">{tr("Возраст маток")}</h2>
          <BarList label={tr("Возраст маток в ульях")} empty={tr("Маток в ульях нет")}
            rows={d.queen_ages.filter((b) => b.key !== 'unknown' || b.count).map((b) => ({ key: b.key, label: b.label, value: b.count }))} />
        </section>

        <Link to="/reports" className="btn btn--secondary btn--block"><Icon name="chart" size={18} />{tr("Годовой отчёт")}</Link>
      </>}
    </div>
  )
}
