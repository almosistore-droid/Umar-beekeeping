import { tr } from '../i18n'
import { useBranding } from '../services/branding'
import { Icon } from './Icon'

/** Turns the supplier contact from the server settings into a link: @username, URL, phone or e-mail. */
export function contactHref(contact: string): string | null {
  const c = contact.trim()
  if (/^@[A-Za-z0-9_]{4,}$/.test(c)) return `https://t.me/${c.slice(1)}`
  if (/^https?:\/\//i.test(c)) return c
  if (/^\+?[\d\s()-]{6,}$/.test(c)) return `tel:${c.replace(/[^\d+]/g, '')}`
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c)) return `mailto:${c}`
  return null
}

function Contact({ contact }: { contact: string }) {
  const href = contactHref(contact)
  return href ? <a href={href} target="_blank" rel="noreferrer">{contact}</a> : <b>{contact}</b>
}

/** The whole app is closed while the subscription of this installation is unpaid. */
export function SubscriptionBlocked() {
  const brand = useBranding()
  const { contact } = brand.subscription
  return (
    <div className="state" role="alert">
      <img className="state__logo" src={brand.logo_url} alt={brand.name} />
      <h2 className="state__title">{tr("Подписка закончилась")}</h2>
      <p className="hint">{tr("Доступ к приложению {0} временно закрыт. Все данные сохранены и снова будут доступны после продления подписки.", brand.name)}</p>
      {contact && <p className="hint">{tr("Для продления:")} <Contact contact={contact} /></p>}
      <button className="btn btn--primary" onClick={() => window.location.reload()}>{tr("Проверить снова")}</button>
    </div>
  )
}

/** For the admin: a reminder during the last days of the paid period. */
export function SubscriptionWarning() {
  const { subscription } = useBranding()
  if (!subscription.active || subscription.days_left === null) return null
  const left = subscription.days_left
  return (
    <div className="warn-box sub-warning" role="status">
      <Icon name="wallet" size={18} />
      <span>
        {left === 0 ? tr("Подписка заканчивается сегодня.") : tr("Подписка заканчивается через {0} дн.", left)}{" "}
        {tr("После этого приложение закроется для всех, пока подписку не продлят.")}
        {subscription.contact && <> {tr("Для продления:")} <Contact contact={subscription.contact} /></>}
      </span>
    </div>
  )
}
