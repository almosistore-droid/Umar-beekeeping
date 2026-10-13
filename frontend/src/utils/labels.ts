import type { IconName } from '../components/Icon'
import type {
  FamilyOrigin, FamilyStatus, FamilyStrength, HiveStatus, HiveType, QueenOrigin, QueenStatus,
} from '../types/api'

export const HIVE_STATUS: Record<HiveStatus, { label: string; icon: string; tone: Tone }> = {
  ACTIVE: { label: 'Активный', icon: '🟢', tone: 'ok' },
  STRONG: { label: 'Сильный', icon: '💪', tone: 'ok' },
  WEAK: { label: 'Слабый', icon: '⚠️', tone: 'warn' },
  SICK: { label: 'Болеет', icon: '🩺', tone: 'bad' },
  QUEENLESS: { label: 'Без матки', icon: '❗', tone: 'bad' },
  EMPTY: { label: 'Пустой', icon: '⚪', tone: 'muted' },
  QUARANTINE: { label: 'Карантин', icon: '🚧', tone: 'bad' },
  MERGED: { label: 'Объединён', icon: '🔗', tone: 'muted' },
  SPLIT: { label: 'Разделён', icon: '✂️', tone: 'muted' },
  SOLD: { label: 'Продан', icon: '💰', tone: 'muted' },
  LOST: { label: 'Потерян', icon: '✖️', tone: 'muted' },
}
export type Tone = 'ok' | 'warn' | 'bad' | 'muted'

// Statuses a user can pick by hand in the edit form
export const EDITABLE_HIVE_STATUSES: HiveStatus[] = ['ACTIVE', 'STRONG', 'WEAK', 'SICK', 'QUARANTINE', 'QUEENLESS', 'EMPTY', 'SOLD', 'LOST']

export const HIVE_TYPE: Record<HiveType, string> = {
  DADANT: 'Дадан', LANGSTROTH: 'Лангстрот', RUTA: 'Рута', ALPINE: 'Альпийский',
  HORIZONTAL: 'Лежак', MULTI_BODY: 'Многокорпусный', NUCLEUS: 'Нуклеус', OTHER: 'Другой',
}

export const STRENGTH: Record<FamilyStrength, { label: string; bars: number }> = {
  VERY_WEAK: { label: 'Очень слабая', bars: 1 },
  WEAK: { label: 'Слабая', bars: 2 },
  MEDIUM: { label: 'Средняя', bars: 3 },
  STRONG: { label: 'Сильная', bars: 4 },
  VERY_STRONG: { label: 'Очень сильная', bars: 5 },
}

export const FAMILY_STATUS: Record<FamilyStatus, string> = {
  ACTIVE: 'Живёт в улье', REPLACED: 'Заменена', MERGED: 'Объединена', SOLD: 'Продана',
  DEAD: 'Погибла', ABSCONDED: 'Слетела',
}

export const FAMILY_ORIGIN: Record<FamilyOrigin, string> = {
  PURCHASED: 'Куплена', PACKAGE: 'Пчелопакет', NUCLEUS: 'Нуклеус', SWARM: 'Рой',
  SPLIT: 'Отводок', MERGE: 'Объединение', OWN: 'Своя', OTHER: 'Другое',
}

export const QUEEN_STATUS: Record<QueenStatus, { label: string; tone: Tone }> = {
  ACTIVE: { label: 'Активная', tone: 'ok' },
  GOOD: { label: 'Хорошая', tone: 'ok' },
  OBSERVATION: { label: 'Под наблюдением', tone: 'warn' },
  WEAK: { label: 'Слабая', tone: 'warn' },
  LOST: { label: 'Пропала', tone: 'muted' },
  REPLACED: { label: 'Заменена', tone: 'muted' },
  DEAD: { label: 'Погибла', tone: 'muted' },
  SOLD: { label: 'Продана', tone: 'muted' },
}
export const ACTIVE_QUEEN_STATUSES: QueenStatus[] = ['ACTIVE', 'GOOD', 'OBSERVATION', 'WEAK']
export const REMOVED_QUEEN_STATUSES: QueenStatus[] = ['REPLACED', 'DEAD', 'LOST', 'SOLD']

