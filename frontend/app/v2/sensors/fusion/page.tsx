'use client';

import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { api } from '@/lib/v2-api';

/* ════════════════════════════════════════════════════════════════════
   /v2/sensors/fusion — SALA DE CONTROLO DE SENSORES
   Mapa central · interruptor Simulação/Real · tudo clicável · ao vivo.
   Backend: /fleet?mode · /fusion/{c}?mode · /fleet/mode · /devices/*
   ════════════════════════════════════════════════════════════════════ */

const REFRESH_MS = 5000;

// Geometria (fonte: clusters_geo). e_m/n_m em metros. bbox 298.5 × 327.3.
const SPAN_E = 298.5, SPAN_N = 327.3;
const GEO: Record<string, { e: number; n: number; uni: boolean; desc: string; cap: number }> = {
  'wc-01': { e: 215.2, n: 327.3, uni: false, desc: 'V34 · junto ao P1', cap: 135 },
  'wc-02': { e: 256.9, n: 286.1, uni: false, desc: 'V35 · fem. dominante', cap: 126 },
  'wc-03': { e: 268.2, n: 194.8, uni: false, desc: 'S36 · entrada', cap: 102 },
  'wc-04': { e: 298.5, n: 288.3, uni: false, desc: 'S37 · cota +20m', cap: 150 },
  'wc-05': { e: 274.2, n: 238.2, uni: true,  desc: 'M38 · só entrada', cap: 133 },
  'wc-06': { e: 60.7,  n: 82.4,  uni: true,  desc: 'W39 · o maior', cap: 208 },
  'wc-07': { e: 228.2, n: 148.1, uni: false, desc: 'M40 · cacifos', cap: 138 },
  'wc-08': { e: 0.0,   n: 0.0,   uni: false, desc: 'V41 · produção', cap: 145 },
};
const LANDMARKS = [
  { id: 'ent', label: 'Entrada', e: 290, n: 175, kind: 'ent' },
  { id: 'pm', label: 'Palco Mundo', e: 70, n: 120, kind: 'stage' },
  { id: 'mv', label: 'Music Valley', e: 30, n: 60, kind: 'stage' },
  { id: 'sb', label: 'Super Bock', e: 120, n: 70, kind: 'stage' },
];
const CLUSTERS = Object.keys(GEO);

// padding do mapa em metros
const PAD = 30;
function toXY(e: number, n: number, w: number, h: number) {
  const x = ((e + PAD) / (SPAN_E + PAD * 2)) * w;
  const y = h - ((n + PAD) / (SPAN_N + PAD * 2)) * h; // norte para cima
  return { x, y };
}

function occColor(pct: number): string {
  if (pct >= 90) return '#C25A1A';       // âmbar (crítico)
  if (pct >= 70) return '#D98A4A';       // âmbar claro
  if (pct >= 40) return '#6FAF82';       // verde claro
  return '#4A7C59';                       // verde
}
function tipoLabel(t: string): string {
  return ({ lilygo:'LilyGo', camera:'Câmara', ir:'Infraverm.', gateway_lora:'Gateway', ap_wifi:'WiFi AP' } as any)[t] || t;
}
function srcLabel(s: string): string {
  return ({ camera:'Câmara', ir:'Infravermelho', wifi:'WiFi (LilyGo)' } as any)[s] || s;
}

type Sensor = {
  id: string; tipo: string; cluster: string | null; status: string;
  modelo?: string; real?: boolean; link?: string; origem?: string;
  battery?: { pct: number; fonte: string };
};
type Fusion = {
  pessoas: number; ocupacao_pct: number; fila_atual: number; tempo_espera_min: number;
  confianca: number; pesos: Record<string, number>; estimativas_por_fonte?: Record<string, number>;
  estado: string; data_source: string; capacidade_dentro: number; fontes_disponiveis: string[];
};

