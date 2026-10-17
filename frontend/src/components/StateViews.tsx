import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'
import { tr } from '../i18n'
import { useBranding } from '../services/branding'

export function LoadingView({ text = tr("Загрузка…") }: { text?: string }) {
  return (
    <div className="state" role="status">
      <div className="spinner" aria-hidden />
      <p className="hint">{text}</p>
    </div>
  )
}

export function MessageView({
  icon,
  logo,
  title,
  text,
  action,
  secondary,
}: {
  icon?: IconName
  logo?: boolean
  title: string
  text?: ReactNode
  action?: { label: string; onClick: () => void }
  secondary?: { label: string; onClick: () => void }
}) {
  const brand = useBranding()
  return (
    <div className="state">
      {logo ? <img className="state__logo" src={brand.logo_url} alt={brand.name} />
        : icon && <div className="state__cell" aria-hidden><Icon name={icon} size={30} /></div>}
      <h2 className="state__title">{title}</h2>
      {text && <p className="hint">{text}</p>}
      {action && (
        <button className="btn btn--primary" onClick={action.onClick}>
          {action.label}
        </button>
      )}
      {secondary && <button className="btn btn--ghost" onClick={secondary.onClick}>{secondary.label}</button>}
    </div>
  )
}
