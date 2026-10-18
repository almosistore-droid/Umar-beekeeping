import { api, apiBlob } from './client'
import { saveOrQueue } from '../services/outbox'

export type HiveRef = { id: string; hive_number?: string | null }
import type {
  Apiary, AuditEntry, Family, FamilyOrigin, FamilyStatus, FamilyStrength, Hive, HiveListItem,
  HiveStatus, HiveType, Page, Queen, QueenAssignment, QueenOrigin, QueenStatus, User, UserRole,
} from '../types/api'
import type {
  CrmSummary, Customer, CustomerDetails, Debtor, Expense, ExpenseCategory, LineInput, Order, OrderStatus, PayNowInput,
  PaymentMethod, Sale,
} from '../types/api'
import type { FramePrep, FramePrepResult, StockCategory, StockItem, StockItemDetails, StockNorms, StockOverview, StockUnit } from '../types/api'
import type { AccountCredentials, AdminOverview, AuditPage, Invite, InviteResult, Dashboard, HiveCheck, LabelsRequest, QrInfo, QrResolve, QrStatus, ReportFormat, YearlyReport } from '../types/api'

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) })

function qs(params: Record<string, string | number | boolean | string[] | undefined | null>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x))
    else sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

// ---------- apiaries ----------
export interface ApiaryInput {
  name: string; description?: string | null; address?: string | null
  latitude?: number | null; longitude?: number | null; is_archived?: boolean
}
export const apiariesApi = {
  list: (includeArchived = false) => api<Apiary[]>(`/api/apiaries${qs({ include_archived: includeArchived })}`),
  create: (body: ApiaryInput) => api<Apiary>('/api/apiaries', json('POST', body)),
  update: (id: string, body: Partial<ApiaryInput>) => api<Apiary>(`/api/apiaries/${id}`, json('PUT', body)),
}

// ---------- hives ----------
export interface HiveFilters { apiary_id?: string; status?: HiveStatus[]; strength?: FamilyStrength[]; needs_inspection?: boolean; q?: string; include_archived?: boolean; limit?: number }
export interface FamilyInput { strength: FamilyStrength; origin: FamilyOrigin; start_date?: string | null; notes?: string | null }
export interface HiveCreateInput {
  id?: string | null; apiary_id: string; hive_number: string; hive_type: HiveType; status?: HiveStatus | null
  installation_date?: string | null; colonization_date?: string | null; notes?: string | null
  family?: FamilyInput | null; queen_id?: string | null
}
export interface HiveUpdateInput {
  hive_number?: string; hive_type?: HiveType; status?: HiveStatus; installation_date?: string | null
  colonization_date?: string | null; notes?: string | null; version?: number; comment?: string | null
}

export const hivesApi = {
  list: (f: HiveFilters = {}) => api<Page<HiveListItem>>(`/api/hives${qs({ ...f })}`),
  get: (id: string) => api<Hive>(`/api/hives/${id}`),
  create: (body: HiveCreateInput) => api<Hive>('/api/hives', json('POST', body)),
  update: (id: string, body: HiveUpdateInput) => api<Hive>(`/api/hives/${id}`, json('PUT', body)),
  history: (id: string) => api<AuditEntry[]>(`/api/hives/${id}/history`),
  families: (id: string) => api<Family[]>(`/api/hives/${id}/families`),
  queens: (id: string) => api<QueenAssignment[]>(`/api/hives/${id}/queens`),
  settleFamily: (id: string, body: FamilyInput & { previous_status?: FamilyStatus; end_reason?: string | null }) =>
    api<Hive>(`/api/hives/${id}/families`, json('POST', body)),
  updateFamily: (id: string, body: { strength?: FamilyStrength; notes?: string | null }) =>
    api<Hive>(`/api/hives/${id}/family`, json('PATCH', body)),
  endFamily: (id: string, body: { status: FamilyStatus; end_date?: string | null; end_reason?: string | null }) =>
    api<Hive>(`/api/hives/${id}/family/end`, json('POST', body)),
  assignQueen: (id: string, body: { queen_id: string; installed_at?: string | null; previous_queen_status?: QueenStatus; removal_reason?: string | null }) =>
    api<Hive>(`/api/hives/${id}/queen`, json('POST', body)),
  removeQueen: (id: string, body: { status: QueenStatus; removed_at?: string | null; reason?: string | null }) =>
    api<Hive>(`/api/hives/${id}/queen/remove`, json('POST', body)),
}

