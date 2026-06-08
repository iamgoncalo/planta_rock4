'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

/* ══════════════════════════════════════════════════════════════════════════
   /v2/flow — Calibração e verificação de fluxos · PlantaOS · RiR Lisboa 2026
   SEM SCROLL. overflow:hidden. 100dvh × 100dvw. Fits 1920×1080 AND 1366×768.
   Dados: GET /api/v1/flow (5s) + WS type:'flow_update'
   ══════════════════════════════════════════════════════════════════════════ */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

const WS_BASE = API_BASE.replace(/^https?/, (p) => (p === 'https' ? 'wss' : 'ws'));

// ── Types ─────────────────────────────────────────────────────────────────

interface Secao {
  cluster_id: string;
  secao: string;
  nome: string;
  unissex: boolean;
  ocupacao_pct: number;
  ocupacao_abs: number;
  fila_actual: number;
  tempo_espera_min: number;
  fluxo_entrada_pmin: number;
  fluxo_saida_pmin: number;
  servico_efetivo_pmin: number;
  confianca_pct: number;
  fontes_activas: string[];
  residual: number;
  deriva: number;
  congestionado: boolean;
  status: string; // 'ok' | 'aviso' | 'critico'
}

interface Kpis {
  kpi_01: number; // índice de fluxo 0-100
  kpi_02: number; // ocupação média %
  kpi_03: number; // alertas críticos
  kpi_04: number; // redireccionados hoje
}

interface Calibracao {
  qualidade_global_pct: number;
  deriva_maxima: number;
  seccoes_calibradas_camara: number;
  seccoes_baixa_confianca: string[];
  seccoes_congestionadas: string[];
}

interface Redirect {
  from: string;
  to: string;
  pax: number;
}

interface FlowData {
  ts: number;
  cor_critica: string;
  kpis: Kpis;
  calibracao: Calibracao;
  routing: Redirect[];
  secoes: Secao[];
}

// ── Helpers ───────────────────────────────────────────────────────────────

function statusColor(s: string): string {
  if (s === 'critico') return '#C25A1A';
  if (s === 'aviso') return '#B08020';
  return '#2E7D4F';
}

function secLabel(sec: Secao): string {
  if (sec.unissex) return sec.cluster_id.toUpperCase();
  return `${sec.cluster_id.toUpperCase()} · ${sec.secao}`;
}

function fonteIcon(f: string): string {
  if (f.includes('ir')) return '╎';
  if (f.includes('wifi')) return '≋';
  if (f.includes('cam')) return '◉';
  return '·';
}

// ── Main component ─────────────────────────────────────────────────────────

