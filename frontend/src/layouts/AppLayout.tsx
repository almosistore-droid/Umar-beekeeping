import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { BottomNav, NAV_ITEMS } from '../components/BottomNav'
import { getWebApp } from '../services/telegram'

const ROOT_PATHS = new Set<string>(NAV_ITEMS.map((i) => i.to))

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()

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
