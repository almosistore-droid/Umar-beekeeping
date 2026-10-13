import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { num } from '../../utils/labels'

export interface BarRow { key: string; label: ReactNode; sub?: ReactNode; value: number; valueText?: string; to?: string }

/**
 * Horizontal single-series bars for categories and rankings. Every row prints its value as text,
 * so the list is its own table; bars share one hue and start from a common zero.
 */
export function BarList({ rows, unit, ranked, empty = 'Данных пока нет', label }: {
  rows: BarRow[]; unit?: string; ranked?: boolean; empty?: string; label: string
}) {
  const max = Math.max(...rows.map((r) => r.value), 0)
  if (!rows.length || max === 0) return <p className="hint">{empty}</p>
  return (
    <ol className={`rank${ranked ? '' : ' rank--plain'}`} aria-label={label}>
      {rows.map((r, i) => {
        const inner = <>
          {ranked && <span className="rank__pos">{i + 1}</span>}
          <span className="rank__name">{r.label}{r.sub && <small>{r.sub}</small>}</span>
          <span className="rank__bar" aria-hidden><i style={{ width: r.value ? `${Math.max(4, (r.value / max) * 100)}%` : 0 }} /></span>
          <span className="rank__kg">{r.valueText ?? `${num(r.value)}${unit ? ` ${unit}` : ''}`}</span>
        </>
        return <li key={r.key}>{r.to ? <Link to={r.to} className="rank__row">{inner}</Link> : <div className="rank__row">{inner}</div>}</li>
      })}
    </ol>
  )
}
