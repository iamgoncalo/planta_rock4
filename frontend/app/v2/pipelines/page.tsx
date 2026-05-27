'use client';

import { useEffect, useState } from 'react';
import { apiV9 as api } from '@/lib/v2-api';
import type { PipelinesOverview, PipelineNode } from '@/lib/v2-api';

const REFRESH_MS = 10_000;

const ROLE_META: Record<string, { icon: string; color: string; label: string }> = {
  ingestion:  { icon: '📡', color: '#1B5A8B', label: 'INGESTÃO' },
  processing: { icon: '⚙', color: '#4A7C59', label: 'PROCESSAMENTO' },
  output:     { icon: '📤', color: '#7A4A8E', label: 'SAÍDA' },
  ai:         { icon: '✦', color: '#A85D00', label: 'INTELIGÊNCIA' },
};

const STATUS_META: Record<string, { bg: string; ink: string; label: string }> = {
  live:        { bg: '#E8F1EA', ink: '#1B3A21', label: 'LIVE' },
  pre_install: { bg: '#FFF2E0', ink: '#7A5A00', label: 'PRÉ-INSTALAÇÃO' },
  idle:        { bg: '#F0F0F0', ink: '#6B7280', label: 'INACTIVO' },
  error:       { bg: '#F8D9C4', ink: '#8B3D0A', label: 'ERRO' },
};

function fmtTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('pt-PT', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

export default function PipelinesPage() {
  const [data, setData] = useState<PipelinesOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = async () => {
    try {
      const d = await api.pipelinesOverview();
      setData(d);
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

  return (
    <div style={{ padding: '32px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 20 }}>
        <div className="section-label">Sistema · Pipelines de dados</div>
        <h1 className="serif" style={{
          fontSize: 'clamp(26px, 4vw, 40px)',
          fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.1, marginBottom: 6,
        }}>
          Fluxos de dados
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13, lineHeight: 1.55 }}>
          Onde os dados entram, como são processados e para onde saem · refresh {REFRESH_MS / 1000}s
        </p>
      </div>

      {error && (
        <div style={{ padding: 10, marginBottom: 12, background: '#FDECDC', color: '#8B3D0A', borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {loading && !data && (
        <div style={{ color: 'var(--color-muted)', padding: 24 }}>A carregar...</div>
      )}

      {/* DATA FLOW VISUAL */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 14,
        marginBottom: 24,
      }}>
        {data?.nodes.map(node => {
          const role = ROLE_META[node.role] || ROLE_META.processing;
          const status = STATUS_META[node.status] || STATUS_META.idle;
          return (
            <div key={node.id} style={{
              background: 'white',
              border: '1px solid var(--color-border)',
              borderTop: `3px solid ${role.color}`,
              borderRadius: 10,
              padding: 18,
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div className="mono" style={{
                    fontSize: 9, color: role.color, letterSpacing: '0.12em',
                    textTransform: 'uppercase', fontWeight: 700, marginBottom: 4,
                  }}>
                    {role.icon} {role.label}
                  </div>
                  <div className="serif" style={{ fontSize: 18, fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.2 }}>
                    {node.label}
                  </div>
                </div>
                <span style={{
                  background: status.bg, color: status.ink,
                  padding: '3px 8px', borderRadius: 999,
                  fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                  whiteSpace: 'nowrap',
                }}>{status.label}</span>
              </div>

              {/* Rate */}
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, borderTop: '1px dashed var(--color-border)', paddingTop: 8 }}>
                <span className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1 }}>
                  {node.rate_per_minute > 0 ? node.rate_per_minute.toFixed(1) : '—'}
                </span>
                <span className="mono" style={{ fontSize: 10, color: 'var(--color-muted)' }}>
                  eventos/min
                </span>
              </div>

              {/* Last event */}
              <div style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                Último: <span className="mono" style={{ color: 'var(--color-ink)' }}>{fmtTime(node.last_event_iso ?? null)}</span>
              </div>

              {/* Details */}
              <div style={{
                background: '#FAFAF7', borderRadius: 6,
                padding: 8, fontSize: 11, color: 'var(--color-muted)',
                marginTop: 4,
              }}>
                {Object.entries(node.details).slice(0, 5).map(([k, v]) => (
                  <div key={k} style={{ marginBottom: 2 }}>
                    <span className="mono" style={{ color: 'var(--color-ink)' }}>{k}:</span>{' '}
                    {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Flow diagram inline */}
      <div style={{
        background: 'white',
        border: '1px solid var(--color-border)',
        borderRadius: 10,
        padding: 18,
        marginBottom: 24,
      }}>
        <div className="mono" style={{
          fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase',
          color: 'var(--color-muted)', marginBottom: 14, fontWeight: 700,
        }}>
          Fluxo geral
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
          flexWrap: 'wrap',
          fontSize: 12,
        }}>
          <FlowBox icon="📡" label="Sensores físicos" sub="11 Jun 2026" color="#1B5A8B" muted />
          <Arrow />
          <FlowBox icon="⚙" label="Auto-tick" sub="simulação 10s" color="#4A7C59" />
          <Arrow />
          <FlowBox icon="🗄" label="DB + state" sub="14 unidades" color="#1A1A1A" />
          <Arrow />
          <FlowBox icon="📤" label="Sensaway" sub="SCOR 10s" color="#7A4A8E" />
        </div>
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px dashed var(--color-border)', textAlign: 'center', fontSize: 11, color: 'var(--color-muted)' }}>
          ↓ Frontend polling refresh 10-30s · /v2 dashboard, /v2/cleaning, /v2/scor, /v2/operations
        </div>
      </div>

      {data && (
        <div style={{ fontSize: 11, color: 'var(--color-muted)', textAlign: 'right' }}>
          <span className="mono">Última actualização: {fmtTime(data.generated_at)}</span>
        </div>
      )}
    </div>
  );
}

function FlowBox({ icon, label, sub, color, muted }: {
  icon: string; label: string; sub: string; color: string; muted?: boolean;
}) {
  return (
    <div style={{
      background: muted ? '#FAFAF7' : 'white',
      border: `1px solid ${muted ? 'var(--color-border)' : color}`,
      borderRadius: 8,
      padding: '10px 14px',
      minWidth: 140,
      textAlign: 'center',
      opacity: muted ? 0.6 : 1,
    }}>
      <div style={{ fontSize: 22, marginBottom: 2 }}>{icon}</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>{label}</div>
      <div className="mono" style={{ fontSize: 10, color: 'var(--color-muted)', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function Arrow() {
  return (
    <div style={{ fontSize: 18, color: 'var(--color-muted)' }}>→</div>
  );
}
