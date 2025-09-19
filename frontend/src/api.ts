import type { TorrentsResp } from './types'

export async function apiLogin(username: string, password: string): Promise<void> {
  const r = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username, password })
  })
  if (!r.ok) throw new Error(await r.text())
}

export async function apiGetConfig() {
  const r = await fetch('/api/config', { credentials: 'include' })
  if (!r.ok) throw new Error('Auth required')
  return r.json()
}

export async function apiListTorrents(): Promise<TorrentsResp> {
  const r = await fetch('/api/torrents', { credentials: 'include' })
  if (!r.ok) throw new Error('Failed to load torrents')
  return r.json()
}

export async function apiMigrate(hashes: string[], opts: { dryRun?: boolean; deleteOld?: boolean }) {
  const r = await fetch('/api/actions/migrate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ hashes, dryRun: !!opts.dryRun, deleteOld: !!opts.deleteOld })
  })
  if (!r.ok) throw new Error('Failed to start migrate task')
  return r.json()
}

export async function apiFixMetadata(hashes: string[]) {
  const r = await fetch('/api/actions/fix-metadata', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ hashes })
  })
  if (!r.ok) throw new Error('Failed to send fix-metadata')
  return r.json()
}