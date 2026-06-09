'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface Secao {
  cluster_id: string;
  secao: string;
  nome: string;
  unissex: boolean;
  ocupacao_pct: number;
  ocupacao_abs: number;
  fila_actual: number;
  tempo_espera_min: number;
  fluxo_entrada_ph?: number;
  fluxo_saida_ph?: number;
  recomendacao?: string;
}

interface FlowPayload {
  ts: number;
  kpis: { kpi_01: number; kpi_02: number; kpi_03: number; kpi_04: number };
  calibracao: { qualidade_global_pct: number; deriva_maxima: number };
  routing: { cluster_id: string; recomendacao: string }[];
  secoes: Secao[];
}

const KPI_LABELS: Record<string, string> = {
  kpi_01: 'Pessoas total',
  kpi_02: 'Ocupação %',
  kpi_03: 'Em fila',
  kpi_04: 'Redirecções',
};

export default function FlowPage() {
  const [flow, setFlow] = useState<FlowPayload | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/flow`, { cache: 'no-store' });
        if (r.ok) setFlow(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, []);

  if (!flow) {
    return (
      <div className="v3-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, color: 'var(--v3-muted)' }}>A carregar…</span>
      </div>
    );
  }

  const byCluster: Record<string, Secao[]> = {};
  for (const s of flow.secoes) {
    const k = s.cluster_id.toUpperCase();
    if (!byCluster[k]) byCluster[k] = [];
    byCluster[k].push(s);
  }

  return (
    <div className="v3-page">
      {/* KPI strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 24 }}>
        {(Object.entries(flow.kpis) as [string, number][]).map(([key, val]) => (
          <div key={key} className="v3-card">
            <div className="v3-kpi-val" style={{ color: 'var(--v3-blue)' }}>{val}</div>
            <div className="v3-kpi-label">{KPI_LABELS[key] ?? key}</div>
          </div>
        ))}
        <div className="v3-card">
          <div className="v3-kpi-val" style={{ color: flow.calibracao.qualidade_global_pct >= 80 ? 'var(--v3-blue)' : 'var(--v3-amber)' }}>
            {flow.calibracao.qualidade_global_pct}%
          </div>
          <div className="v3-kpi-label">calibração</div>
        </div>
      </div>

      {/* Routing tips */}
      {flow.routing.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 8 }}>
            Routing · {flow.routing.length}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {flow.routing.map((r) => (
              <div key={r.cluster_id} style={{ padding: '10px 14px', borderRadius: 'var(--v3-r)', background: 'var(--v3-blue-soft)', border: '1px solid var(--v3-blue)', fontSize: 13, color: 'var(--v3-blue)' }}>
                <strong>{r.cluster_id.toUpperCase()}</strong> — {r.recomendacao}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cluster grids */}
      <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 10 }}>
        Secções · {flow.secoes.length}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 8 }}>
        {flow.secoes.map((s) => {
          const occ = s.ocupacao_pct ?? 0;
          const critical = occ >= 80;
          const key = `${s.cluster_id}-${s.secao}`;
          return (
            <div key={key} className="v3-card" style={critical ? { borderColor: 'var(--v3-amber)' } : undefined}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <span style={{ fontFamily: 'var(--v3-font-mono)', fontWeight: 600, fontSize: 12 }}>
                    {s.cluster_id.toUpperCase()}
                  </span>
                  {!s.unissex && (
                    <span style={{ marginLeft: 5, fontSize: 11, color: 'var(--v3-muted)', fontFamily: 'var(--v3-font-mono)' }}>
                      {s.secao === 'M' ? 'MASC' : 'FEM'}
                    </span>
                  )}
                </div>
                {s.fila_actual > 0 && (
                  <span className="v3-badge v3-badge-amber">fila {s.fila_actual}</span>
                )}
              </div>

              <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.04em', color: critical ? 'var(--v3-amber)' : 'var(--v3-blue)', marginBottom: 6 }}>
                {occ.toFixed(0)}%
              </div>
              <div className="v3-bar-track">
                <div className={`v3-bar-fill${critical ? ' critical' : ''}`} style={{ width: `${Math.min(occ, 100)}%` }} />
              </div>

              <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                <span style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)' }}>
                  {s.ocupacao_abs} pess.
                </span>
                {s.fluxo_entrada_ph != null && (
                  <span style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)' }}>
                    ↑{s.fluxo_entrada_ph}/h
                  </span>
                )}
                {(s.tempo_espera_min ?? 0) > 0 && (
                  <span style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)' }}>
                    ≈{s.tempo_espera_min}min
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
