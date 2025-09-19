import React, { useState } from 'react'

export function Login({
  onLogin,
}: {
  onLogin: (u: string, p: string) => Promise<void>
}) {
  const [u, setU] = useState('admin')
  const [p, setP] = useState('admin')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr(null)
    setLoading(true)
    try {
      await onLogin(u, p)
    } catch (e: any) {
      setErr(e.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form
        onSubmit={submit}
        className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-[360px]"
      >
        <h1 className="text-xl font-semibold mb-4">Login</h1>
        {err && <div className="text-red-400 text-sm mb-2">{err}</div>}
        <div className="space-y-3">
          <input
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2"
            placeholder="Username"
            value={u}
            onChange={(e) => setU(e.target.value)}
          />
          <input
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2"
            placeholder="Password"
            type="password"
            value={p}
            onChange={(e) => setP(e.target.value)}
          />
          <button
            disabled={loading}
            className="w-full mt-1 px-3 py-2 rounded-lg bg-brand-500/20 border border-brand-500 text-brand-500"
          >
            {loading ? '...' : 'Login'}
          </button>
        </div>
      </form>
    </div>
  )
}