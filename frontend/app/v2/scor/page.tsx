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
  simulado: { bg: '#FFF2E0', ink: '#7A5A00', ring: '#A85D00', label: 'LIVE' },
  warn:     { bg: '#FDECDC', ink: '#8B3D0A', ring: '#C25A1A', label: 'ATENÇÃO' },
  fail:     { bg: '#F8D9C4', ink: '#8B3D0A', ring: '#C25A1A', label: 'FALHA' },
};

const AMBER = '#C25A1A';

function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('pt-PT', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function occColor(occ: number) {
  return occ >= 85 ? AMBER : occ >= 65 ? '#A85D00' : '#4A7C59';
}

// ── Drawer de detalhe ────────────────────────────────────────────────────────

function OccBar({ label, pct, isHigh }: { label: string; pct: number; isHigh: boolean }) {
  const color = isHigh ? AMBER : '#4A7C59';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span style={{ width: 20, fontSize: 11, fontWeight: 700, color: 'var(--color-muted)', textAlign: 'center', flexShrink: 0 }}>
        {label}
      </span>
      <div style={{ flex: 1, position: 'relative', height: 10, background: '#F0EEE6', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', inset: '0 auto 0 0',
          width: `${Math.min(100, pct)}%`,
          background: color,
          borderRadius: 999,
          transition: 'width 0.4s ease',
        }} />
      </div>
      <span style={{
        width: 42, textAlign: 'right', fontSize: 15, fontWeight: 700,
        fontVariantNumeric: 'tabular-nums', color: isHigh ? AMBER : 'var(--color-ink)',
        flexShrink: 0,
      }}>{pct}%</span>
    </div>
  );
}

