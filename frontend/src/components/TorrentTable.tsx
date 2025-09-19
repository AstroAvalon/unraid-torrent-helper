import React, { useMemo, useState } from 'react'
import type { Torrent } from '../types'
import { apiFixMetadata, apiMigrate } from '../api'
import { ConfirmModal } from './ConfirmModal'

function bytes(n: number) {
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let x = n
  while (x >= 1024 && i < u.length - 1) {
    x /= 1024
    i++
  }
  return `${x.toFixed(1)} ${u[i]}`
}

type SortKey =
  | 'name'
  | 'hash'
  | 'state'
  | 'progress'
  | 'size'
  | 'save_path'
  | 'misplaced'
  | 'suggested_target'

type SortDir = 'asc' | 'desc'

export function TorrentTable({
  items,
  dryRun,
  onRefresh,
  allowMigrate,
}: {
  items: Torrent[]
  dryRun: boolean
  onRefresh: () => void
  allowMigrate: boolean
}) {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState<Record<string, boolean>>({})
  const [confirmDel, setConfirmDel] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  // --- filtering ---
  const filtered = useMemo(
    () =>
      items.filter(
        (t) =>
          t.name.toLowerCase().includes(q.toLowerCase()) ||
          t.hash.includes(q)
      ),
    [items, q]
  )

  // --- sorting ---
  function toggleSort(k: SortKey) {
    if (sortKey === k) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(k)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    const arr = [...filtered]
    const dir = sortDir === 'asc' ? 1 : -1
    arr.sort((a, b) => {
      const av = getVal(a, sortKey)
      const bv = getVal(b, sortKey)
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir
      if (typeof av === 'boolean' && typeof bv === 'boolean') return (Number(av) - Number(bv)) * dir
      const as = String(av ?? '').toLowerCase()
      const bs = String(bv ?? '').toLowerCase()
      if (as < bs) return -1 * dir
      if (as > bs) return 1 * dir
      return 0
    })
    return arr
  }, [filtered, sortKey, sortDir])

  const selected = useMemo(
    () => Object.keys(sel).filter((h) => sel[h]),
    [sel]
  )

  function getVal(t: Torrent, k: SortKey): string | number | boolean | null {
    switch (k) {
      case 'name': return t.name
      case 'hash': return t.hash
      case 'state': return t.state
      case 'progress': return t.progress
      case 'size': return t.size
      case 'save_path': return t.save_path
      case 'misplaced': return !!t.misplaced
      case 'suggested_target': return t.suggested_target ?? ''
      default: return ''
    }
  }

  function SortButton({
    k,
    children,
    className = '',
  }: {
    k: SortKey
    children: React.ReactNode
    className?: string
  }) {
    const active = sortKey === k
    const arrow = active ? (sortDir === 'asc' ? '▲' : '▼') : '⇅'
    return (
      <button
        className={`flex items-center gap-1 ${className}`}
        onClick={() => toggleSort(k)}
        title="Click to sort"
      >
        <span>{children}</span>
        <span className="text-xs opacity-70">{arrow}</span>
      </button>
    )
  }

  async function migrate(deleteOld: boolean) {
    if (!allowMigrate) return
    if (selected.length === 0) return
    if (deleteOld) {
      setConfirmDel(true)
      return
    }
    await apiMigrate(selected, { dryRun, deleteOld: false })
    onRefresh()
  }

  async function confirmDeleteOld() {
    setConfirmDel(false)
    if (selected.length === 0) return
    await apiMigrate(selected, { dryRun, deleteOld: true })
    onRefresh()
  }

  async function fixMeta() {
    if (selected.length === 0) return
    await apiFixMetadata(selected)
    onRefresh()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name or hash..."
          className="w-80 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2"
        />
        <div className="flex gap-2">
          {allowMigrate && (
            <>
              <button
                onClick={() => migrate(false)}
                className="px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700"
              >
                Migrate Selected {dryRun && '(dry-run)'}
              </button>
              <button
                onClick={() => migrate(true)}
                className="px-3 py-2 rounded-lg bg-red-700"
              >
                Migrate + Delete Old
              </button>
            </>
          )}
          <button
            onClick={fixMeta}
            className="px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700"
          >
            Fix Metadata
          </button>
          <button
            onClick={onRefresh}
            className="px-3 py-2 rounded-lg bg-zinc-800 border border-zinc-700"
          >
            Reload
          </button>
        </div>
      </div>

      {/* No horizontal scroll needed; allow wrapping in long columns */}
      <div className="border border-zinc-800 rounded-xl">
        <table className="min-w-full table-auto text-sm">
          <thead className="bg-zinc-900 text-zinc-300">
            <tr>
              <th className="p-2">
                <input
                  type="checkbox"
                  onChange={(e) => {
                    const all = Object.fromEntries(
                      items.map((t) => [t.hash, e.target.checked])
                    )
                    setSel(all)
                  }}
                />
              </th>
              <th className="p-2 text-left">
                <SortButton k="name">Name</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="hash">Hash</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="state">State</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="progress">Progress</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="size">Size</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="save_path">Save path</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="misplaced">Misplaced</SortButton>
              </th>
              <th className="p-2 text-left">
                <SortButton k="suggested_target">Suggested</SortButton>
              </th>
            </tr>
          </thead>

          <tbody>
            {sorted.map((t) => (
              <tr
                key={t.hash}
                className="border-t border-zinc-800 hover:bg-zinc-900/60 align-top"
              >
                <td className="p-2">
                  <input
                    type="checkbox"
                    checked={!!sel[t.hash]}
                    onChange={(e) =>
                      setSel((s) => ({ ...s, [t.hash]: e.target.checked }))
                    }
                  />
                </td>

                <td className="p-2 break-words">{t.name}</td>

                <td className="p-2 font-mono text-[11px] break-all" title={t.hash}>
                  {t.hash}
                </td>

                <td className="p-2">{t.state}</td>

                <td className="p-2 whitespace-nowrap">
                  {(t.progress * 100).toFixed(1)}%
                </td>

                <td className="p-2 whitespace-nowrap">
                  {bytes(t.size)}
                </td>

                {/* Wrap long paths; keep tooltip for full path */}
                <td className="p-2 break-words" title={t.save_path}>
                  {t.save_path}
                </td>

                <td className="p-2">{t.misplaced ? 'yes' : 'no'}</td>

                <td className="p-2 break-words" title={t.suggested_target ?? ''}>
                  {t.suggested_target ?? ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmModal
        open={confirmDel}
        title="Confirm deletion of old files"
        body="This will delete the ORIGINAL source directory after a migration. Type CONFIRM to proceed."
        onClose={() => setConfirmDel(false)}
        onConfirm={confirmDeleteOld}
      />
    </div>
  )
}