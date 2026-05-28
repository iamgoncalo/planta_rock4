'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/v2-api';

/* ──────────────────────────────────────────────────────────────────
   /v2/sensors/fusion — CONSOLA DE SENSORES (NOC)
   Sem scroll de pagina. Tabs: Visao · Sensores · Rede · Fusao · Manutencao.
   Liga ao backend real: /fleet, /fleet/summary, /fusion/{c}, /devices/*.
   Estilo Planta (Inter, verde, ambar #C25A1A, sem vermelho).
   ────────────────────────────────────────────────────────────────── */

const REFRESH_MS = 10000;
const CLUSTERS = ['wc-01','wc-02','wc-03','wc-04','wc-05','wc-06','wc-07','wc-08'];

const TABS = [
  { id: 'visao', label: 'Visão geral' },
  { id: 'sensores', label: 'Sensores' },
  { id: 'rede', label: 'Rede' },
  { id: 'fusao', label: 'Fusão' },
  { id: 'manut', label: 'Manutenção' },
];

type Sensor = {
  id: string; tipo: string; cluster: string | null; status: string;
  modelo?: string; real?: boolean; porta?: string; role?: string;
  power?: string; link?: string; fonte_fusao?: string;
  battery?: { pct: number; fonte: string; autonomia_h?: number };
};

function statusColor(s: string): string {
  if (s === 'online') return 'var(--green-soft, #4A7C59)';
  if (s === 'degraded') return 'var(--amber, #C25A1A)';
  if (s === 'offline') return '#8A938B';
  if (s === 'maintenance') return '#6FAF82';
  return '#C9CEC4'; // planned
}
function statusLabel(s: string): string {
  return ({ online:'Online', degraded:'Instável', offline:'Offline',
            maintenance:'Manutenção', planned:'Planeado', unknown:'—' } as any)[s] || s;
}
function tipoLabel(t: string): string {
  return ({ lilygo:'LilyGo', camera:'Câmara', ir:'Infravermelho',
            gateway_lora:'Gateway LoRa', ap_wifi:'Ponto WiFi' } as any)[t] || t;
}

