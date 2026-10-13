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
  queen_id?: string | null
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

// ---------- stage 3: health records ----------
export type QueenCondition = 'GOOD' | 'NORMAL' | 'POOR' | 'NOT_SEEN'
export type FoodLevel = 'CRITICAL' | 'LOW' | 'NORMAL' | 'ABUNDANT'
export type InspectionHealth = 'HEALTHY' | 'SUSPICIOUS' | 'SICK'
export type DiseaseSeverity = 'LIGHT' | 'MODERATE' | 'SEVERE'
export type CaseStatus = 'SUSPECTED' | 'CONFIRMED' | 'TREATING' | 'RESOLVED'
export type FeedType = 'SUGAR_SYRUP' | 'CANDY' | 'HONEY' | 'PROTEIN' | 'POLLEN_SUBSTITUTE' | 'MEDICATED' | 'OTHER'
export type FeedUnit = 'KG' | 'G' | 'L' | 'ML' | 'PCS'
export type TaskKind = 'INSPECTION' | 'TREATMENT' | 'FEEDING' | 'OTHER'

export interface Inspection {
  id: string
  hive_id: string
  user_name: string | null
  inspected_at: string
  strength: FamilyStrength
  frames_total: number
  brood_frames: number
  honey_frames: number
  pollen_frames: number
  queen_present: boolean | null
  queen_condition: QueenCondition | null
  egg_laying: boolean | null
  queen_cells: number
  swarming_signs: boolean
  food_level: FoodLevel | null
  aggressiveness: number | null
  health_status: InspectionHealth
  next_inspection_at: string | null
  notes: string | null
}

export interface Disease { id: string; code: string; name: string; is_quarantine: boolean; is_active: boolean }

export interface DiseaseCase {
  id: string
  hive_id: string
  disease: Disease
  detected_at: string
  severity: DiseaseSeverity
  symptoms: string | null
  diagnosis: string | null
  status: CaseStatus
  resolved_at: string | null
  notes: string | null
}

export interface Treatment {
  id: string
  hive_id: string
  disease: Disease | null
  hive_disease_id: string | null
  treated_at: string
  medication: string
  dosage: string | null
  method: string | null
  performed_by_name: string | null
  result: string | null
  next_treatment_date: string | null
  notes: string | null
}

export interface Feeding {
  id: string
  hive_id: string
  fed_at: string
  feed_type: FeedType
  quantity: string
  unit: FeedUnit
  reason: string | null
  result: string | null
  next_feeding_date: string | null
  notes: string | null
}

export interface TaskItem {
  id: string
  hive_id: string | null
  hive_number: string | null
  kind: TaskKind
  title: string
  due_date: string
  status: 'OPEN' | 'DONE' | 'CANCELLED'
}

export interface TimelineItem {
  kind: 'inspection' | 'disease_opened' | 'disease_resolved' | 'treatment' | 'feeding' | 'event'
  at: string
  title: string
  details: string[]
  author: string | null
  ref_id: string | null
  action?: string | null
  entity_type?: string | null
  old_value?: Record<string, unknown> | null
  new_value?: Record<string, unknown> | null
  comment?: string | null
}

export interface RecordWarning { code: string; message: string }
export interface Attention { needs_inspection: number; open_tasks: number; overdue_tasks: number; sick: number }

// ---------- stage 4: harvest & operations ----------
export type ProductType = 'WAX' | 'PROPOLIS' | 'BEE_BREAD' | 'POLLEN' | 'ROYAL_JELLY' | 'QUEENS' | 'COLONIES' | 'PACKAGES'
export type WinteringResult = 'STRONG' | 'WEAK' | 'DIED'

export interface Harvest {
  id: string
  hive_id: string
  apiary_id: string
  harvest_date: string
  harvest_year: number
  harvest_number: number
  honey_type: string | null
  frames_count: number
  weight_kg: string
  price_per_kg: string | null
  total_value: string | null
  notes: string | null
}
export interface HiveHoney { items: Harvest[]; year: number; year_kg: string; year_value: string; all_time_kg: string }
export interface HiveRank { hive_id: string; hive_number: string; apiary_name: string; kg: string; harvests: number }
export interface HoneyStats {
  year: number; month_kg: string; year_kg: string; season_kg: string; all_time_kg: string; year_value: string
  producing_hives: number; avg_per_hive_kg: string; best_hive: HiveRank | null; by_month: string[]; by_hive: HiveRank[]
}
export interface Product {
  id: string; product_type: ProductType; collected_at: string; quantity: string; unit: FeedUnit
  hive_id: string | null; apiary_id: string | null; price_per_unit: string | null; total_value: string | null; notes: string | null
}
export interface Wintering {
  id: string; hive_id: string; season: string; pre_winter_strength: FamilyStrength | null; food_kg: string | null
  frames_count: number | null; queen_condition: string | null; pre_winter_treatment: string | null
  winter_location: string | null; start_date: string; end_date: string | null; spring_strength: FamilyStrength | null
  result: WinteringResult | null; notes: string | null
}
