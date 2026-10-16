import { useEffect, useState } from 'react'
import { Icon } from '../Icon'
import { canPromptInstall, isIos, isStandalone, onInstallAvailabilityChange, promptInstall } from '../../services/pwa'
import { tr } from '../../i18n'

/** «Установить на телефон»: Chrome's install prompt on Android, instructions for Safari on iPhone. */
export function InstallHint({ compact = false }: { compact?: boolean }) {
  const [, rerender] = useState(0)
  useEffect(() => onInstallAvailabilityChange(() => rerender((n) => n + 1)), [])
  if (isStandalone()) return null

  if (canPromptInstall()) {
    return (
      <button type="button" className="btn btn--secondary btn--block" onClick={() => void promptInstall()}>
        <Icon name="mobile" size={18} />{tr("Установить на телефон")}
      </button>
    )
  }
  if (isIos()) {
    return (
      <div className={`install-hint${compact ? ' install-hint--compact' : ''}`}>
        <b>{tr("Установить на iPhone")}</b>
        <span>{tr("В Safari нажмите")} <Icon name="iosShare" size={18} className="install-hint__icon" /> {tr("«Поделиться», затем «На экран «Домой»».")}</span>
      </div>
    )
  }
  return compact ? null : (
    <div className="install-hint">
      <b>{tr("Установить на телефон")}</b>
      <span>{tr("Откройте этот адрес в Chrome на Android и нажмите «Установить приложение» в меню ⋮.")}</span>
    </div>
  )
}