function DrawerStat({ label, value, sub, highlight }: { label: string; value: string | number; sub?: string; highlight?: boolean }) {
  return (
    <div style={{
      background: '#FAFAF7', border: '1px solid #ECE9E2', borderRadius: 10,
      padding: '10px 13px',
    }}>
      <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 3 }}>
        {label}
      </div>
      <div style={{ fontSize: highlight ? 28 : 20, fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: 'var(--color-ink)', lineHeight: 1.1 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function ScorDrawer({ cluster, onClose }: { cluster: ClusterPayload; onClose: () => void }) {
  const p = cluster.params;
  const isUni = UNISEX.has(cluster.cluster_id);
  const estado = p.estado_sensor || 'simulado';
  const stEstado = ESTADO_COLORS[estado] || ESTADO_COLORS.simulado;
  const occ = p.ocupacao_instantanea;
  const cap = p.capacidade_total || 100;
  const capHalf = cap / 2;

  // Ocupação por secção
  const M_pct = isUni ? null : Math.min(100, Math.round(((p.homens ?? 0) / capHalf) * 100));
  const F_pct = isUni ? null : Math.min(100, Math.round(((p.mulheres ?? 0) / capHalf) * 100));
  const U_pct = isUni ? occ : null;

  const fila = p.fila_atual ?? 0;
  const espera = p.tempo_espera_min ?? 0;
  const confianca = Math.round(p.confianca_cruzada * 100);
  const isHigh = occ >= 85;
  const isWarn = occ >= 65;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: '#fff',
    }}>
      {/* Cabeçalho */}
      <div style={{
        flexShrink: 0,
        padding: '20px 20px 14px',
        borderBottom: `3px solid ${stEstado.ring}`,
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        gap: 12,
      }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: stEstado.ring, marginBottom: 2 }}>
            {stEstado.label} · {isUni ? 'Unissexo' : 'M / F'}
          </div>
          <div style={{ fontSize: 'clamp(24px, 3vw, 32px)', fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--color-ink)', lineHeight: 1.1 }}>
            {cluster.cluster_id.toUpperCase()}
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 4, fontVariantNumeric: 'tabular-nums' }}>
            Cap. {cap} · {fmtTime(cluster.ts)}
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label="Fechar painel"
          style={{
            flexShrink: 0, width: 36, height: 36, borderRadius: '50%',
            border: '1px solid #ECE9E2', background: '#F5F3EE',
            cursor: 'pointer', fontSize: 16, color: 'var(--color-ink)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >✕</button>
      </div>

      {/* Corpo com scroll interno */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Ocupação — número grande */}
        <section>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 8 }}>
            Ocupação
          </div>
          <div style={{
            fontSize: 'clamp(52px, 8vw, 72px)', fontWeight: 200, letterSpacing: '-0.04em', lineHeight: 0.9,
            color: isHigh ? AMBER : isWarn ? '#A85D00' : 'var(--color-ink)',
            marginBottom: 14,
          }}>
            {occ}<span style={{ fontSize: '0.36em', fontWeight: 500, opacity: 0.6 }}>%</span>
          </div>

          {/* Barra total */}
          <div style={{ height: 10, background: '#F0EEE6', borderRadius: 999, overflow: 'hidden', marginBottom: 14 }}>
            <div style={{
              width: `${Math.min(100, occ)}%`, height: '100%',
              background: occColor(occ), borderRadius: 999,
              transition: 'width 0.4s ease',
            }} />
          </div>

          {/* Barras M/F ou U */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {isUni ? (
              <OccBar label="●" pct={U_pct ?? 0} isHigh={(U_pct ?? 0) >= 85} />
            ) : (
              <>
                <OccBar label="M" pct={M_pct ?? 0} isHigh={(M_pct ?? 0) >= 85} />
                <OccBar label="F" pct={F_pct ?? 0} isHigh={(F_pct ?? 0) >= 85} />
              </>
            )}
          </div>
        </section>

        {/* Fila + Espera */}
        <section>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 8 }}>
            Fila & Espera
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <DrawerStat label="Fila actual" value={fila} sub="pessoas" highlight />
            <DrawerStat label="Tempo de espera" value={`${espera.toFixed(0)} min`} sub="estimado" />
          </div>
        </section>

        {/* Fluxo */}
        <section>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 8 }}>
            Fluxo IR
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <DrawerStat label="Entradas" value={p.entradas_ir} sub="/intervalo" />
            <DrawerStat label="Saídas" value={p.saidas_ir} sub="/intervalo" />
          </div>
        </section>

        {/* Pessoas */}
        <section>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 8 }}>
            Pessoas
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <DrawerStat label="Pessoas estimadas" value={p.pessoas_estimadas} />
            <DrawerStat label="Telemóveis" value={p.telemoveis_detectados} sub="agregado anónimo" />
          </div>
        </section>

        {/* Confiança */}
        <section>
          <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 8 }}>
            Confiança & Sensor
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <DrawerStat
              label="Confiança cruzada"
              value={`${confianca}%`}
              sub={confianca >= 80 ? 'boa' : confianca >= 50 ? 'aceitável' : 'baixa'}
            />
            <div style={{
              background: stEstado.bg, border: `1px solid ${stEstado.ring}`,
              borderRadius: 10, padding: '10px 13px',
            }}>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: stEstado.ink, marginBottom: 3 }}>
                Estado
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color: stEstado.ink }}>{stEstado.label}</div>
              <div style={{ fontSize: 11, color: stEstado.ink, opacity: 0.7, marginTop: 2 }}>{p.estado_sensor}</div>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}

// ── Página SCOR ───────────────────────────────────────────────────────────────

