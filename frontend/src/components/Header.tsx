import React from 'react'

export function Header({
  dryRun,
  setDryRun,
  onReload,
}: {
  dryRun: boolean
  setDryRun: (b: boolean) => void
  onReload: () => void
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h1 className="text-2xl font-semibold">Unraid Torrent Helper</h1>
      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
          />
          Dry-Run
        </label>
        <button
          onClick={onReload}
          className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700"
        >
          Refresh
        </button>
      </div>
    </div>
  )
}