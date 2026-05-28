'use client';

import Link from 'next/link';
import { useLive } from '@/components/v2/LiveContext';

const CLUSTER_ORDER = ['wc-01', 'wc-02', 'wc-03', 'wc-04', 'wc-05', 'wc-06', 'wc-07', 'wc-08'];
const UNISEX = new Set(['wc-05', 'wc-06']);

export default function HomePage() {
  const { snapshot, connection, tick, totalPessoas, avgOcc, criticos } = useLive();

  const clusters = (() => {
    if (!snapshot) return [];
    const m = new Map(snapshot.clusters.map((c) => [c.cluster_id, c]));
    return CLUSTER_ORDER.map((id) => m.get(id)).filter(Boolean) as NonNullable<ReturnType<typeof m.get>>[];
  })();

  const flowIdx = snapshot?.kpis?.kpi_01 ?? 0;
  const isStreaming = connection === 'sse';

  return (
    <div className="page-full">
      <section style={{ marginBottom: 'clamp(20px, 3vw, 36px)' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            gap: 16,
            flexWrap: 'wrap',
            marginBottom: 24,
          }}
        >
          <div>
            <div className="section-label">Rock in Rio Lisboa · Parque Tejo · 20–28 Jun 2026</div>
            <h1
              className="display"
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'clamp(40px, 6vw, 84px)',
                lineHeight: 0.95,
                letterSpacing: '-0.035em',
                fontWeight: 500,
                marginTop: 4,
              }}
            >
              Em tempo real.
            </h1>
          </div>
          <span className={isStreaming ? 'pill pill-live' : 'pill pill-sim'}>
            {connection === 'sse' ? 'STREAM AO SEGUNDO' :
             connection === 'polling' ? 'FALLBACK · 2s' :
             connection === 'offline' ? 'OFFLINE' : 'A LIGAR'}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 'clamp(12px, 2vw, 28px)',
            borderTop: '1px solid var(--border)',
            paddingTop: 'clamp(14px, 2vw, 22px)',
          }}
        >
          <Kpi label="Pessoas estimadas" value={totalPessoas} accent />
          <Kpi label="Ocupação média" value={`${avgOcc.toFixed(0)}%`} />
          <Kpi label="Índice de fluxo" value={flowIdx} />
          <Kpi label="Críticos" value={criticos} alert={criticos > 0} />
        </div>
      </section>

      <section style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginBottom: 12,
          }}
        >
          <div className="section-label">8 clusters · 1 137 lugares</div>
          <span
            className="mono"
            style={{ fontSize: 11, color: 'var(--faint)' }}
          >
            tick #{tick}
          </span>
        </div>

        <div className="grid grid-8" style={{ alignContent: 'start' }}>
          {clusters.length === 0 &&
            CLUSTER_ORDER.map((id) => (
              <div
                key={id}
                style={{
                  background: 'var(--bg-soft)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  padding: 18,
                  minHeight: 90,
                }}
              />
            ))}
          {clusters.map((c) => {
            const isUni = UNISEX.has(c.cluster_id);
            const occ = c.params.ocupacao_instantanea ?? 0;
            const occColor =
              occ >= 80 ? 'var(--amber)' : occ >= 60 ? '#A85D00' : 'var(--green-dark)';
            return (
              <Link
                key={c.cluster_id}
                href={`/v2/scor`}
                style={{
                  background: 'white',
                  border: '1px solid var(--border)',
                  borderLeft: `3px solid ${isUni ? '#7A4A8E' : 'var(--green-dark)'}`,
                  borderRadius: 'var(--radius)',
                  padding: '14px 16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'border-color 0.18s, box-shadow 0.18s, transform 0.18s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = 'none';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 'clamp(15px, 1.4vw, 18px)',
                        fontWeight: 600,
                        letterSpacing: '-0.015em',
                        color: 'var(--ink)',
                      }}
                    >
                      {c.cluster_id.toUpperCase()}
                    </div>
                    <div
                      className="mono"
                      style={{
                        fontSize: 9,
                        color: 'var(--muted)',
                        letterSpacing: '0.1em',
                        textTransform: 'uppercase',
                        marginTop: 1,
                      }}
                    >
                      {isUni ? 'unissex' : 'masc + fem'}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: 'clamp(18px, 2vw, 24px)',
                      fontWeight: 600,
                      letterSpacing: '-0.02em',
                      color: occColor,
                      lineHeight: 1,
                    }}
                  >
                    {occ}
                    <span style={{ fontSize: '0.55em', marginLeft: 1, color: 'var(--muted)' }}>%</span>
                  </div>
                </div>

                <div
                  style={{
                    height: 4,
                    background: 'var(--bg-soft)',
                    borderRadius: 999,
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, occ)}%`,
                      height: '100%',
                      background: occColor,
                      transition: 'width 0.5s ease',
                    }}
                  />
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 11,
                    color: 'var(--muted)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <span>{c.params.pessoas_estimadas} pessoas</span>
                  {c.params.fila_atual !== undefined && (
                    <span>fila {c.params.fila_atual}</span>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <footer
        style={{
          marginTop: 'clamp(16px, 2vw, 28px)',
          paddingTop: 14,
          borderTop: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 14,
          fontSize: 12,
          color: 'var(--muted)',
          flexWrap: 'wrap',
        }}
      >
        {/* Tagline editorial — alternativas comentadas para troca rapida */}
        {/* "Holding it in is so 2024." */}
        {/* "When nature calls, we answer first." */}
        <div style={{
          fontSize: 'clamp(12px, 1.3vw, 14px)',
          color: 'var(--muted)',
          fontStyle: 'italic',
          letterSpacing: '-0.005em',
          maxWidth: '60ch',
          lineHeight: 1.4,
        }}>
          Someone has to take care of your needs.
        </div>
        <div style={{ display: 'flex', gap: 18, fontSize: 12 }}>
          <Link href="/v2/twin" style={{ color: 'var(--muted)' }}>Digital twin →</Link>
          <Link href="/v2/scor" style={{ color: 'var(--muted)' }}>SCOR live →</Link>
          <Link href="/v2/cleaning" style={{ color: 'var(--muted)' }}>Limpeza →</Link>
        </div>
      </footer>
    </div>
  );
}

function Kpi({ label, value, accent, alert }: {
  label: string;
  value: number | string;
  accent?: boolean;
  alert?: boolean;
}) {
  return (
    <div>
      <div className="kpi-label">{label}</div>
      <div
        className="kpi-value"
        style={{
          color: alert ? 'var(--amber)' : accent ? 'var(--green-dark)' : 'var(--ink)',
          marginTop: 4,
        }}
      >
        {typeof value === 'number' ? value.toLocaleString('pt-PT') : value}
      </div>
    </div>
  );
}
