'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useLive, type LiveSnapshot } from '@/components/v2/LiveContext';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

/* ════════════════════════════════════════════════════════════════════
   TIPOS — payload de /api/v1/clusters/geo (fonte de verdade)
   ════════════════════════════════════════════════════════════════════ */

interface GeoCluster {
  id: string;
  e_m: number;
  n_m: number;
  gps_lat: number;
  gps_lon: number;
  type: 'MF' | 'UNI';
  unisex: boolean;
  desc: string;
  cap_m: number | null;
  cap_f: number | null;
  cap: number | null;
  capacity_total: number;
}
interface GeoLandmark { id: string; label: string; e_m: number; n_m: number; kind: string; }
interface GeoPayload {
  anchor_gps: { lat: number; lon: number };
  span_e_m: number;
  span_n_m: number;
  clusters: GeoCluster[];
  landmarks: GeoLandmark[];
  total_clusters: number;
}

/* Fallback em memória — MESMAS coordenadas da fonte de verdade (nunca ecrã vazio) */
const FALLBACK_GEO: GeoPayload = {
  anchor_gps: { lat: 38.78145, lon: -9.0943 },
  span_e_m: 298.5,
  span_n_m: 327.3,
  clusters: [
    { id: 'WC-01', e_m: 215.2, n_m: 327.3, gps_lat: 38.78439, gps_lon: -9.09182, type: 'MF', unisex: false, desc: 'V34 · junto ao Parque P1', cap_m: 72, cap_f: 63, cap: null, capacity_total: 135 },
    { id: 'WC-02', e_m: 256.9, n_m: 286.1, gps_lat: 38.78402, gps_lon: -9.09134, type: 'MF', unisex: false, desc: 'V35 · feminino dominante', cap_m: 54, cap_f: 72, cap: null, capacity_total: 126 },
    { id: 'WC-03', e_m: 268.2, n_m: 194.8, gps_lat: 38.7832, gps_lon: -9.091209, type: 'MF', unisex: false, desc: 'S36 · entrada principal', cap_m: 54, cap_f: 48, cap: null, capacity_total: 102 },
    { id: 'WC-04', e_m: 298.5, n_m: 288.3, gps_lat: 38.78404, gps_lon: -9.09086, type: 'MF', unisex: false, desc: 'S37 · cota +20 m (ADA)', cap_m: 84, cap_f: 66, cap: null, capacity_total: 150 },
    { id: 'WC-05', e_m: 274.2, n_m: 238.2, gps_lat: 38.78359, gps_lon: -9.09114, type: 'UNI', unisex: true, desc: 'M38 · só entrada', cap_m: null, cap_f: null, cap: 133, capacity_total: 133 },
    { id: 'WC-06', e_m: 60.7, n_m: 82.4, gps_lat: 38.78219, gps_lon: -9.093601, type: 'UNI', unisex: true, desc: 'W39/S39 · maior cluster', cap_m: null, cap_f: null, cap: 208, capacity_total: 208 },
    { id: 'WC-07', e_m: 228.2, n_m: 148.1, gps_lat: 38.78278, gps_lon: -9.09167, type: 'MF', unisex: false, desc: 'M40 · cacifos', cap_m: 84, cap_f: 54, cap: null, capacity_total: 138 },
    { id: 'WC-08', e_m: 0.0, n_m: 0.0, gps_lat: 38.78145, gps_lon: -9.0943, type: 'MF', unisex: false, desc: 'V41 · produção', cap_m: 84, cap_f: 61, cap: null, capacity_total: 145 },
  ],
  landmarks: [
    { id: 'ENTRADA', label: 'Entrada Principal', e_m: 290, n_m: 175, kind: 'entrance' },
    { id: 'PALCO_MUNDO', label: 'Palco Mundo', e_m: 70, n_m: 120, kind: 'stage' },
    { id: 'MUSIC_VALLEY', label: 'Music Valley', e_m: 30, n_m: 60, kind: 'stage' },
    { id: 'SUPER_BOCK', label: 'Super Bock', e_m: 120, n_m: 70, kind: 'stage' },
  ],
  total_clusters: 8,
};

