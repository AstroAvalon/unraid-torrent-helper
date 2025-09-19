import React from 'react'
import { clsx } from 'clsx'

export type TabItem<T extends string = string> = {
  key: T
  label: string
}

export function Tabs<T extends string>({
  items,
  activeKey,
  onTab,
}: {
  items: TabItem<T>[]
  activeKey: T
  onTab: (t: T) => void
}) {
  return (
    <div className="flex gap-2 mb-3">
      {items.map(it => (
        <button
          key={it.key}
          onClick={() => onTab(it.key)}
          className={clsx(
            'px-3 py-1.5 rounded-lg border',
            activeKey === it.key
              ? 'bg-brand-500/20 border-brand-500 text-brand-500'
              : 'bg-zinc-900 border-zinc-700 hover:bg-zinc-800'
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  )
}