import React, { useState } from 'react'

export function ConfirmModal({
  open,
  title,
  body,
  onClose,
  onConfirm,
}: {
  open: boolean
  title: string
  body: string
  onClose: () => void
  onConfirm: () => void
}) {
  const [text, setText] = useState('')
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl p-5 w-[520px]">
        <h2 className="text-lg font-semibold mb-2">{title}</h2>
        <p className="text-sm text-zinc-300 mb-3">{body}</p>
        <input
          className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 mb-4"
          placeholder="Type CONFIRM"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-3 py-2 rounded-lg border border-zinc-700"
          >
            Cancel
          </button>
          <button
            disabled={text !== 'CONFIRM'}
            onClick={onConfirm}
            className="px-3 py-2 rounded-lg bg-red-600 disabled:opacity-40"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}