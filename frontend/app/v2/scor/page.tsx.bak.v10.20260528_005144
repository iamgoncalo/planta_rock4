'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiV9 as api } from '@/lib/v2-api';
import type { ScorOverview, ScorRecord, ScorRecentResponse } from '@/lib/v2-api';

const REFRESH_MS = 5_000;

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('pt-PT', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function fmtNumber(n: number): string {
  return n.toLocaleString('pt-PT', { maximumFractionDigits: 1 });
}

// Sparkline simples em SVG
function Sparkline({ values, color = '#1B3A21', height = 30 }: {
  values: number[]; color?: string; height?: number;
}) {
  const w = 120;
  const h = height;
  if (values.length < 2) {
    return <div style={{ width: w, height: h, fontSize: 10, color: 'var(--color-muted)' }}>—</div>;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}

export default function ScorPage() {
  const [overview, setOverview] = useState<ScorOverview | null>(null);
  const [records, setRecords] = useState<ScorRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ScorRecord | null>(null);

  const fetchAll = async () => {
    try {
      const [ov, recent] = await Promise.all([
        api.scorOverview(),
        api.scorRecent(100),
      ]);
      setOverview(ov);
      setRecords(recent.records);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'erro');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(iv);
  }, []);

  // Sparkline data (mais antigo → mais recente)
  const sparkData = useMemo(() => {
    const recs = [...records].reverse();
    return {
      kpi_01: recs.map(r => r.kpi_01),
      kpi_02: recs.map(r => r.kpi_02),
      kpi_03: recs.map(r => r.kpi_03),
      kpi_04: recs.map(r => r.kpi_04),
      latency: recs.map(r => r.duration_ms),
    };
  }, [records]);

  const latest = overview?.latest;
  const stats = overview?.stats;
  const cfg = overview?.config;

  return (
    <div style={{ padding: '32px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 20 }}>
        <div className="section-label">Pipelines · SCOR · Sensaway</div>
        <h1 className="serif" style={{
          fontSize: 'clamp(26px, 4vw, 40px)',
          fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.1, marginBottom: 6,
        }}>
          SCOR Publisher
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13, lineHeight: 1.55 }}>
          Stream live de cada publicação para a Sensaway · 4 KPIs · refresh {REFRESH_MS / 1000}s
        </p>
      </div>

      {/* Config tile */}
      {cfg && (
        <div style={{
          background: '#FAFAF7',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          padding: 14,
          marginBottom: 16,
          fontSize: 12,
          color: 'var(--color-muted)',
        }}>
          <span className="mono" style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 700, color: 'var(--color-ink)' }}>
            Destino:{' '}
          </span>
          <span className="mono">{cfg.url}</span>
          {' · '}
          <span className="mono">intervalo {cfg.interval_s}s</span>
          {cfg.dry_run && <span style={{ color: '#A85D00', marginLeft: 6 }}>DRY RUN</span>}
        </div>
      )}

      {/* Stats KPIs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: 10,
        marginBottom: 20,
      }}>
        <Kpi label="Sucesso" value={stats ? `${stats.success_rate_pct.toFixed(1)}%` : '—'} color="#1B3A21" />
        <Kpi label="Total OK" value={String(stats?.ok_count ?? '—')} color="#4A7C59" />
        <Kpi label="Erros" value={String(stats?.error_count ?? '—')} color={stats && stats.error_count > 0 ? '#C25A1A' : '#A85D00'} />
        <Kpi label="Latência (5min)" value={stats ? `${stats.avg_latency_ms_5min}ms` : '—'} color="#1A1A1A" />
        <Kpi label="Últimos 5min" value={String(stats?.last_5min_count ?? '—')} color="#1A1A1A" />
      </div>

      {/* Latest payload + Sparklines */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 14,
        marginBottom: 20,
      }}>
        <div style={{
          background: 'white',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          padding: 16,
        }}>
          <div className="mono" style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 10, fontWeight: 700 }}>
            Última publicação
          </div>
          {latest ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <span className="mono" style={{ fontSize: 13, color: 'var(--color-ink)' }}>
                  {fmtTime(latest.iso)}
                </span>
                <span style={{
                  fontSize: 11, fontWeight: 700, letterSpacing: '0.06em',
                  padding: '2px 8px', borderRadius: 999,
                  background: latest.status === 200 ? '#E8F1EA' : '#F8D9C4',
                  color: latest.status === 200 ? '#1B3A21' : '#8B3D0A',
                }}>
                  HTTP {latest.status} · {latest.duration_ms}ms
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
                <KpiBox label="Flow Index" value={String(latest.kpi_01)} />
                <KpiBox label="Ocupação" value={`${fmtNumber(latest.kpi_02)}%`} />
                <KpiBox label="Críticos" value={String(latest.kpi_03)} highlight={latest.kpi_03 > 0} />
                <KpiBox label="Redirecções" value={String(latest.kpi_04)} />
              </div>
            </>
          ) : (
            <div style={{ color: 'var(--color-muted)', fontSize: 13 }}>A aguardar primeira publicação…</div>
          )}
        </div>

        <div style={{
          background: 'white',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          padding: 16,
        }}>
          <div className="mono" style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 10, fontWeight: 700 }}>
            Últimos 100 KPIs
          </div>
          <SparkRow label="Flow Index" values={sparkData.kpi_01} color="#1B3A21" current={latest?.kpi_01 ?? 0} />
          <SparkRow label="Ocupação %" values={sparkData.kpi_02} color="#4A7C59" current={latest?.kpi_02 ?? 0} fmt="pct" />
          <SparkRow label="Críticos" values={sparkData.kpi_03} color="#C25A1A" current={latest?.kpi_03 ?? 0} />
          <SparkRow label="Latência ms" values={sparkData.latency} color="#6B7280" current={latest?.duration_ms ?? 0} />
        </div>
      </div>

      {error && (
        <div style={{
          padding: 10, marginBottom: 12,
          background: '#FDECDC', color: '#8B3D0A',
          borderRadius: 8, fontSize: 13,
        }}>{error}</div>
      )}

      {/* Stream tabela */}
      <h2 className="serif" style={{ fontSize: 20, fontWeight: 500, color: 'var(--color-ink)', marginBottom: 10 }}>
        Stream live
      </h2>
      <div style={{
        background: 'white',
        border: '1px solid var(--color-border)',
        borderRadius: 10,
        overflow: 'hidden',
      }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#FAFAF7', borderBottom: '1px solid var(--color-border)' }}>
              <Th>Hora</Th>
              <Th>Status</Th>
              <Th>ms</Th>
              <Th>Flow</Th>
              <Th>Ocup.</Th>
              <Th>Críticos</Th>
              <Th>Redir.</Th>
            </tr>
          </thead>
          <tbody>
            {loading && records.length === 0 && (
              <tr><td colSpan={7} style={{ padding: 16, textAlign: 'center', color: 'var(--color-muted)' }}>
                A aguardar primeiras publicações...
              </td></tr>
            )}
            {records.slice(0, 50).map((r, idx) => (
              <tr
                key={`${r.ts}-${idx}`}
                onClick={() => setSelected(r)}
                style={{
                  borderBottom: '1px solid var(--color-border)',
                  cursor: 'pointer',
                  background: selected?.ts === r.ts ? '#F4F9F5' : 'transparent',
                }}
              >
                <Td><span className="mono">{fmtTime(r.iso)}</span></Td>
                <Td>
                  <span style={{
                    fontSize: 10, fontWeight: 700,
                    padding: '2px 6px', borderRadius: 4,
                    background: r.status === 200 ? '#E8F1EA' : '#F8D9C4',
                    color: r.status === 200 ? '#1B3A21' : '#8B3D0A',
                  }}>{r.status}</span>
                </Td>
                <Td><span className="mono" style={{ color: 'var(--color-muted)' }}>{r.duration_ms}</span></Td>
                <Td><span className="mono" style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{r.kpi_01}</span></Td>
                <Td><span className="mono">{fmtNumber(r.kpi_02)}%</span></Td>
                <Td>
                  {r.kpi_03 > 0 ? (
                    <span style={{ color: '#C25A1A', fontWeight: 700 }}>{r.kpi_03}</span>
                  ) : (
                    <span style={{ color: 'var(--color-muted)' }}>0</span>
                  )}
                </Td>
                <Td><span className="mono">{r.kpi_04}</span></Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Selected payload modal */}
      {selected && (
        <div
          onClick={() => setSelected(null)}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: 16,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'white', borderRadius: 14, padding: 24,
              maxWidth: 560, width: '100%', maxHeight: '85vh', overflow: 'auto',
            }}
          >
            <h3 className="serif" style={{ fontSize: 18, marginBottom: 4 }}>
              Publicação às {fmtTime(selected.iso)}
            </h3>
            <div className="mono" style={{ fontSize: 11, color: 'var(--color-muted)', marginBottom: 14 }}>
              {selected.iso} · HTTP {selected.status} · {selected.duration_ms}ms
            </div>
            <pre style={{
              background: '#FAFAF7',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              padding: 14,
              fontSize: 12,
              overflow: 'auto',
              fontFamily: 'var(--font-mono, monospace)',
            }}>
{JSON.stringify({
  kpi_01: selected.kpi_01,
  kpi_02: selected.kpi_02,
  kpi_03: selected.kpi_03,
  kpi_04: selected.kpi_04,
  cluster_count: selected.cluster_count,
  ts: selected.ts,
}, null, 2)}
            </pre>
            <button
              onClick={() => setSelected(null)}
              style={{
                marginTop: 14, width: '100%',
                background: 'transparent',
                color: 'var(--color-muted)',
                border: '1px solid var(--color-border)',
                borderRadius: 10,
                padding: '10px 18px',
                fontSize: 13,
                cursor: 'pointer',
              }}
            >Fechar</button>
          </div>
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ background: 'white', border: '1px solid var(--color-border)', borderRadius: 10, padding: 12 }}>
      <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>
        {label}
      </div>
      <div className="serif" style={{ fontSize: 22, fontWeight: 500, color, lineHeight: 1 }}>{value}</div>
    </div>
  );
}

