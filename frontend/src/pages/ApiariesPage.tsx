import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiariesApi, type ApiaryInput } from '../api/resources'
import { ErrorBox, Field, Sheet, SubmitButton, fieldError } from '../components/ui'
import { LoadingView, MessageView } from '../components/StateViews'
import { usePermissions } from '../hooks/usePermissions'
import { haptic } from '../services/telegram'
import type { Apiary } from '../types/api'
import { plural } from '../utils/plural'

export function ApiariesPage() {
  const { canManage } = usePermissions()
  const [showArchived, setShowArchived] = useState(false)
  const [editing, setEditing] = useState<Apiary | 'new' | null>(null)
  const apiaries = useQuery({ queryKey: ['apiaries', showArchived], queryFn: () => apiariesApi.list(showArchived) })

  return (
    <div className="page">
      <div className="page__titlebar">
        <h1 className="page__title">Пасеки</h1>
        {canManage && <button className="btn btn--primary btn--sm" onClick={() => setEditing('new')}>＋ Пасека</button>}
      </div>
      <ErrorBox error={apiaries.error} />
      {apiaries.isLoading ? <LoadingView /> : apiaries.data?.length === 0 ? (
        <MessageView icon="🏡" title="Пасек пока нет" text={canManage ? 'Создайте первую пасеку, затем добавьте в неё ульи.' : undefined}
          action={canManage ? { label: 'Создать пасеку', onClick: () => setEditing('new') } : undefined} />
      ) : (
        <ul className="list">
          {apiaries.data?.map((a) => (
            <li key={a.id} className={`card${a.is_archived ? ' card--muted' : ''}`}>
              <div className="card__titlebar">
                <h2 className="card__title">🏡 {a.name}{a.is_archived && ' (архив)'}</h2>
                {canManage && <button className="icon-btn" onClick={() => setEditing(a)} aria-label="Изменить">✏️</button>}
              </div>
              {a.address && <p className="hint">📍 {a.address}</p>}
              {a.description && <p className="small">{a.description}</p>}
              <div className="btn-row">
                <Link className="btn btn--secondary" to={`/hives?apiary=${a.id}`}>🐝 {a.hive_count} {plural(a.hive_count, 'улей', 'улья', 'ульев')}</Link>
                {canManage && !a.is_archived && <Link className="btn btn--ghost" to={`/hives/new?apiary=${a.id}`}>＋ Улей</Link>}
              </div>
            </li>
          ))}
        </ul>
      )}
      <label className="switch"><input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} /><span>Показать архивные</span></label>
      <Sheet open={editing !== null} title={editing === 'new' ? 'Новая пасека' : 'Пасека'} onClose={() => setEditing(null)}>
        {editing && <ApiaryForm apiary={editing === 'new' ? null : editing} onDone={() => setEditing(null)} />}
      </Sheet>
    </div>
  )
}

function ApiaryForm({ apiary, onDone }: { apiary: Apiary | null; onDone: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState(apiary?.name ?? '')
  const [address, setAddress] = useState(apiary?.address ?? '')
  const [description, setDescription] = useState(apiary?.description ?? '')
  const [coords, setCoords] = useState(apiary?.latitude != null ? `${apiary.latitude}, ${apiary.longitude}` : '')
  const [archived, setArchived] = useState(apiary?.is_archived ?? false)

  const save = useMutation({
    mutationFn: () => {
      const [lat, lon] = coords.split(',').map((s) => s.trim()).filter(Boolean).map(Number)
      const body: ApiaryInput = {
        name, address: address || null, description: description || null,
        latitude: Number.isFinite(lat) ? lat : null, longitude: Number.isFinite(lon) ? lon : null,
      }
      return apiary ? apiariesApi.update(apiary.id, { ...body, is_archived: archived }) : apiariesApi.create(body)
    },
    onSuccess: () => { haptic('success'); qc.invalidateQueries({ queryKey: ['apiaries'] }); qc.invalidateQueries({ queryKey: ['hives'] }); onDone() },
    onError: () => haptic('error'),
  })

  const locate = () => navigator.geolocation?.getCurrentPosition(
    (p) => setCoords(`${p.coords.latitude.toFixed(5)}, ${p.coords.longitude.toFixed(5)}`),
  )

  return (
    <form className="form" onSubmit={(e: FormEvent) => { e.preventDefault(); save.mutate() }}>
      <ErrorBox error={save.error} />
      <Field label="Название" error={fieldError(save.error, 'name')}>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} autoFocus />
      </Field>
      <Field label="Адрес / место"><input className="input" value={address} onChange={(e) => setAddress(e.target.value)} maxLength={255} /></Field>
      <Field label="Координаты" hint="широта, долгота" error={fieldError(save.error, 'latitude') ?? fieldError(save.error, 'longitude')}>
        <div className="input-group">
          <input className="input" value={coords} onChange={(e) => setCoords(e.target.value)} placeholder="38.75, 68.82" inputMode="decimal" />
          <button type="button" className="btn btn--secondary" onClick={locate} aria-label="Моё местоположение">📍</button>
        </div>
      </Field>
      <Field label="Описание"><textarea className="input" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} /></Field>
      {apiary && <label className="switch"><input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} /><span>В архиве</span></label>}
      <SubmitButton pending={save.isPending}>{apiary ? 'Сохранить' : 'Создать'}</SubmitButton>
    </form>
  )
}
