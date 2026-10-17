import type { IconName } from '../components/Icon'
import type {
  FamilyOrigin, FamilyStatus, FamilyStrength, HiveStatus, HiveType, QueenOrigin, QueenStatus, UserRole,
} from '../types/api'
import { ROLE_LABELS } from '../types/api'

export const HIVE_STATUS: Record<HiveStatus, { label: string; icon: string; tone: Tone }> = {
  ACTIVE: { label: tr("Активный"), icon: '🟢', tone: 'ok' },
  STRONG: { label: tr("Сильный"), icon: '💪', tone: 'ok' },
  WEAK: { label: tr("Слабый"), icon: '⚠️', tone: 'warn' },
  SICK: { label: tr("Болеет"), icon: '🩺', tone: 'bad' },
  QUEENLESS: { label: tr("Без матки"), icon: '❗', tone: 'bad' },
  EMPTY: { label: tr("Пустой"), icon: '⚪', tone: 'muted' },
  QUARANTINE: { label: tr("Карантин"), icon: '🚧', tone: 'bad' },
  MERGED: { label: tr("Объединён"), icon: '🔗', tone: 'muted' },
  SPLIT: { label: tr("Разделён"), icon: '✂️', tone: 'muted' },
  SOLD: { label: tr("Продан"), icon: '💰', tone: 'muted' },
  LOST: { label: tr("Потерян"), icon: '✖️', tone: 'muted' },
}
export type Tone = 'ok' | 'warn' | 'bad' | 'muted'

// Statuses a user can pick by hand in the edit form
export const EDITABLE_HIVE_STATUSES: HiveStatus[] = ['ACTIVE', 'STRONG', 'WEAK', 'SICK', 'QUARANTINE', 'QUEENLESS', 'EMPTY', 'SOLD', 'LOST']

export const HIVE_TYPE: Record<HiveType, string> = {
  DADANT: tr("Дадан"), LANGSTROTH: tr("Лангстрот"), RUTA: tr("Рута"), ALPINE: tr("Альпийский"),
  HORIZONTAL: tr("Лежак"), MULTI_BODY: tr("Многокорпусный"), NUCLEUS: tr("Нуклеус"), OTHER: tr("Другой"),
}

export const STRENGTH: Record<FamilyStrength, { label: string; bars: number }> = {
  VERY_WEAK: { label: tr("Очень слабая"), bars: 1 },
  WEAK: { label: tr("Слабая"), bars: 2 },
  MEDIUM: { label: tr("Средняя"), bars: 3 },
  STRONG: { label: tr("Сильная"), bars: 4 },
  VERY_STRONG: { label: tr("Очень сильная"), bars: 5 },
}

export const FAMILY_STATUS: Record<FamilyStatus, string> = {
  ACTIVE: tr("Живёт в улье"), REPLACED: tr("Заменена"), MERGED: tr("Объединена"), SOLD: tr("Продана"),
  DEAD: tr("Погибла"), ABSCONDED: tr("Слетела"),
}

export const FAMILY_ORIGIN: Record<FamilyOrigin, string> = {
  PURCHASED: tr("Куплена"), PACKAGE: tr("Пчелопакет"), NUCLEUS: tr("Нуклеус"), SWARM: tr("Рой"),
  SPLIT: tr("Отводок"), MERGE: tr("Объединение"), OWN: tr("Своя"), OTHER: tr("Другое"),
}

export const QUEEN_STATUS: Record<QueenStatus, { label: string; tone: Tone }> = {
  ACTIVE: { label: tr("Активная"), tone: 'ok' },
  GOOD: { label: tr("Хорошая"), tone: 'ok' },
  OBSERVATION: { label: tr("Под наблюдением"), tone: 'warn' },
  WEAK: { label: tr("Слабая"), tone: 'warn' },
  LOST: { label: tr("Пропала"), tone: 'muted' },
  REPLACED: { label: tr("Заменена"), tone: 'muted' },
  DEAD: { label: tr("Погибла"), tone: 'muted' },
  SOLD: { label: tr("Продана"), tone: 'muted' },
}
export const ACTIVE_QUEEN_STATUSES: QueenStatus[] = ['ACTIVE', 'GOOD', 'OBSERVATION', 'WEAK']
export const REMOVED_QUEEN_STATUSES: QueenStatus[] = ['REPLACED', 'DEAD', 'LOST', 'SOLD']

