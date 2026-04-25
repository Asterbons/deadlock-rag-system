import { useState, useEffect } from 'react'
import { useChat } from './hooks/useChat'
import { useHealth } from './hooks/useHealth'
import { Nav } from './components/Nav'
import { ChatWindow } from './components/ChatWindow'
import { Landing } from './pages/Landing'
import { Combatants } from './pages/Combatants'
import { Artefacts } from './pages/Artefacts'
import { HeroDetail } from './pages/HeroDetail'
import { AttributesTable } from './pages/AttributesTable'

function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash || '#/')
  useEffect(() => {
    const handler = () => { setHash(window.location.hash || '#/'); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])
  return hash
}

function parseRoute(hash: string) {
  const h = (hash || '#/').replace(/^#/, '')
  const [path] = h.split('?')
  const parts = path.split('/').filter(Boolean)
  if (parts.length === 0) return { name: 'landing' as const }
  if (parts[0] === 'chat') return { name: 'chat' as const }
  if (parts[0] === 'heroes' && parts[1]) return { name: 'hero_detail' as const, id: parts[1] }
  if (parts[0] === 'heroes') return { name: 'combatants' as const }
  if (parts[0] === 'items') return { name: 'artefacts' as const }
  if (parts[0] === 'attributes') return { name: 'attributes' as const }
  return { name: 'landing' as const }
}

function ConsultPage() {
  const { messages, isLoading, sendMessage, clearHistory, lastUsage, sessionUsage } = useChat()
  return (
    <ChatWindow
      messages={messages}
      isLoading={isLoading}
      sendMessage={sendMessage}
      clearHistory={clearHistory}
      lastUsage={lastUsage}
      sessionUsage={sessionUsage}
    />
  )
}

export default function App() {
  const hash = useHashRoute()
  const { ollama, qdrant, loading } = useHealth()
  const route = parseRoute(hash)

  let screen: React.ReactNode
  switch (route.name) {
    case 'chat':        screen = <ConsultPage />; break
    case 'combatants':  screen = <Combatants />; break
    case 'hero_detail': screen = <HeroDetail heroId={route.id} />; break
    case 'artefacts':   screen = <Artefacts />; break
    case 'attributes':  screen = <AttributesTable />; break
    default:            screen = <Landing />
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Nav current={hash} ollama={ollama} qdrant={qdrant} loading={loading} />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-app)' }}>
        {screen}
      </main>
    </div>
  )
}
