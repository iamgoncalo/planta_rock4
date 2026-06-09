'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface Section {
  id: string;
  cluster_id: string;
  gender?: string;
  ocupacao_pct: number;
  pessoas: number;
  fila: number;
  espera_min: number;
  estado: string;
  recomendacao?: string;
}

interface StatePayload {
  kpis: { avg_ocupacao_pct: number; total_fila: number; critical_sections: number };
  sections: Section[];
  alerts: { id: string; msg: string; severity: string }[];
  last_tick_age_s: number;
}

function StatusChip({ estado }: { estado: string }) {
  const cfg: Record<string, { label: string; cls: string }> = {
    ok:       { label: 'OK',     cls: 'v3-badge-blue'  },
    warning:  { label: 'ATENÇÃO', cls: 'v3-badge-amber' },
    critical: { label: 'CRÍTICO', cls: 'v3-badge-amber' },
    offline:  { label: 'OFFLINE', cls: 'v3-badge-muted' },
  };
  const { label, cls } = cfg[estado] ?? { label: estado.toUpperCase(), cls: 'v3-badge-muted' };
  return <span className={`v3-badge ${cls}`}>{label}</span>;
}

export default function ScorPage() {
  const [state, setState] = useState<StatePayload | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/state`, { cache: 'no-store' });
        if (r.ok) setState(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, []);

  if (!state) {
    return (
      <div className="v3-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, color: 'var(--v3-muted)' }}>A carregar…</span>
      </div>
    );
  }

  const criticals = state.sections.filter((s) => s.estado === 'critical' || s.estado === 'warning');

  return (
    <div className="v3-page">
      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginBottom: 24 }}>
        {[
          { label: 'Ocupação média', val: `${state.kpis.avg_ocupacao_pct.toFixed(1)}%` },
          { label: 'Em fila', val: state.kpis.total_fila },
          { label: 'Críticas', val: state.kpis.critical_sections, warn: state.kpis.critical_sections > 0 },
          { label: 'Tick age', val: `${state.last_tick_age_s.toFixed(0)}s` },
        ].map(({ label, val, warn }) => (
          <div key={label} className="v3-card">
            <div className="v3-kpi-val" style={{ color: warn ? 'var(--v3-amber)' : 'var(--v3-ink)' }}>
              {val}
            </div>
            <div className="v3-kpi-label">{label}</div>
          </div>
        ))}
      </div>

      {/* Alerts */}
      {state.alerts.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
            Alertas activos · {state.alerts.length}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {state.alerts.map((a) => (
              <div key={a.id} style={{ padding: '10px 14px', borderRadius: 'var(--v3-r)', background: 'var(--v3-amber-soft)', border: '1px solid var(--v3-amber)', fontSize: 13, color: 'var(--v3-amber)' }}>
                {a.msg}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sections table */}
      <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
        Secções · {state.sections.length}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
        {state.sections.map((s) => {
          const occ = s.ocupacao_pct ?? 0;
          const critical = s.estado === 'critical' || s.estado === 'warning';
          return (
            <div key={s.id} className="v3-card" style={critical ? { borderColor: 'var(--v3-amber)' } : undefined}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 12, fontFamily: 'var(--v3-font-mono)', fontWeight: 600 }}>
                  {s.cluster_id.toUpperCase()}{s.gender ? ` · ${s.gender.toUpperCase()}` : ''}
                </span>
                <StatusChip estado={s.estado} />
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: '-0.04em', color: critical ? 'var(--v3-amber)' : 'var(--v3-blue)', marginBottom: 6 }}>
                {occ}%
              </div>
              <div className="v3-bar-track">
                <div className={`v3-bar-fill${critical ? ' critical' : ''}`} style={{ width: `${Math.min(occ, 100)}%` }} />
              </div>
              <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
                <span style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)' }}>{s.pessoas} pess.</span>
                {s.fila > 0 && <span style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-amber)' }}>fila {s.fila}</span>}
              </div>
              {s.recomendacao && (
                <div style={{ marginTop: 8, fontSize: 11, color: 'var(--v3-muted)', fontStyle: 'italic', lineHeight: 1.4 }}>{s.recomendacao}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