export const QUEEN_ORIGIN: Record<QueenOrigin, string> = {
  OWN_BRED: tr("Своя (вывод)"), PURCHASED: tr("Куплена"), SWARM: tr("Роевая"), SUPERSEDURE: tr("Тихая смена"),
  EMERGENCY: tr("Свищевая"), UNKNOWN: tr("Неизвестно"),
}

export const MARKING: Record<string, { label: string; color: string }> = {
  WHITE: { label: tr("Белая"), color: '#f4f4f4' },
  YELLOW: { label: tr("Жёлтая"), color: '#f7d417' },
  RED: { label: tr("Красная"), color: '#e0412f' },
  GREEN: { label: tr("Зелёная"), color: '#2fa84f' },
  BLUE: { label: tr("Синяя"), color: '#2f6fe0' },
}

const CASE_STATUS_LABEL: Record<string, string> = {
  SUSPECTED: tr("подозрение"), CONFIRMED: tr("подтверждено"), TREATING: tr("лечение"), RESOLVED: tr("вылечено"),
}

const FIELD_NAMES: Record<string, string> = {
  hive_number: tr("Номер"), status: tr("Статус"), hive_type: tr("Тип"), notes: tr("Заметки"), strength: tr("Сила"),
  installation_date: tr("Установлен"), colonization_date: tr("Заселён"), next_inspection_at: tr("След. осмотр"),
  queen_code: tr("Матка"), role: tr("Роль"), is_active: tr("Активен"), name: tr("Название"),
  frames_total: tr("Рамок"), brood_frames: tr("Расплод"), honey_frames: tr("Мёд"), pollen_frames: tr("Перга"),
  medication: tr("Препарат"), dosage: tr("Доза"), treated_at: tr("Дата"), fed_at: tr("Дата"), quantity: tr("Количество"),
  next_treatment_date: tr("Следующая"), next_feeding_date: tr("Следующая"), inspected_at: tr("Дата осмотра"),
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
    case 'created': return { icon: 'hive', title: tr("Улей создан"), details: [] }
    case 'queen_installed': return { icon: 'crown', title: tr("Подсажена матка {0}", newV?.queen_code), details: [] }
    case 'queen_replaced': return { icon: 'crown', title: tr("Замена матки"), details: [`${oldV?.queen_code} → ${newV?.queen_code}`] }
    case 'queen_removed': return {
      icon: 'queenless', title: tr("Матка {0} убрана", oldV?.queen_code ?? ''),
      details: newV?.queen_status ? [QUEEN_STATUS[newV.queen_status as QueenStatus]?.label ?? ''] : [],
    }
    case 'family_settled': return { icon: 'hive', title: tr("Заселена семья"), details: [FAMILY_ORIGIN[newV?.origin as FamilyOrigin] ?? ''] }
    case 'family_replaced': return {
      icon: 'hive', title: tr("Смена семьи"),
      details: [tr("Прежняя: {0}", FAMILY_STATUS[oldV?.family_status as FamilyStatus] ?? '')],
    }
    case 'family_ended': return { icon: 'weak', title: tr("Семья выбыла"), details: [FAMILY_STATUS[newV?.family_status as FamilyStatus] ?? ''] }
    case 'number_changed': return { icon: 'edit', title: tr("Изменён номер"), details: changes() }
    case 'health_status': return {
      icon: 'health', title: tr("Состояние улья"),
      details: [`${val('status', oldV?.status)} → ${val('status', newV?.status)}`],
    }
    case 'disease_updated': {
      const st = (v: unknown) => (typeof v === 'string' && v in CASE_STATUS_LABEL ? CASE_STATUS_LABEL[v] : '—')
      return {
        icon: 'health', title: tr("Болезнь: {0}", newV?.disease ?? ''),
        details: newV?.status ? [`${st(oldV?.status)} → ${st(newV?.status)}`] : [],
      }
    }
    case 'corrected': return { icon: 'edit', title: tr("Исправлена запись"), details: changes() }
    case 'moved': return { icon: 'apiary', title: tr("Перемещён на другую пасеку"), details: [`${oldV?.apiary} → ${newV?.apiary}`, ...(oldV?.hive_number !== newV?.hive_number ? [tr("Номер: {0} → {1}", oldV?.hive_number, newV?.hive_number)] : [])] }
    case 'swarmed': return {
      icon: 'hive', title: tr("Роение{0}", Number(newV?.swarm_count) > 1 ? tr(" ({0} роя)", newV?.swarm_count) : ''),
      details: [newV?.captured ? (newV?.new_hive_number ? tr("Пойман, посажен в улей №{0}", newV.new_hive_number) : tr("Рой пойман")) : tr("Рой улетел")],
    }
    case 'swarm_settled': return { icon: 'hive', title: tr("Посажен рой из улья №{0}", newV?.from_hive_number), details: [] }
    case 'split': return { icon: 'hive', title: tr("Сделан отводок: улей №{0}", newV?.new_hive_number), details: [] }
    case 'split_created': return {
      icon: 'hive', title: tr("Отводок от улья №{0}", newV?.source_hive_number),
      details: [newV?.queen_code ? tr("Матка {0}", newV.queen_code) : tr("Без матки")],
    }
    case 'merged_into': return { icon: 'hive', title: tr("Объединён в улей №{0}", newV?.target_hive_number), details: [] }
    case 'merge_target': {
      const nums = Array.isArray(newV?.source_hive_numbers) ? (newV?.source_hive_numbers as string[]).map((n) => `№${n}`).join(', ') : ''
      return { icon: 'hive', title: tr("Присоединены ульи {0}", nums), details: newV?.queen_code ? [tr("Оставлена матка {0}", newV.queen_code)] : [] }
    }
    case 'wintering_started': return { icon: 'apiary', title: tr("Ушёл в зимовку {0}", newV?.season ?? ''), details: [] }
    case 'wintering_finished': return { icon: 'apiary', title: tr("Зимовка {0} завершена", newV?.season ?? ''), details: [WINTERING_RESULT[newV?.result as WinteringResult] ?? ''] }
    case 'qr_printed': return { icon: 'qr', title: tr("Напечатан QR-код"), details: [] }
    case 'task_done': return { icon: 'treat', title: tr("Выполнено: {0}", newV?.title ?? ''), details: [] }
    default: return { icon: 'edit', title: tr("Изменения"), details: changes() }
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

export const QUEEN_CONDITION: Record<QueenCondition, string> = { GOOD: tr("Хорошее"), NORMAL: tr("Нормальное"), POOR: tr("Плохое"), NOT_SEEN: tr("Не видна") }

export const FOOD_LEVEL: Record<FoodLevel, string> = { CRITICAL: tr("Критично"), LOW: tr("Мало"), NORMAL: tr("Норма"), ABUNDANT: tr("Много") }
export const INSPECTION_HEALTH: Record<InspectionHealth, string> = { HEALTHY: tr("Здорова"), SUSPICIOUS: tr("Подозрение"), SICK: tr("Болеет") }
export const SEVERITY: Record<DiseaseSeverity, string> = { LIGHT: tr("Лёгкая"), MODERATE: tr("Средняя"), SEVERE: tr("Тяжёлая") }
export const CASE_STATUS: Record<CaseStatus, { label: string; tone: Tone }> = {
  SUSPECTED: { label: tr("Подозрение"), tone: 'warn' },
  CONFIRMED: { label: tr("Подтверждено"), tone: 'bad' },
  TREATING: { label: tr("Лечение"), tone: 'warn' },
  RESOLVED: { label: tr("Вылечено"), tone: 'ok' },
}
export const FEED_TYPE: Record<FeedType, string> = {
  SUGAR_SYRUP: tr("Сахарный сироп"), CANDY: tr("Канди"), HONEY: tr("Мёд"), PROTEIN: tr("Белковая"),
  POLLEN_SUBSTITUTE: tr("Заменитель перги"), MEDICATED: tr("Лечебная"), OTHER: tr("Другое"),
}
export const FEED_UNIT: Record<FeedUnit, string> = { KG: tr("кг"), G: tr("г"), L: tr("л"), ML: tr("мл"), PCS: tr("шт") }

export function addDaysIso(days: number, from = new Date()): string {
  const d = new Date(from)
  d.setDate(d.getDate() + days)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ---------- stage 4 ----------
import type { ProductType, WinteringResult } from '../types/api'

export const PRODUCT_TYPE: Record<ProductType, string> = {
  WAX: tr("Воск"), PROPOLIS: tr("Прополис"), BEE_BREAD: tr("Перга"), POLLEN: tr("Пыльца"), ROYAL_JELLY: tr("Маточное молочко"),
  QUEENS: tr("Матки"), COLONIES: tr("Пчелосемьи"), PACKAGES: tr("Пчелопакеты"),
}
export const WINTERING_RESULT: Record<WinteringResult, string> = { STRONG: tr("Перезимовала сильной"), WEAK: tr("Перезимовала, ослабла"), DIED: tr("Погибла") }
export const HONEY_TYPES = [tr("Разнотравье"), tr("Акация"), tr("Липа"), tr("Гречиха"), tr("Подсолнечник"), tr("Горный"), tr("Хлопковый"), tr("Эспарцет")]
export const MONTHS_SHORT = [tr("янв"), tr("фев"), tr("мар"), tr("апр"), tr("май"), tr("июн"), tr("июл"), tr("авг"), tr("сен"), tr("окт"), tr("ноя"), tr("дек")]
export const MONTHS = [tr("Январь"), tr("Февраль"), tr("Март"), tr("Апрель"), tr("Май"), tr("Июнь"), tr("Июль"), tr("Август"), tr("Сентябрь"), tr("Октябрь"), tr("Ноябрь"), tr("Декабрь")]


import { tr } from '../i18n'/** 12.50 → "12,5"; keeps up to 2 decimals, Russian decimal comma, thin-space thousands. */
export function num(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—'
  return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 2 })
}

