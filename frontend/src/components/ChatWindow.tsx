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

export function ChatWindow({ messages, isLoading, sendMessage, lastUsage, sessionUsage }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isStreaming = messages.some(m => m.isStreaming)
  const disabled = isStreaming || isLoading
  const canSend = input.trim().length > 0 && !disabled

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const el = inputRef.current
    if (!el) return

    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
    el.style.overflowY = el.scrollHeight > 200 ? 'auto' : 'hidden'
  }, [input])

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
    <div className="chat-pattern" style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', width: '100%' }}>
      <div className="chat-messages">
        {messages.length === 0
          ? <EmptyState onPick={q => { sendMessage(q) }} />
          : messages.map((msg, i) => <Message key={i} message={msg} />)
        }
        <div ref={bottomRef} />
      </div>

      <div className="chat-composer">
        <form onSubmit={handleSubmit} className="chat-input-card">
          <div className="chat-input-field">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              rows={1}
              placeholder="Ask a question or type a command..."
              className="chat-input-textarea"
            />
          </div>
          <button type="submit" disabled={!canSend} className="chat-send-button" aria-label="Send message">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </form>
        <div className="chat-usage">
          {lastUsage && (
            <>
              <span>
                LAST: {lastUsage.prompt_tokens.toLocaleString()} IN + {lastUsage.completion_tokens.toLocaleString()} OUT = {lastUsage.total_tokens.toLocaleString()} TOKENS
                {lastUsage.cost_usd > 0 && ` ($${lastUsage.cost_usd < 0.01 ? (lastUsage.cost_usd * 100).toFixed(3) + '¢' : lastUsage.cost_usd.toFixed(4)})`}
              </span>
              <span>
                SESSION: {sessionUsage.total_tokens.toLocaleString()} TOKENS
                {sessionUsage.cost_usd > 0 && ` ($${sessionUsage.cost_usd.toFixed(4)})`}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