// ---------- queens ----------
export interface QueenFilters { status?: QueenStatus[]; q?: string; in_hive?: boolean; include_removed?: boolean }
export interface QueenInput {
  queen_code?: string; birth_date?: string | null; birth_year?: number | null; breed?: string | null
  origin?: QueenOrigin; status?: QueenStatus; egg_laying_quality?: number | null
  swarming_tendency?: number | null; temperament?: number | null; marking_color?: string | null
  notes?: string | null; hive_id?: string | null; installed_at?: string | null
}
export const queensApi = {
  list: (f: QueenFilters = {}) => api<Page<Queen>>(`/api/queens${qs({ ...f })}`),
  get: (id: string) => api<Queen>(`/api/queens/${id}`),
  create: (body: QueenInput) => api<Queen>('/api/queens', json('POST', body)),
  update: (id: string, body: QueenInput) => api<Queen>(`/api/queens/${id}`, json('PUT', body)),
  history: (id: string) => api<QueenAssignment[]>(`/api/queens/${id}/history`),
}

// ---------- users ----------
export const usersApi = {
  list: () => api<User[]>('/api/users'),
  update: (id: string, body: { role?: UserRole; is_active?: boolean }) => api<User>(`/api/users/${id}`, json('PATCH', body)),
}

// ---------- stage 3: health records ----------
import type {
  Attention, CaseStatus, Disease, DiseaseCase, DiseaseSeverity, Feeding, FeedType, FeedUnit, FoodLevel,
  Inspection, InspectionHealth, QueenCondition, RecordWarning, TaskItem, TimelineItem, Treatment,
} from '../types/api'

export interface InspectionInput {
  inspected_at?: string | null; strength: FamilyStrength; frames_total: number; brood_frames: number
  honey_frames: number; pollen_frames: number; queen_present: boolean | null; queen_condition?: QueenCondition | null
  egg_laying: boolean | null; queen_cells: number; swarming_signs: boolean; food_level: FoodLevel | null
  aggressiveness: number | null; health_status: InspectionHealth; next_inspection_at: string | null; notes: string | null
}
export interface CaseInput {
  disease_id: string; detected_at?: string | null; severity: DiseaseSeverity; status: CaseStatus
  symptoms?: string | null; diagnosis?: string | null; notes?: string | null
}
export interface TreatmentInput {
  treated_at?: string | null; disease_id?: string | null; hive_disease_id?: string | null; medication: string
  dosage?: string | null; method?: string | null; result?: string | null; next_treatment_date?: string | null
  notes?: string | null
  stock_item_id?: string | null; stock_quantity?: number | null
}
export interface FeedingInput {
  fed_at?: string | null; feed_type: FeedType; quantity: number; unit: FeedUnit; reason?: string | null
  result?: string | null; next_feeding_date?: string | null; notes?: string | null
}

export const healthApi = {
  inspections: (hiveId: string) => api<Inspection[]>(`/api/hives/${hiveId}/inspections`),
  check: (hiveId: string) => api<HiveCheck>(`/api/hives/${hiveId}/check`),
  /** Field records: without a connection they are kept on the phone and sent later (services/outbox). */
  inspect: (hive: HiveRef, body: InspectionInput) =>
    saveOrQueue<{ inspection: Inspection; hive: Hive; warnings: RecordWarning[] }>('inspection', hive,
      `/api/hives/${hive.id}/inspections`, { ...body, inspected_at: body.inspected_at ?? new Date().toISOString() }),
  diseases: () => api<Disease[]>('/api/diseases'),
  cases: (hiveId: string) => api<DiseaseCase[]>(`/api/hives/${hiveId}/diseases`),
  openCase: (hiveId: string, body: CaseInput) =>
    api<{ case: DiseaseCase; hive: Hive }>(`/api/hives/${hiveId}/diseases`, json('POST', body)),
  updateCase: (caseId: string, body: { status?: CaseStatus; resolved_at?: string | null; notes?: string | null }) =>
    api<{ case: DiseaseCase; hive: Hive }>(`/api/disease-cases/${caseId}`, json('PUT', body)),
  treatments: (hiveId: string) => api<Treatment[]>(`/api/hives/${hiveId}/treatments`),
  treat: (hive: HiveRef, body: TreatmentInput) =>
    saveOrQueue<{ treatment: Treatment; hive: Hive }>('treatment', hive, `/api/hives/${hive.id}/treatments`, { ...body }),
  feedings: (hiveId: string) => api<Feeding[]>(`/api/hives/${hiveId}/feedings`),
  feed: (hive: HiveRef, body: FeedingInput) =>
    saveOrQueue<{ feeding: Feeding; hive: Hive }>('feeding', hive, `/api/hives/${hive.id}/feedings`, { ...body }),
  timeline: (hiveId: string) => api<TimelineItem[]>(`/api/hives/${hiveId}/timeline`),
  tasks: (params: { hive_id?: string; status?: string } = {}) => api<TaskItem[]>(`/api/tasks${qs(params)}`),
  completeTask: (taskId: string) => api<TaskItem>(`/api/tasks/${taskId}/done`, { method: 'POST' }),
  attention: () => api<Attention>('/api/dashboard/attention'),
}