/** «сегодня», «вчера», «5 дней назад» */
export function daysAgoLabel(days: number): string {
  if (days <= 0) return tr("сегодня")
  if (days === 1) return tr("вчера")
  const n10 = days % 10, n100 = days % 100
  const word = n10 === 1 && n100 !== 11 ? tr("день") : n10 >= 2 && n10 <= 4 && (n100 < 10 || n100 >= 20) ? tr("дня") : tr("дней")
  return tr("{0} {1} назад", days, word)
}

// ---------- stage 7: CRM ----------
import type { ExpenseCategory, OrderStatus, PaymentMethod, SaleCategory, SaleState } from '../types/api'

export const EXPENSE_CATEGORY: Record<ExpenseCategory, string> = {
  HIVES: tr("Ульи"), FRAMES: tr("Рамки"), FOUNDATION: tr("Вощина"), FEED: tr("Корм"), MEDICINE: tr("Лекарства"), EQUIPMENT: tr("Оборудование"),
  TRANSPORT: tr("Транспорт"), FUEL: tr("Топливо"), QUEENS: tr("Матки"), COLONIES: tr("Семьи"), REPAIR: tr("Ремонт"), OTHER: tr("Другое"),
}
export const SALE_CATEGORY: Record<SaleCategory, string> = {
  HONEY: tr("Мёд"), WAX: tr("Воск"), PROPOLIS: tr("Прополис"), BEE_BREAD: tr("Перга"), POLLEN: tr("Пыльца"), QUEENS: tr("Матки"),
  COLONIES: tr("Семьи"), PACKAGES: tr("Пчелопакеты"), OTHER: tr("Другое"),
}
export const DEFAULT_SALE_UNIT: Record<SaleCategory, FeedUnit> = {
  HONEY: 'KG', WAX: 'KG', PROPOLIS: 'G', BEE_BREAD: 'KG', POLLEN: 'KG', QUEENS: 'PCS', COLONIES: 'PCS', PACKAGES: 'PCS', OTHER: 'PCS',
}
export const PAYMENT_METHOD: Record<PaymentMethod, string> = { CASH: tr("Наличные"), CARD: tr("Карта"), TRANSFER: tr("Перевод") }
export const ORDER_STATUS: Record<OrderStatus, { label: string; tone: Tone }> = {
  NEW: { label: tr("Новый"), tone: 'warn' }, READY: { label: tr("Собран"), tone: 'ok' },
  DELIVERED: { label: tr("Выдан"), tone: 'muted' }, CANCELLED: { label: tr("Отменён"), tone: 'muted' },
}
export const SALE_STATE: Record<SaleState, { label: string; tone: Tone }> = {
  paid: { label: tr("Оплачено"), tone: 'ok' }, partial: { label: tr("Частично"), tone: 'warn' },
  unpaid: { label: tr("В долг"), tone: 'bad' }, cancelled: { label: tr("Отменена"), tone: 'muted' },
}

