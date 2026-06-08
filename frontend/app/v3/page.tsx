'use client';

import { useEffect, useState } from 'react';
import { useLiveV3 } from '@/components/v3/LiveContextV3';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface KPIs {
  avg_ocupacao_pct: number;
  total_fila: number;
  critical_sections: number;
  redirected_count: number;
}

function OccBar({ pct }: { pct: number }) {
  const critical = pct >= 80;
  return (
    <div className="v3-bar-track">
      <div
        className={`v3-bar-fill${critical ? ' critical' : ''}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

export default function V3Home() {
  const { clusters, totalPessoas, connected } = useLiveV3();
  const [kpis, setKpis] = useState<KPIs | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/kpis`, { cache: 'no-store' });
        if (r.ok) setKpis(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  // Cluster com maior ocupação → destaque rosa (1 por ecrã)
  const peakCluster = clusters.length > 0
    ? clusters.reduce((a, b) =>
        (b.params?.ocupacao_instantanea ?? 0) > (a.params?.ocupacao_instantanea ?? 0) ? b : a,
      )
    : null;

  return (
    <div className="v3-page">
      {/* KPI strip ─────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 28 }}>
        <div className="v3-card">
          <div className="v3-kpi-val" style={{ color: 'var(--v3-blue)' }}>
            {totalPessoas.toLocaleString('pt-PT')}
          </div>
          <div className="v3-kpi-label">pessoas estimadas</div>
        </div>
        <div className="v3-card">
          <div className="v3-kpi-val">{kpis?.avg_ocupacao_pct.toFixed(1) ?? '—'}%</div>
          <div className="v3-kpi-label">ocupação média</div>
        </div>
        <div className="v3-card">
          <div className="v3-kpi-val">{kpis?.total_fila ?? '—'}</div>
          <div className="v3-kpi-label">em fila agora</div>
        </div>
        <div className="v3-card">
          <div
            className="v3-kpi-val"
            style={{ color: (kpis?.critical_sections ?? 0) > 0 ? 'var(--v3-amber)' : 'var(--v3-ink)' }}
          >
            {kpis?.critical_sections ?? '—'}
          </div>
          <div className="v3-kpi-label">secções críticas</div>
        </div>
      </div>

      {/* Section header ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <h2 style={{ margin: 0, fontSize: 13.5, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--v3-muted)' }}>
          Clusters · {clusters.length}/8
        </h2>
        <span className={`v3-badge ${connected ? 'v3-badge-blue' : 'v3-badge-muted'}`}>
          {connected ? 'AO VIVO' : 'SEM LIGAÇÃO'}
        </span>
      </div>

      {/* Cluster grid ───────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
        {clusters.length === 0
          ? Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="v3-card" style={{ opacity: 0.4 }}>
                <div style={{ fontSize: 12, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', marginBottom: 8 }}>WC-0{i + 1}</div>
                <div style={{ height: 4, background: 'var(--v3-line)', borderRadius: 2 }} />
              </div>
            ))
          : clusters.map((c) => {
              const occ = c.params?.ocupacao_instantanea ?? 0;
              const fila = c.params?.fila_atual ?? 0;
              const pessoas = c.params?.pessoas_estimadas ?? 0;
              const isPeak = peakCluster?.cluster_id === c.cluster_id && occ > 0;
              const critical = occ >= 80;

              return (
                <div
                  key={c.cluster_id}
                  className="v3-card"
                  style={isPeak ? {
                    borderColor: 'var(--v3-pink)',
                    boxShadow: '0 0 0 3px rgba(255,46,147,0.10)',
                  } : critical ? {
                    borderColor: 'var(--v3-amber)',
                  } : undefined}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <span style={{ fontSize: 12, fontFamily: 'var(--v3-font-mono)', fontWeight: 600, color: 'var(--v3-ink)', letterSpacing: '0.02em' }}>
                      {c.cluster_id.toUpperCase()}
                    </span>
                    {isPeak && <span className="v3-badge v3-badge-pink">PICO</span>}
                    {!isPeak && critical && <span className="v3-badge v3-badge-amber">CHEIO</span>}
                    {!isPeak && !critical && fila > 0 && (
                      <span className="v3-badge v3-badge-muted">fila {fila}</span>
                    )}
                  </div>

                  <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1, color: critical ? 'var(--v3-amber)' : isPeak ? 'var(--v3-pink)' : 'var(--v3-blue)', marginBottom: 8 }}>
                    {occ}%
                  </div>

                  <OccBar pct={occ} />

                  <div style={{ marginTop: 10, display: 'flex', gap: 12 }}>
                    <span style={{ fontSize: 11.5, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)' }}>
                      {pessoas} pess.
                    </span>
                    {c.params?.is_unissex && (
                      <span style={{ fontSize: 11, color: 'var(--v3-faint)' }}>UNI</span>
                    )}
                  </div>
                </div>
              );
            })}
      </div>
    </div>
  );
}
