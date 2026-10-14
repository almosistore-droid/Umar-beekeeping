import { NavLink } from 'react-router-dom'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import { Icon, type IconName } from './Icon'
import { tr } from '../i18n'

type NavItem = { to: string; icon: IconName; label: string }
const CRM: NavItem = { to: '/crm', icon: 'wallet', label: 'CRM' }
const QUEENS: NavItem = { to: '/queens', icon: 'crown', label: tr("Матки") }

/** Admin and beekeeper see «CRM» in the 4th slot (queens move to «Ещё»); other roles keep «Матки». */
export function navItems(canManage: boolean): NavItem[] {
  return [
    { to: '/', icon: 'home', label: tr("Главная") },
    { to: '/hives', icon: 'hive', label: tr("Ульи") },
    { to: '/scan', icon: 'scan', label: tr("Сканер") },
    canManage ? CRM : QUEENS,
    { to: '/reports', icon: 'chart', label: tr("Отчёты") },
    { to: '/more', icon: 'menu', label: tr("Ещё") },
  ]
}

/** Every path that is a tab of the bottom bar for some role (no Telegram back button there). */
export const ROOT_PATHS = new Set(['/', '/hives', '/scan', '/queens', '/crm', '/reports', '/more'])

export function BottomNav() {
  const { canManage } = usePermissions()
  return (
    <nav className="bottom-nav" aria-label={tr("Основная навигация")}>
      <div className="bottom-nav__inner">
        {navItems(canManage).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            onClick={() => haptic('light')}
            className={({ isActive }) =>
              `bottom-nav__item${isActive ? ' is-active' : ''}${item.to === '/scan' ? ' is-primary' : ''}`
            }
          >
            <span className="bottom-nav__icon"><Icon name={item.icon} size={item.to === '/scan' ? 26 : 24} /></span>
            <span className="bottom-nav__label">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
