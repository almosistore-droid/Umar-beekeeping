import { api } from './client'
import type {
  Apiary, AuditEntry, Family, FamilyOrigin, FamilyStatus, FamilyStrength, Hive, HiveListItem,
  HiveStatus, HiveType, Page, Queen, QueenAssignment, QueenOrigin, QueenStatus, User, UserRole,
} from '../types/api'

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
export interface HiveFilters { apiary_id?: string; status?: HiveStatus[]; strength?: FamilyStrength[]; q?: string; include_archived?: boolean }
export interface FamilyInput { strength: FamilyStrength; origin: FamilyOrigin; start_date?: string | null; notes?: string | null }
export interface HiveCreateInput {
  apiary_id: string; hive_number: string; hive_type: HiveType; status?: HiveStatus | null
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
