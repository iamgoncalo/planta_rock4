'use client';

import { useEffect, useCallback, useState, useRef } from 'react';

/* ══════════════════════════════════════════════════════════════════════════
   /v2/install — Diagnóstico de instalação · PlantaOS · RiR Lisboa 2026
   SEM SCROLL. position:fixed. 8 cluster cards × fontes online/offline.
   Click LilyGo → painel lateral com info do .ino.
   ══════════════════════════════════════════════════════════════════════════ */

const API = process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

// ── Tipos ──────────────────────────────────────────────────────────────────

interface IngestCluster {
  data_source: 'real' | 'stale' | 'none';
  age_s: number | null;
  ts_device: number | null;
  portas_ativas: string[];
}

interface IngestStatus {
  data_ttl_s: number;
  clusters: Record<string, IngestCluster>;
}

interface SensorHealth {
  last_seen: string | null;
  status: string;
  last_rssi_dbm: number | null;
  last_uptime_s: number | null;
  events_today: number | null;
}

interface SensorRec {
  id: string;
  cluster_id: string;
  type: string;
  model: string | null;
  location_desc: string | null;
  health: SensorHealth | null;
}

interface SourceDef {
  key: string;
  label: string;
  type: 'lilygo' | 'camera' | 'prosegur';
  porta: string | null;
  secao: string | null;
  ino: string | null;
  etiqueta: string;
}

interface ClusterDef {
  id: string;
  num: string;
  mf: boolean;
  sources: SourceDef[];
  lat: number;
  lon: number;
}

// ── Definição estática dos clusters ───────────────────────────────────────

function mfSources(num: string): SourceDef[] {
  const n = num.padStart(2, '0');
  return [
    { key:`LL_m`, label:'LLH',     type:'lilygo',   porta:'LL', secao:'m', ino:`wc${n}_h_ll.ino`,   etiqueta:`WC-${n}_M_LL` },
    { key:`LR_m`, label:'LRH',     type:'lilygo',   porta:'LR', secao:'m', ino:`wc${n}_h_lr.ino`,   etiqueta:`WC-${n}_M_LR` },
    { key:`LL_f`, label:'LLW',     type:'lilygo',   porta:'LL', secao:'f', ino:`wc${n}_w_ll.ino`,   etiqueta:`WC-${n}_F_LL` },
    { key:`LR_f`, label:'LRW',     type:'lilygo',   porta:'LR', secao:'f', ino:`wc${n}_w_lr.ino`,   etiqueta:`WC-${n}_F_LR` },
    { key:`C_m`,  label:'LC',      type:'lilygo',   porta:'C',  secao:'m', ino:`wc${n}_center.ino`, etiqueta:`WC-${n}_M_C`  },
    { key:`lux`,  label:'Luxonis', type:'camera',   porta:null, secao:null, ino:null, etiqueta:'' },
    { key:`pro`,  label:'Prosegur',type:'prosegur', porta:null, secao:null, ino:null, etiqueta:'' },
  ];
}

function uniSources(num: string): SourceDef[] {
  const n = num.padStart(2, '0');
  return [
    { key:`uni_a`, label:'UNI-A',   type:'lilygo',   porta:'', secao:'u', ino:`wc${n}_a.ino`, etiqueta:`WC-${n}_U_A` },
    { key:`uni_b`, label:'UNI-B',   type:'lilygo',   porta:'', secao:'u', ino:`wc${n}_b.ino`, etiqueta:`WC-${n}_U_B` },
    { key:`pro`,   label:'Prosegur',type:'prosegur', porta:null, secao:null, ino:null, etiqueta:'' },
  ];
}

