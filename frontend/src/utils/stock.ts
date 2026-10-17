/**
 * The same consumption rules as the server (backend/app/services/stock_service.py), used to show the
 * calculation before saving. The server makes the real write-off.
 */
import type { FeedType, FeedUnit, StockNorms, StockUnit } from '../types/api'

export interface Need { code: string; quantity: number; unit: StockUnit }

const MASS: Partial<Record<FeedUnit, number>> = { KG: 1, G: 0.001 }
const FEED_ITEM: Partial<Record<FeedType, string>> = { CANDY: 'candy', PROTEIN: 'protein', POLLEN_SUBSTITUTE: 'protein' }
const round3 = (x: number) => Math.round(x * 1000) / 1000

/** Syrup → sugar by the norms; candy and protein feed in kg/g → the same kg; other feed: nothing. */
export function feedingNeed(norms: StockNorms, type: FeedType, quantity: number, unit: FeedUnit): Need | null {
  if (!(quantity > 0)) return null
  if (type === 'SUGAR_SYRUP') {
    if (unit === 'L' || unit === 'ML') {
      const litres = unit === 'ML' ? quantity / 1000 : quantity
      return { code: 'sugar', quantity: round3(litres * Number(norms.sugar_kg_per_l_syrup)), unit: 'KG' }
    }
    const k = MASS[unit]
    return k ? { code: 'sugar', quantity: round3(quantity * k * Number(norms.sugar_kg_per_kg_syrup)), unit: 'KG' } : null
  }
  const code = FEED_ITEM[type]
  const k = MASS[unit]
  return code && k ? { code, quantity: round3(quantity * k), unit: 'KG' } : null
}

/** «N frames»: wire (m), foundation (kg), empty frames used and ready frames made. */
export function frameNeed(norms: StockNorms, frames: number): Need[] {
  if (!(frames > 0)) return []
  return [
    { code: 'wire', quantity: round3(frames * Number(norms.wire_m_per_frame)), unit: 'M' },
    { code: 'foundation', quantity: round3(frames * Number(norms.foundation_g_per_frame) / 1000), unit: 'KG' },
    { code: 'frames_empty', quantity: frames, unit: 'PCS' },
  ].filter((n) => n.quantity > 0) as Need[]
}
