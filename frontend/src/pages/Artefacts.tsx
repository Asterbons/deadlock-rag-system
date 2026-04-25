import { useState, useMemo, useEffect } from 'react'

interface Item {
  id: string
  name: string
  slot: 'weapon' | 'vitality' | 'spirit'
  tier: number
  cost?: number
  description: string
  stats?: Record<string, string | number>
  image?: string
}

const SLOT_STYLES: Record<string, { label: string; fg: string; bg: string; bd: string; accent: string }> = {
  weapon:   { label: 'Weapon',   fg: 'var(--dl-amber-300)',  bg: 'rgba(214,147,33,0.14)',  bd: 'var(--dl-amber-700)',  accent: 'var(--dl-amber-500)' },
  vitality: { label: 'Vitality', fg: 'var(--dl-health-300)', bg: 'rgba(95,170,74,0.14)',   bd: 'var(--dl-health-700)', accent: 'var(--dl-health-500)' },
  spirit:   { label: 'Spirit',   fg: 'var(--dl-spirit-300)', bg: 'rgba(138,75,209,0.14)',  bd: 'var(--dl-spirit-700)', accent: 'var(--dl-spirit-500)' },
}

function TierPip({ tier }: { tier: number }) {
  const glow = tier >= 4
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      background: 'var(--bg-input)', border: `1px solid ${glow ? 'var(--dl-gold-700)' : 'var(--border-1)'}`,
      padding: '3px 8px', borderRadius: 'var(--r-1)',
      fontFamily: 'var(--font-display)', fontSize: 10, fontWeight: 700, letterSpacing: '0.14em',
      color: glow ? 'var(--dl-gold-300)' : 'var(--fg-2)',
      boxShadow: glow ? 'var(--glow-gold)' : 'none',
    }}>T{tier}</div>
  )
}