// ---------- stage 4: harvest & operations ----------
import type { Harvest, HiveHoney, HoneyStats, Product, ProductType, Wintering, WinteringResult } from '../types/api'

export const harvestApi = {
  hiveHoney: (hiveId: string) => api<HiveHoney>(`/api/hives/${hiveId}/honey`),
  harvest: (hiveId: string, body: { harvest_date?: string | null; honey_type?: string | null; frames_count: number; weight_kg: number; price_per_kg?: number | null; notes?: string | null }) =>
    api<Harvest>(`/api/hives/${hiveId}/honey`, json('POST', body)),
  stats: (year: number, apiaryId?: string) => api<HoneyStats>(`/api/honey/stats${qs({ year, apiary_id: apiaryId })}`),
  products: (year?: number) => api<Product[]>(`/api/products${qs({ year })}`),
  addProduct: (body: { product_type: ProductType; quantity: number; unit: FeedUnit; collected_at?: string | null; hive_id?: string | null; apiary_id?: string | null; price_per_unit?: number | null; notes?: string | null }) =>
    api<Product>('/api/products', json('POST', body)),
}

export const operationsApi = {
  move: (hiveId: string, body: { to_apiary_id: string; movement_date?: string | null; reason?: string | null; new_hive_number?: string | null }) =>
    api<Hive>(`/api/hives/${hiveId}/move`, json('POST', body)),
  swarm: (hiveId: string, body: { swarm_date?: string | null; swarm_count: number; captured: boolean; settle_into_hive_id?: string | null; new_hive_number?: string | null; queen_id?: string | null; actions?: string | null }) =>
    api<{ hive: Hive; new_hive: Hive | null }>(`/api/hives/${hiveId}/swarms`, json('POST', body)),
  split: (hiveId: string, body: { split_date?: string | null; new_hive_number?: string | null; target_hive_id?: string | null; queen_id?: string | null; strength?: FamilyStrength; notes?: string | null }) =>
    api<{ source: Hive; new_hive: Hive }>(`/api/hives/${hiveId}/split`, json('POST', body)),
  merge: (body: { source_hive_ids: string[]; target_hive_id?: string | null; new_hive_number?: string | null; keep_queen_id?: string | null; merge_date?: string | null; notes?: string | null }) =>
    api<Hive>('/api/merges', json('POST', body)),
  winterings: (hiveId: string) => api<Wintering[]>(`/api/hives/${hiveId}/winterings`),
  startWintering: (hiveId: string, body: { season: string; pre_winter_strength?: FamilyStrength | null; food_kg?: number | null; frames_count?: number | null; queen_condition?: string | null; pre_winter_treatment?: string | null; winter_location?: string | null; start_date?: string | null }) =>
    api<Wintering>(`/api/hives/${hiveId}/winterings`, json('POST', body)),
  finishWintering: (id: string, body: { end_date?: string | null; spring_strength?: FamilyStrength | null; result: WinteringResult; notes?: string | null }) =>
    api<{ wintering: Wintering; hive: Hive }>(`/api/winterings/${id}/finish`, json('PUT', body)),
}

