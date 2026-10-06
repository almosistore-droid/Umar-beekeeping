import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { HomePage } from '../pages/HomePage'
import { MorePage } from '../pages/MorePage'
import { StagePendingPage } from '../pages/StagePendingPage'
import { MessageView } from '../components/StateViews'

export const routes = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'hives', element: <StagePendingPage icon="🐝" title="Ульи" stage={2} /> },
      { path: 'scan', element: <StagePendingPage icon="📷" title="Сканер" stage={5} /> },
      { path: 'queens', element: <StagePendingPage icon="👑" title="Матки" stage={2} /> },
      { path: 'reports', element: <StagePendingPage icon="📊" title="Отчёты" stage={6} /> },
      { path: 'more', element: <MorePage /> },
      { path: '*', element: <MessageView icon="🔎" title="Страница не найдена" /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
