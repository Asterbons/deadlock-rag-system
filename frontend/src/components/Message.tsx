import { SourceCard } from './SourceCard'
import { WheelMark } from './WheelMark'
import type { ChatMessage } from '../types/api'

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  const regex = /(\*\*(.+?)\*\*|`([^`]+)`)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let i = 0

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(<span key={i++}>{text.slice(lastIndex, match.index)}</span>)
    if (match[2] !== undefined) {
      parts.push(<strong key={i++} style={{ color: 'var(--dl-gold-300)', fontWeight: 700 }}>{match[2]}</strong>)
    } else if (match[3] !== undefined) {
      parts.push(
        <code key={i++} style={{ background: 'var(--bg-input)', color: 'var(--dl-teal-300)', padding: '1px 6px', borderRadius: 3, fontFamily: 'var(--font-mono)', fontSize: '0.9em', border: '1px solid var(--border-2)' }}>
          {match[3]}
        </code>
      )
    }
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) parts.push(<span key={i++}>{text.slice(lastIndex)}</span>)
  return parts
}

function renderText(text: string): React.ReactNode[] {
  return text.split('\n').map((line, i, arr) => (
    <span key={i}>{renderInline(line)}{i < arr.length - 1 ? <br /> : null}</span>
  ))
}

function TypingDots() {
  return (
    <span style={{ color: 'var(--fg-3)', fontStyle: 'italic', fontFamily: 'var(--font-narrative)', fontSize: 14 }}>
      The Oracle consults the Index
      <span style={{ display: 'inline-flex', gap: 4, marginLeft: 6, verticalAlign: 'middle' }}>
        {[0, 0.2, 0.4].map(d => (
          <span key={d} style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--dl-gold-500)', display: 'inline-block', animation: `bounce 1.2s ease-in-out ${d}s infinite` }} />
        ))}
      </span>
    </span>
  )
}

interface Props {
  message: ChatMessage
}

export function Message({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <div style={{
          background: 'var(--dl-teal-700)', color: 'var(--dl-bone)',
          maxWidth: '70%', borderRadius: '2px 12px 2px 12px',
          padding: '12px 16px', lineHeight: 1.5,
          border: '1px solid var(--dl-teal-500)', fontSize: 13,
        }}>
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16, gap: 12 }}>
      <div style={{ flexShrink: 0, marginTop: 4, opacity: 0.8 }}>
        <WheelMark size={22} />
      </div>
      <div style={{ maxWidth: '82%' }}>
        <div style={{ fontSize: 9, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 6 }}>
          The Oracle
        </div>
        <div style={{
          background: 'var(--bg-raised)', color: 'var(--fg-1)',
          borderRadius: '2px 12px 12px 12px',
          padding: '14px 16px', lineHeight: 1.6,
          border: '1px solid var(--border-1)',
          borderLeft: '2px solid var(--dl-gold-700)',
          fontSize: 13.5,
        }}>
          {message.content ? renderText(message.content) : null}
          {message.isStreaming && message.content && (
            <span style={{ display: 'inline-block', width: 7, height: 13, background: 'var(--dl-gold-500)', marginLeft: 2, verticalAlign: 'text-bottom', animation: 'blink 1s step-end infinite' }} />
          )}
          {!message.content && message.isStreaming && <TypingDots />}
        </div>
        {message.sources && message.sources.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 9, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--fg-3)', fontWeight: 700, marginBottom: 6 }}>
              Drawn from the Index
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {message.sources.map((s, i) => <SourceCard key={i} source={s} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
