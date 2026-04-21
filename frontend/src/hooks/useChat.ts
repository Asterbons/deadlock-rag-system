import { useState, useRef } from 'react'
import type { ChatMessage, SSEEvent, UsageData } from '../types/api'

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [lastUsage, setLastUsage] = useState<UsageData | null>(null)
  const [sessionUsage, setSessionUsage] = useState<UsageData>({
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    cost_usd: 0
  })
  const historyRef = useRef<{ role: 'user' | 'assistant'; content: string }[]>([])

  async function sendMessage(question: string) {
    const trimmed = question.trim()
    if (!trimmed) return

    const userMsg: ChatMessage = { role: 'user', content: trimmed }
    const assistantMsg: ChatMessage = { role: 'assistant', content: '', isStreaming: true }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setIsLoading(true)

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed, history: historyRef.current }),
      })

      if (!res.body) throw new Error('No response body')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finalContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          let event: SSEEvent
          try {
            event = JSON.parse(jsonStr)
          } catch {
            continue
          }

          if (event.type === 'token') {
            finalContent += event.content
            const snapshot = finalContent
            setMessages(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last && last.role === 'assistant') {
                next[next.length - 1] = { ...last, content: snapshot }
              }
              return next
            })
          } else if (event.type === 'sources') {
            const sources = event.sources
            setMessages(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last && last.role === 'assistant') {
                next[next.length - 1] = { ...last, sources }
              }
              return next
            })
          } else if (event.type === 'done') {
            setMessages(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last && last.role === 'assistant') {
                next[next.length - 1] = { ...last, isStreaming: false }
              }
              return next
            })
            historyRef.current = [
              ...historyRef.current,
              { role: 'user', content: trimmed },
              { role: 'assistant', content: finalContent },
            ]
            setIsLoading(false)
          } else if (event.type === 'usage') {
            const usage = event as UsageData
            setLastUsage(usage)
            setSessionUsage(prev => ({
              prompt_tokens: prev.prompt_tokens + usage.prompt_tokens,
              completion_tokens: prev.completion_tokens + usage.completion_tokens,
              total_tokens: prev.total_tokens + usage.total_tokens,
              cost_usd: prev.cost_usd + usage.cost_usd
            }))
          } else if (event.type === 'error') {
            const errContent = event.content
            setMessages(prev => {
              const next = [...prev]
              const last = next[next.length - 1]
              if (last && last.role === 'assistant') {
                next[next.length - 1] = { ...last, content: errContent, isStreaming: false }
              }
              return next
            })
            setIsLoading(false)
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setMessages(prev => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last && last.role === 'assistant') {
          next[next.length - 1] = { ...last, content: `Error: ${msg}`, isStreaming: false }
        }
        return next
      })
      setIsLoading(false)
    }
  }

  function clearHistory() {
    setMessages([])
    historyRef.current = []
    setLastUsage(null)
    setSessionUsage({ prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, cost_usd: 0 })
    setIsLoading(false)
  }

  return { messages, isLoading, sendMessage, clearHistory, lastUsage, sessionUsage }
}