export default function SensorConsole() {
  const [tab, setTab] = useState('visao');
  const [fleet, setFleet] = useState<Sensor[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [fusion, setFusion] = useState<Record<string, any>>({});
  const [selCluster, setSelCluster] = useState('wc-06');
  const [filterTipo, setFilterTipo] = useState('todos');
  const [cmdLog, setCmdLog] = useState<string[]>([]);

  useEffect(() => {
    let cancel = false;
    const tick = async () => {
      try {
        const [f, s] = await Promise.all([api.fleet(), api.fleetSummary()]);
        if (cancel) return;
        setFleet(f.sensors || []);
        setSummary(s);
      } catch { /* mantém */ }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => { cancel = true; clearInterval(iv); };
  }, []);

  // Fusao do cluster selecionado (tab fusao)
  useEffect(() => {
    if (tab !== 'fusao') return;
    let cancel = false;
    const tick = async () => {
      try {
        const r = await api.fusion(selCluster);
        if (!cancel) setFusion((prev) => ({ ...prev, [selCluster]: r }));
      } catch { /* */ }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => { cancel = true; clearInterval(iv); };
  }, [tab, selCluster]);

  const stats = useMemo(() => {
    const online = fleet.filter((s) => s.status === 'online').length;
    const total = fleet.length;
    const bats = fleet.filter((s) => s.battery).map((s) => s.battery!.pct);
    const batAvg = bats.length ? Math.round(bats.reduce((a,b)=>a+b,0)/bats.length) : null;
    return { online, total, batAvg };
  }, [fleet]);

  const filtered = useMemo(() => {
    if (filterTipo === 'todos') return fleet;
    return fleet.filter((s) => s.tipo === filterTipo);
  }, [fleet, filterTipo]);

  const runCmd = async (cluster: string, cmd: string, fn: () => Promise<any>) => {
    setCmdLog((l) => [`${new Date().toLocaleTimeString()} · ${cluster} · ${cmd} enviado…`, ...l].slice(0, 12));
    try {
      const r = await fn();
      setCmdLog((l) => [`${new Date().toLocaleTimeString()} · ${cluster} · ${cmd} → ${r?.sent ? 'OK' : 'enviado'}`, ...l].slice(0, 12));
    } catch {
      setCmdLog((l) => [`${new Date().toLocaleTimeString()} · ${cluster} · ${cmd} → device offline`, ...l].slice(0, 12));
    }
  };

  return (
    <div className="sc-root">
      <div className="sc-head">
        <div className="sc-eyebrow">PlantaOS · Consola de sensores</div>
        <h1 className="sc-title">Frota & Fusão</h1>
      </div>

      <div className="sc-tabs">
        {TABS.map((t) => (
          <button key={t.id} className={`sc-tab ${t.id===tab?'is-on':''}`} onClick={()=>setTab(t.id)}>{t.label}</button>
        ))}
      </div>

      <div className="sc-body">
        {/* TAB VISAO */}
        {tab === 'visao' && (
          <div className="sc-overview">
            <div className="sc-kpi-grid">
              <div className="sc-kpi"><b>{stats.total || (summary?.total ?? 0)}</b><span>sensores na frota</span></div>
              <div className="sc-kpi"><b style={{color:'var(--green-soft,#4A7C59)'}}>{stats.online}</b><span>online agora</span></div>
              <div className="sc-kpi"><b>{stats.batAvg != null ? stats.batAvg+'%' : '—'}</b><span>bateria média (est.)</span></div>
              <div className="sc-kpi"><b>{summary?.by_type?.camera ?? 0}</b><span>câmaras</span></div>
            </div>
            {summary && (
              <div className="sc-type-row">
                {Object.entries(summary.by_type).map(([t, n]: any) => (
                  <div key={t} className="sc-type-chip"><b>{n}</b> {tipoLabel(t)}</div>
                ))}
              </div>
            )}
            <p className="sc-note">
              A frota cobre os 8 clusters. LilyGo em todos (coração, powerbank). Câmaras reais
              (OAK 4 D no WC-06, OAK-D Lite no WC-04) e planeadas nos restantes. IR ao mínimo,
              só nos clusters com portas separadas. Tudo configurável.
            </p>
          </div>
        )}

        {/* TAB SENSORES */}
        {tab === 'sensores' && (
          <div className="sc-sensores">
            <div className="sc-filters">
              {['todos','lilygo','camera','ir','gateway_lora','ap_wifi'].map((t)=>(
                <button key={t} className={`sc-fchip ${filterTipo===t?'is-on':''}`} onClick={()=>setFilterTipo(t)}>
                  {t==='todos'?'Todos':tipoLabel(t)}
                </button>
              ))}
            </div>
            <div className="sc-table-wrap">
              <table className="sc-table">
                <thead><tr>
                  <th>Sensor</th><th>Tipo</th><th>Cluster</th><th>Estado</th>
                  <th>Bateria</th><th>Ligação</th>
                </tr></thead>
                <tbody>
                  {filtered.map((s)=>(
                    <tr key={s.id}>
                      <td className="sc-mono">{s.id}{s.modelo && s.real ? <span className="sc-badge">{s.modelo}</span> : ''}</td>
                      <td>{tipoLabel(s.tipo)}</td>
                      <td className="sc-mono">{s.cluster || '—'}</td>
                      <td><span className="sc-dot" style={{background:statusColor(s.status)}} /> {statusLabel(s.status)}</td>
                      <td>
                        {s.battery ? (
                          <div className="sc-bat">
                            <div className="sc-bat-bar"><div className="sc-bat-fill" style={{width:`${s.battery.pct}%`, background: s.battery.pct<20?'var(--amber,#C25A1A)':'var(--green-soft,#4A7C59)'}} /></div>
                            <span>{s.battery.pct}%{s.battery.fonte==='estimada'?' est.':''}</span>
                          </div>
                        ) : <span className="sc-soft">—</span>}
                      </td>
                      <td className="sc-soft">{s.link || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB REDE */}
        {tab === 'rede' && (
          <div className="sc-rede">
            <div className="sc-net-flow">
              <div className="sc-net-node">IR · elétrico</div>
              <span className="sc-arr">→</span>
              <div className="sc-net-node">LilyGo · powerbank</div>
              <span className="sc-arr">→</span>
              <div className="sc-net-col">
                <div className="sc-net-node sc-net-ok">WiFi 6E + mesh ESP-NOW<br/><small>grupo central</small></div>
                <div className="sc-net-node sc-net-warn">LoRa + SIM 4G<br/><small>WC-06, WC-08 isolados</small></div>
              </div>
              <span className="sc-arr">→</span>
              <div className="sc-net-node">Backhaul 4G<br/><small>NOS + Vodafone</small></div>
              <span className="sc-arr">→</span>
              <div className="sc-net-node sc-net-ok">Railway · Fusão</div>
            </div>
            <div className="sc-net-grid">
              {CLUSTERS.map((c)=>{
                const sensores = fleet.filter((s)=>s.cluster===c);
                const online = sensores.filter((s)=>s.status==='online').length;
                const isolated = c==='wc-06'||c==='wc-08';
                return (
                  <div key={c} className="sc-net-card">
                    <div className="sc-net-card-id">{c.toUpperCase()}</div>
                    <div className="sc-net-card-meta">{sensores.length} sensores · {online} online</div>
                    <div className="sc-net-card-link">{isolated?'LoRa + SIM 4G':'WiFi + mesh'}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB FUSAO */}
        {tab === 'fusao' && (
          <div className="sc-fusao">
            <div className="sc-filters">
              {CLUSTERS.map((c)=>(
                <button key={c} className={`sc-fchip ${selCluster===c?'is-on':''}`} onClick={()=>setSelCluster(c)}>
                  {c.toUpperCase()}
                </button>
              ))}
            </div>
            {(() => {
              const f = fusion[selCluster];
              if (!f) return <p className="sc-note">A carregar fusão de {selCluster.toUpperCase()}…</p>;
              if (f.estado === 'sem-dados') return (
                <div className="sc-fusao-empty">
                  <p className="sc-note">Sem dados de sensores para {selCluster.toUpperCase()} neste momento.</p>
                  <p className="sc-soft">Fontes disponíveis: {(f.fontes_disponiveis||[]).join(', ')} · capacidade {f.capacidade_dentro}</p>
                </div>
              );
              return (
                <div className="sc-fusao-grid">
                  <div className="sc-fusao-result">
                    <div className="sc-fr-big">{f.pessoas}<span> pessoas</span></div>
                    <div className="sc-fr-row"><span>Ocupação</span><b>{f.ocupacao_pct}%</b></div>
                    <div className="sc-fr-row"><span>Fila</span><b>{f.fila_atual}</b></div>
                    <div className="sc-fr-row"><span>Espera</span><b>{f.tempo_espera_min} min</b></div>
                    <div className="sc-fr-row"><span>Confiança</span><b>{Math.round((f.confianca||0)*100)}%</b></div>
                  </div>
                  <div className="sc-fusao-sources">
                    <div className="sc-fs-title">Fontes & pesos (ao vivo)</div>
                    {Object.entries(f.pesos||{}).map(([src, w]: any)=>(
                      <div key={src} className="sc-fs-row">
                        <div className="sc-fs-label">{tipoLabel(src==='camera'?'camera':src==='ir'?'ir':'lilygo')}</div>
                        <div className="sc-fs-bar-wrap"><div className="sc-fs-bar" style={{width:`${w*100}%`}} /></div>
                        <div className="sc-fs-val"><b>{Math.round(w*100)}%</b> · est. {f.estimativas_por_fonte?.[src] ?? '—'}</div>
                      </div>
                    ))}
                    <p className="sc-soft" style={{marginTop:12}}>
                      Os pesos redistribuem-se quando uma fonte falha. A confiança sobe quando as
                      fontes concordam. O fator dispositivos→pessoas calibra-se pelo ground-truth.
                    </p>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* TAB MANUTENCAO */}
        {tab === 'manut' && (
          <div className="sc-manut">
            <div className="sc-manut-grid">
              {CLUSTERS.map((c)=>{
                const cu = c.toUpperCase();
                return (
                  <div key={c} className="sc-manut-card">
                    <div className="sc-manut-id">{cu}</div>
                    <div className="sc-manut-btns">
                      <button onClick={()=>runCmd(cu,'ping',()=>api.devicePing(cu))}>Ping</button>
                      <button onClick={()=>runCmd(cu,'diagnóstico',()=>api.deviceDiagnostics(cu))}>Diagnóstico</button>
                      <button onClick={()=>runCmd(cu,'reiniciar',()=>api.deviceRestart(cu))}>Reiniciar</button>
                      <button onClick={()=>runCmd(cu,'reset',()=>api.deviceReset(cu))}>Reset</button>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="sc-log">
              <div className="sc-log-title">Registo de comandos</div>
              {cmdLog.length===0 ? <div className="sc-soft">Sem ações ainda.</div> :
                cmdLog.map((l,i)=><div key={i} className="sc-log-line">{l}</div>)}
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .sc-root { height: calc(100vh - 72px); display: flex; flex-direction: column;
          overflow: hidden; color: var(--color-ink, #0D1A0F); padding: 0; }
        .sc-head { padding: 20px clamp(16px,2.6vw,32px) 4px; flex-shrink: 0; }
        .sc-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
          text-transform: uppercase; color: var(--color-muted,#8A938B); }
        .sc-title { font-size: clamp(22px,3vw,34px); font-weight: 600; margin: 2px 0 0; }
        .sc-tabs { flex-shrink: 0; display: flex; gap: 6px; overflow-x: auto;
          padding: 10px clamp(16px,2.6vw,32px); scrollbar-width: none; }
        .sc-tabs::-webkit-scrollbar { display: none; }
        .sc-tab { white-space: nowrap; background: #fff; border: 1px solid #E5E8E0;
          border-radius: 999px; padding: 8px 16px; font-size: 13px; font-weight: 500;
          cursor: pointer; color: #0D1A0F; font-family: inherit; transition: all .14s; }
        .sc-tab:hover { border-color: #4A7C59; }
        .sc-tab.is-on { background: #1B3A21; border-color: #1B3A21; color: #fff; font-weight: 600; }
        .sc-body { flex: 1; min-height: 0; overflow: hidden; padding: 8px clamp(16px,2.6vw,32px) 20px;
          display: flex; flex-direction: column; }

        .sc-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 14px; }
        .sc-kpi { background: #fff; border: 1px solid #E5E8E0; border-radius: 14px; padding: 16px; }
        .sc-kpi b { display: block; font-size: 34px; font-weight: 600; font-variant-numeric: tabular-nums;
          color: var(--green-dark,#1B3A21); line-height: 1; }
        .sc-kpi span { font-size: 12px; color: var(--color-muted,#8A938B); margin-top: 6px; display:block; }
        .sc-type-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
        .sc-type-chip { background: #fff; border: 1px solid #E5E8E0; border-radius: 8px;
          padding: 6px 12px; font-size: 13px; }
        .sc-type-chip b { color: var(--green-dark,#1B3A21); font-variant-numeric: tabular-nums; }
        .sc-note { font-size: 13px; line-height: 1.55; color: var(--color-ink,#0D1A0F);
          opacity: 0.75; max-width: 680px; margin-top: 16px; }
        .sc-soft { color: var(--color-muted,#8A938B); }

        .sc-filters { display: flex; gap: 6px; flex-wrap: wrap; flex-shrink: 0; margin-bottom: 10px; }
        .sc-fchip { background: #fff; border: 1px solid #E5E8E0; border-radius: 999px;
          padding: 5px 12px; font-size: 12px; cursor: pointer; color: #0D1A0F; font-family: inherit; }
        .sc-fchip.is-on { background: #1B3A21; border-color: #1B3A21; color: #fff; }
        .sc-table-wrap { flex: 1; min-height: 0; overflow-y: auto; border: 1px solid #E5E8E0; border-radius: 12px; background: #fff; }
        .sc-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .sc-table thead th { position: sticky; top: 0; background: #FAFAF7; text-align: left;
          padding: 10px 12px; font-weight: 600; color: var(--color-muted,#8A938B);
          border-bottom: 1px solid #E5E8E0; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
        .sc-table td { padding: 9px 12px; border-bottom: 1px solid #F0F2EC; }
        .sc-mono { font-family: var(--font-dm-mono, monospace); font-size: 12px; }
        .sc-badge { display: inline-block; margin-left: 8px; background: #E8F1EA; color: #1B3A21;
          border-radius: 6px; padding: 1px 7px; font-size: 10px; font-weight: 600; }
        .sc-dot { display:inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .sc-bat { display: flex; align-items: center; gap: 8px; }
        .sc-bat-bar { width: 50px; height: 6px; background: #F0F2EC; border-radius: 3px; overflow: hidden; }
        .sc-bat-fill { height: 100%; border-radius: 3px; }

        .sc-net-flow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 18px; }
        .sc-net-node { background: #fff; border: 1px solid #E5E8E0; border-radius: 10px;
          padding: 10px 14px; font-size: 13px; font-weight: 500; text-align: center; }
        .sc-net-node small { color: var(--color-muted,#8A938B); font-weight: 400; }
        .sc-net-ok { border-color: #4A7C59; }
        .sc-net-warn { border-color: var(--amber,#C25A1A); }
        .sc-net-col { display: flex; flex-direction: column; gap: 6px; }
        .sc-arr { color: var(--color-muted,#8A938B); font-size: 18px; }
        .sc-net-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 10px;
          overflow-y: auto; }
        .sc-net-card { background: #fff; border: 1px solid #E5E8E0; border-radius: 12px; padding: 12px; }
        .sc-net-card-id { font-weight: 700; font-size: 15px; }
        .sc-net-card-meta { font-size: 12px; color: var(--color-muted,#8A938B); margin: 4px 0; }
        .sc-net-card-link { font-size: 12px; color: var(--green-dark,#1B3A21); font-weight: 500; }

        .sc-fusao-grid { display: grid; grid-template-columns: 1fr 1.6fr; gap: 16px; }
        .sc-fusao-result { background: #fff; border: 1px solid #E5E8E0; border-radius: 14px; padding: 18px; }
        .sc-fr-big { font-size: 44px; font-weight: 600; font-variant-numeric: tabular-nums;
          color: var(--green-dark,#1B3A21); line-height: 1; }
        .sc-fr-big span { font-size: 15px; color: var(--color-muted,#8A938B); font-weight: 400; }
        .sc-fr-row { display: flex; justify-content: space-between; padding: 8px 0;
          border-bottom: 1px solid #F0F2EC; font-size: 14px; margin-top: 4px; }
        .sc-fr-row span { color: var(--color-muted,#8A938B); }
        .sc-fr-row b { font-variant-numeric: tabular-nums; }
        .sc-fusao-sources { background: #fff; border: 1px solid #E5E8E0; border-radius: 14px; padding: 18px; }
        .sc-fs-title { font-size: 12px; font-weight: 700; text-transform: uppercase;
          letter-spacing: 0.05em; color: var(--color-muted,#8A938B); margin-bottom: 14px; }
        .sc-fs-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
        .sc-fs-label { width: 110px; font-size: 13px; }
        .sc-fs-bar-wrap { flex: 1; height: 8px; background: #F0F2EC; border-radius: 4px; overflow: hidden; }
        .sc-fs-bar { height: 100%; background: var(--green-soft,#4A7C59); border-radius: 4px; }
        .sc-fs-val { width: 130px; font-size: 12px; text-align: right; font-variant-numeric: tabular-nums; }
        .sc-fs-val b { color: var(--green-dark,#1B3A21); }

        .sc-manut { display: flex; flex-direction: column; gap: 14px; min-height: 0; }
        .sc-manut-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px;
          overflow-y: auto; }
        .sc-manut-card { background: #fff; border: 1px solid #E5E8E0; border-radius: 12px; padding: 14px; }
        .sc-manut-id { font-weight: 700; margin-bottom: 10px; }
        .sc-manut-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
        .sc-manut-btns button { background: #FAFAF7; border: 1px solid #E5E8E0; border-radius: 8px;
          padding: 7px; font-size: 12px; cursor: pointer; color: #0D1A0F; font-family: inherit; }
        .sc-manut-btns button:hover { border-color: #4A7C59; background: #fff; }
        .sc-log { background: #0D1A0F; border-radius: 12px; padding: 14px; max-height: 200px; overflow-y: auto; }
        .sc-log-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
          color: #6FAF82; margin-bottom: 8px; }
        .sc-log-line { font-family: var(--font-dm-mono, monospace); font-size: 12px; color: #BFE0E8; padding: 2px 0; }

        @media (max-width: 720px) {
          .sc-fusao-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
