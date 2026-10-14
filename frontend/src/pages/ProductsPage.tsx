import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiariesApi, harvestApi } from '../api/resources'
import { Choice, ErrorBox, Field, Sheet, SubmitButton, fieldError } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import type { FeedUnit, ProductType } from '../types/api'
import { FEED_UNIT, PRODUCT_TYPE, formatDate, num, todayIso } from '../utils/labels'
import { tr } from '../i18n'

const typeOpts = (Object.keys(PRODUCT_TYPE) as ProductType[]).map((k) => ({ value: k, label: PRODUCT_TYPE[k] }))
const unitOpts = (Object.keys(FEED_UNIT) as FeedUnit[]).map((k) => ({ value: k, label: FEED_UNIT[k] }))
const DEFAULT_UNIT: Record<ProductType, FeedUnit> = {
  WAX: 'KG', PROPOLIS: 'G', BEE_BREAD: 'KG', POLLEN: 'KG', ROYAL_JELLY: 'G', QUEENS: 'PCS', COLONIES: 'PCS', PACKAGES: 'PCS',
}

export function ProductsPage() {
  const { canWrite } = usePermissions()
  const year = new Date().getFullYear()
  const [open, setOpen] = useState(false)
  const products = useQuery({ queryKey: ['products', year], queryFn: () => harvestApi.products(year) })

  const totals = new Map<string, number>()
  for (const p of products.data ?? []) {
    const key = `${p.product_type}|${p.unit}`
    totals.set(key, (totals.get(key) ?? 0) + Number(p.quantity))
  }

  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">{tr("Продукция")}</h1>
        {canWrite && <button className="btn btn--primary btn--sm" onClick={() => setOpen(true)}>{tr("＋ Записать")}</button>}
      </div>
      <ErrorBox error={products.error} />
      {products.isLoading ? <LoadingView /> : !products.data?.length ? (
        <MessageView icon="honey" title={tr("Записей пока нет")} text={tr("Воск, прополис, перга, пыльца, маточное молочко, матки, семьи и пчелопакеты.")} />
      ) : <>
        <div className="stat-row">
          {[...totals.entries()].map(([key, qty]) => {
            const [type, unit] = key.split('|') as [ProductType, FeedUnit]
            return <div key={key} className="stat"><span className="stat__value">{num(qty)} {FEED_UNIT[unit]}</span><span className="stat__label">{PRODUCT_TYPE[type]}, {year}</span></div>
          })}
        </div>
        <section className="card">
          <ul className="plain-list">
            {products.data.map((p) => (
              <li key={p.id} className="row">
                <span><b>{PRODUCT_TYPE[p.product_type]}</b><br /><span className="small hint">{formatDate(p.collected_at)}</span></span>
                <span className="row__value">{num(p.quantity)} {FEED_UNIT[p.unit]}{p.total_value ? <><br /><span className="small hint">{num(p.total_value)}</span></> : null}</span>
              </li>
            ))}
          </ul>
        </section>
      </>}
      <Sheet open={open} title={tr("Продукция")} onClose={() => setOpen(false)}>{open && <ProductForm onDone={() => setOpen(false)} />}</Sheet>
    </div>
  )
}

function ProductForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient()
  const apiaries = useQuery({ queryKey: ['apiaries'], queryFn: () => apiariesApi.list() })
  const [type, setType] = useState<ProductType>('WAX')
  const [qty, setQty] = useState('')
  const [unit, setUnit] = useState<FeedUnit>('KG')
  const [price, setPrice] = useState('')
  const [apiaryId, setApiaryId] = useState<string | null>(null)
  const [date, setDate] = useState(todayIso())
  const save = useMutation({
    mutationFn: () => harvestApi.addProduct({
      product_type: type, quantity: Number(qty.replace(',', '.')), unit, price_per_unit: price ? Number(price.replace(',', '.')) : null,
      apiary_id: apiaryId, collected_at: date,
    }),
    onSuccess: () => { haptic('success'); qc.invalidateQueries({ queryKey: ['products'] }); onDone() },
    onError: () => haptic('error'),
  })
  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Choice label={tr("Что")} options={typeOpts} value={type} onChange={(v) => { if (v) { setType(v); setUnit(DEFAULT_UNIT[v]) } }} />
      <Field label={tr("Количество")} error={fieldError(save.error, 'quantity')}>
        <input className="input input--big" inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} required />
      </Field>
      <Choice label={tr("Единица")} options={unitOpts} value={unit} onChange={(v) => v && setUnit(v)} />
      <Field label={tr("Цена за единицу")} hint={tr("Можно не указывать")}><input className="input" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} /></Field>
      {(apiaries.data?.length ?? 0) > 1 && (
        <Choice label={tr("Пасека")} options={(apiaries.data ?? []).map((a) => ({ value: a.id, label: a.name }))} value={apiaryId} onChange={setApiaryId} allowNone />
      )}
      <Field label={tr("Дата")}><input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></Field>
      <div className="submit-bar"><SubmitButton pending={save.isPending}>{tr("Записать")}</SubmitButton></div>
    </form>
  )
}
