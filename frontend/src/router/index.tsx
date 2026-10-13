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
import { ReportsPage } from '../pages/ReportsPage'
import { AdminPage } from '../pages/admin/AdminPage'
import { AuditLogPage } from '../pages/admin/AuditLogPage'
import { CrmHomePage } from '../pages/crm/CrmHomePage'
import { SaleDetailsPage, SalesPage } from '../pages/crm/SalesPages'
import { ExpensesPage } from '../pages/crm/ExpensesPage'
import { OrderDetailsPage, OrdersPage } from '../pages/crm/OrdersPages'
import { CustomerDetailsPage, CustomersPage } from '../pages/crm/CustomersPages'
import { DebtsPage } from '../pages/crm/DebtsPage'
import { UsersPage } from '../pages/UsersPage'
import { TasksPage } from '../pages/TasksPage'
import { HoneyPage } from '../pages/HoneyPage'
import { ProductsPage } from '../pages/ProductsPage'
import { MessageView } from '../components/StateViews'
import { ScanPage } from '../pages/ScanPage'
import { OpenQrPage } from '../pages/OpenQrPage'
import { QrLabelsPage } from '../pages/QrLabelsPage'
import { HiveVisitPage } from '../pages/HiveVisitPage'
import { HiveInspectPage } from '../pages/HiveInspectPage'
import { HiveCheckPage } from '../pages/HiveCheckPage'

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
      { path: 'hives/:id/visit', element: <HiveVisitPage /> },
      { path: 'hives/:id/inspect', element: <HiveInspectPage /> },
      { path: 'hives/:id/check', element: <HiveCheckPage /> },
      { path: 'queens', element: <QueensPage /> },
      { path: 'queens/new', element: <QueenFormPage /> },
      { path: 'queens/:id', element: <QueenDetailsPage /> },
      { path: 'queens/:id/edit', element: <QueenFormPage /> },
      { path: 'apiaries', element: <ApiariesPage /> },
      { path: 'users', element: <UsersPage /> },
      { path: 'admin', element: <AdminPage /> },
      { path: 'admin/log', element: <AuditLogPage /> },
      { path: 'tasks', element: <TasksPage /> },
      { path: 'honey', element: <HoneyPage /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'scan', element: <ScanPage /> },
      { path: 'open', element: <OpenQrPage /> },
      { path: 'qr-labels', element: <QrLabelsPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'crm', element: <CrmHomePage /> },
      { path: 'crm/sales', element: <SalesPage /> },
      { path: 'crm/sales/:id', element: <SaleDetailsPage /> },
      { path: 'crm/expenses', element: <ExpensesPage /> },
      { path: 'crm/orders', element: <OrdersPage /> },
      { path: 'crm/orders/:id', element: <OrderDetailsPage /> },
      { path: 'crm/customers', element: <CustomersPage /> },
      { path: 'crm/customers/:id', element: <CustomerDetailsPage /> },
      { path: 'crm/debts', element: <DebtsPage /> },
      { path: 'more', element: <MorePage /> },
      { path: '*', element: <MessageView icon="inspect" title="Страница не найдена" /> },
    ],
  },
]

export const router = createBrowserRouter(routes, {
  future: { v7_relativeSplatPath: true },
})
