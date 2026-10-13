import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { BottomNav, ROOT_PATHS } from '../components/BottomNav'
import { getWebApp, takeStartParam } from '../services/telegram'

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  // Opened from a QR deep link (t.me/<bot>/<app>?startapp=hive_<uuid>): go straight to that hive
  useEffect(() => {
    const code = takeStartParam()
    if (code) navigate(`/open?code=${encodeURIComponent(code)}`, { replace: true })
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
        <Outlet />
      </main>
      <BottomNav />
    </div>
  )
}