export default function ScorPage() {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [tickCount, setTickCount] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
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

  // Fechar drawer com Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setSelectedId(null); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Ordenar clusters pela ordem oficial
  const ordered = useMemo(() => {
    if (!snap) return [];
    const m = new Map(snap.clusters.map(c => [c.cluster_id, c]));
    return CLUSTER_ORDER.map(id => m.get(id)).filter(Boolean) as ClusterPayload[];
  }, [snap]);

  const selectedCluster = snap?.clusters.find(c => c.cluster_id === selectedId) ?? null;
  const drawerOpen = selectedCluster !== null;

  return (
    <>
      <div style={{
        position: 'fixed',
        top: 'var(--header-h, 72px)', left: 0, right: 0, bottom: 0,
        height: 'calc(100svh - var(--header-h, 72px))',
        overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
        padding: '14px clamp(16px, 2.6vw, 32px) 0',
      }}>
        <div style={{ marginBottom: 12, flexShrink: 0 }}>
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
          borderRadius: 10, padding: '10px 14px', marginBottom: 16, flexShrink: 0,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          flexWrap: 'wrap', gap: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: streaming ? '#4A7C59' : '#A85D00',
              animation: streaming ? 'scorPulse 1.2s infinite' : 'none',
            }} />
            <span style={{ fontWeight: 600, color: streaming ? '#1B3A21' : '#7A5A00' }}>
              {streaming ? 'STREAM ACTIVO' : 'STREAM DESLIGADO'}
            </span>
            {snap && <>
              <span className="mono" style={{ color: 'var(--color-muted)', fontSize: 11 }}>
                Flow Index <strong style={{ color: 'var(--color-ink)' }}>{snap.kpis.kpi_01}</strong>
                {' · '}Ocup <strong style={{ color: 'var(--color-ink)' }}>{snap.kpis.kpi_02}%</strong>
                {' · '}Críticos <strong style={{ color: snap.kpis.kpi_03 > 0 ? AMBER : 'var(--color-ink)' }}>{snap.kpis.kpi_03}</strong>
              </span>
            </>}
          </div>
          <button
            onClick={() => setPaused(!paused)}
            style={{
              background: 'white', border: '1px solid var(--color-border)',
              borderRadius: 8, padding: '5px 12px',
              fontSize: 12, fontWeight: 600, cursor: 'pointer', color: 'var(--color-ink)',
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

        {/* KPIs */}
        {snap && (
          <div style={{
            background: 'white', border: '1px solid var(--color-border, #E5E8E0)',
            borderRadius: 12, padding: '14px 16px', marginBottom: 16, flexShrink: 0,
          }}>
            <div style={{
              fontSize: 11, fontWeight: 700, letterSpacing: '0.06em',
              textTransform: 'uppercase', color: 'var(--color-muted, #6B7280)', marginBottom: 10,
            }}>
              KPIs enviados ao SCOR
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 }}>
              {[
                { key: 'kpi_01_value', label: 'Flow Index', sub: '0–100', val: String(snap.kpis.kpi_01), crit: false },
                { key: 'kpi_02_value', label: 'Ocupacao media', sub: '% WC', val: snap.kpis.kpi_02 + '%', crit: false },
                { key: 'kpi_03_value', label: 'Alertas criticos', sub: 'activos', val: String(snap.kpis.kpi_03), crit: snap.kpis.kpi_03 > 0 },
                { key: 'kpi_04_value', label: 'Pessoas redirigidas', sub: 'no dia', val: String(snap.kpis.kpi_04), crit: false },
              ].map((k) => (
                <div key={k.key} style={{
                  background: 'var(--color-paper, #FAFAF7)',
                  border: '1px solid var(--color-border, #E5E8E0)',
                  borderRadius: 10, padding: '10px 12px',
                }}>
                  <div style={{
                    fontSize: 26, fontWeight: 600, lineHeight: 1.1,
                    fontVariantNumeric: 'tabular-nums',
                    color: k.crit ? AMBER : 'var(--color-ink, #0D1A0F)',
                  }}>{k.val}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-ink, #0D1A0F)', marginTop: 4, fontWeight: 500 }}>
                    {k.label} <span style={{ color: 'var(--color-muted, #6B7280)', fontWeight: 400 }}>· {k.sub}</span>
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: 'var(--color-muted, #6B7280)', marginTop: 2 }}>
                    {k.key}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Grid de 8 clusters */}
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingBottom: 96, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 14, alignContent: 'start' }}>
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
              isSelected={c.cluster_id === selectedId}
              onClick={() => setSelectedId(prev => prev === c.cluster_id ? null : c.cluster_id)}
            />
          ))}
        </div>
      </div>

      {/* Backdrop */}
      {drawerOpen && (
        <div
          onClick={() => setSelectedId(null)}
          aria-hidden="true"
          style={{
            position: 'fixed', inset: 0, zIndex: 49,
            background: 'rgba(13,26,15,0.28)',
            backdropFilter: 'blur(2px)',
            WebkitBackdropFilter: 'blur(2px)',
            animation: 'scorFadeIn 0.22s ease',
          }}
        />
      )}

      {/* Drawer */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={selectedCluster ? `Detalhe ${selectedCluster.cluster_id.toUpperCase()}` : undefined}
        style={{
          position: 'fixed',
          top: 72,
          right: 0,
          bottom: 0,
          zIndex: 50,
          width: drawerOpen ? 'clamp(300px, 34%, 430px)' : 0,
          overflow: 'hidden',
          boxShadow: drawerOpen ? '-10px 0 36px rgba(13,26,15,0.14)' : 'none',
          transition: 'width 0.3s cubic-bezier(0.2,0.8,0.2,1)',
        }}
      >
        {selectedCluster && (
          <ScorDrawer cluster={selectedCluster} onClose={() => setSelectedId(null)} />
        )}
      </div>

      <style jsx>{`
        @keyframes scorPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.35; }
        }
        @keyframes scorFadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @media (max-width: 640px) {
          div[role="dialog"] {
            top: auto !important;
            right: 0 !important;
            left: 0 !important;
            width: auto !important;
            max-height: 75svh;
            border-top-left-radius: 20px;
            border-top-right-radius: 20px;
            overflow: hidden;
            transform: translateY(${drawerOpen ? '0' : '100%'});
            transition: transform 0.3s cubic-bezier(0.2,0.8,0.2,1) !important;
          }
        }
      `}</style>
    </>
  );
}

