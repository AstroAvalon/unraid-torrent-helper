export function connectSSE(onMessage: (ev: MessageEvent) => void) {
  let es = new EventSource('/api/events/stream', { withCredentials: true } as any)

  es.onopen = () => {
    // optional: you could dispatch a message to your UI here
  }
  es.onerror = () => {
    // Auto-reconnect after a short delay
    try { es.close() } catch {}
    setTimeout(() => {
      es = connectSSE(onMessage) as any
    }, 1500)
  }

  es.onmessage = onMessage
  es.addEventListener('progress', onMessage as any)
  es.addEventListener('state', onMessage as any)
  es.addEventListener('done', onMessage as any)

  return () => {
    try { es.close() } catch {}
  }
}