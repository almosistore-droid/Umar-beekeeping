import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '../api/resources'
import { BarList } from '../components/charts/BarList'
import { ColumnChart } from '../components/charts/ColumnChart'
import { DeliverButtons } from '../components/files/DeliverButtons'
import { LoadingView } from '../components/StateViews'
import { Choice, Chips, ErrorBox, InfoRow } from '../components/ui'
import type { ReportFormat, YearlyReport } from '../types/api'
import { plural } from '../utils/plural'
import { FEED_UNIT, MONTHS_SHORT, PRODUCT_TYPE, formatDate, num } from '../utils/labels'

const FORMATS: { value: ReportFormat; label: string }[] = [
  { value: 'pdf', label: 'PDF' }, { value: 'xlsx', label: 'Excel' }, { value: 'csv', label: 'CSV' },
]
const MONTH_TICKS = MONTHS_SHORT.map((m) => m.slice(0, 1).toUpperCase() + m.slice(1, 3))

function Kv({ value, label }: { value: string | number; label: string }) {
  return <div className="kv"><span className="kv__value">{value}</span><span className="kv__label">{label}</span></div>
}

const ageText = (months: string | null) => {
  if (months === null) return '—'
  const m = Number(months)
  return m >= 12 ? `${num((m / 12).toFixed(1))} года` : `${num(m)} мес.`
}

/** «Отчёты»: yearly report with PDF / Excel / CSV export. */
export function ReportsPage() {
  const current = new Date().getFullYear()
  const [year, setYear] = useState(current)
  const report = useQuery({ queryKey: ['report', year], queryFn: () => reportsApi.yearly(year) })
  const years = report.data?.available_years ?? [current, current - 1]

  return (
    <div className="page">
      <h1 className="page__title">Годовой отчёт</h1>
      <Chips options={years.map((y) => ({ value: String(y), label: String(y) }))} value={String(year)} onChange={(v) => setYear(Number(v))} />
      <ErrorBox error={report.error} />
      {report.isLoading || !report.data ? (report.isLoading ? <LoadingView text="Считаем отчёт…" /> : null) : <Report r={report.data} />}
    </div>
  )
}

function Report({ r }: { r: YearlyReport }) {
  const [format, setFormat] = useState<ReportFormat>('pdf')
  const label = FORMATS.find((f) => f.value === format)!.label
  const { hives: h, queens: q, honey: m, diseases: d } = r
  return <>
    {r.is_partial && <p className="hint">Данные с 1 января по {formatDate(r.period_end)} — год ещё не закончился.</p>}

    <section className="card">
      <h2 className="card__title">Ульи</h2>
      <div className="kv-grid">
        <Kv value={h.at_start} label="На начало года" />
        <Kv value={h.at_end} label={r.is_partial ? 'Сейчас' : 'На конец года'} />
      </div>
      <InfoRow label="Новые">{h.new}</InfoRow>
      <InfoRow label="Потеряны">{h.lost}</InfoRow>
      <InfoRow label="Проданы">{h.sold}</InfoRow>
      <InfoRow label="Объединены">{h.merged}</InfoRow>
      <InfoRow label="Отводки (разделения)">{h.split}</InfoRow>
    </section>

    <section className="card">
      <h2 className="card__title">Матки</h2>
      <div className="kv-grid">
        <Kv value={q.in_hives} label="В ульях" />
        <Kv value={ageText(q.avg_age_months)} label="Средний возраст" />
      </div>
      <InfoRow label="Новые">{q.new}</InfoRow>
      <InfoRow label="Заменены">{q.replaced}</InfoRow>
      {q.age_unknown > 0 && <InfoRow label="Возраст неизвестен">{q.age_unknown}</InfoRow>}
      {q.best_families.length > 0 && <>
        <h3 className="form-section-title">Лучшие семьи по мёду</h3>
        <BarList label="Лучшие семьи по сбору мёда" ranked unit="кг"
          rows={q.best_families.map((b) => ({ key: b.hive_id, label: `№${b.hive_number}`, sub: b.queen_code ? `матка ${b.queen_code}` : b.apiary_name, value: Number(b.kg), to: `/hives/${b.hive_id}` }))} />
      </>}
    </section>

    <section className="card">
      <h2 className="card__title">Мёд</h2>
      <div className="kv-grid">
        <Kv value={`${num(m.total_kg)} кг`} label="Всего собрано" />
        <Kv value={`${num(m.avg_per_hive_kg)} кг`} label={`В среднем на улей (${m.producing_hives})`} />
      </div>
      <InfoRow label="Лучший улей">{m.best_hive ? <Link className="link" to={`/hives/${m.best_hive.hive_id}`}>№{m.best_hive.hive_number} — {num(m.best_hive.kg)} кг</Link> : '—'}</InfoRow>
      <InfoRow label="Худший улей">{m.worst_hive ? <Link className="link" to={`/hives/${m.worst_hive.hive_id}`}>№{m.worst_hive.hive_number} — {num(m.worst_hive.kg)} кг</Link> : '—'}</InfoRow>
      {Number(m.value) > 0 && <InfoRow label="Стоимость мёда">{num(m.value)}</InfoRow>}
      {m.products.map((p) => <InfoRow key={p.product_type + p.unit} label={PRODUCT_TYPE[p.product_type]}>{num(p.quantity)} {FEED_UNIT[p.unit]}</InfoRow>)}
    </section>
    <ColumnChart title="Мёд по месяцам, кг" unit="кг" labelHeader="Месяц" labels={MONTHS_SHORT} shortLabels={MONTH_TICKS} values={m.by_month.map(Number)} />

    <section className="card">
      <h2 className="card__title">Болезни</h2>
      <div className="kv-grid">
        <Kv value={d.cases} label="Случаев выявлено" />
        <Kv value={`${d.resolved} / ${d.open}`} label="Вылечено / не вылечено" />
      </div>
      <BarList label="Болезни по видам" empty="Болезней не было"
        rows={d.by_disease.map((x) => ({ key: x.name, label: x.name, sub: x.open ? `не вылечено: ${x.open}` : 'все вылечены', value: x.cases,
          valueText: `${x.cases} ${plural(x.cases, 'случай', 'случая', 'случаев')}` }))} />
      <InfoRow label="Обработок">{d.treatments}</InfoRow>
      {d.medications.map((x) => <InfoRow key={x.medication} label={x.medication}>{x.count} {plural(x.count, 'раз', 'раза', 'раз')}</InfoRow>)}
    </section>

    <section className="card">
      <h2 className="card__title">Финансы</h2>
      <InfoRow label="Стоимость продукции">{num(r.finance.production_value)}</InfoRow>
      <p className="hint small">По ценам, указанным в записях мёда и продукции. Доходы, расходы и прибыль появятся на этапе 7.</p>
    </section>

    <section className="card form">
      <h2 className="card__title">Выгрузить отчёт</h2>
      <div className="format-pills"><Choice label="Формат" options={FORMATS} value={format} onChange={(v) => v && setFormat(v)} /></div>
      <DeliverButtons key={format} fileLabel={label}
        send={() => reportsApi.send(r.year, format)}
        download={() => reportsApi.download(r.year, format)}
        sentNote={() => <>Отчёт ({label}) отправлен в чат с ботом.</>} />
    </section>
  </>
}
