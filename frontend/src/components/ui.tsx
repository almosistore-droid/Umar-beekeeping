import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { Icon } from './Icon'
import type { Tone } from '../utils/labels'
import { haptic } from '../services/telegram'

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`badge badge--${tone}`}>{children}</span>
}

export function StrengthBars({ bars, label }: { bars: number; label?: string }) {
  return (
    <span className="strength" aria-label={label}>
      {[1, 2, 3, 4, 5].map((i) => <i key={i} className={i <= bars ? 'on' : ''} />)}
      {label && <span className="strength__label">{label}</span>}
    </span>
  )
}

export function Chips<T extends string>({ options, value, onChange }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void
}) {
  return (
    <div className="chips" role="tablist">
      {options.map((o) => (
        <button key={o.value} type="button" role="tab" aria-selected={o.value === value}
          className={`chips__item${o.value === value ? ' is-active' : ''}`}
          onClick={() => { haptic('light'); onChange(o.value) }}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Field({ label, error, hint, children }: { label: string; error?: string; hint?: string; children: ReactNode }) {
  return (
    <label className={`field${error ? ' has-error' : ''}`}>
      <span className="field__label">{label}</span>
      {children}
      {error ? <span className="field__error">{error}</span> : hint ? <span className="field__hint">{hint}</span> : null}
    </label>
  )
}

export function Select<T extends string>({ value, onChange, options, placeholder }: {
  value: T | ''; onChange: (v: T) => void; options: { value: T; label: string }[]; placeholder?: string
}) {
  return (
    <select className="input" value={value} onChange={(e) => onChange(e.target.value as T)}>
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null
  const message = error instanceof ApiError || error instanceof Error ? error.message : 'Что-то пошло не так'
  return <div className="error-box" role="alert">{message}</div>
}

/** Pick the API field error for a form input, e.g. fieldError(err, 'hive_number'). */
export function fieldError(error: unknown, field: string): string | undefined {
  if (!(error instanceof ApiError)) return undefined
  return error.fieldErrors.find((e) => e.field === field || e.field.endsWith(`.${field}`))?.message
}

export function Fab({ to, label }: { to: string; label: string }) {
  return <Link to={to} className="fab" onClick={() => haptic('light')}><Icon name="plus" />{label}</Link>
}

export function Sheet({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = '' }
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="sheet" role="dialog" aria-modal="true" aria-label={title}>
      <div className="sheet__backdrop" onClick={onClose} />
      <div className="sheet__panel">
        <div className="sheet__head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Закрыть">✕</button>
        </div>
        <div className="sheet__body">{children}</div>
      </div>
    </div>
  )
}

export function SubmitButton({ pending, children, danger }: { pending: boolean; children: ReactNode; danger?: boolean }) {
  return (
    <button type="submit" className={`btn btn--block ${danger ? 'btn--danger' : 'btn--primary'}`} disabled={pending}>
      {pending ? 'Сохранение…' : children}
    </button>
  )
}

export function InfoRow({ label, children }: { label: string; children: ReactNode }) {
  return <div className="row"><span className="hint">{label}</span><span className="row__value">{children}</span></div>
}
