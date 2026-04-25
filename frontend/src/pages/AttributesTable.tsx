import { useState, useMemo, useEffect } from 'react'

interface HeroStats {
  hero: string
  name: string
  hero_type: string
  image?: string
  base_health?: number
  max_move_speed?: number
  sprint_speed?: number
  crouch_speed?: number
  light_melee_damage?: number
  heavy_melee_damage?: number
  weapon_power?: number
  reload_speed?: number
  stamina?: number
  health_regen?: number
  stamina_regen_per_second?: number
  spirit_duration?: number
  spirit_range?: number
  [key: string]: string | number | undefined
}

type SortField = keyof HeroStats
type SortDir = 'asc' | 'desc'

export function AttributesTable() {
  const [heroes, setHeroes] = useState<HeroStats[]>([])
  const [loading, setLoading] = useState(true)
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  useEffect(() => {
    fetch('/api/heroes')
      .then(r => r.json())
      .then(d => {
        // We need to fetch each hero's detail to get their full stats, OR the /api/heroes returns full stats?
        // Wait, /api/heroes returns HeroIndex which only has base_health!
        // To do a full attributes table, we should either fetch all hero details, or add an endpoint.
        // But /api/heroes reads from heroes_index.json which has `base_stats` inside it!
        // Wait, does heroes_index.json have base_stats? Let's check!
        const list = Array.isArray(d) ? d : d.heroes ?? []
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setHeroes(list.map((h: any) => ({
          ...h,
          ...h.base_stats // Flatten base stats into the hero object
        })))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc') // Default to desc for stats
    }
  }

  const sortedHeroes = useMemo(() => {
    return [...heroes].sort((a, b) => {
      let va = a[sortField]
      let vb = b[sortField]
      if (va === undefined) va = -Infinity
      if (vb === undefined) vb = -Infinity
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [heroes, sortField, sortDir])

  const COLUMNS: { label: string; field: SortField; width?: number }[] = [
    { label: 'Hero', field: 'name', width: 140 },
    { label: 'HP', field: 'health', width: 60 },
    { label: 'HP Regen', field: 'health_regen', width: 80 },
    { label: 'Weapon', field: 'weapon_power', width: 70 },
    { label: 'Move Spd', field: 'max_move_speed', width: 80 },
    { label: 'Sprint Spd', field: 'sprint_speed', width: 90 },
    { label: 'Crouch Spd', field: 'crouch_speed', width: 90 },
    { label: 'L. Melee', field: 'light_melee_damage', width: 80 },
    { label: 'H. Melee', field: 'heavy_melee_damage', width: 80 },
    { label: 'Stamina', field: 'stamina', width: 70 },
  ]

  function Th({ col }: { col: typeof COLUMNS[0] }) {
    const isSorted = sortField === col.field
    return (
      <th 
        onClick={() => handleSort(col.field)}
        style={{ 
          padding: '12px 16px', textAlign: 'left', cursor: 'pointer',
          borderBottom: '2px solid var(--border-2)', background: 'var(--bg-surface)',
          color: isSorted ? 'var(--dl-gold-300)' : 'var(--fg-2)',
          fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', fontWeight: 700,
          whiteSpace: 'nowrap', userSelect: 'none', width: col.width
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {col.label}
          <span style={{ fontSize: 12, opacity: isSorted ? 1 : 0.2 }}>
            {isSorted ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
          </span>
        </div>
      </th>
    )
  }

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 40px 60px' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 10 }}>
            Combatant Statistics
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 42, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1.1, margin: 0 }}>
            Hero Attributes Table
          </h1>
          <div className="dl-hairline" style={{ width: 120, marginTop: 16 }} />
        </div>

        {loading ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--fg-3)', fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 16 }}>
            Consulting the archive…
          </div>
        ) : (
          <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
              <thead>
                <tr>
                  {COLUMNS.map(c => <Th key={c.field as string} col={c} />)}
                </tr>
              </thead>
              <tbody>
                {sortedHeroes.map((hero, i) => (
                  <tr key={hero.hero} style={{ borderBottom: '1px solid var(--border-1)', background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.1)' }}>
                    <td style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 10 }}>
                      {hero.image && (
                        <img src={hero.image} alt={hero.name} style={{ width: 32, height: 32, borderRadius: 'var(--r-1)', objectFit: 'cover', border: '1px solid var(--border-2)' }} />
                      )}
                      <a href={`#/heroes/${hero.hero.replace('hero_', '')}`} style={{ fontFamily: 'var(--font-display)', fontSize: 14, fontWeight: 700, color: 'var(--dl-bone)', textDecoration: 'none', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        {hero.name}
                      </a>
                    </td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.health ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.health_regen ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.weapon_power ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.max_move_speed ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.sprint_speed ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.crouch_speed ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.light_melee_damage ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.heavy_melee_damage ?? '-'}</td>
                    <td style={{ padding: '8px 16px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)' }}>{hero.stamina ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