function KpiBox({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{
      background: highlight ? '#FDECDC' : '#FAFAF7',
      borderRadius: 8,
      padding: 10,
    }}>
      <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 16, fontWeight: 600, color: highlight ? '#C25A1A' : 'var(--color-ink)' }}>{value}</div>
    </div>
  );
}

function SparkRow({ label, values, color, current, fmt }: {
  label: string; values: number[]; color: string; current: number; fmt?: 'pct';
}) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '90px 1fr 60px',
      gap: 8,
      alignItems: 'center',
      padding: '6px 0',
      borderBottom: '1px dashed var(--color-border)',
    }}>
      <div style={{ fontSize: 11, color: 'var(--color-muted)' }}>{label}</div>
      <Sparkline values={values} color={color} />
      <div style={{ textAlign: 'right', fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>
        {fmt === 'pct' ? `${fmtNumber(current)}%` : fmtNumber(current)}
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '8px 12px',
  fontSize: 10,
  color: 'var(--color-muted)',
  fontWeight: 600,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
};
const tdStyle: React.CSSProperties = {
  padding: '7px 12px',
  color: 'var(--color-ink)',
};
function Th({ children }: { children: React.ReactNode }) { return <th style={thStyle}>{children}</th>; }
function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) { return <td style={{ ...tdStyle, ...style }}>{children}</td>; }
