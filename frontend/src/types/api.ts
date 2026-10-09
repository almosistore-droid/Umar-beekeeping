export type UserRole = 'ADMIN' | 'BEEKEEPER' | 'ASSISTANT' | 'VIEWER'

export interface User {
  id: string
  telegram_id: number
  username: string | null
  first_name: string | null
  last_name: string | null
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
  start_param: string | null
}

export type HiveStatus =
  | 'ACTIVE' | 'WEAK' | 'STRONG' | 'SICK' | 'QUEENLESS' | 'EMPTY' | 'QUARANTINE'
  | 'MERGED' | 'SPLIT' | 'SOLD' | 'LOST'
export type HiveType = 'DADANT' | 'LANGSTROTH' | 'RUTA' | 'ALPINE' | 'HORIZONTAL' | 'MULTI_BODY' | 'NUCLEUS' | 'OTHER'
export type FamilyStrength = 'VERY_WEAK' | 'WEAK' | 'MEDIUM' | 'STRONG' | 'VERY_STRONG'
export type FamilyStatus = 'ACTIVE' | 'REPLACED' | 'MERGED' | 'SOLD' | 'DEAD' | 'ABSCONDED'
export type FamilyOrigin = 'PURCHASED' | 'PACKAGE' | 'NUCLEUS' | 'SWARM' | 'SPLIT' | 'MERGE' | 'OWN' | 'OTHER'
export type QueenStatus = 'ACTIVE' | 'GOOD' | 'OBSERVATION' | 'WEAK' | 'LOST' | 'REPLACED' | 'DEAD' | 'SOLD'
export type QueenOrigin = 'OWN_BRED' | 'PURCHASED' | 'SWARM' | 'SUPERSEDURE' | 'EMERGENCY' | 'UNKNOWN'

export interface Apiary {
  id: string
  name: string
  description: string | null
  address: string | null
  latitude: number | null
  longitude: number | null
  owner_id: string | null
  is_archived: boolean
  hive_count: number
  created_at: string
  updated_at: string
}

export interface ApiaryBrief { id: string; name: string }

export interface Family {
  id: string
  hive_id: string
  strength: FamilyStrength
  status: FamilyStatus
  origin: FamilyOrigin
  start_date: string
  end_date: string | null
  end_reason: string | null
  notes: string | null
}

export interface QueenBrief {
  id: string
  queen_code: string
  status: QueenStatus
  birth_date: string | null
  birth_year: number | null
  age_months: number | null
  age_label: string | null
  breed: string | null
  marking_color: string | null
  installed_at: string | null
}

export interface Hive {
  id: string
  apiary: ApiaryBrief
  hive_number: string
  hive_type: HiveType
  status: HiveStatus
  is_archived: boolean
  installation_date: string | null
  colonization_date: string | null
  last_inspection_at: string | null
  next_inspection_at: string | null
  notes: string | null
  version: number
  current_family: Family | null
  current_queen: QueenBrief | null
  created_at: string
  updated_at: string
}

export interface HiveListItem {
  id: string
  apiary: ApiaryBrief
  hive_number: string
  hive_type: HiveType
  status: HiveStatus
  is_archived: boolean
  strength: FamilyStrength | null
  queen_code: string | null
  queen_age_label: string | null
  last_inspection_at: string | null
  next_inspection_at: string | null
}

export interface Page<T> { items: T[]; total: number }

export interface Queen extends QueenBrief {
  origin: QueenOrigin
  current_hive: { id: string; hive_number: string; apiary_name: string } | null
  removed_at: string | null
  removal_reason: string | null
  egg_laying_quality: number | null
  swarming_tendency: number | null
  temperament: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface QueenAssignment {
  id: string
  queen_id: string
  queen_code: string
  hive_id: string
  hive_number: string
  installed_at: string
  removed_at: string | null
  removal_reason: string | null
}

export interface AuditEntry {
  id: string
  created_at: string
  user_name: string | null
  entity_type: string
  entity_id: string
  action: string
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  comment: string | null
}

export const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: 'Администратор',
  BEEKEEPER: 'Пчеловод',
  ASSISTANT: 'Помощник',
  VIEWER: 'Наблюдатель',
}
