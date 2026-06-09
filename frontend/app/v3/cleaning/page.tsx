'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface CleaningUnit {
  unit_id: string;
  cluster_id: string;
  gender: string;
  label: string;
  masc: number;
  fem: number;
  espera: number;
  total: number;
  note: string;
}

interface UnitsPayload {
  units: CleaningUnit[];
  total_count: number;
  total_masc: number;
  total_fem: number;
  total_espera: number;
  total_capacity: number;
}

interface HistoryEntry {
  ts: number | string;
  cleaned_by?: string;
  notes?: string;
}

function GenderChip({ gender }: { gender: string }) {
  if (gender === 'M') return <span className="v3-badge v3-badge-blue">MASC</span>;
  if (gender === 'F') return <span className="v3-badge" style={{ background: 'var(--v3-pink-soft)', color: 'var(--v3-pink)' }}>FEM</span>;
  return <span className="v3-badge v3-badge-muted">UNI</span>;
}

export default function CleaningPage() {
  const [payload, setPayload] = useState<UnitsPayload | null>(null);
  const [marking, setMarking] = useState<string | null>(null);
  const [history, setHistory] = useState<Record<string, HistoryEntry[]>>({});

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/cleaning/units`, { cache: 'no-store' });
        if (r.ok) setPayload(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, []);

  const markDone = async (unitId: string) => {
    setMarking(unitId);
    try {
      await fetch(`${API}/api/v1/cleaning/units/${encodeURIComponent(unitId)}/done`, { method: 'POST' });
      const r = await fetch(`${API}/api/v1/cleaning/units`, { cache: 'no-store' });
      if (r.ok) setPayload(await r.json());
      const hr = await fetch(`${API}/api/v1/cleaning/units/${encodeURIComponent(unitId)}/history`, { cache: 'no-store' });
      if (hr.ok) {
        const h = await hr.json();
        setHistory((prev) => ({ ...prev, [unitId]: h.slice(0, 3) }));
      }
    } catch {}
    setMarking(null);
  };

  if (!payload) {
    return (
      <div className="v3-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, color: 'var(--v3-muted)' }}>A carregar…</span>
      </div>
    );
  }

  const highLoad = payload.units.filter((u) => u.espera > 20);

  return (
    <div className="v3-page">
      {/* Summary strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10, marginBottom: 24 }}>
        {[
          { label: 'Total instalações', val: payload.units.length },
          { label: 'Capacidade total', val: payload.total_capacity },
          { label: 'Em espera', val: payload.total_espera, warn: payload.total_espera > 50 },
          { label: 'Alta prioridade', val: highLoad.length, warn: highLoad.length > 0 },
        ].map(({ label, val, warn }) => (
          <div key={label} className="v3-card">
            <div className="v3-kpi-val" style={{ color: warn ? 'var(--v3-amber)' : 'var(--v3-ink)' }}>
              {val}
            </div>
            <div className="v3-kpi-label">{label}</div>
          </div>
        ))}
      </div>

      {/* Unit cards */}
      <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
        Instalações · {payload.units.length}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
        {payload.units.map((u) => {
          const urgent = u.espera > 20;
          const recent = history[u.unit_id];
          return (
            <div key={u.unit_id} className="v3-card" style={urgent ? { borderColor: 'var(--v3-amber)' } : undefined}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--v3-font-mono)', fontWeight: 600, fontSize: 12 }}>
                  {u.label}
                </span>
                <GenderChip gender={u.gender} />
              </div>

              <div style={{ display: 'flex', gap: 16, marginBottom: 10 }}>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.04em', color: urgent ? 'var(--v3-amber)' : 'var(--v3-blue)' }}>
                    {u.total.toFixed(0)}
                  </div>
                  <div style={{ fontSize: 10, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.04em' }}>TOTAL</div>
                </div>
                {u.espera > 0 && (
                  <div>
                    <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--v3-amber)' }}>
                      {u.espera.toFixed(0)}
                    </div>
                    <div style={{ fontSize: 10, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.04em' }}>ESPERA</div>
                  </div>
                )}
              </div>

              {u.note && (
                <p style={{ fontSize: 11.5, color: 'var(--v3-muted)', margin: '0 0 10px', lineHeight: 1.5 }}>{u.note}</p>
              )}

              <button
                onClick={() => markDone(u.unit_id)}
                disabled={marking === u.unit_id}
                style={{
                  width: '100%',
                  padding: '8px 0',
                  borderRadius: 'var(--v3-r-sm)',
                  border: '1px solid var(--v3-line)',
                  background: marking === u.unit_id ? 'var(--v3-line)' : 'var(--v3-bg)',
                  color: 'var(--v3-ink)',
                  fontSize: 12,
                  fontFamily: 'var(--v3-font-mono)',
                  fontWeight: 500,
                  cursor: marking === u.unit_id ? 'default' : 'pointer',
                  transition: 'background 0.14s',
                }}
                onMouseEnter={(e) => { if (marking !== u.unit_id) e.currentTarget.style.background = 'var(--v3-bg-soft)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = marking === u.unit_id ? 'var(--v3-line)' : 'var(--v3-bg)'; }}
              >
                {marking === u.unit_id ? 'A registar…' : 'Marcar limpo'}
              </button>

              {recent && recent.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {recent.map((h, i) => (
                    <div key={i} style={{ fontSize: 10.5, color: 'var(--v3-faint)', fontFamily: 'var(--v3-font-mono)', marginTop: 2 }}>
                      {typeof h.ts === 'number' ? new Date(h.ts * 1000).toLocaleTimeString('pt-PT') : String(h.ts)}
                      {h.cleaned_by ? ` · ${h.cleaned_by}` : ''}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
