import { createBrowserRouter } from 'react-router-dom'
import { lazyPage } from './lazyPage'
import { AppLayout } from '../layouts/AppLayout'
import { HiveDetailsPage } from '../pages/HiveDetailsPage'
import { HiveFormPage } from '../pages/HiveFormPage'
import { HivesPage } from '../pages/HivesPage'
import { HomePage } from '../pages/HomePage'
import { MorePage } from '../pages/MorePage'
import { TasksPage } from '../pages/TasksPage'
import { MessageView } from '../components/StateViews'
import { ScanPage } from '../pages/ScanPage'
import { OpenQrPage } from '../pages/OpenQrPage'
import { HiveVisitPage } from '../pages/HiveVisitPage'
import { HiveInspectPage } from '../pages/HiveInspectPage'
import { HiveCheckPage } from '../pages/HiveCheckPage'
import { tr } from '../i18n'
import { OutboxPage } from '../pages/OutboxPage'

// Less frequent screens load on first open (see lazyPage)
const ApiariesPage = lazyPage(() => import('../pages/ApiariesPage'), 'ApiariesPage')
const QueenDetailsPage = lazyPage(() => import('../pages/QueenDetailsPage'), 'QueenDetailsPage')
const QueenFormPage = lazyPage(() => import('../pages/QueenFormPage'), 'QueenFormPage')
const QueensPage = lazyPage(() => import('../pages/QueensPage'), 'QueensPage')
const ReportsPage = lazyPage(() => import('../pages/ReportsPage'), 'ReportsPage')
const AdminPage = lazyPage(() => import('../pages/admin/AdminPage'), 'AdminPage')
const AuditLogPage = lazyPage(() => import('../pages/admin/AuditLogPage'), 'AuditLogPage')
const CrmHomePage = lazyPage(() => import('../pages/crm/CrmHomePage'), 'CrmHomePage')
const SaleDetailsPage = lazyPage(() => import('../pages/crm/SalesPages'), 'SaleDetailsPage')
const SalesPage = lazyPage(() => import('../pages/crm/SalesPages'), 'SalesPage')
const ExpensesPage = lazyPage(() => import('../pages/crm/ExpensesPage'), 'ExpensesPage')
const OrderDetailsPage = lazyPage(() => import('../pages/crm/OrdersPages'), 'OrderDetailsPage')
const OrdersPage = lazyPage(() => import('../pages/crm/OrdersPages'), 'OrdersPage')
const CustomerDetailsPage = lazyPage(() => import('../pages/crm/CustomersPages'), 'CustomerDetailsPage')
const CustomersPage = lazyPage(() => import('../pages/crm/CustomersPages'), 'CustomersPage')
const DebtsPage = lazyPage(() => import('../pages/crm/DebtsPage'), 'DebtsPage')
const UsersPage = lazyPage(() => import('../pages/UsersPage'), 'UsersPage')
const HoneyPage = lazyPage(() => import('../pages/HoneyPage'), 'HoneyPage')
const ProductsPage = lazyPage(() => import('../pages/ProductsPage'), 'ProductsPage')
const QrLabelsPage = lazyPage(() => import('../pages/QrLabelsPage'), 'QrLabelsPage')
const StockPage = lazyPage(() => import('../pages/stock/StockPage'), 'StockPage')
const RearingBatchPage = lazyPage(() => import('../pages/rearing/RearingPages'), 'RearingBatchPage')
const RearingListPage = lazyPage(() => import('../pages/rearing/RearingPages'), 'RearingListPage')
const StockItemPage = lazyPage(() => import('../pages/stock/StockItemPage'), 'StockItemPage')
const StockNormsPage = lazyPage(() => import('../pages/stock/StockNormsPage'), 'StockNormsPage')

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
      { path: 'queens', element: QueensPage },
      { path: 'queens/new', element: QueenFormPage },
      { path: 'queens/:id', element: QueenDetailsPage },
      { path: 'queens/:id/edit', element: QueenFormPage },
      { path: 'apiaries', element: ApiariesPage },
      { path: 'users', element: UsersPage },
      { path: 'admin', element: AdminPage },
      { path: 'admin/log', element: AuditLogPage },
      { path: 'tasks', element: <TasksPage /> },
      { path: 'honey', element: HoneyPage },
      { path: 'products', element: ProductsPage },
      { path: 'scan', element: <ScanPage /> },
      { path: 'open', element: <OpenQrPage /> },
      { path: 'qr-labels', element: QrLabelsPage },
      { path: 'reports', element: ReportsPage },
      { path: 'crm', element: CrmHomePage },
      { path: 'crm/sales', element: SalesPage },
      { path: 'crm/sales/:id', element: SaleDetailsPage },
      { path: 'crm/expenses', element: ExpensesPage },
      { path: 'crm/orders', element: OrdersPage },
      { path: 'crm/orders/:id', element: OrderDetailsPage },
      { path: 'crm/customers', element: CustomersPage },
      { path: 'crm/customers/:id', element: CustomerDetailsPage },
      { path: 'crm/debts', element: DebtsPage },
      { path: 'stock', element: StockPage },
      { path: 'stock/norms', element: StockNormsPage },
      { path: 'stock/:id', element: StockItemPage },
      { path: 'outbox', element: <OutboxPage /> },
      { path: 'rearing', element: RearingListPage },
      { path: 'rearing/:id', element: RearingBatchPage },
      { path: 'more', element: <MorePage /> },
      { path: '*', element: <MessageView icon="inspect" title={tr("Страница не найдена")} /> },
    ],
  },
]

export const router = createBrowserRouter(routes, {
  future: { v7_relativeSplatPath: true },
})
