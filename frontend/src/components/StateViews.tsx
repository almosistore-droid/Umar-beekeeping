import type { ReactNode } from 'react'

export function LoadingView({ text = 'Загрузка…' }: { text?: string }) {
  return (
    <div className="state" role="status">
      <div className="spinner" aria-hidden />
      <p className="hint">{text}</p>
    </div>
  )
}

export function MessageView({
  icon,
  title,
  text,
  action,
}: {
  icon: string
  title: string
  text?: ReactNode
  action?: { label: string; onClick: () => void }
}) {
  return (
    <div className="state">
      <div className="state__icon" aria-hidden>{icon}</div>
      <h2 className="state__title">{title}</h2>
      {text && <p className="hint">{text}</p>}
      {action && (
        <button className="btn btn--primary" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  )
}
