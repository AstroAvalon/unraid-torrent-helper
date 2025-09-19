import React, { useEffect, useState } from 'react'

export function Toast({
  msg,
  onDone,
}: {
  msg: string
  onDone?: () => void
}) {
  const [show, setShow] = useState(true)
  useEffect(() => {
    const t = setTimeout(() => {
      setShow(false)
      onDone?.()
    }, 3500)
    return () => clearTimeout(t)
  }, [onDone])
  if (!show) return null
  return (
    <div className="fixed bottom-4 right-4 bg-zinc-800 text-zinc-50 px-4 py-2 rounded-xl shadow-lg border border-zinc-700">
      {msg}
    </div>
  )
}