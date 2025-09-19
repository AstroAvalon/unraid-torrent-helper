import { useEffect, useMemo, useState } from 'react'
import { Header } from './components/Header'
import { Tabs } from './components/Tabs'
import { TorrentTable } from './components/TorrentTable'
import { Login } from './components/Login'
import { useAuth } from './hooks/useAuth'
import { apiListTorrents } from './api'
import type { Torrent } from './types'
import { connectSSE } from './sse'
import { LogPanel } from './components/LogPanel'

type TabKey = 'Misplaced' | 'OK' | 'Stuck'

export default function App() {
  const { ok, login } = useAuth()
  const [dryRun, setDryRun] = useState(true)
  const [tab, setTab] = useState<TabKey>('Misplaced')
  const [items, setItems] = useState<Torrent[]>([])
  const [lines, setLines] = useState<string[]>([])

  async function load() {
    const r = await apiListTorrents()
    setItems(r.items)
  }

  useEffect(() => { if (ok) load() }, [ok])

  useEffect(() => {
    if (!ok) return
    const close = connectSSE((ev) => {
      try {
        const data = JSON.parse((ev as any).data || '{}')
        if (typeof data.line === 'string') {
          setLines(prev => [data.line, ...prev].slice(0, 1000))
        } else if (typeof data.message === 'string') {
          const tag = data.level ? `[${data.level}] ` : ''
          const hash = data.hash ? `${String(data.hash).slice(0,8)} ` : ''
          setLines(prev => [`${hash}${tag}${data.message}`, ...prev].slice(0, 1000))
        }
      } catch {
        /* ignore non-JSON and heartbeat comments */
      }
    })
    return close
  }, [ok])

  const misplaced = useMemo(() => items.filter(t => t.misplaced), [items])
  const stuck = useMemo(() => items.filter(t => t.state === 'metaDL'), [items])
  const okList = useMemo(() => items.filter(t => !t.misplaced), [items])

  if (ok === false) return <Login onLogin={login} />
  if (ok === null) return <div className="p-6">Loading…</div>

  const tabs = [
    { key: 'Misplaced' as TabKey, label: `Misplaced (${misplaced.length})` },
    { key: 'OK' as TabKey,        label: `OK (${okList.length})` },
    { key: 'Stuck' as TabKey,     label: `Stuck (${stuck.length})` },
  ]

  const current =
    tab === 'Misplaced' ? misplaced :
    tab === 'Stuck' ? stuck :
    okList

  const allowMigrate = tab !== 'OK'

  return (
    <div className="p-6 max-w-[1800px] mx-auto">
      <Header dryRun={dryRun} setDryRun={setDryRun} onReload={load} />
      <Tabs items={tabs} activeKey={tab} onTab={(k)=>setTab(k)} />

      <div className="flex">
        {/* main content */}
        <div className="flex-1 min-w-0">
          <TorrentTable items={current} dryRun={dryRun} onRefresh={load} allowMigrate={allowMigrate} />
        </div>

        {/* side log */}
        <LogPanel lines={lines} onClear={() => setLines([])} />
      </div>
    </div>
  )
}