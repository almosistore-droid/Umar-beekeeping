import { NavLink } from 'react-router-dom'
import { haptic } from '../services/telegram'

export const NAV_ITEMS = [
  { to: '/', icon: '🏠', label: 'Главная' },
  { to: '/hives', icon: '🐝', label: 'Ульи' },
  { to: '/scan', icon: '📷', label: 'Сканер' },
  { to: '/queens', icon: '👑', label: 'Матки' },
  { to: '/reports', icon: '📊', label: 'Отчёты' },
  { to: '/more', icon: '☰', label: 'Ещё' },
] as const

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Основная навигация">
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
          <span className="bottom-nav__icon" aria-hidden>{item.icon}</span>
          <span className="bottom-nav__label">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
