import { useState } from 'react'
import { ColumnChart } from '../components/charts/ColumnChart'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { harvestApi } from '../api/resources'
import { Chips, ErrorBox } from '../components/ui'
import { LoadingView } from '../components/StateViews'
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

        <ColumnChart title="По месяцам, кг" unit="кг" labelHeader="Месяц" labels={MONTHS_SHORT} values={s.by_month.map(Number)}
          shortLabels={MONTHS_SHORT.map((m) => m.slice(0, 1).toUpperCase() + m.slice(1, 3))} />

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
