import { useState, useMemo, useEffect, type ReactNode } from 'react'

interface HeroStats {
  hero: string
  name: string
  hero_type: string
  image?: string
  // base_stats (flattened)
  health?: number
  health_regen?: number
  max_move_speed?: number
  sprint_speed?: number
  crouch_speed?: number
  move_acceleration?: number
  light_melee_damage?: number
  heavy_melee_damage?: number
  stamina?: number
  stamina_regen_per_second?: number
  ground_dash_distance_in_meters?: number
  air_dash_distance_in_meters?: number
  // weapon (flattened)
  bullet_damage?: number
  rounds_per_sec?: number
  clip_size?: number
  reload_time?: number
  bullets_per_shot?: number
  bullet_speed?: number
  crit_bonus?: number
  falloff_start?: number
  falloff_end?: number
  // computed
  dps?: number
  sustained_dps?: number
  // scaling per level (used for inline display next to base value)
  health_per_lvl?: number
  bullet_dmg_per_lvl?: number
  melee_dmg_per_lvl?: number
  spirit_power_per_lvl?: number
  [key: string]: string | number | undefined
}

type SortField = keyof HeroStats
type SortDir = 'asc' | 'desc'

interface ColumnDef {
  label: string
  field: SortField
  width?: number
  decimals?: number
  scalingField?: SortField  // when set, render "{base} +{scaling}" inline (wiki style)
}

interface SectionDef {
  label: string
  columns: ColumnDef[]
}

const SECTIONS: SectionDef[] = [
  {
    label: '',
    columns: [
      { label: 'Hero', field: 'name', width: 150 },
    ],
  },
  {
    label: 'Vitality',
    columns: [
      { label: 'HP',       field: 'health',       width: 90, scalingField: 'health_per_lvl' },
      { label: 'HP Regen', field: 'health_regen', width: 75 },
    ],
  },
  {
    label: 'Weapon',
    columns: [
      { label: 'DPS',           field: 'dps',              width: 65, decimals: 1 },
      { label: 'Sus. DPS',      field: 'sustained_dps',    width: 75, decimals: 1 },
      { label: 'Bullet Dmg',    field: 'bullet_damage',    width: 100, decimals: 2, scalingField: 'bullet_dmg_per_lvl' },
      { label: 'Fire Rate',     field: 'rounds_per_sec',   width: 75, decimals: 2 },
      { label: 'Ammo',          field: 'clip_size',        width: 60 },
      { label: 'Reload',        field: 'reload_time',      width: 65, decimals: 2 },
      { label: 'Blt/Shot',      field: 'bullets_per_shot', width: 70 },
      { label: 'Bullet Vel',    field: 'bullet_speed',     width: 80 },
      { label: 'Crit Bonus',    field: 'crit_bonus',       width: 80, decimals: 2 },
      { label: 'Falloff Start', field: 'falloff_start',    width: 95, decimals: 1 },
      { label: 'Falloff End',   field: 'falloff_end',      width: 90, decimals: 1 },
      { label: 'L. Melee',      field: 'light_melee_damage', width: 95, scalingField: 'melee_dmg_per_lvl' },
      { label: 'H. Melee',      field: 'heavy_melee_damage', width: 95, scalingField: 'melee_dmg_per_lvl' },
    ],
  },
  {
    label: 'Mobility',
    columns: [
      { label: 'Move Spd',   field: 'max_move_speed',                 width: 80 },
      { label: 'Sprint Spd', field: 'sprint_speed',                   width: 85 },
      { label: 'Crouch Spd', field: 'crouch_speed',                   width: 85 },
      { label: 'Move Accel', field: 'move_acceleration',              width: 85 },
      { label: 'Stamina',    field: 'stamina',                        width: 70 },
      { label: 'Stam Regen', field: 'stamina_regen_per_second',       width: 90, decimals: 2 },
      { label: 'G. Dash',    field: 'ground_dash_distance_in_meters', width: 75 },
      { label: 'A. Dash',    field: 'air_dash_distance_in_meters',    width: 75 },
    ],
  },
  {
    label: 'Other',
    columns: [
      { label: 'Spirit/Lvl', field: 'spirit_power_per_lvl', width: 85, decimals: 2 },
    ],
  },
]

const ALL_COLUMNS: ColumnDef[] = SECTIONS.flatMap(s => s.columns)

function formatVal(val: string | number | undefined, decimals?: number): string {
  if (val === undefined || val === null) return '-'
  if (typeof val !== 'number') return String(val)
  if (decimals !== undefined) return val.toFixed(decimals)
  if (Number.isInteger(val)) return String(val)
  return (+val.toFixed(2)).toString()
}

function formatScaling(val: number): string {
  if (Number.isInteger(val)) return String(val)
  if (Math.abs(val) >= 1) return (+val.toFixed(2)).toString()
  return (+val.toFixed(3)).toString()
}

