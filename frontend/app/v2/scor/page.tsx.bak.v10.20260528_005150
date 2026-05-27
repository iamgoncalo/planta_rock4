'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

// 8 clusters oficiais (lowercase no payload)
const CLUSTER_ORDER = ['wc-01', 'wc-02', 'wc-03', 'wc-04', 'wc-05', 'wc-06', 'wc-07', 'wc-08'];
const UNISEX = new Set(['wc-05', 'wc-06']);

interface ClusterPayload {
  cluster_id: string;
  ts: number;
  params: {
    telemoveis_detectados: number;
    pessoas_estimadas: number;
    homens: number | null;
    mulheres: number | null;
    entradas_ir: number;
    saidas_ir: number;
    ocupacao_instantanea: number;
    contagem_prosegur: number;
    confianca_cruzada: number;
    estado_sensor: string;
    fila_atual?: number;
    tempo_espera_min?: number;
    is_unissex?: boolean;
    capacidade_total?: number;
  };
}

interface Snapshot {
  clusters: ClusterPayload[];
  kpis: { kpi_01: number; kpi_02: number; kpi_03: number; kpi_04: number };
  cluster_count: number;
}

const ESTADO_COLORS: Record<string, { bg: string; ink: string; ring: string; label: string }> = {
  okay:     { bg: '#E8F1EA', ink: '#1B3A21', ring: '#4A7C59', label: 'OK' },
  simulado: { bg: '#FFF2E0', ink: '#7A5A00', ring: '#A85D00', label: 'SIMULADO' },
  warn:     { bg: '#FDECDC', ink: '#8B3D0A', ring: '#C25A1A', label: 'ATENÇÃO' },
  fail:     { bg: '#F8D9C4', ink: '#8B3D0A', ring: '#C25A1A', label: 'FALHA' },
};

