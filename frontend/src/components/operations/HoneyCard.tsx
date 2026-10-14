import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { harvestApi } from '../../api/resources'
import { formatDate, num } from '../../utils/labels'
import { tr } from '../../i18n'

/** This year's honey of one hive; hidden until the first harvest. */
export function HoneyCard({ hiveId }: { hiveId: string }) {
  const q = useQuery({ queryKey: ['hive-honey', hiveId], queryFn: () => harvestApi.hiveHoney(hiveId) })
  if (!q.data?.items.length) return null
  const last = q.data.items[0]
  return (
    <section className="card honey-card">
      <div className="card__titlebar">
        <h2 className="card__title">{tr("Мёд {0}", q.data.year)}</h2>
        <Link className="link small" to="/honey">{tr("Вся пасека")}</Link>
      </div>
      <div className="honey-card__value"><span>{num(q.data.year_kg)}</span>{" "}{tr("кг")}</div>
      <div className="small hint">{tr("Последняя откачка {0}: {1} кг", formatDate(last.harvest_date), num(last.weight_kg))}{last.honey_type ? `, ${last.honey_type.toLowerCase()}` : ''}{tr(". За всё время {0} кг.", num(q.data.all_time_kg))}</div>
    </section>
  )
}