// ---------- stage 5: QR ----------
export const qrApi = {
  get: (hiveId: string) => api<QrInfo>(`/api/hives/${hiveId}/qr`),
  status: () => api<QrStatus>('/api/qr/status'),
  resolve: (code: string) => api<QrResolve>(`/api/qr/resolve${qs({ code })}`),
  sendLabels: (body: LabelsRequest) => api<{ sent: boolean; labels: number }>('/api/qr/labels', json('POST', { ...body, delivery: 'telegram' })),
  downloadLabels: (body: LabelsRequest) => apiBlob('/api/qr/labels', json('POST', { ...body, delivery: 'download' })),
}

// ---------- stage 6: dashboard & reports ----------
export const reportsApi = {
  dashboard: (year?: number) => api<Dashboard>(`/api/dashboard${qs({ year })}`),
  yearly: (year: number) => api<YearlyReport>(`/api/reports/yearly/${year}`),
  download: (year: number, format: ReportFormat) => apiBlob(`/api/reports/yearly/${year}/export${qs({ format })}`),
  send: (year: number, format: ReportFormat) => api<{ sent: boolean }>(`/api/reports/yearly/${year}/send${qs({ format })}`, { method: 'POST' }),
}

// ---------- stage 7: CRM ----------
export interface CustomerInput { name: string; phone?: string | null; city?: string | null; notes?: string | null }
export interface ExpenseInput { expense_date?: string | null; category: ExpenseCategory; amount: number; description?: string | null; apiary_id?: string | null }
export interface SaleInput extends PayNowInput { sale_date?: string | null; customer_id?: string | null; items: LineInput[]; notes?: string | null }
export interface OrderInput { customer_id: string; order_date?: string | null; due_date?: string | null; items: LineInput[]; notes?: string | null }
export interface PaymentInput { amount: number; paid_at?: string | null; method: PaymentMethod; notes?: string | null }
type Period = { year?: number; month?: number | null }

export const crmApi = {
  settings: () => api<{ currency: string }>('/api/crm/settings'),
  summary: (p: Period) => api<CrmSummary>(`/api/crm/summary${qs({ year: p.year, month: p.month })}`),
  customers: (q?: string, includeArchived = false) => api<Customer[]>(`/api/crm/customers${qs({ q, include_archived: includeArchived })}`),
  customer: (id: string) => api<CustomerDetails>(`/api/crm/customers/${id}`),
  createCustomer: (body: CustomerInput) => api<Customer>('/api/crm/customers', json('POST', body)),
  updateCustomer: (id: string, body: Partial<CustomerInput> & { is_archived?: boolean }) => api<CustomerDetails>(`/api/crm/customers/${id}`, json('PUT', body)),
  expenses: (p: Period & { include_cancelled?: boolean }) => api<Expense[]>(`/api/crm/expenses${qs({ ...p })}`),
  createExpense: (body: ExpenseInput) => api<Expense>('/api/crm/expenses', json('POST', body)),
  updateExpense: (id: string, body: Partial<ExpenseInput> & { comment?: string | null }) => api<Expense>(`/api/crm/expenses/${id}`, json('PUT', body)),
  cancelExpense: (id: string, reason: string) => api<Expense>(`/api/crm/expenses/${id}/cancel`, json('POST', { reason })),
  sales: (p: Period & { unpaid?: boolean; customer_id?: string; include_cancelled?: boolean }) => api<Sale[]>(`/api/crm/sales${qs({ ...p })}`),
  sale: (id: string) => api<Sale>(`/api/crm/sales/${id}`),
  createSale: (body: SaleInput) => api<Sale>('/api/crm/sales', json('POST', body)),
  pay: (saleId: string, body: PaymentInput) => api<Sale>(`/api/crm/sales/${saleId}/payments`, json('POST', body)),
  cancelSale: (id: string, reason: string) => api<Sale>(`/api/crm/sales/${id}/cancel`, json('POST', { reason })),
  orders: (p: { status?: OrderStatus; open_only?: boolean; customer_id?: string }) => api<Order[]>(`/api/crm/orders${qs({ ...p })}`),
  order: (id: string) => api<Order>(`/api/crm/orders/${id}`),
  createOrder: (body: OrderInput) => api<Order>('/api/crm/orders', json('POST', body)),
  updateOrder: (id: string, body: { due_date?: string | null; notes?: string | null; items?: LineInput[]; status?: 'READY' }) => api<Order>(`/api/crm/orders/${id}`, json('PUT', body)),
  deliver: (id: string, body: PayNowInput & { sale_date?: string | null }) => api<Sale>(`/api/crm/orders/${id}/deliver`, json('POST', body)),
  cancelOrder: (id: string, reason: string) => api<Order>(`/api/crm/orders/${id}/cancel`, json('POST', { reason })),
  debts: () => api<Debtor[]>('/api/crm/debts'),
}