// ── ClusterCard ───────────────────────────────────────────────────────────────

function ClusterCard({ cluster, history, isSelected, onClick }: {
  cluster: ClusterPayload;
  history?: { occ: number[]; pessoas: number[] };
  isSelected: boolean;
  onClick: () => void;
}) {
  const c = cluster;
  const isUni = UNISEX.has(c.cluster_id);
  const estado = c.params.estado_sensor || 'simulado';
  const stEstado = ESTADO_COLORS[estado] || ESTADO_COLORS.simulado;
  const occ = c.params.ocupacao_instantanea;
  const cap = c.params.capacidade_total || 100;
  const oc = occColor(occ);

  return (
    <div
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      onClick={onClick}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); }}
      style={{
        background: 'white',
        border: isSelected ? `2px solid #1B3A21` : '1px solid var(--color-border)',
        borderLeft: isSelected ? `4px solid #1B3A21` : `4px solid ${stEstado.ring}`,
        borderRadius: 10,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        cursor: 'pointer',
        boxShadow: isSelected ? '0 0 0 3px rgba(27,58,33,0.12)' : 'none',
        transition: 'box-shadow 0.14s, border-color 0.14s',
      }}
    >
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

      {/* Ocupação */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
          <span className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Ocupação instantânea
          </span>
          <span className="serif" style={{ fontSize: 22, fontWeight: 600, color: oc }}>
            {occ}<span style={{ fontSize: 14, color: 'var(--color-muted)', marginLeft: 2 }}>%</span>
          </span>
        </div>
        <div style={{ height: 8, background: '#FAFAF7', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{
            width: `${Math.min(100, occ)}%`, height: '100%',
            background: oc, transition: 'width 0.4s ease',
          }} />
        </div>
        {history && history.occ.length > 1 && (
          <Sparkline values={history.occ} color={oc} height={20} />
        )}
      </div>

      {/* Params grid */}
      <div style={{
        background: '#FAFAF7', borderRadius: 8, padding: 10,
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11,
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

      {/* Footer */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', fontSize: 11,
        color: 'var(--color-muted)', borderTop: '1px dashed var(--color-border)', paddingTop: 8,
      }}>
        <span>Fila <strong style={{ color: 'var(--color-ink)' }}>{c.params.fila_atual ?? '—'}</strong></span>
        <span>Espera <strong style={{ color: 'var(--color-ink)' }}>{c.params.tempo_espera_min ?? '—'} min</strong></span>
        <span className="mono" style={{ fontSize: 10 }}>{fmtTime(c.ts)}</span>
      </div>

      {/* Dica para clicar */}
      <div style={{ fontSize: 10, color: 'var(--color-muted)', textAlign: 'center', opacity: isSelected ? 0 : 0.55 }}>
        Clica para ver detalhe →
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
        <span style={{ fontSize: highlight ? 16 : 13, fontWeight: highlight ? 700 : 600, color: 'var(--color-ink)' }}>
          {value}
        </span>
      </div>
    </div>
  );
}

function Sparkline({ values, color, height = 20 }: { values: number[]; color: string; height?: number }) {
  if (values.length < 2) return null;
  const w = 100; const h = height;
  const min = Math.min(...values); const max = Math.max(...values);
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
