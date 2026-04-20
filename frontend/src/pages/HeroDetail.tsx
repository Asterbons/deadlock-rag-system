import { useState, useEffect } from 'react'
import type { Hero, HeroAbility } from '../types/api'

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--border-2)' }}>
      <span style={{ fontSize: 12, color: 'var(--fg-3)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>{label.replace(/_/g, ' ')}</span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--dl-bone)', fontVariantNumeric: 'tabular-nums' }}>{value}</span>
    </div>
  )
}

function AbilityCard({ ability }: { ability: HeroAbility }) {
  const castColors: Record<string, string> = {
    Active: 'var(--dl-teal-400)', Passive: 'var(--dl-gold-500)', Channeled: 'var(--dl-spirit-400)',
  }
  const color = castColors[ability.cast_type] ?? 'var(--fg-3)'
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', padding: '16px 18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10, marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 9, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--fg-4)', marginBottom: 4 }}>Ability {ability.slot}</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 15, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--dl-bone)' }}>
            {ability.name}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <span style={{ background: 'var(--bg-input)', border: `1px solid ${color}`, color, fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', padding: '3px 7px', borderRadius: 'var(--r-1)' }}>
            {ability.cast_type}
          </span>
        </div>
      </div>
      {Object.keys(ability.stats).length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {Object.entries(ability.stats).slice(0, 6).map(([k, v]) => (
            <span key={k} style={{ background: 'var(--bg-input)', border: '1px solid var(--border-2)', color: 'var(--fg-2)', fontFamily: 'var(--font-mono)', fontSize: 10, padding: '3px 8px', borderRadius: 'var(--r-1)' }}>
              {k.replace(/_/g, ' ')}: {v}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

interface Props {
  heroId: string
}

export function HeroDetail({ heroId }: Props) {
  const [hero, setHero] = useState<Hero | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    setHero(null)
    setError(false)
    fetch(`/api/heroes/${heroId}`)
      .then(r => { if (!r.ok) throw new Error('Not found'); return r.json() })
      .then(d => setHero(d))
      .catch(() => setError(true))
  }, [heroId])

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: 16, padding: 60 }}>
        <div style={{ fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 18, color: 'var(--fg-3)' }}>
          The archive holds no record of this combatant.
        </div>
        <a href="#/heroes" style={{ color: 'var(--dl-gold-500)', fontSize: 12, letterSpacing: '0.16em', textTransform: 'uppercase', textDecoration: 'none' }}>← Return to the Index</a>
      </div>
    )
  }

  if (!hero) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
        <div style={{ color: 'var(--fg-3)', fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 16 }}>Consulting the archive…</div>
      </div>
    )
  }

  const TYPE_COLORS: Record<string, { fg: string; accent: string }> = {
    Marksman: { fg: 'var(--dl-amber-300)', accent: 'var(--dl-amber-500)' },
    Brawler:  { fg: 'var(--dl-blood-300)', accent: 'var(--dl-blood-500)' },
    Mystic:   { fg: 'var(--dl-spirit-300)', accent: 'var(--dl-spirit-500)' },
  }
  const tc = TYPE_COLORS[hero.hero_type] ?? { fg: 'var(--dl-gold-300)', accent: 'var(--dl-gold-500)' }

  const keyStats = Object.entries(hero.base_stats).filter(([, v]) => v !== undefined && v !== 0).slice(0, 8)

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '40px 40px 60px' }}>
        <a href="#/heroes" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--fg-3)', fontSize: 11, letterSpacing: '0.18em', textTransform: 'uppercase', textDecoration: 'none', marginBottom: 24 }}
          onMouseOver={e => e.currentTarget.style.color = 'var(--dl-gold-300)'}
          onMouseOut={e => e.currentTarget.style.color = 'var(--fg-3)'}
        >← All Combatants</a>

        {/* Header */}
        <div style={{ marginBottom: 32, paddingBottom: 24, borderBottom: '1px solid var(--border-1)' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: tc.fg, fontWeight: 700, marginBottom: 8 }}>{hero.hero_type}</div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 48, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1, margin: '0 0 12px' }}>
            {hero.name}
          </h1>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {hero.tags.flavor?.map(t => (
              <span key={t} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', color: 'var(--fg-2)', fontSize: 10, padding: '4px 10px', borderRadius: 'var(--r-pill)', fontWeight: 600 }}>{t}</span>
            ))}
            {hero.tags.playstyle?.map(t => (
              <span key={t} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', color: 'var(--fg-2)', fontSize: 10, padding: '4px 10px', borderRadius: 'var(--r-pill)', fontWeight: 600 }}>{t}</span>
            ))}
          </div>
          <div className="dl-hairline" style={{ width: 120, marginTop: 20 }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 32 }}>
          {/* Stats */}
          <div>
            <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 12 }}>Base Stats</div>
            <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', padding: '12px 16px' }}>
              {keyStats.map(([k, v]) => (
                <StatRow key={k} label={k} value={String(v)} />
              ))}
            </div>
            {Object.keys(hero.scaling_per_level).length > 0 && (
              <>
                <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginTop: 20, marginBottom: 12 }}>Scaling per Level</div>
                <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', borderRadius: 'var(--r-3)', padding: '12px 16px' }}>
                  {Object.entries(hero.scaling_per_level).filter(([, v]) => v !== undefined).map(([k, v]) => (
                    <StatRow key={k} label={k} value={String(v)} />
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Abilities */}
          <div>
            <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 12 }}>Abilities</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {hero.abilities.map(a => <AbilityCard key={a.slot} ability={a} />)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
