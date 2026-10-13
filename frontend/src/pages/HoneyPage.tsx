import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { harvestApi } from '../api/resources'
import { Chips, ErrorBox } from '../components/ui'
import { LoadingView } from '../components/StateViews'
import type { HoneyStats } from '../types/api'
import { MONTHS_SHORT, num } from '../utils/labels'

export function HoneyPage() {
  const now = new Date().getFullYear()
  const [year, setYear] = useState(now)
  const stats = useQuery({ queryKey: ['honey-stats', year], queryFn: () => harvestApi.stats(year) })
  const s = stats.data

  return (
    <div className="page">
      <h1 className="page__title">Мёд</h1>
      <Chips options={[now, now - 1, now - 2].map((y) => ({ value: String(y), label: String(y) }))}
        value={String(year)} onChange={(v) => setYear(Number(v))} />
      <ErrorBox error={stats.error} />
      {stats.isLoading || !s ? <LoadingView /> : <>
        <section className="honey-hero">
          <div className="honey-hero__value"><span>{num(s.year_kg)}</span> кг</div>
          <div className="hint">собрано за {year} год{s.producing_hives ? `, ${s.producing_hives} ульев дали мёд` : ''}</div>
        </section>

        <div className="stat-row">
          {year === now && <Stat label="В этом месяце" value={`${num(s.month_kg)} кг`} />}
          <Stat label="В среднем на улей" value={`${num(s.avg_per_hive_kg)} кг`} />
          <Stat label="За всё время" value={`${num(s.all_time_kg)} кг`} />
          {Number(s.year_value) > 0 && <Stat label="Стоимость" value={num(s.year_value)} />}
        </div>

        <MonthChart stats={s} />

        <section className="card">
          <h2 className="card__title">Ульи по сбору</h2>
          {!s.by_hive.length ? <p className="hint">В {year} году откачек не было.</p> : (
            <ol className="rank">
              {s.by_hive.slice(0, 15).map((h, i) => {
                const share = Number(h.kg) / Number(s.by_hive[0].kg)
                return (
                  <li key={h.hive_id}>
                    <Link to={`/hives/${h.hive_id}`} className="rank__row">
                      <span className="rank__pos">{i + 1}</span>
                      <span className="rank__name">№{h.hive_number}<small>{h.apiary_name}</small></span>
                      <span className="rank__bar" aria-hidden><i style={{ width: `${Math.max(4, share * 100)}%` }} /></span>
                      <span className="rank__kg">{num(h.kg)} кг</span>
                    </Link>
                  </li>
                )
              })}
            </ol>
          )}
        </section>
      </>}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="stat"><span className="stat__value">{value}</span><span className="stat__label">{label}</span></div>
}

/** Kg by month — one series, so one hue and no legend; tap a bar for its value; table for exact numbers. */
function MonthChart({ stats }: { stats: HoneyStats }) {
  const [active, setActive] = useState<number | null>(null)
  const [asTable, setAsTable] = useState(false)
  const values = stats.by_month.map(Number)
  const max = Math.max(...values, 0)
  const peak = values.indexOf(max)
  if (max === 0) return null
  return (
    <section className="card">
      <div className="card__titlebar">
        <h2 className="card__title">По месяцам, кг</h2>
        <button type="button" className="link-btn small" onClick={() => setAsTable((v) => !v)}>{asTable ? 'График' : 'Таблица'}</button>
      </div>
      {asTable ? (
        <table className="data-table">
          <thead><tr><th>Месяц</th><th>кг</th></tr></thead>
          <tbody>{values.map((v, i) => v > 0 && <tr key={i}><td>{MONTHS_SHORT[i]}</td><td>{num(v)}</td></tr>)}</tbody>
        </table>
      ) : (
        <div className="bars" role="img" aria-label={`Сбор мёда по месяцам ${stats.year}: ` + values.map((v, i) => `${MONTHS_SHORT[i]} ${num(v)} кг`).filter((_, i) => values[i] > 0).join(', ')}>
          {values.map((v, i) => {
            const isActive = active === i
            return (
              <button key={i} type="button" className={`bars__col${isActive ? ' is-active' : ''}`}
                onClick={() => setActive(isActive ? null : i)} onMouseEnter={() => setActive(i)} onMouseLeave={() => setActive(null)}
                aria-label={`${MONTHS_SHORT[i]}: ${num(v)} кг`}>
                <span className="bars__track">
                  {(isActive || (active === null && i === peak)) && v > 0 && <span className="bars__tip">{num(v)}</span>}
                  <span className="bars__bar" style={{ height: `${v ? Math.max(3, (v / max) * 100) : 0}%` }} />
                </span>
                <span className="bars__label">{MONTHS_SHORT[i].slice(0, 1).toUpperCase() + MONTHS_SHORT[i].slice(1, 3)}</span>
              </button>
            )
          })}
        </div>
      )}
    </section>
  )
}
