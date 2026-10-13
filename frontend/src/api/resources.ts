import { api, apiBlob } from './client'
import type {
  Apiary, AuditEntry, Family, FamilyOrigin, FamilyStatus, FamilyStrength, Hive, HiveListItem,
  HiveStatus, HiveType, Page, Queen, QueenAssignment, QueenOrigin, QueenStatus, User, UserRole,
} from '../types/api'
import type { LabelsRequest, QrInfo, QrResolve, QrStatus } from '../types/api'

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
export interface HiveFilters { apiary_id?: string; status?: HiveStatus[]; strength?: FamilyStrength[]; needs_inspection?: boolean; q?: string; include_archived?: boolean }
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
}
export interface FeedingInput {
  fed_at?: string | null; feed_type: FeedType; quantity: number; unit: FeedUnit; reason?: string | null
  result?: string | null; next_feeding_date?: string | null; notes?: string | null
}

export const healthApi = {
  inspections: (hiveId: string) => api<Inspection[]>(`/api/hives/${hiveId}/inspections`),
  inspect: (hiveId: string, body: InspectionInput) =>
    api<{ inspection: Inspection; hive: Hive; warnings: RecordWarning[] }>(`/api/hives/${hiveId}/inspections`, json('POST', body)),
  diseases: () => api<Disease[]>('/api/diseases'),
  cases: (hiveId: string) => api<DiseaseCase[]>(`/api/hives/${hiveId}/diseases`),
  openCase: (hiveId: string, body: CaseInput) =>
    api<{ case: DiseaseCase; hive: Hive }>(`/api/hives/${hiveId}/diseases`, json('POST', body)),
  updateCase: (caseId: string, body: { status?: CaseStatus; resolved_at?: string | null; notes?: string | null }) =>
    api<{ case: DiseaseCase; hive: Hive }>(`/api/disease-cases/${caseId}`, json('PUT', body)),
  treatments: (hiveId: string) => api<Treatment[]>(`/api/hives/${hiveId}/treatments`),
  treat: (hiveId: string, body: TreatmentInput) =>
    api<{ treatment: Treatment; hive: Hive }>(`/api/hives/${hiveId}/treatments`, json('POST', body)),
  feedings: (hiveId: string) => api<Feeding[]>(`/api/hives/${hiveId}/feedings`),
  feed: (hiveId: string, body: FeedingInput) =>
    api<{ feeding: Feeding; hive: Hive }>(`/api/hives/${hiveId}/feedings`, json('POST', body)),
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