export default function FlowPage() {
  const [data, setData] = useState<FlowData | null>(null);
  const [live, setLive] = useState(false);
  const [clock, setClock] = useState('');
  const [reanchorBusy, setReanchorBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const fetchData = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/v1/flow`);
      if (!r.ok) return;
      const d: FlowData = await r.json();
      setData(d);
    } catch {
      // silent — WS or next poll will recover
    }
  }, []);

  // Clock tick
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setClock(now.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Initial fetch + polling every 5s
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(fetchData, 5000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchData]);

  // WebSocket subscription
  useEffect(() => {
    let ws: WebSocket;
    let dead = false;
    const connect = () => {
      if (dead) return;
      try {
        ws = new WebSocket(`${WS_BASE}/api/v1/ws`);
        wsRef.current = ws;
        ws.onopen = () => setLive(true);
        ws.onclose = () => {
          setLive(false);
          if (!dead) setTimeout(connect, 3000);
        };
        ws.onerror = () => ws.close();
        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'flow_update' && msg.data) {
              setData(msg.data as FlowData);
            }
          } catch {/**/}
        };
      } catch {/**/}
    };
    connect();
    return () => {
      dead = true;
      ws?.close();
    };
  }, []);

  const doReanchor = async (cluster_id: string, secao: string, ocupacao_camara: number) => {
    setReanchorBusy(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/flow/reanchor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cluster_id, secao, ocupacao_camara }),
      });
      if (r.ok) {
        showToast(`Re-âncora OK · ${cluster_id}/${secao}`);
        await fetchData();
      } else {
        showToast('Erro na re-âncora');
      }
    } catch {
      showToast('Erro de rede');
    }
    setReanchorBusy(false);
  };

  const kpis = data?.kpis;
  const cal = data?.calibracao;
  const secoes = data?.secoes ?? [];
  const routing = data?.routing ?? [];

  // Sort: critical first, then by cluster_id
  const sorted = [...secoes].sort((a, b) => {
    const order = (s: string) => s === 'critico' ? 0 : s === 'aviso' ? 1 : 2;
    return order(a.status) - order(b.status) || a.cluster_id.localeCompare(b.cluster_id);
  });

  return (
    <div className="fl-root">
      {/* ── KPI strip ─────────────────────────────────────────────────── */}
      <div className="fl-kpi-strip">
        <div className="fl-live-dot">
          <span className={`fl-dot ${live ? 'on' : ''}`} />
          <span className="fl-live-label">{live ? 'LIVE' : 'POLL'}</span>
        </div>
        <div className="fl-clock">{clock}</div>

        {/* kpi_01 — Flow Index gauge */}
        <div className="fl-kpi fl-kpi-gauge">
          <div className="fl-kpi-label">Índice de Fluxo</div>
          <div className="fl-gauge-wrap">
            <div className="fl-gauge-track">
              <div
                className="fl-gauge-fill"
                style={{
                  width: `${kpis?.kpi_01 ?? 0}%`,
                  background: (kpis?.kpi_01 ?? 100) < 40 ? '#C25A1A' : (kpis?.kpi_01 ?? 100) < 70 ? '#B08020' : '#2E7D4F',
                }}
              />
            </div>
            <span className="fl-gauge-num">{kpis?.kpi_01 ?? '—'}</span>
          </div>
        </div>

        {/* Qualidade global calibração — único nesta página */}
        <div className="fl-kpi">
          <div className="fl-kpi-label">Qualidade</div>
          <div className="fl-kpi-val" style={{ color: (cal?.qualidade_global_pct ?? 100) < 40 ? '#C25A1A' : '#0D1A0F' }}>
            {cal?.qualidade_global_pct ?? '—'}<span className="fl-kpi-unit">%</span>
          </div>
        </div>

        {/* kpi_03 — Critical alerts */}
        <div className="fl-kpi">
          <div className="fl-kpi-label">Críticos</div>
          <div className="fl-kpi-val" style={{ color: (kpis?.kpi_03 ?? 0) > 0 ? '#C25A1A' : '#0D1A0F' }}>
            {kpis?.kpi_03 ?? '—'}
          </div>
        </div>

        {/* kpi_04 — Redirected today */}
        <div className="fl-kpi">
          <div className="fl-kpi-label">Redireccionados</div>
          <div className="fl-kpi-val">{kpis?.kpi_04 ?? '—'}</div>
        </div>
      </div>

      {/* ── Body: sections grid (left 8/12) + calibration panel (right 4/12) ── */}
      <div className="fl-body">

        {/* LEFT — 14 section cards */}
        <div className="fl-sections">
          {!data && (
            <div className="fl-loading">A carregar motor de fluxos…</div>
          )}
          <div className="fl-grid">
            {sorted.map((s) => {
              const crit = s.status === 'critico';
              const warn = s.status === 'aviso';
              return (
                <div
                  key={`${s.cluster_id}_${s.secao}`}
                  className={`fl-card ${crit ? 'crit' : warn ? 'warn' : 'ok'}`}
                >
                  <div className="fl-card-head">
                    <span className="fl-card-id">{secLabel(s)}</span>
                    {s.congestionado && (
                      <span className="fl-badge-cong">congest.</span>
                    )}
                    <span
                      className="fl-badge-status"
                      style={{ color: statusColor(s.status) }}
                    >
                      {s.status}
                    </span>
                  </div>

                  {/* Ocupação — secundária, barra fina */}
                  <div className="fl-occ-compact">
                    <div className="fl-occ-cbar">
                      <div
                        className="fl-occ-cfill"
                        style={{
                          width: `${Math.min(100, s.ocupacao_pct)}%`,
                          background: crit ? '#C25A1A' : warn ? '#B08020' : '#2E7D4F',
                        }}
                      />
                    </div>
                    <span
                      className="fl-occ-cpct"
                      style={{ color: crit ? '#C25A1A' : warn ? '#B08020' : '#6B7268' }}
                    >
                      {Math.round(s.ocupacao_pct)}%
                    </span>
                  </div>

                  {/* Fluxos — elemento principal desta página */}
                  <div className="fl-flows-main">
                    <span className="fl-flow-in">↑ {s.fluxo_entrada_pmin.toFixed(1)}<span className="fl-flow-unit">/min</span></span>
                    <span className="fl-flow-out">↓ {s.fluxo_saida_pmin.toFixed(1)}<span className="fl-flow-unit">/min</span></span>
                  </div>

                  {/* Confidence + sources */}
                  <div className="fl-conf-row">
                    <span
                      className="fl-conf-val"
                      style={{ color: s.confianca_pct < 40 ? '#C25A1A' : '#6B7268' }}
                    >
                      {Math.round(s.confianca_pct)}% conf.
                    </span>
                    <span className="fl-sources">
                      {s.fontes_activas.map((f, i) => (
                        <span key={i} title={f}>{fonteIcon(f)}</span>
                      ))}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT — Calibration panel */}
        <div className="fl-cal-panel">
          <div className="fl-cal-title">Calibração</div>

          {/* Routing activo — elemento mais único desta página, topo do painel */}
          <div className="fl-cal-section-label" style={{ marginTop: 0 }}>
            Redistribuição activa
          </div>
          {routing.length > 0 ? (
            <div className="fl-routing-list">
              {routing.slice(0, 6).map((r, i) => (
                <div key={i} className="fl-route-row">
                  <span className="fl-route-from">{r.from}</span>
                  <span className="fl-route-arrow">→</span>
                  <span className="fl-route-to">{r.to}</span>
                  <span className="fl-route-pax">{r.pax} pax</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="fl-cal-ok">Sem redistribuições activas</div>
          )}

          {/* Global quality */}
          {cal && (
            <div className="fl-cal-qual">
              <span>Qualidade global</span>
              <strong style={{ color: cal.qualidade_global_pct < 40 ? '#C25A1A' : '#1B3A21' }}>
                {cal.qualidade_global_pct}%
              </strong>
            </div>
          )}

          {/* Residual continuity bars */}
          <div className="fl-cal-section-label">Resíduo continuidade (IR − câmara)</div>
          <div className="fl-residuals">
            {sorted.slice(0, 10).map((s) => {
              const r = s.residual;
              const abs = Math.abs(r);
              const maxR = 20;
              const pct = Math.min(100, (abs / maxR) * 100);
              return (
                <div key={`${s.cluster_id}_${s.secao}`} className="fl-res-row">
                  <span className="fl-res-label">{secLabel(s)}</span>
                  <div className="fl-res-track">
                    <div
                      className="fl-res-bar"
                      style={{
                        width: `${pct}%`,
                        background: abs > 10 ? '#C25A1A' : abs > 5 ? '#B08020' : '#2E7D4F',
                        marginLeft: r < 0 ? `${50 - pct / 2}%` : '50%',
                      }}
                    />
                    <div className="fl-res-center" />
                  </div>
                  <span className="fl-res-val">{r > 0 ? '+' : ''}{r.toFixed(1)}</span>
                </div>
              );
            })}
          </div>

          {/* Drift + Re-anchor */}
          <div className="fl-cal-section-label">
            Deriva máx.{' '}
            <strong style={{ color: (cal?.deriva_maxima ?? 0) > 15 ? '#C25A1A' : '#0D1A0F' }}>
              {cal?.deriva_maxima?.toFixed(1) ?? '—'}
            </strong>
          </div>
          <div className="fl-drift-list">
            {sorted
              .filter((s) => s.deriva > 2)
              .slice(0, 5)
              .map((s) => (
                <div key={`${s.cluster_id}_${s.secao}`} className="fl-drift-row">
                  <span className="fl-drift-id">{secLabel(s)}</span>
                  <span
                    className="fl-drift-val"
                    style={{ color: s.deriva > 10 ? '#C25A1A' : '#B08020' }}
                  >
                    {s.deriva.toFixed(1)} pess.
                  </span>
                  <button
                    className="fl-reanchor-btn"
                    disabled={reanchorBusy}
                    onClick={() => doReanchor(s.cluster_id, s.secao, s.ocupacao_abs)}
                    title="Re-âncora com valor da câmara"
                  >
                    ↺
                  </button>
                </div>
              ))}
            {sorted.filter((s) => s.deriva > 2).length === 0 && (
              <div className="fl-cal-ok">Deriva dentro do normal</div>
            )}
          </div>

          {/* Active sources health */}
          <div className="fl-cal-section-label">Fontes activas por secção</div>
          <div className="fl-sources-list">
            {sorted.slice(0, 8).map((s) => (
              <div key={`${s.cluster_id}_${s.secao}`} className="fl-src-row">
                <span className="fl-src-id">{secLabel(s)}</span>
                <span className="fl-src-icons">
                  {s.fontes_activas.length === 0 ? (
                    <span style={{ color: '#C25A1A' }}>sem fontes</span>
                  ) : (
                    s.fontes_activas.map((f, i) => (
                      <span key={i} className="fl-src-badge">{f}</span>
                    ))
                  )}
                </span>
              </div>
            ))}
          </div>

          {/* Routing block moved to top of panel */}
        </div>
      </div>

      {/* Toast */}
      {toast && <div className="fl-toast">{toast}</div>}

      <style jsx>{`
        /* ── Root: no-scroll container ── */
        .fl-root {
          position: fixed;
          top: var(--header-h, 72px);
          left: 0; right: 0;
          bottom: calc(var(--searchbar-h, 88px) + 24px);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          background: var(--bg-soft, #FAFAF8);
          font-family: var(--font-sans, 'Inter', system-ui, sans-serif);
          color: var(--ink, #0D1A0F);
        }

        /* ── KPI strip ── */
        .fl-kpi-strip {
          flex-shrink: 0;
          height: 52px;
          display: flex;
          align-items: center;
          gap: clamp(8px, 1.2vw, 20px);
          padding: 0 clamp(10px, 1.5vw, 24px);
          background: #fff;
          border-bottom: 1px solid #ECE9E2;
        }

        .fl-live-dot { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
        .fl-dot {
          width: 8px; height: 8px; border-radius: 50%;
          background: #B7B9B0;
          transition: background .3s;
        }
        .fl-dot.on {
          background: #2E7D4F;
          box-shadow: 0 0 0 3px rgba(46,125,79,.18), 0 0 8px rgba(46,125,79,.4);
        }
        .fl-live-label {
          font-size: 10px; font-weight: 700;
          letter-spacing: .07em; color: #6B7268;
        }
        .fl-clock {
          font-size: clamp(11px, .9vw, 13px);
          font-variant-numeric: tabular-nums;
          color: #6B7268;
          font-family: var(--font-mono, monospace);
          flex-shrink: 0;
        }

        .fl-kpi {
          display: flex; flex-direction: column;
          gap: 2px; flex-shrink: 0;
          border-left: 1px solid #ECE9E2;
          padding-left: clamp(8px, 1vw, 16px);
        }
        .fl-kpi-label {
          font-size: clamp(9px, .7vw, 11px);
          font-weight: 700; text-transform: uppercase;
          letter-spacing: .06em; color: #6B7268;
          white-space: nowrap;
        }
        .fl-kpi-val {
          font-size: clamp(18px, 1.6vw, 26px);
          font-weight: 700; line-height: 1;
          font-variant-numeric: tabular-nums;
        }
        .fl-kpi-unit { font-size: .6em; font-weight: 400; margin-left: 1px; }

        /* kpi_01 gauge */
        .fl-kpi-gauge { min-width: clamp(90px, 8vw, 130px); }
        .fl-gauge-wrap { display: flex; align-items: center; gap: 6px; }
        .fl-gauge-track {
          flex: 1; height: 6px;
          background: #ECE9E2; border-radius: 3px; overflow: hidden;
        }
        .fl-gauge-fill {
          height: 100%; border-radius: 3px;
          transition: width .6s ease, background .4s;
        }
        .fl-gauge-num {
          font-size: clamp(14px, 1.2vw, 18px);
          font-weight: 700; font-variant-numeric: tabular-nums;
          flex-shrink: 0;
        }

        /* ── Body ── */
        .fl-body {
          flex: 1;
          display: flex;
          overflow: hidden;
          gap: 0;
        }

        /* ── Left: sections grid ── */
        .fl-sections {
          flex: 0 0 67%;
          overflow: hidden;
          padding: clamp(6px, .8vw, 12px);
          border-right: 1px solid #ECE9E2;
        }

        .fl-loading {
          padding: 20px; text-align: center;
          color: #6B7268; font-size: 13px;
        }

        .fl-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: clamp(4px, .5vw, 8px);
          height: 100%;
          align-content: start;
        }

        .fl-card {
          background: #fff;
          border: 1px solid #ECE9E2;
          border-radius: 8px;
          padding: clamp(5px, .6vw, 9px) clamp(6px, .7vw, 10px);
          display: flex; flex-direction: column;
          gap: clamp(2px, .25vw, 4px);
          overflow: hidden;
          transition: border-color .2s;
        }
        .fl-card.crit {
          border-color: #C25A1A;
          background: linear-gradient(180deg, #FFF6F1 0%, #fff 100%);
        }
        .fl-card.warn {
          border-color: #D4A020;
          background: linear-gradient(180deg, #FFFBF0 0%, #fff 100%);
        }

        .fl-card-head {
          display: flex; align-items: center;
          gap: 4px; flex-wrap: wrap;
        }
        .fl-card-id {
          font-size: clamp(9px, .7vw, 11px);
          font-weight: 700; font-family: monospace;
          color: #0D1A0F; flex: 1;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .fl-badge-cong {
          font-size: 8px; font-weight: 700;
          background: #FFF0E0; color: #C25A1A;
          border: 1px solid #F0C080;
          border-radius: 3px; padding: 0 3px;
          text-transform: uppercase; letter-spacing: .03em;
          flex-shrink: 0;
        }
        .fl-badge-status {
          font-size: 8px; font-weight: 700;
          text-transform: uppercase; letter-spacing: .04em;
          flex-shrink: 0;
        }

        .fl-occ-row {
          display: flex; align-items: baseline; gap: 2px;
        }
        .fl-occ-num {
          font-size: clamp(18px, 1.8vw, 28px);
          font-weight: 700; line-height: 1;
          font-variant-numeric: tabular-nums;
        }
        .fl-occ-unit {
          font-size: clamp(9px, .7vw, 11px);
          color: #6B7268; margin-right: 4px;
        }
        .fl-occ-bar {
          flex: 1; height: 4px;
          background: #ECE9E2; border-radius: 2px; overflow: hidden;
          align-self: center;
        }
        .fl-occ-fill {
          height: 100%; border-radius: 2px;
          transition: width .5s ease;
        }

        /* Occupancy compact (secondary) */
        .fl-occ-compact {
          display: flex; align-items: center; gap: 5px;
        }
        .fl-occ-cbar {
          flex: 1; height: 3px;
          background: #ECE9E2; border-radius: 2px; overflow: hidden;
        }
        .fl-occ-cfill { height: 100%; border-radius: 2px; transition: width .5s ease; }
        .fl-occ-cpct {
          font-size: clamp(8px, .62vw, 10px); font-weight: 700;
          font-variant-numeric: tabular-nums; flex-shrink: 0;
        }

        /* Fluxos — elemento principal do card */
        .fl-flows-main {
          display: flex; gap: 8px;
          font-size: clamp(11px, .9vw, 14px);
          font-weight: 600;
          font-variant-numeric: tabular-nums;
        }
        .fl-flow-in { color: #2E7D4F; }
        .fl-flow-out { color: #6B7268; }
        .fl-flow-unit { font-weight: 400; font-size: .82em; }

        .fl-conf-row {
          display: flex; justify-content: space-between; align-items: center;
          font-size: clamp(8px, .6vw, 10px);
        }
        .fl-conf-val { font-weight: 600; }
        .fl-sources {
          display: flex; gap: 3px;
          font-size: 10px; color: #6B7268;
        }

        /* ── Right: calibration panel ── */
        .fl-cal-panel {
          flex: 0 0 33%;
          overflow-y: auto;
          overflow-x: hidden;
          padding: clamp(8px, .9vw, 14px);
          display: flex; flex-direction: column; gap: 8px;
          scrollbar-width: thin;
          scrollbar-color: #ECE9E2 transparent;
        }

        .fl-cal-title {
          font-size: clamp(11px, .85vw, 14px);
          font-weight: 700; text-transform: uppercase;
          letter-spacing: .07em; color: #6B7268;
          border-bottom: 1px solid #ECE9E2;
          padding-bottom: 6px; flex-shrink: 0;
        }

        .fl-cal-qual {
          display: flex; justify-content: space-between;
          align-items: center;
          font-size: clamp(11px, .8vw, 13px);
          padding: 4px 0;
          border-bottom: 1px solid #ECE9E2;
        }

        .fl-cal-section-label {
          font-size: clamp(9px, .68vw, 11px);
          font-weight: 700; text-transform: uppercase;
          letter-spacing: .06em; color: #6B7268;
          margin-top: 4px;
        }

        /* Residual bars */
        .fl-residuals { display: flex; flex-direction: column; gap: 3px; }
        .fl-res-row {
          display: flex; align-items: center; gap: 5px;
          font-size: clamp(8px, .63vw, 10px);
        }
        .fl-res-label {
          flex: 0 0 60px; font-family: monospace;
          font-size: clamp(7px, .58vw, 9px);
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .fl-res-track {
          flex: 1; height: 6px; background: #F0EFE8;
          border-radius: 3px; position: relative; overflow: hidden;
        }
        .fl-res-bar {
          position: absolute; top: 0; height: 100%;
          border-radius: 2px; transition: width .4s;
          min-width: 2px;
        }
        .fl-res-center {
          position: absolute; top: 0; bottom: 0;
          left: 50%; width: 1px; background: #C9C6BD;
        }
        .fl-res-val {
          flex: 0 0 28px; text-align: right;
          font-variant-numeric: tabular-nums;
          font-size: clamp(7px, .58vw, 9px);
          font-weight: 600;
        }

        /* Drift */
        .fl-drift-list { display: flex; flex-direction: column; gap: 3px; }
        .fl-drift-row {
          display: flex; align-items: center; gap: 5px;
          font-size: clamp(9px, .68vw, 11px);
        }
        .fl-drift-id {
          flex: 1; font-family: monospace;
          font-size: clamp(8px, .62vw, 10px);
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .fl-drift-val { font-weight: 600; flex-shrink: 0; }
        .fl-reanchor-btn {
          background: #1B3A21; color: #fff;
          border: none; border-radius: 4px;
          width: 22px; height: 22px;
          font-size: 13px; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
          transition: background .14s;
        }
        .fl-reanchor-btn:hover { background: #2A5232; }
        .fl-reanchor-btn:disabled { background: #B7B9B0; cursor: not-allowed; }
        .fl-cal-ok { font-size: 11px; color: #2E7D4F; font-weight: 600; }

        /* Sources health */
        .fl-sources-list { display: flex; flex-direction: column; gap: 3px; }
        .fl-src-row {
          display: flex; align-items: flex-start; gap: 5px;
          font-size: clamp(8px, .63vw, 10px);
        }
        .fl-src-id {
          flex: 0 0 65px; font-family: monospace;
          font-size: clamp(7px, .58vw, 9px);
          overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .fl-src-icons { display: flex; flex-wrap: wrap; gap: 3px; }
        .fl-src-badge {
          font-size: clamp(7px, .55vw, 9px);
          font-weight: 600; padding: 1px 4px;
          background: #EDF4EF; color: #1B3A21;
          border-radius: 3px; white-space: nowrap;
        }

        /* Routing */
        .fl-routing-list { display: flex; flex-direction: column; gap: 4px; }
        .fl-route-row {
          display: flex; align-items: center; gap: 5px;
          font-size: clamp(9px, .68vw, 11px);
          background: #F5F8F5; border-radius: 5px;
          padding: 4px 6px;
        }
        .fl-route-from, .fl-route-to {
          font-family: monospace; font-weight: 700;
          font-size: clamp(8px, .63vw, 10px);
        }
        .fl-route-arrow { color: #6B7268; }
        .fl-route-pax {
          margin-left: auto; font-size: clamp(8px, .63vw, 10px);
          font-weight: 600; color: #6B7268;
          font-variant-numeric: tabular-nums;
        }

        /* Toast */
        .fl-toast {
          position: fixed; bottom: calc(var(--searchbar-h, 88px) + 32px);
          left: 50%; transform: translateX(-50%);
          background: #1B3A21; color: #fff;
          padding: 9px 16px; border-radius: 8px;
          font-size: 13px; z-index: 200;
          box-shadow: 0 6px 20px rgba(0,0,0,.18);
          pointer-events: none;
        }

        /* Scrollbar cal panel */
        .fl-cal-panel::-webkit-scrollbar { width: 4px; }
        .fl-cal-panel::-webkit-scrollbar-track { background: transparent; }
        .fl-cal-panel::-webkit-scrollbar-thumb { background: #ECE9E2; border-radius: 2px; }

        /* 1366×768 tight fit */
        @media (max-width: 1400px) {
          .fl-grid { grid-template-columns: repeat(4, 1fr); }
        }
        @media (max-width: 1100px) {
          .fl-sections { flex: 0 0 60%; }
          .fl-cal-panel { flex: 0 0 40%; }
          .fl-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 800px) {
          .fl-body { flex-direction: column; overflow-y: auto; }
          .fl-sections { flex: none; overflow: visible; border-right: none; border-bottom: 1px solid #ECE9E2; }
          .fl-cal-panel { flex: none; overflow: visible; }
          .fl-grid { grid-template-columns: repeat(2, 1fr); }
        }
      `}</style>
    </div>
  );
}
