import { useState, useRef, useEffect } from 'react'
import { Message } from './Message'
import { WheelMark } from './WheelMark'
import type { ChatMessage, UsageData } from '../types/api'

const SUGGESTIONS = [
  'What is the base health of Infernus?',
  'How much damage does Concussive Combustion deal at 150 spirit power?',
  'Should I buy Mystic Shot on Infernus?',
  'Which combatants are best for beginners?',
]

interface Props {
  messages: ChatMessage[]
  isLoading: boolean
  sendMessage: (q: string) => void
  clearHistory: () => void
  lastUsage: UsageData | null
  sessionUsage: UsageData
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 22, padding: '40px 20px', textAlign: 'center' }}>
      <WheelMark size={64} />
      <div>
        <div style={{ fontSize: 10, letterSpacing: '0.28em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 12 }}>The Archive Stirs</div>
        <div style={{ fontFamily: 'var(--font-display)', fontSize: 28, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dl-bone)', fontWeight: 700, lineHeight: 1.1 }}>
          What knowledge<br />do you seek?
        </div>
      </div>
      <div className="dl-hairline" style={{ width: 180 }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%', maxWidth: 560 }}>
        {SUGGESTIONS.map((s, i) => (
          <button key={i} onClick={() => onPick(s)} style={{
            background: 'var(--bg-card)', border: '1px solid var(--border-1)', color: 'var(--fg-2)',
            padding: '12px 16px', borderRadius: 'var(--r-2)', textAlign: 'left',
            fontSize: 13, cursor: 'pointer', fontFamily: 'var(--font-body)', transition: 'all 120ms',
          }}
            onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--dl-gold-700)'; e.currentTarget.style.color = 'var(--dl-gold-300)'; e.currentTarget.style.background = 'var(--bg-raised)' }}
            onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border-1)'; e.currentTarget.style.color = 'var(--fg-2)'; e.currentTarget.style.background = 'var(--bg-card)' }}
          >
            <span style={{ color: 'var(--dl-gold-500)', marginRight: 10, fontFamily: 'var(--font-display)' }}>›</span>{s}
          </button>
        ))}
      </div>
    </div>
  )
}

export function ChatWindow({ messages, isLoading, sendMessage, clearHistory, lastUsage, sessionUsage }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isStreaming = messages.some(m => m.isStreaming)
  const disabled = isStreaming || isLoading
  const canSend = input.trim() && !disabled

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || disabled) return
    sendMessage(trimmed)
    setInput('')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as unknown as React.FormEvent)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', maxWidth: 900, width: '100%', margin: '0 auto', borderLeft: '1px solid var(--border-2)', borderRight: '1px solid var(--border-2)' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px', minHeight: 0 }}>
        {messages.length === 0
          ? <EmptyState onPick={q => { sendMessage(q) }} />
          : messages.map((msg, i) => <Message key={i} message={msg} />)
        }
        <div ref={bottomRef} />
      </div>

      <div style={{ borderTop: '1px solid var(--border-1)', padding: '14px 20px 18px', background: 'var(--bg-surface)' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            placeholder="Speak your query into the rift…"
            style={{
              flex: 1, background: 'var(--bg-input)', color: 'var(--fg-1)',
              border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)',
              padding: '12px 14px', fontSize: 14, resize: 'none', outline: 'none',
              lineHeight: 1.5, maxHeight: 120, fontFamily: 'var(--font-body)',
              opacity: disabled ? 0.6 : 1, transition: 'border-color 120ms, box-shadow 120ms',
            }}
            onInput={e => { const el = e.currentTarget; el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px' }}
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--dl-gold-500)'; e.currentTarget.style.boxShadow = 'var(--glow-gold)' }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-1)'; e.currentTarget.style.boxShadow = 'none' }}
          />
          <button type="submit" disabled={!canSend} style={{
            background: canSend ? 'var(--action)' : 'var(--bg-card)',
            color: canSend ? 'var(--dl-bone)' : 'var(--fg-3)',
            border: `1px solid ${canSend ? 'var(--dl-teal-300)' : 'var(--border-1)'}`,
            borderRadius: 'var(--r-2)', padding: '12px 20px',
            fontSize: 11, fontWeight: 700, cursor: canSend ? 'pointer' : 'not-allowed',
            letterSpacing: '0.18em', textTransform: 'uppercase', transition: 'all 120ms',
            boxShadow: canSend ? 'var(--glow-teal)' : 'none', whiteSpace: 'nowrap',
          }}>Consult</button>
          <button type="button" onClick={clearHistory} disabled={disabled} style={{
            background: 'transparent', color: 'var(--fg-3)',
            border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)',
            padding: '12px 14px', fontSize: 11, cursor: disabled ? 'not-allowed' : 'pointer',
            letterSpacing: '0.18em', textTransform: 'uppercase',
          }}>Clear</button>
        </form>
        <div style={{ marginTop: 8, fontSize: 10, color: 'var(--fg-4)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          Enter to send · Shift+Enter for newline
        </div>
      </div>

      {lastUsage && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: '6px 20px',
          fontSize: '10px',
          color: 'var(--fg-3)',
          borderTop: '1px solid var(--border-1)',
          background: 'var(--bg-app)',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.02em',
          opacity: 0.8
        }}>
          <span>
            LAST: {lastUsage.prompt_tokens.toLocaleString()} IN + {lastUsage.completion_tokens.toLocaleString()} OUT = {lastUsage.total_tokens.toLocaleString()} TOKENS
            {lastUsage.cost_usd > 0 && ` ($${lastUsage.cost_usd < 0.01 ? (lastUsage.cost_usd * 100).toFixed(3) + '¢' : lastUsage.cost_usd.toFixed(4)})`}
          </span>
          <span>
            SESSION: {sessionUsage.total_tokens.toLocaleString()} TOKENS
            {sessionUsage.cost_usd > 0 && ` ($${sessionUsage.cost_usd.toFixed(4)})`}
          </span>
        </div>
      )}
    </div>
  )
}