/* ════════════════════════════════════════════════════════════════════
   MOTOR DE COORDENADAS — metros → ecrã (§ENGINE)
   ════════════════════════════════════════════════════════════════════ */

const VB = 1000;
const PAD = 0.12 * VB;

function makeEngine(geo: GeoPayload) {
  const spanE = geo.span_e_m;
  const spanN = geo.span_n_m;
  const S = (VB - 2 * PAD) / Math.max(spanE, spanN); // px por metro
  const offX = (VB - 2 * PAD - spanE * S) / 2;
  const offY = (VB - 2 * PAD - spanN * S) / 2;
  const x = (e_m: number) => PAD + offX + e_m * S;
  const y = (n_m: number) => VB - PAD - offY - n_m * S; // inverte Y: Norte em cima
  return { S, x, y };
}

/* ════════════════════════════════════════════════════════════════════
   ESTADO AO VIVO + DISTÂNCIAS
   ════════════════════════════════════════════════════════════════════ */

type State = 'ok' | 'warn' | 'crit';
function occState(occ: number): State {
  if (occ >= 85) return 'crit';
  if (occ >= 65) return 'warn';
  return 'ok';
}
const STATE_VAR: Record<State, string> = {
  ok: 'var(--ok, #6FAF82)',
  warn: 'var(--warn, #D48B3A)',
  crit: 'var(--critical, #C25A1A)',
};
const STATE_LABEL: Record<State, string> = { ok: 'Livre', warn: 'Moderado', crit: 'Cheio' };

function liveOcc(snapshot: LiveSnapshot | null, id: string): number | null {
  const c = snapshot?.clusters?.find((x) => x.cluster_id.toLowerCase() === id.toLowerCase());
  if (!c) return null;
  return Math.round(c.params?.ocupacao_instantanea ?? 0);
}
function distM(a: GeoCluster, b: GeoCluster): number {
  return Math.hypot(a.e_m - b.e_m, a.n_m - b.n_m);
}

/* ════════════════════════════════════════════════════════════════════
   COMPONENTE
   ════════════════════════════════════════════════════════════════════ */

