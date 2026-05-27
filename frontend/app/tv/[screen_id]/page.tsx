'use client'

import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || ''

interface TVState {
  screen_id?: string
  best_wc?: string
  direction?: string
  walk_time_min?: number
  queue_wait_min?: number
  occupacy_pct?: number
  alternatives?: Array<{ section_id: string; queue_wait_min?: number }>
  avoid?: string[]
  alert?: string
  any_simulated?: boolean
}

export default function TVScreen({ params }: { params: { screen_id: string } }) {
  const [state, setState] = useState<TVState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const screenId = params.screen_id

  async function fetchState() {
    try {
      const res = await fetch(`${API}/api/v1/tv/${screenId}`, { cache: 'no-store' })
      if (!res.ok) {
        setError(`Erro ${res.status}`)
        return
      }
      const data = await res.json()
      setState(data)
      setError(null)
    } catch (e) {
      setError('Sem dados ao vivo')
    }
  }

  useEffect(() => {
    fetchState()
    const t = setInterval(fetchState, 5000)
    return () => clearInterval(t)
  }, [screenId])

  if (error || !state) {
    return (
      <main style={{ minHeight: '100vh', background: '#FAFAF7', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '48px', fontFamily: 'system-ui, sans-serif', color: '#1A1A1A' }}>
        <div style={{ background: '#C25A1A', color: 'white', padding: '48px', borderRadius: '16px', fontSize: '48px', fontWeight: 600 }}>
          {error || 'A carregar…'}
        </div>
      </main>
    )
  }

  return (
    <main style={{ minHeight: '100vh', background: '#FAFAF7', color: '#1A1A1A', padding: '64px', fontFamily: 'system-ui, sans-serif', display: 'flex', flexDirection: 'column' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '64px' }}>
        <div style={{ fontSize: '32px', fontWeight: 600 }}>{screenId}</div>
        {state.any_simulated && (
          <div style={{ fontSize: '24px', padding: '8px 24px', background: '#1A1A1A', color: '#FAFAF7', borderRadius: '999px', fontWeight: 500 }}>SIMULADO</div>
        )}
      </header>

      <section style={{ textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
        <p style={{ fontSize: '40px', color: '#666', margin: '0 0 24px 0' }}>Casa de banho mais próxima</p>
        <h1 style={{ fontSize: '160px', fontWeight: 700, margin: '0', letterSpacing: '-0.02em', lineHeight: 1 }}>
          {state.best_wc || '—'}
        </h1>
        <div style={{ fontSize: '200px', lineHeight: 1, margin: '32px 0', color: '#C25A1A' }}>
          {state.direction === 'right' ? '→' : state.direction === 'left' ? '←' : state.direction === 'up' ? '↑' : state.direction === 'down' ? '↓' : '→'}
        </div>
        <div style={{ fontSize: '120px', fontWeight: 600, fontFamily: 'ui-monospace, monospace', lineHeight: 1 }}>
          {(state.queue_wait_min ?? 0).toFixed(0)} min
        </div>
        <p style={{ fontSize: '40px', color: '#666', marginTop: '16px' }}>de espera</p>
      </section>

      {state.alternatives && state.alternatives.length > 0 && (
        <section style={{ marginTop: '48px', padding: '32px', background: 'white', borderRadius: '16px', border: '2px solid #E5E5E5', display: 'flex', justifyContent: 'space-around' }}>
          {state.alternatives.slice(0, 2).map((alt) => (
            <div key={alt.section_id} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '32px', color: '#666' }}>{alt.section_id}</div>
              <div style={{ fontSize: '48px', fontWeight: 600, fontFamily: 'ui-monospace, monospace' }}>{(alt.queue_wait_min ?? 0).toFixed(0)} min</div>
            </div>
          ))}
        </section>
      )}

      {state.alert && (
        <section style={{ marginTop: '24px', padding: '32px', background: '#C25A1A', color: 'white', borderRadius: '16px', textAlign: 'center', fontSize: '40px', fontWeight: 600 }}>
          ⚠ {state.alert}
        </section>
      )}
    </main>
  )
}