export default function ControlRoom() {
  const [mode, setMode] = useState<'sim' | 'real'>('sim');
  const [view, setView] = useState<'sala' | 'rede' | 'manut'>('sala');
  const [fleet, setFleet] = useState<Sensor[]>([]);
  const [fusions, setFusions] = useState<Record<string, Fusion>>({});
  const [sel, setSel] = useState<string>('wc-06');
  const [selSensor, setSelSensor] = useState<Sensor | null>(null);
  const [cmdLog, setCmdLog] = useState<string[]>([]);
  const [tick, setTick] = useState(0);
  const mapRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ w: 600, h: 460 });

  // ler o modo do backend uma vez
  useEffect(() => {
    api.fleetMode().then((r: any) => { if (r?.mode) setMode(r.mode); }).catch(()=>{});
  }, []);

  // medir o mapa
  useEffect(() => {
    const measure = () => {
      if (mapRef.current) {
        const r = mapRef.current.getBoundingClientRect();
        setDims({ w: r.width, h: r.height });
      }
    };
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [view]);

  // polling: fleet + fusao de todos os clusters
  useEffect(() => {
    let cancel = false;
    const load = async () => {
      try {
        const f = await api.fleet(mode);
        if (cancel) return;
        setFleet(f.sensors || []);
        const results = await Promise.all(
          CLUSTERS.map((c) => api.fusion(c, mode).catch(() => null))
        );
        if (cancel) return;
        const fu: Record<string, Fusion> = {};
        CLUSTERS.forEach((c, i) => { if (results[i]) fu[c] = results[i]; });
        setFusions(fu);
        setTick((t) => t + 1);
      } catch { /* */ }
    };
    load();
    const iv = setInterval(load, REFRESH_MS);
    return () => { cancel = true; clearInterval(iv); };
  }, [mode]);

  const toggleMode = async () => {
    const next = mode === 'sim' ? 'real' : 'sim';
    setMode(next);
    try { await api.setFleetMode(next); } catch { /* */ }
  };

  const stats = useMemo(() => {
    const online = fleet.filter((s) => s.status === 'online').length;
    const bats = fleet.filter((s) => s.battery).map((s) => s.battery!.pct);
    const batAvg = bats.length ? Math.round(bats.reduce((a,b)=>a+b,0)/bats.length) : null;
    const totalPessoas = Object.values(fusions).reduce((a, f) => a + (f.pessoas || 0), 0);
    return { online, total: fleet.length, batAvg, totalPessoas };
  }, [fleet, fusions]);

  const selFusion = fusions[sel];
  const sensorsOfSel = useMemo(() => fleet.filter((s) => s.cluster === sel), [fleet, sel]);

  const runCmd = async (cluster: string, label: string, fn: () => Promise<any>) => {
    const cu = cluster.toUpperCase();
    setCmdLog((l) => [`${new Date().toLocaleTimeString()} · ${cu} · ${label}…`, ...l].slice(0, 14));
    try {
      const r = await fn();
      setCmdLog((l) => [`${new Date().toLocaleTimeString()} · ${cu} · ${label} → ${r?.sent ? 'OK' : 'enviado'}`, ...l].slice(0, 14));
    } catch {
      setCmdLog((l) => [`${new Date().toLocaleTimeString()} · ${cu} · ${label} → device offline`, ...l].slice(0, 14));
    }
  };

  return (
    <div className="cr-root">
      {/* HEADER */}
      <div className="cr-head">
        <div className="cr-head-l">
          <div className="cr-eyebrow">PlantaOS · Sala de controlo</div>
          <h1 className="cr-title">Sensores & Fusão</h1>
        </div>
        <div className="cr-head-r">
          <button className={`cr-mode ${mode==='sim'?'is-sim':'is-real'}`} onClick={toggleMode}>
            <span className="cr-mode-dot" />
            {mode==='sim' ? 'Simulação' : 'Dados reais'}
            <span className="cr-mode-sub">tocar para trocar</span>
          </button>
          <div className="cr-refresh">atualiza {REFRESH_MS/1000}s · ●{tick%2?'':' '}</div>
        </div>
      </div>

      {/* VIEW TABS */}
      <div className="cr-tabs">
        {[['sala','Sala de controlo'],['rede','Rede'],['manut','Manutenção']].map(([id,l])=>(
          <button key={id} className={`cr-tab ${view===id?'is-on':''}`} onClick={()=>setView(id as any)}>{l}</button>
        ))}
      </div>

      <div className="cr-body">
        {/* ─────────── SALA DE CONTROLO ─────────── */}
        {view === 'sala' && (
          <div className="cr-sala">
            {/* KPIs topo */}
            <div className="cr-kpis">
              <div className="cr-kpi"><b>{stats.totalPessoas}</b><span>pessoas no recinto</span></div>
              <div className="cr-kpi"><b style={{color:'#4A7C59'}}>{stats.online}/{stats.total}</b><span>sensores online</span></div>
              <div className="cr-kpi"><b>{stats.batAvg!=null?stats.batAvg+'%':'—'}</b><span>bateria média</span></div>
              <div className="cr-kpi"><b className={mode==='sim'?'cr-tag-sim':'cr-tag-real'}>{mode==='sim'?'SIMULAÇÃO':'REAL'}</b><span>origem dos dados</span></div>
            </div>

            <div className="cr-main">
              {/* MAPA */}
              <div className="cr-map" ref={mapRef}>
                <svg width={dims.w} height={dims.h} className="cr-svg">
                  {/* grelha leve */}
                  {[0.25,0.5,0.75].map((g)=>(
                    <g key={g}>
                      <line x1={dims.w*g} y1={0} x2={dims.w*g} y2={dims.h} stroke="#EEF1EA" strokeWidth={1}/>
                      <line x1={0} y1={dims.h*g} x2={dims.w} y2={dims.h*g} stroke="#EEF1EA" strokeWidth={1}/>
                    </g>
                  ))}
                  {/* landmarks */}
                  {LANDMARKS.map((lm)=>{
                    const {x,y}=toXY(lm.e,lm.n,dims.w,dims.h);
                    return (
                      <g key={lm.id}>
                        <rect x={x-26} y={y-9} width={52} height={18} rx={4}
                          fill={lm.kind==='ent'?'#E8F1EA':'#F0EEE6'} stroke="#D8DCD2" strokeWidth={1}/>
                        <text x={x} y={y+3} textAnchor="middle" fontSize={9} fill="#6A746B">{lm.label}</text>
                      </g>
                    );
                  })}
                  {/* clusters */}
                  {CLUSTERS.map((c)=>{
                    const g=GEO[c]; const {x,y}=toXY(g.e,g.n,dims.w,dims.h);
                    const f=fusions[c]; const pct=f?.ocupacao_pct ?? 0;
                    const col=occColor(pct);
                    const r=14 + (pct/100)*16; // raio cresce com ocupação
                    const isSel=c===sel;
                    const hasData = f && f.estado==='ok';
                    return (
                      <g key={c} onClick={()=>setSel(c)} style={{cursor:'pointer'}}>
                        {hasData && <circle cx={x} cy={y} r={r+8} fill={col} opacity={0.12}>
                          <animate attributeName="r" values={`${r+4};${r+12};${r+4}`} dur="3s" repeatCount="indefinite"/>
                          <animate attributeName="opacity" values="0.18;0.05;0.18" dur="3s" repeatCount="indefinite"/>
                        </circle>}
                        <circle cx={x} cy={y} r={r} fill={hasData?col:'#C9CEC4'}
                          stroke={isSel?'#0D1A0F':'#fff'} strokeWidth={isSel?3:2}/>
                        <text x={x} y={y-r-6} textAnchor="middle" fontSize={11} fontWeight={700} fill="#0D1A0F">{c.toUpperCase()}</text>
                        {hasData && <text x={x} y={y+4} textAnchor="middle" fontSize={11} fontWeight={700} fill="#fff">{Math.round(pct)}%</text>}
                        {g.uni && <text x={x} y={y+r+13} textAnchor="middle" fontSize={8} fill="#6A746B">unissex</text>}
                      </g>
                    );
                  })}
                </svg>
                <div className="cr-map-legend">
                  <span><i style={{background:'#4A7C59'}}/>&lt;40%</span>
                  <span><i style={{background:'#6FAF82'}}/>40-70%</span>
                  <span><i style={{background:'#D98A4A'}}/>70-90%</span>
                  <span><i style={{background:'#C25A1A'}}/>&gt;90%</span>
                </div>
              </div>

              {/* PAINEL DO CLUSTER */}
              <div className="cr-panel">
                {selFusion ? (
                  <>
                    <div className="cr-panel-head">
                      <div>
                        <div className="cr-panel-id">{sel.toUpperCase()}</div>
                        <div className="cr-panel-desc">{GEO[sel]?.desc}</div>
                      </div>
                      <div className={`cr-prov cr-prov-${selFusion.data_source}`}>
                        {selFusion.data_source==='simulado'?'simulado':
                         selFusion.data_source==='real'?'real':
                         selFusion.data_source==='stale'?'desatualizado':'sem dados'}
                      </div>
                    </div>

                    {selFusion.estado==='ok' ? (
                      <>
                        <div className="cr-big">{selFusion.pessoas}<span> pessoas</span></div>
                        <div className="cr-occ-bar">
                          <div className="cr-occ-fill" style={{width:`${Math.min(100,selFusion.ocupacao_pct)}%`, background:occColor(selFusion.ocupacao_pct)}}/>
                        </div>
                        <div className="cr-occ-label">{selFusion.ocupacao_pct}% de {selFusion.capacidade_dentro} lugares</div>

                        <div className="cr-metrics">
                          <div><span>Fila</span><b>{selFusion.fila_atual}</b></div>
                          <div><span>Espera</span><b>{selFusion.tempo_espera_min} min</b></div>
                          <div><span>Confiança</span><b>{Math.round(selFusion.confianca*100)}%</b></div>
                        </div>

                        <div className="cr-fs-title">Fontes & pesos · ao vivo</div>
                        {Object.entries(selFusion.pesos||{}).map(([src,w])=>(
                          <div key={src} className="cr-fs-row">
                            <div className="cr-fs-lbl">{srcLabel(src)}</div>
                            <div className="cr-fs-track"><div className="cr-fs-bar" style={{width:`${w*100}%`}}/></div>
                            <div className="cr-fs-val"><b>{Math.round(w*100)}%</b> · {selFusion.estimativas_por_fonte?.[src] ?? '—'}</div>
                          </div>
                        ))}
                        <p className="cr-hint">Os pesos redistribuem-se se uma fonte cai. A confiança sobe quando as fontes concordam.</p>
                      </>
                    ) : (
                      <div className="cr-empty">
                        <p>Sem dados de sensores para {sel.toUpperCase()}.</p>
                        <p className="cr-soft">Fontes possíveis: {(selFusion.fontes_disponiveis||[]).join(', ')}</p>
                        {mode==='real' && <p className="cr-soft">Em modo real, os números só aparecem quando um sensor envia.</p>}
                      </div>
                    )}

                    {/* sensores deste cluster */}
                    <div className="cr-cl-sensors">
                      <div className="cr-fs-title">Sensores ({sensorsOfSel.length})</div>
                      <div className="cr-chips">
                        {sensorsOfSel.map((s)=>(
                          <button key={s.id} className="cr-chip" onClick={()=>setSelSensor(s)}>
                            <span className="cr-chip-dot" style={{background: s.status==='online'?'#4A7C59':s.status==='degraded'?'#C25A1A':'#C9CEC4'}}/>
                            {tipoLabel(s.tipo)}{s.battery?` ${s.battery.pct}%`:''}
                          </button>
                        ))}
                      </div>
                    </div>
                  </>
                ) : <p className="cr-soft">A carregar…</p>}
              </div>
            </div>
          </div>
        )}

        {/* ─────────── REDE ─────────── */}
        {view === 'rede' && (
          <div className="cr-rede">
            <div className="cr-flow">
              <div className="cr-fnode">IR · elétrico</div><span>→</span>
              <div className="cr-fnode">LilyGo · powerbank</div><span>→</span>
              <div className="cr-fcol">
                <div className="cr-fnode cr-ok">WiFi 6E + mesh<br/><small>grupo central</small></div>
                <div className="cr-fnode cr-warn">LoRa + SIM 4G<br/><small>WC-06, WC-08</small></div>
              </div><span>→</span>
              <div className="cr-fnode">Backhaul 4G</div><span>→</span>
              <div className="cr-fnode cr-ok">Railway · Fusão</div>
            </div>
            <div className="cr-net-grid">
              {CLUSTERS.map((c)=>{
                const sens=fleet.filter((s)=>s.cluster===c);
                const on=sens.filter((s)=>s.status==='online').length;
                const iso=c==='wc-06'||c==='wc-08';
                return (
                  <div key={c} className="cr-net-card" onClick={()=>{setSel(c);setView('sala');}}>
                    <div className="cr-net-id">{c.toUpperCase()}</div>
                    <div className="cr-net-meta">{on}/{sens.length} online</div>
                    <div className="cr-net-link" style={{color:iso?'#C25A1A':'#1B3A21'}}>{iso?'LoRa + SIM':'WiFi + mesh'}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ─────────── MANUTENÇÃO ─────────── */}
        {view === 'manut' && (
          <div className="cr-manut">
            <div className="cr-manut-grid">
              {CLUSTERS.map((c)=>{
                const cu=c.toUpperCase();
                return (
                  <div key={c} className="cr-manut-card">
                    <div className="cr-manut-id">{cu}</div>
                    <div className="cr-manut-btns">
                      <button onClick={()=>runCmd(c,'Ping',()=>api.devicePing(cu))}>Ping</button>
                      <button onClick={()=>runCmd(c,'Diagnóstico',()=>api.deviceDiagnostics(cu))}>Diagnóstico</button>
                      <button onClick={()=>runCmd(c,'Reiniciar',()=>api.deviceRestart(cu))}>Reiniciar</button>
                      <button onClick={()=>runCmd(c,'Reset',()=>api.deviceReset(cu))}>Reset</button>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="cr-log">
              <div className="cr-log-title">Registo de comandos</div>
              {cmdLog.length===0?<div className="cr-soft">Sem ações ainda.</div>:cmdLog.map((l,i)=><div key={i} className="cr-log-line">{l}</div>)}
            </div>
          </div>
        )}
      </div>

      {/* DRAWER SENSOR */}
      {selSensor && (
        <div className="cr-drawer-bg" onClick={()=>setSelSensor(null)}>
          <div className="cr-drawer" onClick={(e)=>e.stopPropagation()}>
            <div className="cr-drawer-head">
              <div className="cr-mono">{selSensor.id}</div>
              <button className="cr-x" onClick={()=>setSelSensor(null)}>&times;</button>
            </div>
            {selSensor.modelo && selSensor.real && <div className="cr-badge">{selSensor.modelo}</div>}
            <div className="cr-drawer-rows">
              <div><span>Tipo</span><b>{tipoLabel(selSensor.tipo)}</b></div>
              <div><span>Cluster</span><b>{selSensor.cluster?.toUpperCase()||'—'}</b></div>
              <div><span>Estado</span><b>{selSensor.status}</b></div>
              <div><span>Bateria</span><b>{selSensor.battery?`${selSensor.battery.pct}% (${selSensor.battery.fonte})`:'sem bateria'}</b></div>
              <div><span>Ligação</span><b>{selSensor.link||'—'}</b></div>
              <div><span>Origem</span><b>{selSensor.origem||'—'}</b></div>
            </div>
            {selSensor.cluster && (
              <div className="cr-drawer-cmds">
                <button onClick={()=>runCmd(selSensor.cluster!,'Ping',()=>api.devicePing(selSensor.cluster!.toUpperCase()))}>Ping cluster</button>
                <button onClick={()=>runCmd(selSensor.cluster!,'Diagnóstico',()=>api.deviceDiagnostics(selSensor.cluster!.toUpperCase()))}>Diagnóstico</button>
              </div>
            )}
            <p className="cr-soft" style={{marginTop:10,fontSize:12}}>Os comandos chegam ao LilyGo do cluster (que lê este sensor).</p>
          </div>
        </div>
      )}

      <style jsx>{`
        .cr-root { height: calc(100vh - 72px); display: flex; flex-direction: column;
          overflow: hidden; color: #0D1A0F; }
        .cr-head { display: flex; justify-content: space-between; align-items: flex-end;
          padding: 18px clamp(16px,2.6vw,32px) 6px; flex-shrink: 0; }
        .cr-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
          text-transform: uppercase; color: #8A938B; }
        .cr-title { font-size: clamp(20px,2.6vw,30px); font-weight: 600; margin: 2px 0 0; }
        .cr-head-r { display: flex; align-items: center; gap: 14px; }
        .cr-mode { display: flex; flex-direction: column; align-items: flex-start;
          border: none; border-radius: 12px; padding: 8px 18px; cursor: pointer;
          font-family: inherit; font-size: 15px; font-weight: 600; position: relative; transition: all .2s; }
        .cr-mode.is-sim { background: #1B3A21; color: #fff; }
        .cr-mode.is-real { background: #C25A1A; color: #fff; }
        .cr-mode-dot { display: none; }
        .cr-mode-sub { font-size: 10px; font-weight: 400; opacity: 0.7; }
        .cr-refresh { font-size: 11px; color: #8A938B; }

        .cr-tabs { display: flex; gap: 6px; padding: 6px clamp(16px,2.6vw,32px); flex-shrink: 0; }
        .cr-tab { background: #fff; border: 1px solid #E5E8E0; border-radius: 999px;
          padding: 7px 16px; font-size: 13px; cursor: pointer; color: #0D1A0F; font-family: inherit; }
        .cr-tab.is-on { background: #1B3A21; border-color: #1B3A21; color: #fff; font-weight: 600; }

        .cr-body { flex: 1; min-height: 0; overflow: hidden; padding: 8px clamp(16px,2.6vw,32px) 18px;
          display: flex; flex-direction: column; }

        .cr-sala { display: flex; flex-direction: column; min-height: 0; flex: 1; gap: 12px; }
        .cr-kpis { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; flex-shrink: 0; }
        .cr-kpi { background: #fff; border: 1px solid #E5E8E0; border-radius: 12px; padding: 12px 14px; }
        .cr-kpi b { display: block; font-size: 26px; font-weight: 600; line-height: 1;
          font-variant-numeric: tabular-nums; color: #1B3A21; }
        .cr-kpi span { font-size: 11px; color: #8A938B; margin-top: 4px; display: block; }
        .cr-tag-sim { color: #1B3A21 !important; font-size: 20px !important; }
        .cr-tag-real { color: #C25A1A !important; font-size: 20px !important; }

        .cr-main { flex: 1; min-height: 0; display: grid; grid-template-columns: 1.5fr 1fr; gap: 14px; }
        .cr-map { background: #fff; border: 1px solid #E5E8E0; border-radius: 14px;
          position: relative; min-height: 0; overflow: hidden; }
        .cr-svg { display: block; width: 100%; height: 100%; }
        .cr-map-legend { position: absolute; bottom: 10px; left: 12px; display: flex; gap: 12px;
          background: rgba(255,255,255,0.9); padding: 5px 10px; border-radius: 8px; font-size: 11px; color: #6A746B; }
        .cr-map-legend span { display: flex; align-items: center; gap: 4px; }
        .cr-map-legend i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }

        .cr-panel { background: #fff; border: 1px solid #E5E8E0; border-radius: 14px;
          padding: 16px; overflow-y: auto; min-height: 0; }
        .cr-panel-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .cr-panel-id { font-size: 20px; font-weight: 700; }
        .cr-panel-desc { font-size: 12px; color: #8A938B; }
        .cr-prov { font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 6px; }
        .cr-prov-simulado { background: #E8F1EA; color: #1B3A21; }
        .cr-prov-real { background: #DEF0E4; color: #1B3A21; }
        .cr-prov-stale { background: #F5E6D8; color: #C25A1A; }
        .cr-prov-none { background: #F0F2EC; color: #8A938B; }
        .cr-big { font-size: 46px; font-weight: 600; line-height: 1; color: #1B3A21; font-variant-numeric: tabular-nums; }
        .cr-big span { font-size: 14px; color: #8A938B; font-weight: 400; }
        .cr-occ-bar { height: 10px; background: #F0F2EC; border-radius: 5px; overflow: hidden; margin: 12px 0 5px; }
        .cr-occ-fill { height: 100%; border-radius: 5px; transition: width .6s ease, background .6s; }
        .cr-occ-label { font-size: 12px; color: #8A938B; }
        .cr-metrics { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin: 14px 0; }
        .cr-metrics div { background: #FAFAF7; border-radius: 8px; padding: 8px; text-align: center; }
        .cr-metrics span { display: block; font-size: 11px; color: #8A938B; }
        .cr-metrics b { font-size: 18px; font-variant-numeric: tabular-nums; }
        .cr-fs-title { font-size: 11px; font-weight: 700; text-transform: uppercase;
          letter-spacing: 0.05em; color: #8A938B; margin: 14px 0 10px; }
        .cr-fs-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
        .cr-fs-lbl { width: 95px; font-size: 13px; }
        .cr-fs-track { flex: 1; height: 8px; background: #F0F2EC; border-radius: 4px; overflow: hidden; }
        .cr-fs-bar { height: 100%; background: #4A7C59; border-radius: 4px; transition: width .6s ease; }
        .cr-fs-val { width: 90px; text-align: right; font-size: 12px; font-variant-numeric: tabular-nums; }
        .cr-fs-val b { color: #1B3A21; }
        .cr-hint { font-size: 12px; color: #8A938B; line-height: 1.5; margin-top: 6px; }
        .cr-empty { padding: 20px 0; }
        .cr-empty p { margin: 4px 0; }
        .cr-soft { color: #8A938B; }
        .cr-cl-sensors { margin-top: 16px; border-top: 1px solid #F0F2EC; padding-top: 12px; }
        .cr-chips { display: flex; flex-wrap: wrap; gap: 6px; }
        .cr-chip { display: flex; align-items: center; gap: 5px; background: #FAFAF7;
          border: 1px solid #E5E8E0; border-radius: 999px; padding: 4px 10px; font-size: 12px;
          cursor: pointer; color: #0D1A0F; font-family: inherit; }
        .cr-chip:hover { border-color: #4A7C59; }
        .cr-chip-dot { width: 7px; height: 7px; border-radius: 50%; }

        .cr-rede { display: flex; flex-direction: column; gap: 16px; min-height: 0; overflow-y: auto; }
        .cr-flow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .cr-flow span { color: #8A938B; }
        .cr-fnode { background: #fff; border: 1px solid #E5E8E0; border-radius: 10px;
          padding: 10px 14px; font-size: 13px; text-align: center; }
        .cr-fnode small { color: #8A938B; }
        .cr-ok { border-color: #4A7C59; } .cr-warn { border-color: #C25A1A; }
        .cr-fcol { display: flex; flex-direction: column; gap: 6px; }
        .cr-net-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 10px; }
        .cr-net-card { background: #fff; border: 1px solid #E5E8E0; border-radius: 12px; padding: 12px; cursor: pointer; }
        .cr-net-card:hover { border-color: #4A7C59; }
        .cr-net-id { font-weight: 700; }
        .cr-net-meta { font-size: 12px; color: #8A938B; margin: 4px 0; }
        .cr-net-link { font-size: 12px; font-weight: 500; }

        .cr-manut { display: flex; flex-direction: column; gap: 14px; min-height: 0; }
        .cr-manut-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(210px,1fr)); gap: 12px; overflow-y: auto; }
        .cr-manut-card { background: #fff; border: 1px solid #E5E8E0; border-radius: 12px; padding: 14px; }
        .cr-manut-id { font-weight: 700; margin-bottom: 10px; }
        .cr-manut-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
        .cr-manut-btns button { background: #FAFAF7; border: 1px solid #E5E8E0; border-radius: 8px;
          padding: 7px; font-size: 12px; cursor: pointer; color: #0D1A0F; font-family: inherit; }
        .cr-manut-btns button:hover { border-color: #4A7C59; background: #fff; }
        .cr-log { background: #0D1A0F; border-radius: 12px; padding: 14px; max-height: 180px; overflow-y: auto; }
        .cr-log-title { font-size: 11px; text-transform: uppercase; color: #6FAF82; margin-bottom: 8px; }
        .cr-log-line { font-family: monospace; font-size: 12px; color: #BFE0E8; padding: 2px 0; }

        .cr-drawer-bg { position: fixed; inset: 0; background: rgba(13,26,15,0.3); z-index: 50;
          display: flex; justify-content: flex-end; }
        .cr-drawer { width: 360px; max-width: 90vw; background: #fff; height: 100%; padding: 20px;
          overflow-y: auto; box-shadow: -8px 0 30px rgba(0,0,0,0.12); }
        .cr-drawer-head { display: flex; justify-content: space-between; align-items: center; }
        .cr-x { background: none; border: none; font-size: 18px; cursor: pointer; color: #8A938B; }
        .cr-mono { font-family: monospace; font-size: 14px; font-weight: 600; }
        .cr-badge { display: inline-block; margin-top: 10px; background: #E8F1EA; color: #1B3A21;
          border-radius: 6px; padding: 3px 10px; font-size: 12px; font-weight: 600; }
        .cr-drawer-rows { margin-top: 16px; }
        .cr-drawer-rows div { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid #F0F2EC; font-size: 14px; }
        .cr-drawer-rows span { color: #8A938B; }
        .cr-drawer-cmds { display: flex; gap: 8px; margin-top: 16px; }
        .cr-drawer-cmds button { flex: 1; background: #1B3A21; color: #fff; border: none;
          border-radius: 8px; padding: 9px; font-size: 13px; cursor: pointer; font-family: inherit; }

        @media (max-width: 820px) {
          .cr-main { grid-template-columns: 1fr; }
          .cr-kpis { grid-template-columns: repeat(2,1fr); }
        }
      `}</style>
    </div>
  );
}
