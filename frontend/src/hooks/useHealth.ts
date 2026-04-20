import { useState, useEffect } from 'react'
import type { HealthStatus } from '../types/api'

export function useHealth() {
  const [health, setHealth] = useState<{ ollama: boolean; qdrant: boolean; loading: boolean }>({
    ollama: false,
    qdrant: false,
    loading: true,
  })

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        const res = await fetch('/api/health')
        if (!res.ok) throw new Error('health check failed')
        const data: HealthStatus = await res.json()
        if (!cancelled) {
          setHealth({ ollama: data.ollama, qdrant: data.qdrant, loading: false })
        }
      } catch {
        if (!cancelled) {
          setHealth({ ollama: false, qdrant: false, loading: false })
        }
      }
    }

    check()
    const id = setInterval(check, 10000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  return health
}