function ArtefactCard({ item }: { item: Item }) {
  const s = SLOT_STYLES[item.slot] ?? SLOT_STYLES.weapon
  return (
    <div
      style={{
        background: 'var(--bg-card)', border: '1px solid var(--border-1)',
        borderLeft: `2px solid ${s.accent}`,
        borderRadius: 'var(--r-3)', padding: '16px 18px',
        display: 'flex', flexDirection: 'column', gap: 10, transition: 'all 150ms',
      }}
      onMouseOver={e => { e.currentTarget.style.borderColor = s.accent; e.currentTarget.style.boxShadow = `0 4px 14px rgba(0,0,0,0.4), 0 0 0 1px ${s.accent}` }}
      onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border-1)'; e.currentTarget.style.boxShadow = 'none' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
        {item.image && (
          <img src={item.image} alt={item.name} style={{ width: 40, height: 40, borderRadius: 'var(--r-1)', objectFit: 'cover', border: `1px solid var(--border-2)` }} />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1.2 }}>
            {item.name}
          </div>
          <div style={{ marginTop: 4, display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ background: s.bg, border: `1px solid ${s.bd}`, color: s.fg, fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', padding: '2px 6px', borderRadius: 'var(--r-1)' }}>
              {s.label}
            </span>
            <TierPip tier={item.tier} />
          </div>
        </div>
        {item.cost && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--dl-gold-300)', whiteSpace: 'nowrap' }}>
            {item.cost.toLocaleString()}
          </div>
        )}
      </div>
      <div style={{ fontSize: 12, color: 'var(--fg-2)', lineHeight: 1.5 }}>{item.description}</div>
      {item.stats && Object.keys(item.stats).length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {Object.entries(item.stats).slice(0, 4).map(([k, v]) => (
            <span key={k} style={{ background: 'var(--bg-input)', border: '1px solid var(--border-2)', color: 'var(--fg-2)', fontFamily: 'var(--font-mono)', fontSize: 9, padding: '2px 6px', borderRadius: 'var(--r-1)' }}>
              {String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

const TIERS = [1, 2, 3, 4]

export function Artefacts() {
  const [allItems, setAllItems] = useState<Item[]>([])
  const [slot, setSlot] = useState('all')
  const [tiers, setTiers] = useState<number[]>([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/items')
      .then(r => r.json())
      .then(d => {
        const flat: Item[] = []
        if (Array.isArray(d)) {
          flat.push(...d)
        } else {
          for (const s of ['weapon', 'vitality', 'spirit']) {
            if (Array.isArray(d[s])) flat.push(...d[s].map((i: Item) => ({ ...i, slot: s as Item['slot'] })))
          }
        }
        setAllItems(flat)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  function toggleTier(t: number) {
    setTiers(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t])
  }

  const filtered = useMemo(() => allItems.filter(item => {
    if (slot !== 'all' && item.slot !== slot) return false
    if (tiers.length > 0 && !tiers.includes(item.tier)) return false
    if (q && !item.name.toLowerCase().includes(q.toLowerCase())) return false
    return true
  }), [allItems, slot, tiers, q])

  const SLOTS = [
    { key: 'all', label: 'All' },
    { key: 'weapon', label: 'Weapon' },
    { key: 'vitality', label: 'Vitality' },
    { key: 'spirit', label: 'Spirit' },
  ]

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 40px 60px' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 10 }}>
            The Vault of Power
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 42, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1.1, margin: 0 }}>
            Artefacts
          </h1>
          <div style={{ marginTop: 10, fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 17, color: 'var(--fg-2)' }}>
            Items of power from the streets of the Cursed Apple.
          </div>
          <div className="dl-hairline" style={{ width: 120, marginTop: 16 }} />
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 28 }}>
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg-surface)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)', padding: 3 }}>
            {SLOTS.map(s => {
              const active = s.key === slot
              const st = SLOT_STYLES[s.key]
              return (
                <button key={s.key} onClick={() => setSlot(s.key)} style={{
                  background: active ? 'var(--dl-smoke)' : 'transparent',
                  color: active ? (st?.fg ?? 'var(--dl-gold-300)') : 'var(--fg-2)',
                  border: active ? `1px solid ${st?.bd ?? 'var(--dl-gold-700)'}` : '1px solid transparent',
                  borderRadius: 'var(--r-1)', padding: '7px 14px',
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase',
                  cursor: 'pointer', fontFamily: 'var(--font-body)',
                }}>{s.label}</button>
              )
            })}
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {TIERS.map(t => {
              const active = tiers.includes(t)
              return (
                <button key={t} onClick={() => toggleTier(t)} style={{
                  background: active ? 'var(--dl-smoke)' : 'transparent',
                  color: active ? 'var(--dl-gold-300)' : 'var(--fg-2)',
                  border: `1px solid ${active ? 'var(--dl-gold-700)' : 'var(--border-1)'}`,
                  borderRadius: 'var(--r-1)', padding: '7px 11px',
                  fontSize: 10, fontWeight: 700, letterSpacing: '0.14em',
                  cursor: 'pointer', fontFamily: 'var(--font-display)',
                }}>T{t}</button>
              )
            })}
          </div>
          <div style={{ position: 'relative', flex: 1, maxWidth: 260 }}>
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name…"
              style={{ width: '100%', background: 'var(--bg-input)', color: 'var(--fg-1)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-2)', padding: '9px 14px 9px 34px', fontSize: 13, outline: 'none', fontFamily: 'var(--font-body)' }}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--dl-gold-700)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border-1)'}
            />
            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--fg-3)', fontSize: 14 }}>⌕</span>
          </div>
          <div style={{ marginLeft: 'auto', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--fg-3)', fontWeight: 700 }}>
            {filtered.length} / {allItems.length}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--fg-3)', fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 16 }}>Consulting the archive…</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
            {filtered.map(item => <ArtefactCard key={item.id} item={item} />)}
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--fg-3)', fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 16 }}>
            The vault holds no artefact matching that query.
          </div>
        )}
      </div>
    </div>
  )
}
