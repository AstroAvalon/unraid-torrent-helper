import React from 'react'

export function LogPanel({
  lines,
  onClear
}: {
  lines: string[]
  onClear: () => void
}) {
  return (
    <aside className="sticky top-4 h-[calc(100vh-2rem)] w-[420px] shrink-0 bg-black/30 border border-zinc-800 rounded-xl p-3 ml-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm text-zinc-400">Live log</h3>
        <button onClick={onClear} className="text-xs text-zinc-400 hover:text-zinc-200">clear</button>
      </div>
      <div className="h-full overflow-auto font-mono text-xs leading-5">
        {lines.length === 0 ? (
          <div className="text-zinc-500">No activity yet…</div>
        ) : (
          lines.map((l, i) => <div key={i}>{l}</div>)
        )}
      </div>
    </aside>
  )
}