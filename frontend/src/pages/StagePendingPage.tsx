import type { IconName } from '../components/Icon'
import { MessageView } from '../components/StateViews'

/** Shown for sections whose backend arrives in a later development stage. */
export function StagePendingPage({ icon, title, stage }: { icon: IconName; title: string; stage: number }) {
  return (
    <div className="page">
      <h1 className="page__title">{title}</h1>
      <MessageView icon={icon} title="Раздел подключается" text={`Модуль появится на этапе ${stage}.`} />
    </div>
  )
}
