import { WheelMark } from './WheelMark'

interface StatusDotProps {
  ok: boolean
  label: string
}

function StatusDot({ ok, label }: StatusDotProps) {
  const color = ok ? 'var(--dl-health-500)' : 'var(--dl-blood-500)'
  const fg = ok ? 'var(--dl-health-300)' : 'var(--dl-blood-300)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', fontWeight: 700, color: fg }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}`, flexShrink: 0 }} />
      {label}
    </div>
  )
}

interface NavProps {
  current: string
  ollama: boolean
  qdrant: boolean
  loading: boolean
}

const NAV_LINKS = [
  { href: '#/', label: 'The Archive' },
  { href: '#/chat', label: 'Consult' },
  { href: '#/heroes', label: 'Combatants' },
  { href: '#/attributes', label: 'Attributes' },
  { href: '#/items', label: 'Artefacts' },
]

function isActive(href: string, current: string): boolean {
  const path = (current || '#/').split('?')[0]
  if (href === '#/') return path === '#/' || path === '' || path === '#'
  return path === href || path.startsWith(href + '/')
}

export function Nav({ current, ollama, qdrant, loading }: NavProps) {
  return (
    <header style={{
      background: 'var(--bg-surface)', borderBottom: '1px solid var(--border-1)',
      padding: '0 24px', display: 'flex', alignItems: 'center', height: 58,
      flexShrink: 0, gap: 28, position: 'relative', zIndex: 10,
    }}>
      <a href="#/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none' }}>
        <WheelMark size={22} />
        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '0.18em', color: 'var(--dl-bone)', fontSize: 15 }}>
          THE <span style={{ color: 'var(--dl-gold-500)' }}>ORACLE</span>
        </div>
      </a>

      <nav style={{ display: 'flex', gap: 4, marginLeft: 12 }}>
        {NAV_LINKS.map(l => {
          const active = isActive(l.href, current)
          return (
            <a key={l.href} href={l.href} style={{
              textDecoration: 'none', fontSize: 11, fontFamily: 'var(--font-body)',
              fontWeight: 600, letterSpacing: '0.18em', textTransform: 'uppercase',
              color: active ? 'var(--dl-gold-300)' : 'var(--fg-2)',
              padding: '8px 14px',
              borderBottom: `2px solid ${active ? 'var(--dl-gold-500)' : 'transparent'}`,
              transition: 'all 150ms',
            }}>{l.label}</a>
          )
        })}
      </nav>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
        {loading ? (
          <span style={{ color: 'var(--fg-3)', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase' }}>Checking services…</span>
        ) : (
          <>
            <StatusDot ok={ollama} label="Engine" />
            <StatusDot ok={qdrant} label="Index" />
          </>
        )}
      </div>
    </header>
  )
}
