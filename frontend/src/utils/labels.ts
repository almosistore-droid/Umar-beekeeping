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

const CASE_STATUS_LABEL: Record<string, string> = {
  SUSPECTED: 'подозрение', CONFIRMED: 'подтверждено', TREATING: 'лечение', RESOLVED: 'вылечено',
}

const FIELD_NAMES: Record<string, string> = {
  hive_number: 'Номер', status: 'Статус', hive_type: 'Тип', notes: 'Заметки', strength: 'Сила',
  installation_date: 'Установлен', colonization_date: 'Заселён', next_inspection_at: 'След. осмотр',
  queen_code: 'Матка', role: 'Роль', is_active: 'Активен', name: 'Название',
  frames_total: 'Рамок', brood_frames: 'Расплод', honey_frames: 'Мёд', pollen_frames: 'Перга',
  medication: 'Препарат', dosage: 'Доза', treated_at: 'Дата', fed_at: 'Дата', quantity: 'Количество',
  next_treatment_date: 'Следующая', next_feeding_date: 'Следующая', inspected_at: 'Дата осмотра',
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
    case 'health_status': return {
      icon: 'health', title: 'Состояние улья',
      details: [`${val('status', oldV?.status)} → ${val('status', newV?.status)}`],
    }
    case 'disease_updated': {
      const st = (v: unknown) => (typeof v === 'string' && v in CASE_STATUS_LABEL ? CASE_STATUS_LABEL[v] : '—')
      return {
        icon: 'health', title: `Болезнь: ${newV?.disease ?? ''}`,
        details: newV?.status ? [`${st(oldV?.status)} → ${st(newV?.status)}`] : [],
      }
    }
    case 'corrected': return { icon: 'edit', title: 'Исправлена запись', details: changes() }
    case 'moved': return { icon: 'apiary', title: 'Перемещён на другую пасеку', details: [`${oldV?.apiary} → ${newV?.apiary}`, ...(oldV?.hive_number !== newV?.hive_number ? [`Номер: ${oldV?.hive_number} → ${newV?.hive_number}`] : [])] }
    case 'swarmed': return {
      icon: 'hive', title: `Роение${Number(newV?.swarm_count) > 1 ? ` (${newV?.swarm_count} роя)` : ''}`,
      details: [newV?.captured ? (newV?.new_hive_number ? `Пойман, посажен в улей №${newV.new_hive_number}` : 'Рой пойман') : 'Рой улетел'],
    }
    case 'swarm_settled': return { icon: 'hive', title: `Посажен рой из улья №${newV?.from_hive_number}`, details: [] }
    case 'split': return { icon: 'hive', title: `Сделан отводок: улей №${newV?.new_hive_number}`, details: [] }
    case 'split_created': return {
      icon: 'hive', title: `Отводок от улья №${newV?.source_hive_number}`,
      details: [newV?.queen_code ? `Матка ${newV.queen_code}` : 'Без матки'],
    }
    case 'merged_into': return { icon: 'hive', title: `Объединён в улей №${newV?.target_hive_number}`, details: [] }
    case 'merge_target': {
      const nums = Array.isArray(newV?.source_hive_numbers) ? (newV?.source_hive_numbers as string[]).map((n) => `№${n}`).join(', ') : ''
      return { icon: 'hive', title: `Присоединены ульи ${nums}`, details: newV?.queen_code ? [`Оставлена матка ${newV.queen_code}`] : [] }
    }
    case 'wintering_started': return { icon: 'apiary', title: `Ушёл в зимовку ${newV?.season ?? ''}`, details: [] }
    case 'wintering_finished': return { icon: 'apiary', title: `Зимовка ${newV?.season ?? ''} завершена`, details: [WINTERING_RESULT[newV?.result as WinteringResult] ?? ''] }
    case 'qr_printed': return { icon: 'qr', title: 'Напечатан QR-код', details: [] }
    case 'task_done': return { icon: 'treat', title: `Выполнено: ${newV?.title ?? ''}`, details: [] }
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

// ---------- stage 3 ----------
import type { CaseStatus, DiseaseSeverity, FeedType, FeedUnit, FoodLevel, InspectionHealth, QueenCondition } from '../types/api'

export const QUEEN_CONDITION: Record<QueenCondition, string> = { GOOD: 'Хорошее', NORMAL: 'Нормальное', POOR: 'Плохое', NOT_SEEN: 'Не видна' }

export const FOOD_LEVEL: Record<FoodLevel, string> = { CRITICAL: 'Критично', LOW: 'Мало', NORMAL: 'Норма', ABUNDANT: 'Много' }
export const INSPECTION_HEALTH: Record<InspectionHealth, string> = { HEALTHY: 'Здорова', SUSPICIOUS: 'Подозрение', SICK: 'Болеет' }
export const SEVERITY: Record<DiseaseSeverity, string> = { LIGHT: 'Лёгкая', MODERATE: 'Средняя', SEVERE: 'Тяжёлая' }
export const CASE_STATUS: Record<CaseStatus, { label: string; tone: Tone }> = {
  SUSPECTED: { label: 'Подозрение', tone: 'warn' },
  CONFIRMED: { label: 'Подтверждено', tone: 'bad' },
  TREATING: { label: 'Лечение', tone: 'warn' },
  RESOLVED: { label: 'Вылечено', tone: 'ok' },
}
export const FEED_TYPE: Record<FeedType, string> = {
  SUGAR_SYRUP: 'Сахарный сироп', CANDY: 'Канди', HONEY: 'Мёд', PROTEIN: 'Белковая',
  POLLEN_SUBSTITUTE: 'Заменитель перги', MEDICATED: 'Лечебная', OTHER: 'Другое',
}
export const FEED_UNIT: Record<FeedUnit, string> = { KG: 'кг', G: 'г', L: 'л', ML: 'мл', PCS: 'шт' }

export function addDaysIso(days: number, from = new Date()): string {
  const d = new Date(from)
  d.setDate(d.getDate() + days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ---------- stage 4 ----------
import type { ProductType, WinteringResult } from '../types/api'

export const PRODUCT_TYPE: Record<ProductType, string> = {
  WAX: 'Воск', PROPOLIS: 'Прополис', BEE_BREAD: 'Перга', POLLEN: 'Пыльца', ROYAL_JELLY: 'Маточное молочко',
  QUEENS: 'Матки', COLONIES: 'Пчелосемьи', PACKAGES: 'Пчелопакеты',
}
export const WINTERING_RESULT: Record<WinteringResult, string> = { STRONG: 'Перезимовала сильной', WEAK: 'Перезимовала, ослабла', DIED: 'Погибла' }
export const HONEY_TYPES = ['Разнотравье', 'Акация', 'Липа', 'Гречиха', 'Подсолнечник', 'Горный', 'Хлопковый', 'Эспарцет']
export const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
export const MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

/** 12.50 → "12,5"; keeps up to 2 decimals, Russian decimal comma, thin-space thousands. */
export function num(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—'
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 2 })
}

/** «сегодня», «вчера», «5 дней назад» */
export function daysAgoLabel(days: number): string {
  if (days <= 0) return 'сегодня'
  if (days === 1) return 'вчера'
  const n10 = days % 10, n100 = days % 100
  const word = n10 === 1 && n100 !== 11 ? 'день' : n10 >= 2 && n10 <= 4 && (n100 < 10 || n100 >= 20) ? 'дня' : 'дней'
  return `${days} ${word} назад`
}

// ---------- stage 7: CRM ----------
import type { ExpenseCategory, OrderStatus, PaymentMethod, SaleCategory, SaleState } from '../types/api'

export const EXPENSE_CATEGORY: Record<ExpenseCategory, string> = {
  HIVES: 'Ульи', FRAMES: 'Рамки', FOUNDATION: 'Вощина', FEED: 'Корм', MEDICINE: 'Лекарства', EQUIPMENT: 'Оборудование',
  TRANSPORT: 'Транспорт', FUEL: 'Топливо', QUEENS: 'Матки', COLONIES: 'Семьи', REPAIR: 'Ремонт', OTHER: 'Другое',
}
export const SALE_CATEGORY: Record<SaleCategory, string> = {
  HONEY: 'Мёд', WAX: 'Воск', PROPOLIS: 'Прополис', BEE_BREAD: 'Перга', POLLEN: 'Пыльца', QUEENS: 'Матки',
  COLONIES: 'Семьи', PACKAGES: 'Пчелопакеты', OTHER: 'Другое',
}
export const DEFAULT_SALE_UNIT: Record<SaleCategory, FeedUnit> = {
  HONEY: 'KG', WAX: 'KG', PROPOLIS: 'G', BEE_BREAD: 'KG', POLLEN: 'KG', QUEENS: 'PCS', COLONIES: 'PCS', PACKAGES: 'PCS', OTHER: 'PCS',
}
export const PAYMENT_METHOD: Record<PaymentMethod, string> = { CASH: 'Наличные', CARD: 'Карта', TRANSFER: 'Перевод' }
export const ORDER_STATUS: Record<OrderStatus, { label: string; tone: Tone }> = {
  NEW: { label: 'Новый', tone: 'warn' }, READY: { label: 'Собран', tone: 'ok' },
  DELIVERED: { label: 'Выдан', tone: 'muted' }, CANCELLED: { label: 'Отменён', tone: 'muted' },
}
export const SALE_STATE: Record<SaleState, { label: string; tone: Tone }> = {
  paid: { label: 'Оплачено', tone: 'ok' }, partial: { label: 'Частично', tone: 'warn' },
  unpaid: { label: 'В долг', tone: 'bad' }, cancelled: { label: 'Отменена', tone: 'muted' },
}

/** 1 250 смн */
export function money(v: string | number | null | undefined, currency: string): string {
  if (v === null || v === undefined || v === '') return '—'
  return `${Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ${currency}`
}
