import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ApiariesPage } from '../pages/ApiariesPage'
import { HiveDetailsPage } from '../pages/HiveDetailsPage'
import { HiveFormPage } from '../pages/HiveFormPage'
import { HivesPage } from '../pages/HivesPage'
import { HomePage } from '../pages/HomePage'
import { MorePage } from '../pages/MorePage'
import { QueenDetailsPage } from '../pages/QueenDetailsPage'
import { QueenFormPage } from '../pages/QueenFormPage'
import { QueensPage } from '../pages/QueensPage'
import { StagePendingPage } from '../pages/StagePendingPage'
import { UsersPage } from '../pages/UsersPage'
import { TasksPage } from '../pages/TasksPage'
import { HoneyPage } from '../pages/HoneyPage'
import { ProductsPage } from '../pages/ProductsPage'
import { MessageView } from '../components/StateViews'

export const routes = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'hives', element: <HivesPage /> },
      { path: 'hives/new', element: <HiveFormPage /> },
      { path: 'hives/:id', element: <HiveDetailsPage /> },
      { path: 'hives/:id/edit', element: <HiveFormPage /> },
      { path: 'queens', element: <QueensPage /> },
      { path: 'queens/new', element: <QueenFormPage /> },
      { path: 'queens/:id', element: <QueenDetailsPage /> },
      { path: 'queens/:id/edit', element: <QueenFormPage /> },
      { path: 'apiaries', element: <ApiariesPage /> },
      { path: 'users', element: <UsersPage /> },
      { path: 'tasks', element: <TasksPage /> },
      { path: 'honey', element: <HoneyPage /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'scan', element: <StagePendingPage icon="scan" title="Сканер" stage={5} /> },
      { path: 'reports', element: <StagePendingPage icon="chart" title="Отчёты" stage={6} /> },
      { path: 'more', element: <MorePage /> },
      { path: '*', element: <MessageView icon="inspect" title="Страница не найдена" /> },
    ],
  },
]

export const router = createBrowserRouter(routes, {
  future: { v7_relativeSplatPath: true },
})