function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('pt-PT', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

export default function ScorPage() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [tickCount, setTickCount] = useState(0);
  // Histórico para sparklines (últimos 60 valores por cluster, por param)
  const historyRef = useRef<Map<string, { occ: number[]; pessoas: number[] }>>(new Map());

  useEffect(() => {
    if (paused) return;
    let es: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      try {
        es = new EventSource(`${API_BASE}/api/v1/telemetry/clusters/stream`);
        setStreaming(true);
        es.onmessage = (ev) => {
          try {
            const data: Snapshot = JSON.parse(ev.data);
            setSnap(data);
            setError(null);
            setTickCount(c => c + 1);

            // Actualizar histórico para sparklines
            data.clusters.forEach(c => {
              const h = historyRef.current.get(c.cluster_id) || { occ: [], pessoas: [] };
              h.occ.push(c.params.ocupacao_instantanea);
              h.pessoas.push(c.params.pessoas_estimadas);
              if (h.occ.length > 60) h.occ.shift();
              if (h.pessoas.length > 60) h.pessoas.shift();
              historyRef.current.set(c.cluster_id, h);
            });
          } catch (e) {
            console.error('parse error', e);
          }
        };
        es.onerror = () => {
          setStreaming(false);
          setError('Stream desligado, a reconectar...');
          if (es) es.close();
          retryTimer = setTimeout(connect, 3000);
        };
      } catch (e) {
        setError(e instanceof Error ? e.message : 'connect error');
      }
    };
    connect();

    return () => {
      if (es) es.close();
      if (retryTimer) clearTimeout(retryTimer);
      setStreaming(false);
    };
  }, [paused]);

  // Ordenar clusters pela ordem oficial
  const ordered = useMemo(() => {
    if (!snap) return [];
    const m = new Map(snap.clusters.map(c => [c.cluster_id, c]));
    return CLUSTER_ORDER.map(id => m.get(id)).filter(Boolean) as ClusterPayload[];
  }, [snap]);

  return (
    <div style={{ padding: '32px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 18 }}>
        <div className="section-label">Pipelines · SCOR live · 8 clusters</div>
        <h1 className="serif" style={{
          fontSize: 'clamp(26px, 4vw, 40px)',
          fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.1, marginBottom: 6,
        }}>
          SCOR · Telemetria ao segundo
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13, lineHeight: 1.55 }}>
          Stream live · 8 clusters · 10 parâmetros por cluster · update a cada 1 s ·{' '}
          <span className="mono">{tickCount}</span> ticks recebidos
          {snap && <> · payload às <span className="mono">{fmtTime(snap.clusters[0]?.ts || 0)}</span></>}
        </p>
      </div>

      {/* Status bar */}
      <div style={{
        background: streaming ? '#E8F1EA' : '#FFF2E0',
        border: `1px solid ${streaming ? '#4A7C59' : '#A85D00'}`,
        borderRadius: 10, padding: '10px 14px', marginBottom: 16,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: streaming ? '#4A7C59' : '#A85D00',
            animation: streaming ? 'pulse 1.2s infinite' : 'none',
          }} />
          <span style={{ fontWeight: 600, color: streaming ? '#1B3A21' : '#7A5A00' }}>
            {streaming ? 'STREAM ACTIVO' : 'STREAM DESLIGADO'}
          </span>
          {snap && <>
            <span className="mono" style={{ color: 'var(--color-muted)', fontSize: 11 }}>
              Flow Index <strong style={{ color: 'var(--color-ink)' }}>{snap.kpis.kpi_01}</strong>
              {' · '}Ocup <strong style={{ color: 'var(--color-ink)' }}>{snap.kpis.kpi_02}%</strong>
              {' · '}Críticos <strong style={{ color: snap.kpis.kpi_03 > 0 ? '#C25A1A' : 'var(--color-ink)' }}>{snap.kpis.kpi_03}</strong>
            </span>
          </>}
        </div>
        <button
          onClick={() => setPaused(!paused)}
          style={{
            background: 'white',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            padding: '5px 12px',
            fontSize: 12, fontWeight: 600,
            cursor: 'pointer',
            color: 'var(--color-ink)',
          }}
        >{paused ? '▶ Retomar' : '⏸ Pausar'}</button>
      </div>

      {error && (
        <div style={{
          padding: 10, marginBottom: 12,
          background: '#FDECDC', color: '#8B3D0A',
          borderRadius: 8, fontSize: 13,
        }}>{error}</div>
      )}

      {/* GRID DE 8 CLUSTERS */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(330px, 1fr))',
        gap: 14,
      }}>
        {!snap && (
          <div style={{ padding: 32, color: 'var(--color-muted)', gridColumn: '1 / -1' }}>
            A aguardar primeiros dados do stream...
          </div>
        )}
        {ordered.map(c => (
          <ClusterCard
            key={c.cluster_id}
            cluster={c}
            history={historyRef.current.get(c.cluster_id)}
          />
        ))}
      </div>

      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}