export const QUEEN_ORIGIN: Record<QueenOrigin, string> = {
  OWN_BRED: 'Своя (вывод)', PURCHASED: 'Куплена', SWARM: 'Роевая', SUPERSEDURE: 'Тихая смена',
  EMERGENCY: 'Свищевая', UNKNOWN: 'Неизвестно',
}

export const MARKING: Record<string, { label: string; color: string }> = {
  WHITE: { label: 'Белая', color: '#f4f4f4' },
  YELLOW: { label: 'Жёлтая', color: '#f7d417' },
  RED: { label: 'Красная', color: '#e0412f' },
  GREEN: { label: 'Зелёная', color: '#2fa84f' },
  BLUE: { label: 'Синяя', color: '#2f6fe0' },
}

const FIELD_NAMES: Record<string, string> = {
  hive_number: 'Номер', status: 'Статус', hive_type: 'Тип', notes: 'Заметки', strength: 'Сила',
  installation_date: 'Установлен', colonization_date: 'Заселён', next_inspection_at: 'След. осмотр',
  queen_code: 'Матка', role: 'Роль', is_active: 'Активен', name: 'Название',
}

/** Human-readable one-liner for a history (audit) entry. */
export function describeAudit(action: string, oldV: Record<string, unknown> | null, newV: Record<string, unknown> | null): { icon: IconName; title: string; details: string[] } {
  const val = (k: string, v: unknown): string => {
    if (v === null || v === undefined || v === '') return '—'
    if (k === 'status' && typeof v === 'string' && v in HIVE_STATUS) return HIVE_STATUS[v as HiveStatus].label
    if (k === 'strength' && typeof v === 'string' && v in STRENGTH) return STRENGTH[v as FamilyStrength].label
    if (k === 'hive_type' && typeof v === 'string' && v in HIVE_TYPE) return HIVE_TYPE[v as HiveType]
    if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)) return formatDate(v)
    return String(v)
  }
  const changes = () =>
    Object.keys(newV ?? {}).filter((k) => k in FIELD_NAMES).map((k) =>
      `${FIELD_NAMES[k]}: ${val(k, oldV?.[k])} → ${val(k, newV?.[k])}`)

  switch (action) {
    case 'created': return { icon: 'hive', title: 'Улей создан', details: [] }
    case 'queen_installed': return { icon: 'crown', title: `Подсажена матка ${newV?.queen_code}`, details: [] }
    case 'queen_replaced': return { icon: 'crown', title: 'Замена матки', details: [`${oldV?.queen_code} → ${newV?.queen_code}`] }
    case 'queen_removed': return {
      icon: 'queenless', title: `Матка ${oldV?.queen_code ?? ''} убрана`,
      details: newV?.queen_status ? [QUEEN_STATUS[newV.queen_status as QueenStatus]?.label ?? ''] : [],
    }
    case 'family_settled': return { icon: 'hive', title: 'Заселена семья', details: [FAMILY_ORIGIN[newV?.origin as FamilyOrigin] ?? ''] }
    case 'family_replaced': return {
      icon: 'hive', title: 'Смена семьи',
      details: [`Прежняя: ${FAMILY_STATUS[oldV?.family_status as FamilyStatus] ?? ''}`],
    }
    case 'family_ended': return { icon: 'weak', title: 'Семья выбыла', details: [FAMILY_STATUS[newV?.family_status as FamilyStatus] ?? ''] }
    case 'number_changed': return { icon: 'edit', title: 'Изменён номер', details: changes() }
    default: return { icon: 'edit', title: 'Изменения', details: changes() }
  }
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
