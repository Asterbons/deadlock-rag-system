import { useState, useMemo, useEffect } from 'react'

interface HeroIndex {
  hero: string
  hero_id: number
  name: string
  hero_type: string
  complexity: number
  base_health?: number
}

const TYPE_COLORS: Record<string, { fg: string; bg: string; bd: string; accent: string }> = {
  Marksman: { fg: 'var(--dl-amber-300)',  bg: 'rgba(214,147,33,0.16)',  bd: 'var(--dl-amber-700)',  accent: 'var(--dl-amber-500)' },
  Brawler:  { fg: 'var(--dl-blood-300)',  bg: 'rgba(163,49,40,0.16)',   bd: 'var(--dl-blood-700)',  accent: 'var(--dl-blood-500)' },
  Mystic:   { fg: 'var(--dl-spirit-300)', bg: 'rgba(138,75,209,0.16)',  bd: 'var(--dl-spirit-700)', accent: 'var(--dl-spirit-500)' },
}

function getTypeColors(type: string) {
  return TYPE_COLORS[type] ?? TYPE_COLORS.Marksman
}

function ComplexityDots({ n }: { n: number }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {[1, 2, 3].map(i => (
        <span key={i} style={{
          width: 7, height: 7, borderRadius: '50%',
          background: i <= n ? 'var(--dl-gold-500)' : 'var(--dl-stone)',
          boxShadow: i <= n ? '0 0 6px rgba(201,169,110,0.5)' : 'none',
        }} />
      ))}
    </div>
  )
}

function HeroCard({ hero }: { hero: HeroIndex }) {
  const [hover, setHover] = useState(false)
  const c = getTypeColors(hero.hero_type)
  const slug = hero.hero.replace('hero_', '')

  return (
    <a href={`#/heroes/${slug}`}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        position: 'relative',
        background: 'var(--bg-card)',
        border: `1px solid ${hover ? c.accent : 'var(--border-1)'}`,
        borderTop: `2px solid ${c.accent}`,
        borderRadius: 'var(--r-3)',
        padding: '18px 16px 16px',
        cursor: 'pointer',
        textDecoration: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        transition: 'all 150ms',
        boxShadow: hover ? `0 6px 20px rgba(0,0,0,0.5), 0 0 0 1px ${c.accent}` : 'none',
        overflow: 'hidden',
      }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1.15 }}>
            {hero.name}
          </div>
          <div style={{ marginTop: 4, fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', fontWeight: 700, color: c.fg }}>
            {hero.hero_type}
          </div>
        </div>
        <span style={{ background: c.bg, border: `1px solid ${c.bd}`, color: c.fg, fontSize: 9, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase', padding: '3px 7px', borderRadius: 'var(--r-1)', whiteSpace: 'nowrap' }}>
          {hero.hero_type.slice(0, 3)}
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto' }}>
        {hero.base_health && (
          <div>
            <div style={{ fontSize: 9, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--fg-4)', marginBottom: 2 }}>HP</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: 'var(--dl-bone)', lineHeight: 1 }}>{hero.base_health}</div>
          </div>
        )}
        <ComplexityDots n={hero.complexity} />
      </div>
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        padding: '8px 16px',
        background: 'linear-gradient(180deg, transparent 0%, rgba(7,16,15,0.9) 100%)',
        fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase',
        color: 'var(--dl-gold-300)', fontWeight: 700, textAlign: 'right',
        transform: hover ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 180ms var(--ease-out)',
        pointerEvents: 'none',
      }}>View Dossier →</div>
    </a>
  )
}

const TYPE_LABELS: Record<string, string> = { All: 'All Combatants', Marksman: 'Marksmen', Brawler: 'Brawlers', Mystic: 'Mystics' }

export function Combatants() {
  const [heroes, setHeroes] = useState<HeroIndex[]>([])
  const [type, setType] = useState('All')
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/heroes')
      .then(r => r.json())
      .then(d => { setHeroes(Array.isArray(d) ? d : d.heroes ?? []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => heroes.filter(h => {
    if (type !== 'All' && h.hero_type !== type) return false
    if (q && !h.name.toLowerCase().includes(q.toLowerCase())) return false
    return true
  }), [heroes, type, q])

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 40px 60px' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 10 }}>
            The Index of Heroes
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 42, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1.1, margin: 0 }}>
            Combatants of the Cursed Apple
          </h1>
          <div style={{ marginTop: 10, fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 17, color: 'var(--fg-2)' }}>
            Those who fight for the Patrons in the streets of New York.
          </div>
          <div className="dl-hairline" style={{ width: 120, marginTop: 16 }} />
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 28 }}>
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg-surface)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)', padding: 3 }}>
            {Object.keys(TYPE_LABELS).map(t => {
              const active = t === type
              return (
                <button key={t} onClick={() => setType(t)} style={{
                  background: active ? 'var(--dl-smoke)' : 'transparent',
                  color: active ? 'var(--dl-gold-300)' : 'var(--fg-2)',
                  border: active ? '1px solid var(--dl-gold-700)' : '1px solid transparent',
                  borderRadius: 'var(--r-1)', padding: '7px 14px',
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase',
                  cursor: 'pointer', fontFamily: 'var(--font-body)',
                }}>{TYPE_LABELS[t]}</button>
              )
            })}
          </div>
          <div style={{ position: 'relative', flex: 1, maxWidth: 280 }}>
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name…"
              style={{
                width: '100%', background: 'var(--bg-input)', color: 'var(--fg-1)',
                border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)',
                padding: '9px 14px 9px 34px', fontSize: 13, outline: 'none', fontFamily: 'var(--font-body)',
              }}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--dl-gold-700)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border-1)'}
            />
            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--fg-3)', fontSize: 14 }}>⌕</span>
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--fg-3)', fontWeight: 700 }}>
            {filtered.length} / {heroes.length}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--fg-3)', fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 16 }}>
            Consulting the archive…
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
            {filtered.map(h => <HeroCard key={h.hero} hero={h} />)}
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--fg-3)', fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 16 }}>
            The archive holds no record matching that query.
          </div>
        )}
      </div>
    </div>
  )
}