function ClusterCard({ cluster, history }: {
  cluster: ClusterPayload;
  history?: { occ: number[]; pessoas: number[] };
}) {
  const c = cluster;
  const isUni = UNISEX.has(c.cluster_id);
  const estado = c.params.estado_sensor || 'simulado';
  const stEstado = ESTADO_COLORS[estado] || ESTADO_COLORS.simulado;
  const occ = c.params.ocupacao_instantanea;
  const cap = c.params.capacidade_total || 100;

  // Cor da barra de ocupação
  const occColor = occ >= 80 ? '#C25A1A' : occ >= 60 ? '#A85D00' : '#4A7C59';

  return (
    <div style={{
      background: 'white',
      border: '1px solid var(--color-border)',
      borderLeft: `4px solid ${stEstado.ring}`,
      borderRadius: 10,
      padding: 16,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span className="serif" style={{ fontSize: 24, fontWeight: 600, color: 'var(--color-ink)' }}>
              {c.cluster_id.toUpperCase()}
            </span>
            {isUni && (
              <span style={{
                background: '#F3EAFF', color: '#7A4A8E',
                padding: '2px 8px', borderRadius: 999,
                fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
              }}>UNISSEX</span>
            )}
          </div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--color-muted)', marginTop: 2 }}>
            cap. {cap} · {isUni ? 'cluster único' : 'masc + fem'}
          </div>
        </div>
        <span style={{
          background: stEstado.bg, color: stEstado.ink,
          padding: '3px 8px', borderRadius: 999,
          fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
        }}>{stEstado.label}</span>
      </div>

      {/* Ocupação grande */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
          <span className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Ocupação instantânea
          </span>
          <span className="serif" style={{ fontSize: 22, fontWeight: 600, color: occColor }}>
            {occ}<span style={{ fontSize: 14, color: 'var(--color-muted)', marginLeft: 2 }}>%</span>
          </span>
        </div>
        <div style={{
          height: 8, background: '#FAFAF7', borderRadius: 999, overflow: 'hidden',
        }}>
          <div style={{
            width: `${Math.min(100, occ)}%`,
            height: '100%',
            background: occColor,
            transition: 'width 0.4s ease',
          }} />
        </div>
        {history && history.occ.length > 1 && (
          <Sparkline values={history.occ} color={occColor} height={20} />
        )}
      </div>

      {/* Grid dos 10 params */}
      <div style={{
        background: '#FAFAF7',
        borderRadius: 8,
        padding: 10,
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 6,
        fontSize: 11,
      }}>
        <Param label="Pessoas estimadas" value={c.params.pessoas_estimadas} highlight />
        <Param label="Telemóveis" value={c.params.telemoveis_detectados} />
        {!isUni ? (
          <>
            <Param label="Homens" value={c.params.homens ?? 0} icon="♂" iconColor="#1B5A8B" />
            <Param label="Mulheres" value={c.params.mulheres ?? 0} icon="♀" iconColor="#A8226F" />
          </>
        ) : (
          <>
            <Param label="Homens" value="—" muted />
            <Param label="Mulheres" value="—" muted />
          </>
        )}
        <Param label="Entradas IR" value={c.params.entradas_ir} icon="→" />
        <Param label="Saídas IR" value={c.params.saidas_ir} icon="←" />
        <Param label="Contagem Prosegur" value={c.params.contagem_prosegur} />
        <Param label="Confiança cruzada" value={`${(c.params.confianca_cruzada * 100).toFixed(0)}%`} />
      </div>

      {/* Footer: fila e tempo */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: 11,
        color: 'var(--color-muted)',
        borderTop: '1px dashed var(--color-border)',
        paddingTop: 8,
      }}>
        <span>
          Fila <strong style={{ color: 'var(--color-ink)' }}>{c.params.fila_atual ?? '—'}</strong>
        </span>
        <span>
          Espera <strong style={{ color: 'var(--color-ink)' }}>{c.params.tempo_espera_min ?? '—'} min</strong>
        </span>
        <span className="mono" style={{ fontSize: 10 }}>
          {fmtTime(c.ts)}
        </span>
      </div>
    </div>
  );
}

function Param({ label, value, icon, iconColor, highlight, muted }: {
  label: string; value: number | string;
  icon?: string; iconColor?: string;
  highlight?: boolean; muted?: boolean;
}) {
  return (
    <div style={{ opacity: muted ? 0.4 : 1 }}>
      <div className="mono" style={{ fontSize: 8, color: 'var(--color-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 1 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        {icon && <span style={{ color: iconColor || 'var(--color-muted)', fontSize: 12 }}>{icon}</span>}
        <span style={{
          fontSize: highlight ? 16 : 13,
          fontWeight: highlight ? 700 : 600,
          color: 'var(--color-ink)',
        }}>{value}</span>
      </div>
    </div>
  );
}

function Sparkline({ values, color, height = 20 }: { values: number[]; color: string; height?: number }) {
  if (values.length < 2) return null;
  const w = 100;
  const h = height;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 2) - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ marginTop: 4 }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" opacity={0.7} />
    </svg>
  );
}
