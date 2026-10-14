import { useState, type ReactNode } from 'react'
import { num } from '../../utils/labels'
import { tr } from '../../i18n'

/**
 * Single-series columns (one hue, no legend — the title names the series). Tap or hover a column
 * for its value; the peak is labelled when nothing is selected; «Таблица» shows exact numbers.
 */
export function ColumnChart({ title, labels, shortLabels, values, unit, labelHeader = '', action }: {
  title: string
  labels: string[]
  shortLabels?: string[]
  values: number[]
  unit: string
  labelHeader?: string
  action?: ReactNode
}) {
  const [active, setActive] = useState<number | null>(null)
  const [asTable, setAsTable] = useState(false)
  const max = Math.max(...values, 0)
  const peak = values.indexOf(max)
  return (
    <section className="card">
      <div className="card__titlebar">
        <h2 className="card__title">{title}</h2>
        {max > 0 && <button type="button" className="link-btn small" onClick={() => setAsTable((v) => !v)}>{asTable ? tr("График") : tr("Таблица")}</button>}
        {action}
      </div>
      {max === 0 ? <p className="hint">{tr("Данных пока нет")}</p> : asTable ? (
        <table className="data-table">
          <thead><tr><th>{labelHeader}</th><th>{unit}</th></tr></thead>
          <tbody>{values.map((v, i) => v > 0 && <tr key={i}><td>{labels[i]}</td><td>{num(v)}</td></tr>)}</tbody>
        </table>
      ) : (
        <div className="bars" style={{ gridTemplateColumns: `repeat(${values.length}, 1fr)` }} role="img"
          aria-label={`${title}: ` + values.map((v, i) => `${labels[i]} ${num(v)} ${unit}`).filter((_, i) => values[i] > 0).join(', ')}>
          {values.map((v, i) => {
            const isActive = active === i
            return (
              <button key={i} type="button" className={`bars__col${isActive ? ' is-active' : ''}`}
                onClick={() => setActive(isActive ? null : i)} onMouseEnter={() => setActive(i)} onMouseLeave={() => setActive(null)}
                aria-label={`${labels[i]}: ${num(v)} ${unit}`}>
                <span className="bars__track">
                  {(isActive || (active === null && i === peak)) && v > 0 && <span className="bars__tip">{num(v)}</span>}
                  <span className="bars__bar" style={{ height: `${v ? Math.max(3, (v / max) * 100) : 0}%` }} />
                </span>
                <span className="bars__label">{(shortLabels ?? labels)[i]}</span>
              </button>
            )
          })}
        </div>
      )}
    </section>
  )
}
