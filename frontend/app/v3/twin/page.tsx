'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useLiveV3, type ClusterLive } from '@/components/v3/LiveContextV3';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface GeoCluster {
  id: string;
  e_m: number;
  n_m: number;
  type: 'MF' | 'UNI';
  desc: string;
  cap_m: number | null;
  cap_f: number | null;
  cap: number | null;
  capacity_total: number;
}

interface GeoPayload {
  span_e_m: number;
  span_n_m: number;
  clusters: GeoCluster[];
}

interface Landmark {
  id: string;
  label: string;
  e_m: number;
  n_m: number;
  kind: string;
}

function occColour(pct: number): string {
  if (pct >= 80) return 'var(--v3-amber)';
  if (pct >= 55) return 'var(--v3-blue)';
  return '#22C55E';
}

export default function TwinPage() {
  const { clusters: live, connected } = useLiveV3();
  const [geo, setGeo] = useState<GeoPayload | null>(null);
  const [landmarks, setLandmarks] = useState<Landmark[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/clusters/geo`, { cache: 'no-store' })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => {
        if (d) {
          setGeo(d);
          setLandmarks(d.landmarks ?? []);
        }
      })
      .catch(() => {});
  }, []);

  const liveMap = useMemo(() => {
    const m: Record<string, ClusterLive> = {};
    for (const c of live) m[c.cluster_id.toUpperCase()] = c;
    return m;
  }, [live]);

  const selectedCluster = selected ? liveMap[selected] : null;
  const selectedGeo = selected ? geo?.clusters.find((c) => c.id === selected) : null;

  if (!geo) {
    return (
      <div className="v3-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, color: 'var(--v3-muted)' }}>
          A carregar mapa…
        </span>
      </div>
    );
  }

  const PAD = 40;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Map ──────────────────────────────────────────────────────── */}
      <div ref={canvasRef} style={{ flex: 1, position: 'relative', overflow: 'hidden', background: 'var(--v3-bg-soft)' }}>
        <svg
          viewBox={`-${PAD} -${PAD} ${geo.span_e_m + PAD * 2} ${geo.span_n_m + PAD * 2}`}
          style={{ width: '100%', height: '100%' }}
          aria-label="Mapa twin digital dos clusters WC"
        >
          {/* Grid lines */}
          {[0, 50, 100, 150, 200, 250, 300].map((v) => (
            <g key={`grid-${v}`}>
              <line x1={v} y1={0} x2={v} y2={geo.span_n_m} stroke="var(--v3-line)" strokeWidth="0.5" />
              <line x1={0} y1={geo.span_n_m - v} x2={geo.span_e_m} y2={geo.span_n_m - v} stroke="var(--v3-line)" strokeWidth="0.5" />
            </g>
          ))}

          {/* Landmarks */}
          {landmarks.map((lm) => (
            <g key={lm.id} transform={`translate(${lm.e_m},${geo.span_n_m - lm.n_m})`}>
              <circle r="5" fill="var(--v3-line-strong)" opacity="0.6" />
              <text
                y="14"
                textAnchor="middle"
                fontSize="9"
                fontFamily="var(--v3-font-mono)"
                fill="var(--v3-faint)"
              >
                {lm.label}
              </text>
            </g>
          ))}

          {/* Cluster nodes */}
          {geo.clusters.map((gc) => {
            const cl = liveMap[gc.id];
            const occ = cl?.params?.ocupacao_pct ?? cl?.params?.ocupacao_instantanea ?? 0;
            const colour = occColour(occ);
            const isSelected = selected === gc.id;
            const cy = geo.span_n_m - gc.n_m;

            return (
              <g
                key={gc.id}
                transform={`translate(${gc.e_m},${cy})`}
                style={{ cursor: 'pointer' }}
                onClick={() => setSelected(isSelected ? null : gc.id)}
                role="button"
                aria-label={`Cluster ${gc.id}, ocupação ${occ}%`}
              >
                {isSelected && (
                  <circle r="22" fill={colour} opacity="0.15" />
                )}
                <circle
                  r="14"
                  fill={colour}
                  stroke={isSelected ? 'var(--v3-ink)' : 'var(--v3-bg)'}
                  strokeWidth={isSelected ? 2 : 1.5}
                  opacity={cl ? 1 : 0.35}
                />
                <text
                  y="1"
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="7.5"
                  fontWeight="700"
                  fontFamily="var(--v3-font-mono)"
                  fill="white"
                >
                  {occ > 0 ? `${occ}%` : gc.id.replace('WC-', '')}
                </text>
                <text
                  y="22"
                  textAnchor="middle"
                  fontSize="8"
                  fontFamily="var(--v3-font-mono)"
                  fill="var(--v3-ink)"
                  fontWeight="500"
                >
                  {gc.id}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div style={{ position: 'absolute', bottom: 16, left: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
          {[
            { colour: '#22C55E', label: '< 55%' },
            { colour: 'var(--v3-blue)', label: '55–79%' },
            { colour: 'var(--v3-amber)', label: '≥ 80%' },
          ].map(({ colour, label }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: colour }} />
              <span style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)' }}>{label}</span>
            </div>
          ))}
          <span className={`v3-badge ${connected ? 'v3-badge-blue' : 'v3-badge-muted'}`} style={{ fontSize: 11 }}>
            {connected ? 'AO VIVO' : 'SEM LIGAÇÃO'}
          </span>
        </div>
      </div>

      {/* Detail panel ───────────────────────────────────────────── */}
      {selected && selectedGeo && (
        <div style={{
          width: 260,
          borderLeft: '1px solid var(--v3-line)',
          padding: '20px 18px',
          overflow: 'auto',
          background: 'var(--v3-bg)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
            <span style={{ fontFamily: 'var(--v3-font-mono)', fontWeight: 700, fontSize: 14 }}>
              {selectedGeo.id}
            </span>
            <button
              onClick={() => setSelected(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--v3-muted)', padding: 4 }}
              aria-label="Fechar painel"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" />
              </svg>
            </button>
          </div>

          <p style={{ fontSize: 12, color: 'var(--v3-muted)', margin: '0 0 18px', lineHeight: 1.5 }}>
            {selectedGeo.desc}
          </p>

          {selectedCluster ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                { label: 'Ocupação', value: `${selectedCluster.params?.ocupacao_pct ?? selectedCluster.params?.ocupacao_instantanea ?? 0}%` },
                { label: 'Pessoas', value: selectedCluster.params?.pessoas_estimadas ?? 0 },
                { label: 'Fila', value: selectedCluster.params?.fila_atual ?? 0 },
                { label: 'Espera', value: `${selectedCluster.params?.tempo_espera_min ?? 0} min` },
                { label: 'Capacidade', value: selectedGeo.capacity_total },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ fontSize: 12, color: 'var(--v3-muted)' }}>{label}</span>
                  <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, fontWeight: 600, color: 'var(--v3-ink)' }}>
                    {value}
                  </span>
                </div>
              ))}

              <div style={{ marginTop: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--v3-muted)', fontFamily: 'var(--v3-font-mono)', letterSpacing: '0.04em' }}>
                  OCUPAÇÃO
                </span>
                <div style={{ marginTop: 6 }}>
                  <div className="v3-bar-track">
                    <div
                      className={`v3-bar-fill${(selectedCluster.params?.ocupacao_pct ?? selectedCluster.params?.ocupacao_instantanea ?? 0) >= 80 ? ' critical' : ''}`}
                      style={{ width: `${Math.min(selectedCluster.params?.ocupacao_pct ?? selectedCluster.params?.ocupacao_instantanea ?? 0, 100)}%` }}
                    />
                  </div>
                </div>
              </div>

              <div style={{ paddingTop: 8, borderTop: '1px solid var(--v3-line)', display: 'flex', justifyContent: 'space-between' }}>
                <span className="v3-badge v3-badge-muted">{selectedGeo.type === 'UNI' ? 'UNISSEX' : 'M/F'}</span>
                <span className={`v3-badge ${(selectedCluster.params?.confianca_cruzada ?? 0) > 0.5 ? 'v3-badge-blue' : 'v3-badge-muted'}`}>
                  conf {Math.round((selectedCluster.params?.confianca_cruzada ?? 0) * 100)}%
                </span>
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 12, color: 'var(--v3-faint)', fontFamily: 'var(--v3-font-mono)' }}>
              Sem dados ao vivo
            </div>
          )}
        </div>
      )}
    </div>
  );
}
