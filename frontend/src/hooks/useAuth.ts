import { useEffect, useState } from 'react'
import { apiGetConfig, apiLogin } from '../api'

export function useAuth() {
  const [ok, setOk] = useState<boolean | null>(null)
  const [cfg, setCfg] = useState<any>(null)

  async function refresh() {
    try {
      const c = await apiGetConfig()
      setCfg(c)
      setOk(true)
    } catch (e) {
      setOk(false)
    }
  }

  useEffect(() => { refresh() }, [])

  async function login(username: string, password: string) {
    await apiLogin(username, password)
    await refresh()
  }

  return { ok, cfg, login }
}