const CLUSTERS: ClusterDef[] = [
  { id:'wc-01', num:'01', mf:true,  sources:mfSources('01'), lat:38.78439, lon:-9.09182 },
  { id:'wc-02', num:'02', mf:true,  sources:mfSources('02'), lat:38.78406, lon:-9.09143 },
  { id:'wc-03', num:'03', mf:true,  sources:mfSources('03'), lat:38.78320, lon:-9.09132 },
  { id:'wc-04', num:'04', mf:true,  sources:mfSources('04'), lat:38.78407, lon:-9.09111 },
  { id:'wc-05', num:'05', mf:false, sources:uniSources('05'), lat:38.78360, lon:-9.09121 },
  { id:'wc-06', num:'06', mf:false, sources:uniSources('06'), lat:38.78220, lon:-9.09364 },
  { id:'wc-07', num:'07', mf:true,  sources:mfSources('07'), lat:38.78279, lon:-9.09264 },
  { id:'wc-08', num:'08', mf:true,  sources:mfSources('08'), lat:38.78145, lon:-9.09430 },
];

// ── Painel de detalhe ──────────────────────────────────────────────────────

interface PanelSel {
  cluster: ClusterDef;
  source: SourceDef;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtAge(s: number | null): string {
  if (s === null) return '—';
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s/60)}min`;
  return `${Math.round(s/3600)}h`;
}

function secaoLabel(s: string | null): string {
  if (s === 'm') return 'Masculina';
  if (s === 'f') return 'Feminina';
  if (s === 'u') return 'Unissexo';
  return s || '—';
}

function copyText(text: string, onDone: () => void) {
  navigator.clipboard.writeText(text).then(onDone).catch(() => {});
}

// ── Componente principal ───────────────────────────────────────────────────

export default function InstallPage() {
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [sensors, setSensors] = useState<SensorRec[]>([]);
  const [panel, setPanel] = useState<PanelSel | null>(null);
  const [copied, setCopied] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const tickRef = useRef(0);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/ingest/status`, { cache: 'no-store' });
      if (r.ok) { setStatus(await r.json()); setLastUpdate(new Date()); }
    } catch {}
  }, []);

  const fetchSensors = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/sensors?limit=200`, { cache: 'no-store' });
      if (r.ok) {
        const d = await r.json();
        setSensors(d.sensors || d.data || []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchSensors();
    const t = setInterval(() => { fetchStatus(); tickRef.current++; }, 5000);
    const t2 = setInterval(() => fetchSensors(), 30_000);
    return () => { clearInterval(t); clearInterval(t2); };
  }, [fetchStatus, fetchSensors]);

  // ── Online logic ──────────────────────────────────────────────────────

  function isOnline(cid: string, src: SourceDef): boolean {
    const cl = status?.clusters[cid];
    if (!cl) return false;
    if (src.type === 'lilygo') {
      if (src.porta === '' || !src.porta) {
        // unisex: online se cluster tiver dado real recente
        return cl.data_source === 'real';
      }
      const pk = `${src.porta}_${src.secao}`;
      return cl.portas_ativas.includes(pk);
    }
    if (src.type === 'camera') {
      return sensors.some(s =>
        s.cluster_id === cid &&
        (s.type === 'camera' || s.type === 'luxonis' || s.type === 'oak') &&
        s.health?.status === 'online'
      );
    }
    if (src.type === 'prosegur') {
      return sensors.some(s =>
        s.cluster_id === cid &&
        (s.type === 'prosegur' || s.type === 'contagem') &&
        s.health?.status === 'online'
      );
    }
    return false;
  }

  function clusterOnlineCount(c: ClusterDef): number {
    return c.sources.filter(s => isOnline(c.id, s)).length;
  }

  function clusterAgeS(cid: string): number | null {
    return status?.clusters[cid]?.age_s ?? null;
  }

  // ── Painel lateral ────────────────────────────────────────────────────

  function openPanel(cluster: ClusterDef, source: SourceDef) {
    if (source.type !== 'lilygo') return;
    setPanel({ cluster, source });
    setCopied(false);
  }

  function closePanel() { setPanel(null); }

  function inoHeader(c: ClusterDef, s: SourceDef): string {
    return [
      `/* ETIQUETA: ${s.etiqueta}`,
      ` * cluster_id = "${c.id}"`,
      s.porta ? ` * porta      = "${s.porta}"` : ` * porta      = "" (unissexo)`,
      ` * secao      = "${s.secao}"`,
      ` * IR_A       = GPIO36 (VP)  exterior`,
      ` * IR_B       = IO33         interior`,
      ` * A->B       = entrada    B->A = saida`,
      ` * debounce   = -10000`,
      ` */`,
    ].join('\n');
  }

  const panelCluster = panel ? status?.clusters[panel.cluster.id] : null;
  const panelOnline = panel ? isOnline(panel.cluster.id, panel.source) : false;

  // ── Contagem global ───────────────────────────────────────────────────

  const totalSources = CLUSTERS.reduce((a, c) => a + c.sources.length, 0);
  const totalOnline  = CLUSTERS.reduce((a, c) => a + clusterOnlineCount(c), 0);

  return (
    <div className="in-root">
      {/* Header strip */}
      <div className="in-header">
        <div className="in-header-left">
          <span className="in-title">Instalação · RiR2026</span>
          <span className="in-subtitle">firmware Opção A · GPIO36/IO33</span>
        </div>
        <div className="in-header-right">
          <span className={`in-global-dot ${totalOnline > 0 ? 'in-dot-green' : 'in-dot-grey'}`} />
          <span className="in-global-count">{totalOnline}/{totalSources} activas</span>
          {lastUpdate && (
            <span className="in-last-update">há {fmtAge((Date.now() - lastUpdate.getTime()) / 1000)}</span>
          )}
        </div>
      </div>

      {/* Grid 2×4 */}
      <div className="in-grid">
        {CLUSTERS.map(c => {
          const online = clusterOnlineCount(c);
          const total  = c.sources.length;
          const cl     = status?.clusters[c.id];
          const fresh  = cl?.data_source === 'real';
          const age    = clusterAgeS(c.id);
          return (
            <div
              key={c.id}
              className={`in-card ${fresh ? 'in-card-live' : ''}`}
            >
              <div className="in-card-head">
                <span className="in-card-id">{c.id.toUpperCase()}</span>
                <span className={`in-card-badge ${c.mf ? 'in-badge-mf' : 'in-badge-uni'}`}>
                  {c.mf ? 'M/F' : 'UNI'}
                </span>
                <span className="in-card-geo">{c.lat.toFixed(4)}°N · {Math.abs(c.lon).toFixed(4)}°W</span>
                <span className="in-card-count">
                  <span className={`in-dot-sm ${online > 0 ? 'in-dot-green' : 'in-dot-grey'}`} />
                  {online}/{total}
                </span>
                {age !== null && (
                  <span className={`in-card-age ${fresh ? 'in-age-fresh' : 'in-age-stale'}`}>
                    {fmtAge(age)}
                  </span>
                )}
              </div>
              <div className="in-sources">
                {c.sources.map(src => {
                  const on = isOnline(c.id, src);
                  const clickable = src.type === 'lilygo';
                  return (
                    <button
                      key={src.key}
                      className={`in-chip ${on ? 'in-chip-on' : 'in-chip-off'} ${clickable ? 'in-chip-click' : ''} ${panel?.source.key === src.key && panel?.cluster.id === c.id ? 'in-chip-active' : ''}`}
                      onClick={() => clickable ? openPanel(c, src) : undefined}
                      title={clickable ? `${src.etiqueta} — clique para detalhes` : src.label}
                    >
                      <span className={`in-dot ${on ? 'in-dot-pulse' : ''}`} />
                      <span className="in-chip-label">{src.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Side panel */}
      {panel && (
        <div className="in-panel-overlay" onClick={closePanel}>
          <div className="in-panel" onClick={e => e.stopPropagation()}>
            <div className="in-panel-header">
              <div>
                <div className="in-panel-etiqueta">{panel.source.etiqueta}</div>
                <div className="in-panel-sub">
                  <span className={`in-dot-sm ${panelOnline ? 'in-dot-green in-dot-pulse' : 'in-dot-grey'}`} />
                  {panelOnline ? 'Online' : 'Offline'}
                </div>
              </div>
              <button className="in-panel-close" onClick={closePanel}>✕</button>
            </div>

            <div className="in-panel-body">
              <div className="in-panel-section">
                <div className="in-panel-row">
                  <span className="in-panel-k">cluster_id</span>
                  <span className="in-panel-v">{panel.cluster.id}</span>
                </div>
                {panel.source.porta && (
                  <div className="in-panel-row">
                    <span className="in-panel-k">porta</span>
                    <span className="in-panel-v in-mono">{panel.source.porta}</span>
                  </div>
                )}
                <div className="in-panel-row">
                  <span className="in-panel-k">secção</span>
                  <span className="in-panel-v">{secaoLabel(panel.source.secao)}</span>
                </div>
                <div className="in-panel-row">
                  <span className="in-panel-k">IR A (exterior)</span>
                  <span className="in-panel-v in-mono in-pin">GPIO36 (VP)</span>
                </div>
                <div className="in-panel-row">
                  <span className="in-panel-k">IR B (interior)</span>
                  <span className="in-panel-v in-mono in-pin">IO33</span>
                </div>
                <div className="in-panel-row">
                  <span className="in-panel-k">debounce</span>
                  <span className="in-panel-v in-mono">-10000 µs</span>
                </div>
                <div className="in-panel-row">
                  <span className="in-panel-k">A→B</span>
                  <span className="in-panel-v">entrada &nbsp;·&nbsp; B→A saída</span>
                </div>
              </div>

              {panel.source.ino && (
                <div className="in-panel-section">
                  <div className="in-panel-section-title">Ficheiro</div>
                  <div className="in-panel-row">
                    <span className="in-panel-k">firmware</span>
                    <span className="in-panel-v in-mono">{panel.source.ino}</span>
                  </div>
                  <div className="in-panel-code">
                    <pre>{inoHeader(panel.cluster, panel.source)}</pre>
                    <button
                      className={`in-copy-btn ${copied ? 'in-copy-done' : ''}`}
                      onClick={() => copyText(inoHeader(panel.cluster, panel.source), () => { setCopied(true); setTimeout(() => setCopied(false), 2000); })}
                    >
                      {copied ? '✓ copiado' : 'copiar'}
                    </button>
                  </div>
                </div>
              )}

              {panelCluster && (
                <div className="in-panel-section">
                  <div className="in-panel-section-title">Dados ao vivo</div>
                  {panelCluster.data_source === 'none' ? (
                    <div className="in-panel-empty">Sem dados recebidos ainda</div>
                  ) : (
                    <>
                      <div className="in-panel-row">
                        <span className="in-panel-k">fonte</span>
                        <span className={`in-panel-v ${panelCluster.data_source === 'real' ? 'in-v-green' : 'in-v-amber'}`}>
                          {panelCluster.data_source}
                        </span>
                      </div>
                      <div className="in-panel-row">
                        <span className="in-panel-k">último sinal</span>
                        <span className="in-panel-v">{fmtAge(panelCluster.age_s)} atrás</span>
                      </div>
                      {panelCluster.portas_ativas.length > 0 && (
                        <div className="in-panel-row">
                          <span className="in-panel-k">portas activas</span>
                          <span className="in-panel-v in-mono">{panelCluster.portas_ativas.join(', ')}</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        /* ── Root no-scroll ── */
        .in-root {
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

        /* ── Header strip ── */
        .in-header {
          flex-shrink: 0;
          height: 46px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 clamp(10px, 1.5vw, 24px);
          background: #fff;
          border-bottom: 1px solid var(--border, #ECE9E2);
        }
        .in-header-left { display: flex; align-items: baseline; gap: 12px; }
        .in-title {
          font-size: clamp(13px, 1vw, 15px);
          font-weight: 600;
          letter-spacing: -0.02em;
          color: var(--ink, #0D1A0F);
        }
        .in-subtitle {
          font-size: 11px;
          color: var(--muted, #6B7268);
          font-family: 'DM Mono', monospace;
        }
        .in-header-right { display: flex; align-items: center; gap: 10px; }
        .in-global-count { font-size: 12px; font-weight: 500; }
        .in-last-update { font-size: 11px; color: var(--muted, #6B7268); }

        /* ── Dots ── */
        .in-global-dot, .in-dot-sm {
          display: inline-block;
          width: 8px; height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .in-dot-green { background: #4A7C59; }
        .in-dot-grey  { background: #C9CEC4; }
        .in-dot-pulse {
          background: #4A7C59;
          box-shadow: 0 0 0 0 rgba(74,124,89,0.5);
          animation: pulse-ring 2s ease-out infinite;
        }
        @keyframes pulse-ring {
          0%   { box-shadow: 0 0 0 0   rgba(74,124,89,0.5); }
          70%  { box-shadow: 0 0 0 5px rgba(74,124,89,0);   }
          100% { box-shadow: 0 0 0 0   rgba(74,124,89,0);   }
        }
        .in-dot {
          display: inline-block;
          width: 7px; height: 7px;
          border-radius: 50%;
          background: #C9CEC4;
          flex-shrink: 0;
          transition: background 0.3s;
        }
        .in-dot-pulse { background: #4A7C59; }

        /* ── Grid ── */
        .in-grid {
          flex: 1;
          min-height: 0;
          display: grid;
          grid-template-columns: 1fr 1fr;
          grid-template-rows: repeat(4, 1fr);
          gap: clamp(4px, 0.5vw, 8px);
          padding: clamp(4px, 0.5vw, 8px);
          overflow: hidden;
        }

        /* ── Card ── */
        .in-card {
          background: #fff;
          border: 1px solid var(--border, #ECE9E2);
          border-radius: 8px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          transition: border-color 0.4s, box-shadow 0.4s;
          min-height: 0;
        }
        .in-card-live {
          border-color: rgba(74,124,89,0.35);
          box-shadow: 0 0 0 1px rgba(74,124,89,0.12);
        }

        /* ── Card header ── */
        .in-card-head {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          gap: 7px;
          padding: clamp(5px, 0.6vh, 9px) clamp(8px, 0.8vw, 12px);
          border-bottom: 1px solid var(--border, #ECE9E2);
          background: var(--bg-soft, #FAFAF8);
          overflow: hidden;
        }
        .in-card-id {
          font-size: clamp(11px, 0.85vw, 13px);
          font-weight: 700;
          letter-spacing: -0.01em;
          flex-shrink: 0;
        }
        .in-card-badge {
          font-size: 9px;
          font-weight: 600;
          padding: 1px 5px;
          border-radius: 3px;
          flex-shrink: 0;
        }
        .in-badge-mf  { background: #EDF4EF; color: #2E7D4F; }
        .in-badge-uni { background: #FFF3EC; color: #C25A1A; }
        .in-card-geo {
          font-size: 10px;
          color: var(--muted, #6B7268);
          font-family: 'DM Mono', monospace;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .in-card-count {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 11px;
          font-weight: 500;
          flex-shrink: 0;
        }
        .in-card-age {
          font-size: 10px;
          font-family: 'DM Mono', monospace;
          flex-shrink: 0;
        }
        .in-age-fresh { color: #4A7C59; }
        .in-age-stale { color: #C25A1A; }

        /* ── Sources ── */
        .in-sources {
          flex: 1;
          min-height: 0;
          display: flex;
          flex-wrap: wrap;
          align-content: center;
          gap: clamp(3px, 0.4vw, 6px);
          padding: clamp(5px, 0.7vh, 9px) clamp(8px, 0.8vw, 12px);
          overflow: hidden;
        }

        /* ── Chips ── */
        .in-chip {
          display: flex;
          align-items: center;
          gap: 5px;
          padding: clamp(3px, 0.4vh, 5px) clamp(6px, 0.5vw, 9px);
          border-radius: 5px;
          border: 1px solid transparent;
          font-size: clamp(9px, 0.7vw, 11px);
          font-family: 'DM Mono', monospace;
          white-space: nowrap;
          transition: background 0.25s, border-color 0.25s, transform 0.15s;
          cursor: default;
          background: none;
          color: inherit;
        }
        .in-chip-click { cursor: pointer; }
        .in-chip-on {
          background: #EDF4EF;
          border-color: rgba(74,124,89,0.25);
        }
        .in-chip-off {
          background: var(--bg-soft, #FAFAF8);
          border-color: var(--border, #ECE9E2);
          color: var(--muted, #6B7268);
        }
        .in-chip-click:hover {
          border-color: rgba(74,124,89,0.45);
          transform: scale(1.04);
        }
        .in-chip-active {
          border-color: #2E7D4F !important;
          background: #D6EAD6 !important;
        }
        .in-chip-label { font-size: inherit; }

        /* ── Panel overlay ── */
        .in-panel-overlay {
          position: absolute;
          inset: 0;
          z-index: 50;
          background: rgba(13,26,15,0.18);
          display: flex;
          justify-content: flex-end;
          animation: fade-in 0.15s ease;
        }
        @keyframes fade-in {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        .in-panel {
          width: clamp(260px, 28vw, 380px);
          height: 100%;
          background: #fff;
          border-left: 1px solid var(--border, #ECE9E2);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          animation: slide-in 0.18s ease;
        }
        @keyframes slide-in {
          from { transform: translateX(100%); }
          to   { transform: translateX(0);    }
        }

        /* ── Panel header ── */
        .in-panel-header {
          flex-shrink: 0;
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          padding: 14px 16px 12px;
          border-bottom: 1px solid var(--border, #ECE9E2);
          background: var(--bg-soft, #FAFAF8);
        }
        .in-panel-etiqueta {
          font-size: 15px;
          font-weight: 700;
          letter-spacing: -0.02em;
          font-family: 'DM Mono', monospace;
        }
        .in-panel-sub {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 11px;
          color: var(--muted, #6B7268);
          margin-top: 3px;
        }
        .in-panel-close {
          background: none;
          border: none;
          cursor: pointer;
          color: var(--muted, #6B7268);
          font-size: 14px;
          padding: 2px 4px;
          border-radius: 3px;
          transition: color 0.15s, background 0.15s;
        }
        .in-panel-close:hover { color: var(--ink, #0D1A0F); background: #ECE9E2; }

        /* ── Panel body ── */
        .in-panel-body {
          flex: 1;
          overflow-y: auto;
          padding: 12px 16px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .in-panel-section {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .in-panel-section-title {
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--muted, #6B7268);
          margin-bottom: 4px;
        }
        .in-panel-row {
          display: flex;
          align-items: baseline;
          gap: 8px;
          padding: 4px 0;
          border-bottom: 1px solid var(--border, #ECE9E2);
          font-size: 12px;
        }
        .in-panel-row:last-child { border-bottom: none; }
        .in-panel-k {
          color: var(--muted, #6B7268);
          min-width: 90px;
          flex-shrink: 0;
        }
        .in-panel-v { flex: 1; font-weight: 500; }
        .in-mono { font-family: 'DM Mono', monospace; font-size: 11px; }
        .in-pin { color: #2E7D4F; }
        .in-v-green { color: #2E7D4F; }
        .in-v-amber { color: #C25A1A; }

        /* ── Panel code block ── */
        .in-panel-code {
          position: relative;
          background: #F4F3EF;
          border: 1px solid var(--border, #ECE9E2);
          border-radius: 6px;
          padding: 10px 12px;
          margin-top: 6px;
          overflow: hidden;
        }
        .in-panel-code pre {
          font-family: 'DM Mono', monospace;
          font-size: 10px;
          line-height: 1.6;
          margin: 0;
          white-space: pre-wrap;
          color: var(--ink, #0D1A0F);
        }
        .in-copy-btn {
          position: absolute;
          top: 8px; right: 8px;
          font-size: 10px;
          font-family: 'DM Mono', monospace;
          background: #fff;
          border: 1px solid var(--border, #ECE9E2);
          border-radius: 4px;
          padding: 3px 8px;
          cursor: pointer;
          transition: background 0.15s, color 0.15s, border-color 0.15s;
          color: var(--ink, #0D1A0F);
        }
        .in-copy-btn:hover { background: #EDF4EF; border-color: #4A7C59; }
        .in-copy-done { background: #EDF4EF; border-color: #4A7C59; color: #2E7D4F; }

        .in-panel-empty {
          font-size: 12px;
          color: var(--muted, #6B7268);
          font-style: italic;
          padding: 4px 0;
        }
      `}</style>
    </div>
  );
}
