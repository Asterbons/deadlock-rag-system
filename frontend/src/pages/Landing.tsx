import { useState, useEffect } from 'react'
import { WheelMark } from '../components/WheelMark'

interface Stats { heroes: number; abilities: number; items: number; last_updated: string }

function StatBlock({ num, label }: { num: string | number; label: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '0 20px' }}>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 48, fontWeight: 700, color: 'var(--dl-gold-300)', letterSpacing: '0.04em', lineHeight: 1 }}>{num}</div>
      <div style={{ marginTop: 8, fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--fg-3)', fontWeight: 600 }}>{label}</div>
    </div>
  )
}

function Step({ num, title, desc }: { num: number; title: string; desc: string }) {
  return (
    <div style={{ flex: 1, position: 'relative', padding: '24px 20px', borderLeft: '1px solid var(--border-1)' }}>
      <div style={{ position: 'absolute', top: -1, left: -1, width: 28, height: 1, background: 'var(--dl-gold-500)' }} />
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--dl-gold-500)', letterSpacing: '0.2em', marginBottom: 10 }}>0{num} /</div>
      <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 600, color: 'var(--dl-bone)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 10, lineHeight: 1.2 }}>{title}</div>
      <div style={{ fontSize: 13, color: 'var(--fg-2)', lineHeight: 1.6 }}>{desc}</div>
    </div>
  )
}

const TECH_STACK = ['Python', 'FastAPI', 'Qdrant', 'Ollama', 'mxbai-embed-large', 'qwen2.5:7b', 'Valve KV3', 'APScheduler']

export function Landing() {
  const [stats, setStats] = useState<Stats>({ heroes: 38, abilities: 152, items: 171, last_updated: '—' })

  useEffect(() => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(d => setStats(d))
      .catch(() => {})
  }, [])

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      {/* Hero */}
      <section className="dl-grain" style={{ position: 'relative', padding: '80px 40px 60px', textAlign: 'center', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center, rgba(47,107,104,0.18) 0%, transparent 60%), linear-gradient(180deg, var(--dl-ink) 0%, var(--dl-tar) 100%)', zIndex: 0 }} />
        <div style={{ position: 'relative', zIndex: 1, maxWidth: 820, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, marginBottom: 20 }}>
            <div className="dl-hairline" style={{ width: 60 }} />
            <WheelMark size={38} color="var(--dl-gold-500)" />
            <div className="dl-hairline" style={{ width: 60 }} />
          </div>
          <div style={{ fontSize: 10, letterSpacing: '0.32em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 18 }}>
            An Occult Intelligence Archive
          </div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(40px, 8vw, 72px)', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--dl-bone)', lineHeight: 1, margin: 0 }}>
            The Occult<br />Index
          </h1>
          <div style={{ marginTop: 22, fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 20, color: 'var(--fg-2)', lineHeight: 1.5, maxWidth: 560, margin: '22px auto 0' }}>
            Arcane intelligence from the streets of the Cursed Apple.
          </div>
          <div style={{ marginTop: 10, fontSize: 13, color: 'var(--fg-3)', letterSpacing: '0.02em' }}>
            The Patrons are watching. Are you prepared?
          </div>
          <div style={{ marginTop: 36, display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <a href="#/chat" style={{
              background: 'var(--action)', color: 'var(--dl-bone)', border: '1px solid var(--dl-teal-300)',
              padding: '14px 28px', borderRadius: 'var(--r-2)', fontSize: 12, fontWeight: 700,
              letterSpacing: '0.2em', textTransform: 'uppercase', textDecoration: 'none',
              boxShadow: 'var(--glow-teal)', fontFamily: 'var(--font-body)',
            }}>Consult the Oracle →</a>
            <a href="#/heroes" style={{
              background: 'transparent', color: 'var(--dl-gold-300)', border: '1px solid var(--dl-gold-700)',
              padding: '14px 28px', borderRadius: 'var(--r-2)', fontSize: 12, fontWeight: 700,
              letterSpacing: '0.2em', textTransform: 'uppercase', textDecoration: 'none',
              fontFamily: 'var(--font-body)',
            }}>Browse Combatants</a>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section style={{ borderTop: '1px solid var(--border-1)', borderBottom: '1px solid var(--border-1)', background: 'var(--bg-surface)', padding: '40px 20px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', justifyContent: 'center', alignItems: 'center', flexWrap: 'wrap', gap: '24px 8px' }}>
          <StatBlock num={stats.heroes} label="Combatants Catalogued" />
          <div style={{ width: 1, height: 40, background: 'var(--border-1)' }} />
          <StatBlock num={stats.abilities} label="Arcane Abilities Indexed" />
          <div style={{ width: 1, height: 40, background: 'var(--border-1)' }} />
          <StatBlock num={stats.items} label="Artefacts of Power" />
          {stats.last_updated !== '—' && (
            <>
              <div style={{ width: 1, height: 40, background: 'var(--border-1)' }} />
              <StatBlock num="✧" label={`Updated ${stats.last_updated}`} />
            </>
          )}
        </div>
      </section>

      {/* How it works */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '70px 40px' }}>
        <div style={{ textAlign: 'center', marginBottom: 42 }}>
          <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--dl-gold-500)', fontWeight: 700, marginBottom: 10 }}>The Rite</div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 32, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--dl-bone)', margin: 0 }}>
            How the Oracle Sees
          </h2>
          <div className="dl-hairline" style={{ width: 80, margin: '14px auto 0' }} />
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', border: '1px solid var(--border-1)', background: 'var(--bg-surface)', borderRadius: 'var(--r-3)', overflow: 'hidden' }}>
          <Step num={1} title="The Extraction" desc="Game files decoded from the Astral source. Valve's KV3 blobs, translated strings, and shop tables are parsed into structured JSON." />
          <Step num={2} title="The Indexing" desc="Knowledge bound to the vector index. Each hero, ability, and artefact becomes an embedding, held in Qdrant's dark." />
          <Step num={3} title="The Revelation" desc="Your question answered from the archive. A local LLM consults the index and returns only what the record contains — no hallucinations, only citations." />
        </div>
      </section>

      {/* Tech */}
      <section style={{ padding: '40px 40px 80px', borderTop: '1px solid var(--border-2)' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.24em', textTransform: 'uppercase', color: 'var(--fg-3)', fontWeight: 700, marginBottom: 14, textAlign: 'center' }}>Built Upon</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            {TECH_STACK.map(t => (
              <span key={t} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-1)', color: 'var(--fg-2)', fontFamily: 'var(--font-mono)', fontSize: 11, padding: '6px 12px', borderRadius: 'var(--r-2)', letterSpacing: '0.04em' }}>{t}</span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border-1)', background: 'var(--bg-surface)', padding: '30px 40px', textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--font-narrative)', fontStyle: 'italic', fontSize: 14, color: 'var(--fg-3)', maxWidth: 600, margin: '0 auto', lineHeight: 1.6 }}>
          The Oracle operates in the shadows of the Cursed Apple. Data extracted from the Astral Index. Updated on every rift.
        </div>
        <div style={{ marginTop: 14, fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--fg-4)' }}>
          Not affiliated with Valve Corporation
        </div>
      </footer>
    </div>
  )
}
