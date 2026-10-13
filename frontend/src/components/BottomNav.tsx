import { NavLink } from 'react-router-dom'
import { haptic } from '../services/telegram'
import { Icon, type IconName } from './Icon'

export const NAV_ITEMS: readonly { to: string; icon: IconName; label: string }[] = [
  { to: '/', icon: 'home', label: 'Главная' },
  { to: '/hives', icon: 'hive', label: 'Ульи' },
  { to: '/scan', icon: 'scan', label: 'Сканер' },
  { to: '/queens', icon: 'crown', label: 'Матки' },
  { to: '/reports', icon: 'chart', label: 'Отчёты' },
  { to: '/more', icon: 'menu', label: 'Ещё' },
]

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Основная навигация">
      <div className="bottom-nav__inner">
        {NAV_ITEMS.map((item) => (
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
