import React from 'react'
import type { Torrent } from '../types'

export function Drawer({
  open,
  onClose,
  tor,
}: {
  open: boolean
  onClose: () => void
  tor?: Torrent | null
}) {
  if (!open || !tor) return null
  return (
    <div className="fixed inset-y-0 right-0 w-[420px] bg-zinc-900 border-l border-zinc-800 p-5 z-40">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold">Details</h3>
        <button onClick={onClose} className="text-zinc-400">
          ✕
        </button>
      </div>
      <div className="space-y-2 text-sm">
        <div>
          <span className="text-zinc-400">Name:</span> {tor.name}
        </div>
        <div>
          <span className="text-zinc-400">Hash:</span> {tor.hash}
        </div>
        <div>
          <span className="text-zinc-400">State:</span> {tor.state}
        </div>
        <div>
          <span className="text-zinc-400">Progress:</span>{' '}
          {(tor.progress * 100).toFixed(1)}%
        </div>
        <div className="truncate">
          <span className="text-zinc-400">Save path:</span> {tor.save_path}
        </div>
        {tor.misplaced && tor.suggested_target && (
          <div className="text-amber-400">
            Suggested: {tor.suggested_target}
          </div>
        )}
      </div>
    </div>
  )
}