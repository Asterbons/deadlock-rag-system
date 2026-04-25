import type { Source } from '../types/api'

const typeStyles: Record<Source['type'], { bg: string; bd: string; fg: string }> = {
  hero:    { bg: 'rgba(74,138,134,0.2)',   bd: 'var(--dl-teal-500)',   fg: 'var(--dl-teal-300)'   },
  ability: { bg: 'rgba(138,75,209,0.18)',  bd: 'var(--dl-spirit-500)', fg: 'var(--dl-spirit-300)' },
  item:    { bg: 'rgba(214,147,33,0.18)',  bd: 'var(--dl-amber-500)',  fg: 'var(--dl-amber-300)'  },
}

interface Props {
  source: Source
}

export function SourceCard({ source }: Props) {
  const c = typeStyles[source.type] ?? typeStyles.hero
  const imageUrl = typeof source.metadata?.image === 'string' ? source.metadata.image : undefined
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      background: 'var(--bg-raised)', border: '1px solid var(--border-1)',
      borderRadius: 'var(--r-2)', padding: '6px 10px', fontSize: 12,
    }}>
      <span style={{
        background: c.bg, border: `1px solid ${c.bd}`, color: c.fg,
        padding: '2px 7px', borderRadius: 'var(--r-1)',
        fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase',
      }}>{source.type}</span>
      {imageUrl && (
        <img 
          src={imageUrl} 
          alt={source.label} 
          style={{ width: 24, height: 24, objectFit: 'contain', borderRadius: 4 }} 
        />
      )}
      <span style={{ flex: 1, color: 'var(--fg-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {source.label}
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--fg-3)' }}>
        {source.score.toFixed(4)}
      </span>
    </div>
  )
}
