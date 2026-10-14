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
import { FEED_UNIT, MONTHS_SHORT, PRODUCT_TYPE, formatDate, money, num } from '../utils/labels'
import { tr } from '../i18n'

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
  return m >= 12 ? tr("{0} года", num((m / 12).toFixed(1))) : tr("{0} мес.", num(m))
}

/** «Отчёты»: yearly report with PDF / Excel / CSV export. */
export function ReportsPage() {
  const current = new Date().getFullYear()
  const [year, setYear] = useState(current)
  const report = useQuery({ queryKey: ['report', year], queryFn: () => reportsApi.yearly(year) })
  const years = report.data?.available_years ?? [current, current - 1]

  return (
    <div className="page">
      <h1 className="page__title">{tr("Годовой отчёт")}</h1>
      <Chips options={years.map((y) => ({ value: String(y), label: String(y) }))} value={String(year)} onChange={(v) => setYear(Number(v))} />
      <ErrorBox error={report.error} />
      {report.isLoading || !report.data ? (report.isLoading ? <LoadingView text={tr("Считаем отчёт…")} /> : null) : <Report r={report.data} />}
    </div>
  )
}

function Report({ r }: { r: YearlyReport }) {
  const [format, setFormat] = useState<ReportFormat>('pdf')
  const label = FORMATS.find((f) => f.value === format)!.label
  const { hives: h, queens: q, honey: m, diseases: d } = r
  return <>
    {r.is_partial && <p className="hint">{tr("Данные с 1 января по {0} — год ещё не закончился.", formatDate(r.period_end))}</p>}

    <section className="card">
      <h2 className="card__title">{tr("Ульи")}</h2>
      <div className="kv-grid">
        <Kv value={h.at_start} label={tr("На начало года")} />
        <Kv value={h.at_end} label={r.is_partial ? tr("Сейчас") : tr("На конец года")} />
      </div>
      <InfoRow label={tr("Новые")}>{h.new}</InfoRow>
      <InfoRow label={tr("Потеряны")}>{h.lost}</InfoRow>
      <InfoRow label={tr("Проданы")}>{h.sold}</InfoRow>
      <InfoRow label={tr("Объединены")}>{h.merged}</InfoRow>
      <InfoRow label={tr("Отводки (разделения)")}>{h.split}</InfoRow>
    </section>

    <section className="card">
      <h2 className="card__title">{tr("Матки")}</h2>
      <div className="kv-grid">
        <Kv value={q.in_hives} label={tr("В ульях")} />
        <Kv value={ageText(q.avg_age_months)} label={tr("Средний возраст")} />
      </div>
      <InfoRow label={tr("Новые")}>{q.new}</InfoRow>
      <InfoRow label={tr("Заменены")}>{q.replaced}</InfoRow>
      {q.age_unknown > 0 && <InfoRow label={tr("Возраст неизвестен")}>{q.age_unknown}</InfoRow>}
      {q.best_families.length > 0 && <>
        <h3 className="form-section-title">{tr("Лучшие семьи по мёду")}</h3>
        <BarList label={tr("Лучшие семьи по сбору мёда")} ranked unit={tr("кг")}
          rows={q.best_families.map((b) => ({ key: b.hive_id, label: `№${b.hive_number}`, sub: b.queen_code ? tr("матка {0}", b.queen_code) : b.apiary_name, value: Number(b.kg), to: `/hives/${b.hive_id}` }))} />
      </>}
    </section>

    <section className="card">
      <h2 className="card__title">{tr("Мёд")}</h2>
      <div className="kv-grid">
        <Kv value={tr("{0} кг", num(m.total_kg))} label={tr("Всего собрано")} />
        <Kv value={tr("{0} кг", num(m.avg_per_hive_kg))} label={tr("В среднем на улей ({0})", m.producing_hives)} />
      </div>
      <InfoRow label={tr("Лучший улей")}>{m.best_hive ? <Link className="link" to={`/hives/${m.best_hive.hive_id}`}>{tr("№{0} — {1} кг", m.best_hive.hive_number, num(m.best_hive.kg))}</Link> : '—'}</InfoRow>
      <InfoRow label={tr("Худший улей")}>{m.worst_hive ? <Link className="link" to={`/hives/${m.worst_hive.hive_id}`}>{tr("№{0} — {1} кг", m.worst_hive.hive_number, num(m.worst_hive.kg))}</Link> : '—'}</InfoRow>
      {Number(m.value) > 0 && <InfoRow label={tr("Стоимость мёда")}>{num(m.value)}</InfoRow>}
      {m.products.map((p) => <InfoRow key={p.product_type + p.unit} label={PRODUCT_TYPE[p.product_type]}>{num(p.quantity)} {FEED_UNIT[p.unit]}</InfoRow>)}
    </section>
    <ColumnChart title={tr("Мёд по месяцам, кг")} unit={tr("кг")} labelHeader={tr("Месяц")} labels={MONTHS_SHORT} shortLabels={MONTH_TICKS} values={m.by_month.map(Number)} />

    <section className="card">
      <h2 className="card__title">{tr("Болезни")}</h2>
      <div className="kv-grid">
        <Kv value={d.cases} label={tr("Случаев выявлено")} />
        <Kv value={`${d.resolved} / ${d.open}`} label={tr("Вылечено / не вылечено")} />
      </div>
      <BarList label={tr("Болезни по видам")} empty={tr("Болезней не было")}
        rows={d.by_disease.map((x) => ({ key: x.name, label: x.name, sub: x.open ? tr("не вылечено: {0}", x.open) : tr("все вылечены"), value: x.cases,
          valueText: `${x.cases} ${plural(x.cases, tr("случай"), tr("случая"), tr("случаев"))}` }))} />
      <InfoRow label={tr("Обработок")}>{d.treatments}</InfoRow>
      {d.medications.map((x) => <InfoRow key={x.medication} label={x.medication}>{x.count} {plural(x.count, tr("раз"), tr("раза"), tr("раз"))}</InfoRow>)}
    </section>

    <section className="card">
      <h2 className="card__title">{tr("Финансы")}</h2>
      {r.finance.visible ? <>
        <div className="kv-grid">
          <Kv value={money(r.finance.income, r.finance.currency)} label={tr("Доход")} />
          <Kv value={money(r.finance.expenses, r.finance.currency)} label={tr("Расход")} />
        </div>
        <InfoRow label={tr("Прибыль")}><b className={Number(r.finance.profit) >= 0 ? 'money__value--ok' : 'money__value--bad'}>{money(r.finance.profit, r.finance.currency)}</b></InfoRow>
        <InfoRow label={tr("Получено денег")}>{money(r.finance.received, r.finance.currency)}</InfoRow>
        <InfoRow label={tr("Долги клиентов сейчас")}>{money(r.finance.debts_total, r.finance.currency)}</InfoRow>
        {r.finance.income_by_category.length > 0 && <>
          <h3 className="form-section-title">{tr("Доход по видам")}</h3>
          <BarList label={tr("Доход по видам")} unit={r.finance.currency} rows={r.finance.income_by_category.map((x) => ({ key: x.key, label: x.label, value: Number(x.amount) }))} />
        </>}
        {r.finance.expenses_by_category.length > 0 && <>
          <h3 className="form-section-title">{tr("Расход по категориям")}</h3>
          <BarList label={tr("Расход по категориям")} unit={r.finance.currency} rows={r.finance.expenses_by_category.map((x) => ({ key: x.key, label: x.label, value: Number(x.amount) }))} />
        </>}
      </> : <p className="hint small">{tr("Деньги видят администратор и пчеловод.")}</p>}
      <InfoRow label={tr("Стоимость продукции по ценам в записях")}>{money(r.finance.production_value, r.finance.currency)}</InfoRow>
    </section>

    <section className="card form">
      <h2 className="card__title">{tr("Выгрузить отчёт")}</h2>
      <div className="format-pills"><Choice label={tr("Формат")} options={FORMATS} value={format} onChange={(v) => v && setFormat(v)} /></div>
      <DeliverButtons key={format} fileLabel={label}
        send={() => reportsApi.send(r.year, format)}
        download={() => reportsApi.download(r.year, format)}
        sentNote={() => <>{tr("Отчёт ({0}) отправлен в чат с ботом.", label)}</>} />
    </section>
  </>
}