/** 1 250 смн */
export function money(v: string | number | null | undefined, currency: string): string {
  if (v === null || v === undefined || v === '') return '—'
  return `${Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 2 })} ${currency}`
}

// ---------- admin panel ----------
export const ENTITY_LABEL: Record<string, string> = {
  hive: tr("Улей"), bee_family: tr("Семья"), queen: tr("Матка"), apiary: tr("Пасека"), inspection: tr("Осмотр"), hive_disease: tr("Болезнь"),
  disease: tr("Справочник болезней"), treatment: tr("Обработка"), feeding: tr("Подкормка"), task: tr("Напоминание"),
  honey_harvest: tr("Мёд"), other_product: tr("Продукция"), swarm: tr("Роение"), hive_split: tr("Отводок"), hive_merge: tr("Объединение"),
  wintering: tr("Зимовка"), qr_code: tr("QR-код"), user: tr("Пользователь"), user_invite: tr("Приглашение"), customer: tr("Клиент"),
  sale: tr("Продажа"), payment: tr("Оплата"), expense: tr("Расход"), order: tr("Заказ"),
  stock_item: tr("Склад"), stock_movement: tr("Склад"), frame_prep: tr("Подготовка рамок"), stock_norms: tr("Нормы расхода"),
}
const ACTION_LABEL: Record<string, string> = {
  created: tr("создан(а)"), updated: tr("изменён(а)"), corrected: tr("исправлен(а)"), cancelled: tr("отменён(а)"), delivered: tr("выдан"),
  payment: tr("принята оплата"), invited: tr("приглашён"), invite_revoked: tr("приглашение отозвано"), joined_by_invite: tr("вошёл по приглашению"), role_from_config: tr("стал администратором (настройки сервера)"), device_login: tr("вошёл в приложение на телефоне"),
  account_created: tr("создан вход по логину"), password_reset: tr("выдан новый пароль"), password_changed: tr("сменил(а) пароль"),
  login_locked: tr("вход заблокирован на 15 минут: неверный пароль"),
  archived: tr("в архиве"), qr_printed: tr("напечатан"),
  restored: tr("возвращён(а) из архива"), receipt: tr("приход"), consumption: tr("расход"), inventory: tr("пересчёт"),
  frame_prep: tr("на подготовку рамок"), feeding: tr("на подкормку"), treatment: tr("на обработку"), frames_prepared: tr("рамки подготовлены"),
}
/** One line for the admin activity log: hive events reuse the hive timeline wording. */
export function describeLogEntry(e: { entity_type: string; action: string; hive_id: string | null; old_value: Record<string, unknown> | null; new_value: Record<string, unknown> | null }): string {
  if (e.hive_id && !['sale', 'order', 'expense', 'customer'].includes(e.entity_type)) {
    return describeAudit(e.action, e.old_value, e.new_value).title
  }
  const what = ENTITY_LABEL[e.entity_type] ?? e.entity_type
  const how = ACTION_LABEL[e.action] ?? e.action
  if (e.entity_type === 'user' && e.action === 'updated' && e.new_value) {
    const parts = []
    if ('role' in e.new_value) parts.push(tr("роль: {0}", ROLE_LABELS[e.new_value.role as UserRole] ?? e.new_value.role))
    if ('is_active' in e.new_value) parts.push(e.new_value.is_active ? tr("доступ открыт") : tr("доступ закрыт"))
    return `${what}: ${parts.join(', ') || how}`
  }
  return `${what} — ${how}`
}