export default function TwinPage() {
  const { snapshot, connection } = useLive();
  const [geo, setGeo] = useState<GeoPayload>(FALLBACK_GEO);
  const [usedFallback, setUsedFallback] = useState(false);
  const [origin, setOrigin] = useState<string | null>(null); // cluster escolhido como "estou aqui"

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/clusters/geo`, { cache: 'no-store' });
        if (!r.ok) throw new Error(String(r.status));
        const j: GeoPayload = await r.json();
        if (!cancelled && j?.clusters?.length) { setGeo(j); setUsedFallback(false); }
      } catch {
        if (!cancelled) setUsedFallback(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const eng = useMemo(() => makeEngine(geo), [geo]);

  // ocupação por cluster
  const occById = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of geo.clusters) {
      const o = liveOcc(snapshot, c.id);
      m.set(c.id, o ?? 0);
    }
    return m;
  }, [geo, snapshot]);

  // recomendação a partir da origem
  const recommendation = useMemo(() => {
    if (!origin) return null;
    const from = geo.clusters.find((c) => c.id === origin);
    if (!from) return null;
    const ranked = geo.clusters
      .filter((c) => c.id !== origin)
      .map((c) => ({ c, d: distM(from, c), occ: occById.get(c.id) ?? 0 }))
      .filter((r) => r.occ < 85)
      .sort((a, b) => a.d - b.d);
    const best = ranked[0] ?? geo.clusters
      .filter((c) => c.id !== origin)
      .map((c) => ({ c, d: distM(from, c), occ: occById.get(c.id) ?? 0 }))
      .sort((a, b) => a.occ - b.occ)[0];
    if (!best) return null;
    const walkMin = Math.max(1, Math.round(best.d / (1.35 * 60)));
    return { from, to: best.c, dist: Math.round(best.d), walkMin, occ: best.occ, allFull: ranked.length === 0 };
  }, [origin, geo, occById]);

  const live = connection === 'sse' || connection === 'polling';
  const scaleBarPx = 100 * eng.S; // 100 metros

  return (
    <div className="tw-root">
      {/* HUD topo */}
      <div className="tw-hud">
        <div>
          <div className="tw-eyebrow">PlantaOS · Digital Twin</div>
          <h1 className="tw-title">Parque Tejo <span className="tw-sub">onde estás · WC mais perto</span></h1>
        </div>
        <div className="tw-conn">
          <span className="tw-conn-dot" style={{ background: live ? 'var(--ok, #6FAF82)' : 'var(--offline, #6B7280)' }} />
          {live ? 'ao vivo' : (usedFallback ? 'a religar…' : 'a ligar…')}
        </div>
      </div>

      {/* MAPA */}
      <div className="tw-map">
        <svg viewBox={`0 0 ${VB} ${VB}`} preserveAspectRatio="xMidYMid meet" className="tw-svg">
          {/* parcela do recinto */}
          <rect
            x={eng.x(0) - 30} y={eng.y(geo.span_n_m) - 30}
            width={(geo.span_e_m * eng.S) + 60} height={(geo.span_n_m * eng.S) + 60}
            rx="28" fill="var(--parcel, #F4F8EC)" stroke="var(--parcel-edge, #C9DDB6)" strokeWidth="2"
          />

          {/* Rio Tejo a sul (parte de baixo) */}
          <rect x="0" y={VB - PAD * 0.55} width={VB} height={PAD * 0.55} fill="var(--water, #BFE0E8)" opacity="0.6" />
          <text x={PAD} y={VB - 14} fontSize="15" fill="var(--ink, #1B3A21)" opacity="0.5" fontStyle="italic">Rio Tejo</text>

          {/* Landmarks (palcos + entrada) */}
          {geo.landmarks.map((l) => (
            <g key={l.id} transform={`translate(${eng.x(l.e_m)}, ${eng.y(l.n_m)})`}>
              <rect x="-46" y="-13" width="92" height="26" rx="13"
                fill={l.kind === 'entrance' ? 'var(--ink, #1B3A21)' : 'rgba(27,58,33,0.08)'}
                stroke={l.kind === 'entrance' ? 'none' : 'var(--parcel-edge, #C9DDB6)'} />
              <text x="0" y="4" fontSize="13" textAnchor="middle"
                fill={l.kind === 'entrance' ? '#fff' : 'var(--ink, #1B3A21)'} fontWeight="600">{l.label}</text>
            </g>
          ))}

          {/* Caminho recomendado */}
          {recommendation && (
            <line
              x1={eng.x(recommendation.from.e_m)} y1={eng.y(recommendation.from.n_m)}
              x2={eng.x(recommendation.to.e_m)} y2={eng.y(recommendation.to.n_m)}
              stroke="var(--route, #4A7C59)" strokeWidth="4" strokeDasharray="10 8" strokeLinecap="round"
              className="tw-route"
            />
          )}

          {/* Clusters */}
          {geo.clusters.map((c, i) => {
            const occ = occById.get(c.id) ?? 0;
            const st = occState(occ);
            const cx = eng.x(c.e_m);
            const cy = eng.y(c.n_m);
            const isOrigin = origin === c.id;
            const isReco = recommendation?.to.id === c.id;
            const r = c.unisex ? 34 : 28;
            return (
              <g key={c.id} transform={`translate(${cx}, ${cy})`} className="tw-node"
                style={{ ['--delay' as any]: `${i * 70}ms`, cursor: 'pointer' }}
                onClick={() => setOrigin(isOrigin ? null : c.id)}>
                {isReco && <circle r={r + 12} fill="none" stroke="var(--route, #4A7C59)" strokeWidth="2.5" opacity="0.7" className="tw-reco-ring" />}
                <circle r={r} fill="#fff" stroke={STATE_VAR[st]} strokeWidth="4"
                  className={st === 'crit' ? 'tw-crit' : ''} />
                <text x="0" y="-2" fontSize={c.unisex ? 16 : 14} textAnchor="middle" fontWeight="700" fill="var(--ink, #1B3A21)">
                  {c.id.replace('WC-', '')}
                </text>
                <text x="0" y="15" fontSize="11" textAnchor="middle" fontWeight="600" fill={STATE_VAR[st]}>
                  {occ}%
                </text>
                {/* etiqueta de tipo */}
                <text x="0" y={r + 16} fontSize="10" textAnchor="middle" fill="var(--ink, #1B3A21)" opacity="0.55">
                  {c.unisex ? 'unissexo' : 'M/F'}
                </text>
                {isOrigin && (
                  <g className="tw-you">
                    <circle r={r + 18} fill="none" stroke="var(--you, #1B3A21)" strokeWidth="3" />
                    <rect x="-44" y={-(r + 42)} width="88" height="24" rx="12" fill="var(--you, #1B3A21)" />
                    <text x="0" y={-(r + 25)} fontSize="12" textAnchor="middle" fill="#fff" fontWeight="700">ESTÁS AQUI</text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Norte */}
          <g transform={`translate(${VB - PAD * 0.7}, ${PAD * 0.7})`}>
            <line x1="0" y1="14" x2="0" y2="-14" stroke="var(--ink, #1B3A21)" strokeWidth="2.5" />
            <polygon points="0,-18 -5,-8 5,-8" fill="var(--ink, #1B3A21)" />
            <text x="0" y="30" fontSize="13" textAnchor="middle" fontWeight="700" fill="var(--ink, #1B3A21)">N</text>
          </g>

          {/* Barra de escala 100 m */}
          <g transform={`translate(${PAD}, ${VB - PAD * 0.62})`}>
            <line x1="0" y1="0" x2={scaleBarPx} y2="0" stroke="var(--ink, #1B3A21)" strokeWidth="3" />
            <line x1="0" y1="-5" x2="0" y2="5" stroke="var(--ink, #1B3A21)" strokeWidth="3" />
            <line x1={scaleBarPx} y1="-5" x2={scaleBarPx} y2="5" stroke="var(--ink, #1B3A21)" strokeWidth="3" />
            <text x={scaleBarPx / 2} y="-9" fontSize="13" textAnchor="middle" fontWeight="600" fill="var(--ink, #1B3A21)">100 metros</text>
          </g>
        </svg>
      </div>

      {/* Faixa inferior: recomendação ou convite */}
      <div className="tw-bar">
        {!origin && (
          <div className="tw-hint">Toca num WC para definires onde estás · mostro-te o mais rápido a partir daí.</div>
        )}
        {origin && recommendation && (
          <div className="tw-reco">
            <div className="tw-reco-from">
              <span className="tw-reco-label">Estás em</span>
              <span className="tw-reco-wc">{recommendation.from.id}</span>
            </div>
            <span className="tw-reco-arrow">→</span>
            <div className="tw-reco-to">
              <span className="tw-reco-label">{recommendation.allFull ? 'Menos cheio' : 'Mais perto e livre'}</span>
              <span className="tw-reco-wc" style={{ color: 'var(--route, #4A7C59)' }}>{recommendation.to.id}</span>
            </div>
            <div className="tw-reco-metrics">
              <span><strong>{recommendation.dist}</strong> m</span>
              <span><strong>{recommendation.walkMin}</strong> min</span>
              <span style={{ color: STATE_VAR[occState(recommendation.occ)] }}>{STATE_LABEL[occState(recommendation.occ)]}</span>
            </div>
            <button className="tw-reco-clear" onClick={() => setOrigin(null)} aria-label="Limpar">✕</button>
          </div>
        )}
      </div>

      <style jsx>{`
        .tw-root {
          position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0;
          display: flex; flex-direction: column; overflow: hidden;
          background: var(--paper, #EAF3DF); color: var(--ink, #1B3A21);
        }
        .tw-hud { flex-shrink: 0; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: clamp(10px,1.4vw,18px) clamp(14px,2.6vw,34px) 0; }
        .tw-eyebrow { font-size: 10px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase; opacity: 0.5; }
        .tw-title { font-size: clamp(20px,2.8vw,36px); font-weight: 800; letter-spacing: -0.03em; line-height: 1; margin-top: 4px; }
        .tw-sub { font-size: 0.42em; font-weight: 500; opacity: 0.55; margin-left: 8px; letter-spacing: 0; }
        .tw-conn { display: flex; align-items: center; gap: 7px; font-size: 12px; font-weight: 600; opacity: 0.7; flex-shrink: 0; }
        .tw-conn-dot { width: 8px; height: 8px; border-radius: 50%; animation: tw-pulse 1.8s ease-in-out infinite; }

        .tw-map { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; padding: 4px clamp(8px,2vw,28px); }
        .tw-svg { width: 100%; height: 100%; max-width: min(92vh, 100%); display: block; }

        .tw-node { animation: tw-pop 0.5s cubic-bezier(0.2,0.7,0.2,1) backwards; animation-delay: var(--delay); }
        .tw-crit { animation: tw-crit-pulse 2s ease-in-out infinite; }
        .tw-reco-ring { animation: tw-pulse 1.6s ease-in-out infinite; }
        .tw-route { animation: tw-dash 0.8s linear infinite; }
        .tw-you { animation: tw-pop 0.4s cubic-bezier(0.2,0.7,0.2,1); }

        .tw-bar { flex-shrink: 0; padding: clamp(10px,1.4vw,16px) clamp(14px,2.6vw,34px) max(14px, env(safe-area-inset-bottom)); }
        .tw-hint { text-align: center; font-size: 14px; opacity: 0.6; }
        .tw-reco { display: flex; align-items: center; gap: clamp(10px,1.6vw,22px); background: #fff; border: 1px solid var(--parcel-edge, #C9DDB6); border-radius: var(--radius, 18px); padding: 12px clamp(14px,2vw,22px); max-width: 760px; margin: 0 auto; box-shadow: var(--shadow, 0 6px 0 rgba(27,58,33,.12)); }
        .tw-reco-from, .tw-reco-to { display: flex; flex-direction: column; gap: 1px; }
        .tw-reco-label { font-size: 9.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.5; }
        .tw-reco-wc { font-size: clamp(16px,1.8vw,22px); font-weight: 800; letter-spacing: -0.02em; }
        .tw-reco-arrow { font-size: 20px; opacity: 0.4; }
        .tw-reco-metrics { display: flex; gap: clamp(10px,1.4vw,18px); margin-left: auto; font-size: clamp(13px,1.4vw,16px); font-variant-numeric: tabular-nums; }
        .tw-reco-metrics strong { font-weight: 800; }
        .tw-reco-clear { background: transparent; border: none; font-size: 16px; cursor: pointer; color: var(--ink, #1B3A21); opacity: 0.4; flex-shrink: 0; }
        .tw-reco-clear:hover { opacity: 1; }

        @keyframes tw-pop { from { opacity: 0; transform: translateY(8px) scale(0.85); } to { opacity: 1; transform: scale(1); } }
        @keyframes tw-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
        @keyframes tw-crit-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.55; } }
        @keyframes tw-dash { to { stroke-dashoffset: -18; } }

        @media (max-width: 560px) {
          .tw-reco { flex-wrap: wrap; gap: 10px; }
          .tw-reco-metrics { width: 100%; margin-left: 0; justify-content: space-between; }
        }
        @media (prefers-reduced-motion: reduce) {
          .tw-node, .tw-you { animation: none; }
          .tw-crit, .tw-reco-ring, .tw-route, .tw-conn-dot { animation: none; }
        }
      `}</style>
    </div>
  );
}
