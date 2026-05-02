import { WheelMark } from './WheelMark'

interface NavProps {
  current: string
}

const NAV_LINKS = [
  { href: '#/', label: 'The Archive' },
  { href: '#/chat', label: 'Ask' },
  { href: '#/heroes', label: 'Heroes' },
  { href: '#/attributes', label: 'Attributes' },
  { href: '#/items', label: 'Items' },
]

function isActive(href: string, current: string): boolean {
  const path = (current || '#/').split('?')[0]
  if (href === '#/') return path === '#/' || path === '' || path === '#'
  return path === href || path.startsWith(href + '/')
}

export function Nav({ current }: NavProps) {
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

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }} />
    </header>
  )
}
