import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { BottomNav, ROOT_PATHS } from '../components/BottomNav'
import { getWebApp, takeStartParam } from '../services/telegram'
import { OfflineBar } from '../components/offline/OfflineBar'

/** Start parameters used by the reminder buttons in Telegram (stage 8). */
export const START_SCREENS: Record<string, string> = {
  go_tasks: '/tasks', go_hives: '/hives', go_debts: '/crm/debts', go_orders: '/crm/orders', go_stock: '/stock',
}

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  // Opened from a QR deep link (t.me/<bot>/<app>?startapp=hive_<uuid>): go straight to that hive;
  // a reminder's button (startapp=go_debts…) opens its screen
  useEffect(() => {
    const code = takeStartParam()
    if (!code) return
    const screen = START_SCREENS[code]
    navigate(screen ?? `/open?code=${encodeURIComponent(code)}`, { replace: true })
  }, [navigate])

  // Telegram's native back button on nested screens
  useEffect(() => {
    const back = getWebApp()?.BackButton
    if (!back) return
    const goBack = () => navigate(-1)
    if (ROOT_PATHS.has(location.pathname)) back.hide()
    else {
      back.show()
      back.onClick(goBack)
    }
    return () => back.offClick(goBack)
  }, [location.pathname, navigate])

  return (
    <div className="app">
      <main className="app__content">
        <OfflineBar />
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