/** «только что», «5 мин назад», «3 ч назад», «вчера», date */
export function agoLabel(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return tr("ещё не входил(а)")
  const d = new Date(iso)
  const min = Math.floor((now.getTime() - d.getTime()) / 60000)
  if (min < 2) return tr("только что")
  if (min < 60) return tr("{0} мин назад", min)
  if (min < 24 * 60) return tr("{0} ч назад", Math.floor(min / 60))
  if (min < 48 * 60) return tr("вчера")
  return formatDate(iso)
}

/** Second line for CRM/admin log entries: the essentials stored in the change (amount, customer, who). */
export function logDetail(e: { entity_type: string; action: string; new_value: Record<string, unknown> | null }, currency = ''): string | null {
  const v = e.new_value ?? {}
  const money = (x: unknown) => `${num(x as string)}${currency ? ` ${currency}` : ''}`
  const parts: (string | null | undefined | false)[] = []
  if (e.entity_type === 'sale' && e.action === 'created') parts.push(v.total !== undefined && money(v.total), v.customer as string, Array.isArray(v.lines) && (v.lines as string[]).join(', '))
  else if (e.entity_type === 'sale' && e.action === 'payment') parts.push(v.amount !== undefined && money(v.amount), v.debt_left !== undefined && Number(v.debt_left) > 0 && tr("осталось {0}", money(v.debt_left)))
  else if (e.entity_type === 'order') parts.push(v.total !== undefined && money(v.total), v.customer as string, v.status === 'READY' && tr("собран"))
  else if (e.entity_type === 'expense') parts.push(v.amount !== undefined && money(v.amount), EXPENSE_CATEGORY[v.category as ExpenseCategory], v.description as string)
  else if (e.entity_type === 'customer' || e.entity_type === 'apiary') parts.push(v.name as string, v.city as string)
  else if (e.entity_type === 'user' && e.action === 'account_created') parts.push(v.name as string, (v.login ? tr("логин: {0}", v.login as string) : null), v.role ? ROLE_LABELS[v.role as UserRole] : null)
  else if (e.entity_type === 'user' && e.action === 'password_reset') parts.push((v.login ? tr("логин: {0}", v.login as string) : null))
  else if (e.entity_type === 'user' && e.action === 'device_login') parts.push(v.device as string, v.method === 'password' ? tr("по паролю") : 'Telegram')
  else if (e.entity_type === 'stock_movement') parts.push(v.item as string, v.quantity !== undefined && `${Number(v.quantity) > 0 ? '+' : ''}${num(v.quantity as string)} ${STOCK_UNIT[v.unit as StockUnit] ?? ''}`)
  else if (e.entity_type === 'stock_item') parts.push(v.name as string)
  else if (e.entity_type === 'frame_prep' && v.frames !== undefined) parts.push(tr("{0} шт", v.frames as number))
  else if (e.entity_type === 'user_invite') parts.push(v.username ? `@${v.username}` : v.telegram_id ? `ID ${v.telegram_id}` : null, v.role ? ROLE_LABELS[v.role as UserRole] : null, v.note as string)
  const out = parts.filter(Boolean).join(' · ')
  return out || null
}

// ---------- warehouse ----------
import type { StockCategory, StockMovementKind, StockUnit } from '../types/api'
export const STOCK_UNIT: Record<StockUnit, string> = {
  PCS: tr("шт"), KG: tr("кг"), G: tr("г"), L: tr("л"), ML: tr("мл"), M: tr("м"), PACK: tr("уп."),
}
export const STOCK_CATEGORY: Record<StockCategory, string> = {
  FRAMES: tr("Рамки и вощина"), FEED: tr("Корм"), MEDICINE: tr("Лекарства"), OTHER: tr("Другое"),
}
export const MOVEMENT_KIND: Record<StockMovementKind, string> = {
  RECEIPT: tr("Приход"), CONSUMPTION: tr("Расход"), INVENTORY: tr("Пересчёт"), FRAME_PREP: tr("Подготовка рамок"),
  FEEDING: tr("Подкормка"), TREATMENT: tr("Обработка"),
}
/** «12,5 кг» — up to 3 decimals (grams of wax, millilitres). */
export function qty(v: string | number, unit: StockUnit): string {
  return `${Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 3 })} ${STOCK_UNIT[unit]}`
}
