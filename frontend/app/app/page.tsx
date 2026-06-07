'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface RouteDecision {
  chosen_section?: string
  walk_time_min?: number
  queue_wait_min?: number
  total_cost_min?: number
  confidence?: number
  reasons?: string[]
  alternatives?: Array<{ section_id: string; total_cost_min: number; queue_wait_min?: number }>
  avoid?: string[]
  any_simulated?: boolean
}

export default function PublicApp() {
  const [route, setRoute] = useState<RouteDecision | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [now, setNow] = useState<Date>(new Date())

  async function fetchRoute() {
    try {
      const res = await fetch(`${API}/api/v1/route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: { lat: 38.7636, lon: -9.0956 },
          gender: 'any',
        }),
        cache: 'no-store',
      })
      if (!res.ok) {
        setError(`Erro ${res.status}`)
        return
      }
      const data = await res.json()
      setRoute(data)
      setError(null)
      setNow(new Date())
    } catch (e) {
      setError('Sem dados ao vivo')
    }
  }

  useEffect(() => {
    fetchRoute()
    const t = setInterval(fetchRoute, 5000)
    return () => clearInterval(t)
  }, [])

  if (error) {
    return (
      <main style={{ minHeight: '100vh', background: '#FAFAF7', padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', color: '#1A1A1A', fontFamily: 'system-ui, sans-serif' }}>
        <div style={{ background: '#C25A1A', color: 'white', padding: '24px', borderRadius: '12px', fontSize: '22px', fontWeight: 600, maxWidth: '480px' }}>
          Sem dados ao vivo — sistema offline
        </div>
        <p style={{ fontSize: '18px', marginTop: '24px', color: '#666' }}>{error}</p>
      </main>
    )
  }

  if (!route) {
    return (
      <main style={{ minHeight: '100vh', background: '#FAFAF7', display: 'flex', justifyContent: 'center', alignItems: 'center', fontSize: '22px', color: '#1A1A1A', fontFamily: 'system-ui, sans-serif' }}>
        A procurar a melhor casa de banho…
      </main>
    )
  }

  const chosen = route.chosen_section || '—'
  const wait = route.queue_wait_min ?? 0
  const walk = route.walk_time_min ?? 0
  const conf = Math.round((route.confidence ?? 0) * 100)

  return (
    <main style={{ minHeight: '100vh', background: '#FAFAF7', color: '#1A1A1A', padding: '24px', fontFamily: 'system-ui, sans-serif', display: 'flex', flexDirection: 'column' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div style={{ fontSize: '20px', fontWeight: 600 }}>Planta · Rock in Rio</div>
        {/* any_simulated intencionalmente omitido — label proibida em UI pública */}
      </header>

      <section style={{ textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <p style={{ fontSize: '20px', color: '#666', margin: '0 0 16px 0' }}>Vai para</p>
        <h1 style={{ fontSize: '64px', fontWeight: 700, margin: '0 0 8px 0', letterSpacing: '-0.02em' }}>{chosen}</h1>
        <div style={{ fontSize: '96px', lineHeight: 1, margin: '24px 0', color: '#C25A1A' }}>→</div>
        <div style={{ fontSize: '56px', fontWeight: 600, fontFamily: 'ui-monospace, monospace' }}>
          {wait.toFixed(0)} min
        </div>
        <p style={{ fontSize: '18px', color: '#666', marginTop: '8px' }}>de espera · {walk.toFixed(0)} min a andar</p>
      </section>

      {route.alternatives && route.alternatives.length > 0 && (
        <section style={{ marginTop: '32px', padding: '24px', background: 'white', borderRadius: '12px', border: '1px solid #E5E5E5' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '0 0 16px 0', color: '#666' }}>Alternativas</h2>
          {route.alternatives.slice(0, 2).map((alt) => (
            <div key={alt.section_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', fontSize: '20px', borderTop: '1px solid #F0F0F0' }}>
              <span style={{ fontWeight: 500 }}>{alt.section_id}</span>
              <span style={{ fontFamily: 'ui-monospace, monospace', color: '#666' }}>{alt.total_cost_min?.toFixed(0) ?? '—'} min</span>
            </div>
          ))}
        </section>
      )}

      {route.avoid && route.avoid.length > 0 && (
        <section style={{ marginTop: '16px', padding: '16px', background: '#FFF4ED', borderRadius: '12px', border: '1px solid #C25A1A' }}>
          <p style={{ fontSize: '16px', color: '#C25A1A', margin: 0, fontWeight: 500 }}>
            Evita: {route.avoid.join(', ')}
          </p>
        </section>
      )}

      <footer style={{ marginTop: '24px', textAlign: 'center', fontSize: '14px', color: '#999' }}>
        Confiança {conf}% · {now.toLocaleTimeString('pt-PT')}
      </footer>
    </main>
  )
}