// ---------- admin panel ----------
export const adminApi = {
  overview: () => api<AdminOverview>('/api/admin/overview'),
  invites: () => api<Invite[]>('/api/admin/invites'),
  invite: (body: { telegram_id?: number | null; username?: string | null; role: UserRole; note?: string | null }) =>
    api<InviteResult>('/api/admin/invites', json('POST', body)),
  revoke: (id: string) => api<Invite>(`/api/admin/invites/${id}/revoke`, { method: 'POST' }),
  createAccount: (body: { first_name: string; last_name?: string | null; login: string; role: UserRole }) =>
    api<AccountCredentials>('/api/admin/accounts', json('POST', body)),
  resetPassword: (userId: string, login?: string | null) =>
    api<AccountCredentials>(`/api/admin/users/${userId}/password`, json('POST', { login: login || null })),
  audit: (p: { user_id?: string; entity_type?: string; offset?: number; limit?: number }) => api<AuditPage>(`/api/admin/audit${qs(p)}`),
}

// ---------- stage 8: Telegram reminders ----------
export interface NotificationSettings { field: boolean; crm: boolean; crm_available: boolean; telegram: boolean; hours: string }
export const notificationsApi = {
  settings: () => api<NotificationSettings>('/api/notifications/settings'),
  update: (body: { field?: boolean; crm?: boolean }) => api<NotificationSettings>('/api/notifications/settings', json('PUT', body)),
  test: () => api<{ sent: boolean }>('/api/notifications/test', { method: 'POST' }),
}

// ---------- warehouse ----------
export interface StockItemInput {
  name: string; category: StockCategory; unit: StockUnit; min_quantity?: number | null; notes?: string | null
  initial_quantity?: number | null; initial_amount?: number | null
}
export interface MovementInput { kind: 'RECEIPT' | 'CONSUMPTION' | 'INVENTORY'; quantity: number; moved_at?: string; note?: string | null; amount?: number | null }
export interface NormsInput { wire_m_per_frame: number; foundation_g_per_frame: number; sugar_kg_per_l_syrup: number; sugar_kg_per_kg_syrup: number }
export const stockApi = {
  overview: (archived = false) => api<StockOverview>(`/api/stock${qs({ archived: archived || undefined })}`),
  item: (id: string) => api<StockItemDetails>(`/api/stock/items/${id}`),
  createItem: (body: StockItemInput) => api<StockItem>('/api/stock/items', json('POST', body)),
  updateItem: (id: string, body: StockItemInput) => api<StockItem>(`/api/stock/items/${id}`, json('PUT', body)),
  archive: (id: string) => api<StockItem>(`/api/stock/items/${id}/archive`, { method: 'POST' }),
  restore: (id: string) => api<StockItem>(`/api/stock/items/${id}/restore`, { method: 'POST' }),
  move: (id: string, body: MovementInput) => api<StockItem>(`/api/stock/items/${id}/movements`, json('POST', body)),
  cancelMovement: (id: string, reason: string) => api<StockItem>(`/api/stock/movements/${id}/cancel`, json('POST', { reason })),
  prepareFrames: (body: { frames: number; prepared_at?: string; notes?: string | null }) =>
    api<FramePrepResult>('/api/stock/frame-preps', json('POST', body)),
  framePreps: () => api<FramePrep[]>('/api/stock/frame-preps'),
  cancelFramePrep: (id: string, reason: string) => api<FramePrep>(`/api/stock/frame-preps/${id}/cancel`, json('POST', { reason })),
  norms: () => api<StockNorms>('/api/stock/norms'),
  saveNorms: (body: NormsInput) => api<StockNorms>('/api/stock/norms', json('PUT', body)),
}