export function AttributesTable() {
  const [heroes, setHeroes] = useState<HeroStats[]>([])
  const [loading, setLoading] = useState(true)
  const [sortField, setSortField] = useState<SortField>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  useEffect(() => {
    fetch('/api/heroes')
      .then(r => r.json())
      .then(d => {
        const list = Array.isArray(d) ? d : d.heroes ?? []
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setHeroes(list.map((h: any) => {
          const w  = h.weapon || {}
          const sc = h.scaling_per_level || {}
          const bd = w.bullet_damage ?? 0
          const rps = w.rounds_per_sec ?? 0
          const bps = w.bullets_per_shot ?? 1
          const clip = w.clip_size ?? 0
          const rt = w.reload_time ?? 0
          const dps = bd * rps * bps
          const cycle = rps > 0 ? clip / rps + rt : 0
          const sustained = cycle > 0 ? (clip * bd * bps) / cycle : 0
          const falloff = Array.isArray(w.falloff_range) ? w.falloff_range : []
          return {
            ...h,
            ...h.base_stats,
            bullet_damage:    w.bullet_damage,
            rounds_per_sec:   w.rounds_per_sec,
            clip_size:        w.clip_size,
            reload_time:      w.reload_time,
            bullets_per_shot: w.bullets_per_shot,
            bullet_speed:     w.bullet_speed,
            crit_bonus:       w.crit_bonus,
            falloff_start:    falloff[0],
            falloff_end:      falloff[1],
            dps,
            sustained_dps:    sustained,
            health_per_lvl:        sc.health,
            bullet_dmg_per_lvl:    sc.base_bullet_damage_from_level,
            melee_dmg_per_lvl:     sc.base_melee_damage_from_level,
            spirit_power_per_lvl:  sc.spirit_power,
          }
        }))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const sortedHeroes = useMemo(() => {
    return [...heroes].sort((a, b) => {
      let va = a[sortField]
      let vb = b[sortField]
      if (va === undefined) va = sortDir === 'asc' ? Infinity : -Infinity
      if (vb === undefined) vb = sortDir === 'asc' ? Infinity : -Infinity
      if (typeof va === 'string' && typeof vb === 'string') {
        return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }, [heroes, sortField, sortDir])

  function Th({ col }: { col: ColumnDef }) {
    const isSorted = sortField === col.field
    return (
      <th
        onClick={() => handleSort(col.field)}
        style={{
          padding: '10px 12px', textAlign: 'left', cursor: 'pointer',
          borderBottom: '2px solid var(--border-2)', background: 'var(--bg-surface)',
          color: isSorted ? 'var(--dl-gold-300)' : 'var(--fg-2)',
          fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 700,
          whiteSpace: 'nowrap', userSelect: 'none', width: col.width, position: 'sticky', top: 28, zIndex: 1,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {col.label}
          <span style={{ fontSize: 11, opacity: isSorted ? 1 : 0.2 }}>
            {isSorted ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
          </span>
        </div>
      </th>
    )
  }

  function renderCell(hero: HeroStats, col: ColumnDef) {
    if (col.field === 'name') {
      return (
        <td key="name" style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {hero.image && (
              <img
                src={hero.image}
                alt={hero.name}
                style={{ width: 30, height: 30, borderRadius: 'var(--r-1)', objectFit: 'cover', border: '1px solid var(--border-2)', flexShrink: 0 }}
              />
            )}
            <a
              href={`#/heroes/${hero.hero.replace('hero_', '')}`}
              style={{ fontFamily: 'var(--font-display)', fontSize: 13, fontWeight: 700, color: 'var(--dl-bone)', textDecoration: 'none', textTransform: 'uppercase', letterSpacing: '0.04em' }}
            >
              {hero.name}
            </a>
          </div>
        </td>
      )
    }

    const baseStr = formatVal(hero[col.field], col.decimals)
    let scalingNode: ReactNode = null
    if (col.scalingField) {
      const s = hero[col.scalingField]
      if (typeof s === 'number') {
        scalingNode = (
          <span style={{ color: 'var(--dl-gold-500)', marginLeft: 5, fontSize: 11, fontWeight: 600 }}>
            +{formatScaling(s)}
          </span>
        )
      }
    }

    return (
      <td
        key={col.field as string}
        style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--fg-1)', whiteSpace: 'nowrap' }}
      >
        {baseStr}
        {scalingNode}
      </td>
    )
  }

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <div style={{ maxWidth: 1600, margin: '0 auto', padding: '40px 32px 60px' }}>
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
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 1800 }}>
              <thead>
                <tr>
                  {SECTIONS.map((s, idx) => (
                    <th
                      key={`section-${idx}`}
                      colSpan={s.columns.length}
                      style={{
                        padding: s.label ? '8px 12px' : 0,
                        textAlign: 'left',
                        background: 'var(--bg-surface)',
                        color: 'var(--dl-gold-400)',
                        fontFamily: 'var(--font-display)',
                        fontSize: 11,
                        letterSpacing: '0.18em',
                        textTransform: 'uppercase',
                        fontWeight: 700,
                        borderBottom: '1px solid var(--border-1)',
                        borderRight: idx < SECTIONS.length - 1 ? '1px solid var(--border-2)' : 'none',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {s.label}
                    </th>
                  ))}
                </tr>
                <tr>
                  {ALL_COLUMNS.map(c => <Th key={c.field as string} col={c} />)}
                </tr>
              </thead>
              <tbody>
                {sortedHeroes.map((hero, i) => (
                  <tr
                    key={hero.hero}
                    style={{ borderBottom: '1px solid var(--border-1)', background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.1)' }}
                  >
                    {ALL_COLUMNS.map(col => renderCell(hero, col))}
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
