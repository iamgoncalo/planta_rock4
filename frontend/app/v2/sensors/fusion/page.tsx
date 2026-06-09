'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/v2-api';

/* ════════════════════════════════════════════════════════════════════
   /v2/sensors/fusion — CONSOLA DE SENSORES (NOC completo)
   Cada sensor clicavel. Cada botao responde (sim coerente / real MQTT).
   Tabs: Sensores · Rede · Fusão · Terminal.
   Interruptor Simulação/Real. Backend: /fleet /fusion /sensorctl /devices.
   ════════════════════════════════════════════════════════════════════ */

const REFRESH_MS = 6000;
const CLUSTERS = ['wc-01','wc-02','wc-03','wc-04','wc-05','wc-06','wc-07','wc-08'];

const GEO: Record<string,{e:number;n:number;uni:boolean}> = {
  'wc-01':{e:215.2,n:327.3,uni:false},'wc-02':{e:256.9,n:286.1,uni:false},
  'wc-03':{e:268.2,n:194.8,uni:false},'wc-04':{e:298.5,n:288.3,uni:false},
  'wc-05':{e:274.2,n:238.2,uni:true}, 'wc-06':{e:60.7,n:82.4,uni:true},
  'wc-07':{e:228.2,n:148.1,uni:false},'wc-08':{e:0,n:0,uni:false},
};
const SPAN_E=298.5, SPAN_N=327.3, PAD=30;

const TABS = [['sensores','Sensores'],['rede','Rede'],['fusao','Fusão'],['terminal','Terminal']];
const CMDS: [string,string][] = [
  ['ping','Ping'],['diagnostics','Diagnóstico'],['restart','Reiniciar'],
  ['reset_counters','Reset'],['calibrate','Calibrar'],['identify','Identificar'],['ota','OTA'],
];

function tipoLabel(t:string){return ({lilygo:'LilyGo',camera:'Câmara',ir:'Infravermelho',gateway_lora:'Gateway LoRa',ap_wifi:'Ponto WiFi'} as any)[t]||t;}
function statusColor(s:string){return s==='online'?'#4A7C59':s==='degraded'?'#C25A1A':s==='offline'?'#8A938B':s==='planned'?'#C9CEC4':'#C9CEC4';}
function statusLabel(s:string){return ({online:'Online',degraded:'Instável',offline:'Offline',maintenance:'Manutenção',planned:'Planeado','sem-dados':'Sem dados'} as any)[s]||s;}
function srcLabel(s:string){return ({camera:'Câmara',ir:'Infraverm.',wifi:'WiFi'} as any)[s]||s;}
function secLabel(s:string){return ({m:'Masculino',f:'Feminino',u:'Unissexo'} as any)[s]||s;}
function idadeLabel(s:number|null){
  if(s==null)return 'sem âncora';
  if(s<90)return `há ${Math.round(s)}s`;
  return `há ${Math.round(s/60)}min`;
}

type Sensor={id:string;tipo:string;cluster:string|null;status:string;modelo?:string;real?:boolean;link?:string;role?:string;origem?:string;battery?:{pct:number;fonte:string};};

export default function SensorConsole(){
  const [mode,setMode]=useState<'sim'|'real'>('sim');
  const [tab,setTab]=useState('sensores');
  const [fleet,setFleet]=useState<Sensor[]>([]);
  const [fusions,setFusions]=useState<Record<string,any>>({});
  const [filterCluster,setFilterCluster]=useState('todos');
  const [filterTipo,setFilterTipo]=useState('todos');
  const [selSensor,setSelSensor]=useState<Sensor|null>(null);
  const [detail,setDetail]=useState<any>(null);
  const [cmdResults,setCmdResults]=useState<any[]>([]);
  const [busy,setBusy]=useState<string|null>(null);
  const [selFusion,setSelFusion]=useState('wc-06');
  // terminal
  const [termLines,setTermLines]=useState<string[]>(['PlantaOS Device Terminal','Escreve help para ver comandos.','']);
  const [termInput,setTermInput]=useState('');
  const wsRef=useRef<WebSocket|null>(null);
  const termRef=useRef<HTMLDivElement>(null);
  const [lastUpdate,setLastUpdate]=useState<Date|null>(null);
  const [loading,setLoading]=useState(true);
  const [switching,setSwitching]=useState(false);

  // ler modo inicial
  useEffect(()=>{api.fleetMode().then((r:any)=>{if(r?.mode)setMode(r.mode);}).catch(()=>{});},[]);

  // polling fleet + fusao
  useEffect(()=>{
    let cancel=false;
    const load=async()=>{
      try{
        const f=await api.fleet(mode);
        if(cancel)return;
        setFleet(f.sensors||[]);
        const rs=await Promise.all(CLUSTERS.map(c=>api.fusion(c,mode).catch(()=>null)));
        if(cancel)return;
        const fu:Record<string,any>={};
        CLUSTERS.forEach((c,i)=>{if(rs[i])fu[c]=rs[i];});
        setFusions(fu);
        setLastUpdate(new Date());
        setLoading(false);
      }catch{setLoading(false);}
    };
    load();const iv=setInterval(load,REFRESH_MS);
    return()=>{cancel=true;clearInterval(iv);};
  },[mode]);

  // detalhe do sensor selecionado
  useEffect(()=>{
    if(!selSensor)return;
    setDetail(null);setCmdResults([]);
    api.sensorDetail(selSensor.id).then(setDetail).catch(()=>{});
  },[selSensor]);

  const toggleMode=async()=>{
    const next=mode==='sim'?'real':'sim';
    setSwitching(true);
    setMode(next);
    try{await api.setFleetMode(next);}catch{}
    setTimeout(()=>setSwitching(false),600);
  };

  const runCmd=async(cmd:string)=>{
    if(!selSensor)return;
    setBusy(cmd);
    try{
      const value=cmd==='calibrate'?20:undefined;
      const r=await api.sensorCmd(selSensor.id,cmd,value);
      setCmdResults((l)=>[{cmd,ts:new Date().toLocaleTimeString(),r},...l].slice(0,8));
    }catch(e:any){
      setCmdResults((l)=>[{cmd,ts:new Date().toLocaleTimeString(),r:{ok:false,resposta:'erro de rede'}},...l].slice(0,8));
    }
    setBusy(null);
  };

  // WebSocket terminal
  useEffect(()=>{
    if(tab!=='terminal')return;
    const proto=window.location.protocol==='https:'?'wss:':'ws:';
    const url=`${proto}//${(process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com').replace(/^https?:\/\//, '')}/api/v1/devices/terminal`;
    let ws:WebSocket;
    try{
      ws=new WebSocket(url);
      wsRef.current=ws;
      ws.onmessage=(ev)=>{
        try{const d=JSON.parse(ev.data);if(d.output){const clean=d.output.replace(/\x1b\[[0-9;]*m/g,'');setTermLines((l)=>[...l,clean].slice(-200));}}catch{}
      };
      ws.onerror=()=>setTermLines((l)=>[...l,'[erro de ligação ao terminal]']);
    }catch{}
    return()=>{try{ws&&ws.close();}catch{}};
  },[tab]);

  useEffect(()=>{if(termRef.current)termRef.current.scrollTop=termRef.current.scrollHeight;},[termLines]);

  const sendTerm=()=>{
    const cmd=termInput.trim();if(!cmd)return;
    setTermLines((l)=>[...l,`$ ${cmd}`]);
    try{wsRef.current?.send(JSON.stringify({command:cmd}));}catch{setTermLines((l)=>[...l,'[terminal offline]']);}
    setTermInput('');
  };

  const stats=useMemo(()=>{
    const online=fleet.filter(s=>s.status==='online').length;
    const bats=fleet.filter(s=>s.battery).map(s=>s.battery!.pct);
    const batAvg=bats.length?Math.round(bats.reduce((a,b)=>a+b,0)/bats.length):null;
    return {online,total:fleet.length,batAvg};
  },[fleet]);

  const filtered=useMemo(()=>fleet.filter(s=>
    (filterCluster==='todos'||s.cluster===filterCluster)&&
    (filterTipo==='todos'||s.tipo===filterTipo)
  ),[fleet,filterCluster,filterTipo]);

  return (
    <div className="sx-root">
      <div className="sx-head">
        <div>
          <div className="sx-eyebrow">PlantaOS · Consola de sensores</div>
          <h1 className="sx-title">Controlo da frota</h1>
        </div>
        <div className="sx-head-r">
          {lastUpdate && <div className="sx-upd">atualizado {lastUpdate.toLocaleTimeString()}</div>}
          <button className={`sx-mode ${mode} ${switching?'sw':''}`} onClick={toggleMode}>
            {mode==='sim'?'Simulação':'Dados reais'}
            <span>{switching?'a trocar…':'tocar para trocar'}</span>
          </button>
        </div>
      </div>

      <div className="sx-kpis">
        <div className="sx-kpi"><b>{stats.total}</b><span>sensores</span></div>
        <div className="sx-kpi"><b style={{color:'#4A7C59'}}>{stats.online}</b><span>online</span></div>
        <div className="sx-kpi"><b>{stats.batAvg!=null?stats.batAvg+'%':'—'}</b><span>bateria média</span></div>
        <div className="sx-kpi"><b className={mode==='sim'?'tsim':'treal'}>{mode==='sim'?'SIM':'REAL'}</b><span>origem</span></div>
      </div>

      <div className="sx-tabs">
        {TABS.map(([id,l])=><button key={id} className={`sx-tab ${tab===id?'on':''}`} onClick={()=>setTab(id)}>{l}</button>)}
      </div>

      <div className="sx-body">
        {/* SENSORES */}
        {tab==='sensores' && (
          <div className="sx-sensores">
            <div className="sx-filters">
              <select value={filterCluster} onChange={e=>setFilterCluster(e.target.value)}>
                <option value="todos">Todos os clusters</option>
                {CLUSTERS.map(c=><option key={c} value={c}>{c.toUpperCase()}</option>)}
              </select>
              <select value={filterTipo} onChange={e=>setFilterTipo(e.target.value)}>
                <option value="todos">Todos os tipos</option>
                {['lilygo','camera','ir','gateway_lora','ap_wifi'].map(t=><option key={t} value={t}>{tipoLabel(t)}</option>)}
              </select>
              <span className="sx-count">{filtered.length} sensores</span>
            </div>
            <div className="sx-grid">
              {loading && fleet.length===0 && Array.from({length:12}).map((_,i)=>(
                <div key={'sk'+i} className="sx-card sx-skel"/>
              ))}
              {filtered.map(s=>{
                const isPlanned=s.status==='planned';
                return (
                <button key={s.id} className={`sx-card ${selSensor?.id===s.id?'sel':''} st-${s.status||'unknown'}`} onClick={()=>setSelSensor(s)}>
                  <div className="sx-card-top">
                    <span className="sx-dot" style={{background:statusColor(s.status)}}/>
                    <span className="sx-card-tipo">{tipoLabel(s.tipo)}</span>
                    {s.cluster&&<span className="sx-card-cluster">{s.cluster.replace('wc-','').toUpperCase()}</span>}
                  </div>
                  <div className="sx-card-id">{s.id}</div>
                  <div className="sx-card-bot">
                    <span className="sx-card-st">{statusLabel(s.status)}</span>
                    {s.battery&&(
                      <span className="sx-card-bat" title={`bateria ${s.battery.pct}%`}>
                        <span className="sx-batbar"><span className="sx-batfill" style={{width:`${s.battery.pct}%`}}/></span>
                        {s.battery.pct}%
                      </span>
                    )}
                    {s.modelo&&!s.battery&&<span className="sx-card-mod">{s.modelo}</span>}
                  </div>
                </button>
                );
              })}
            </div>
          </div>
        )}

        {/* REDE */}
        {tab==='rede' && (
          <div className="sx-rede">
            <div className="sx-flow">
              <div className="sx-fn">IR<small>elétrico</small></div><span>→</span>
              <div className="sx-fn">LilyGo<small>powerbank</small></div><span>→</span>
              <div className="sx-fcol">
                <div className="sx-fn ok">WiFi 6E + mesh<small>central</small></div>
                <div className="sx-fn warn">LoRa + SIM<small>WC-06/08</small></div>
              </div><span>→</span>
              <div className="sx-fn">4G<small>NOS+Vodafone</small></div><span>→</span>
              <div className="sx-fn ok">Railway<small>fusão</small></div>
            </div>
            <div className="sx-net-grid">
              {CLUSTERS.map(c=>{
                const sens=fleet.filter(s=>s.cluster===c);
                const on=sens.filter(s=>s.status==='online').length;
                const lily=sens.filter(s=>s.tipo==='lilygo').length;
                const iso=c==='wc-06'||c==='wc-08';
                return (
                  <div key={c} className="sx-net-card">
                    <div className="sx-net-id">{c.toUpperCase()}</div>
                    <div className="sx-net-row"><span>Sensores</span><b>{on}/{sens.length}</b></div>
                    <div className="sx-net-row"><span>LilyGo</span><b>{lily}</b></div>
                    <div className="sx-net-link" style={{color:iso?'#C25A1A':'#1B3A21'}}>{iso?'LoRa + SIM 4G':'WiFi + mesh'}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* FUSAO */}
        {tab==='fusao' && (
          <div className="sx-fusao">
            <div className="sx-filters">
              {CLUSTERS.map(c=><button key={c} className={`sx-chip ${selFusion===c?'on':''}`} onClick={()=>setSelFusion(c)}>{c.toUpperCase()}</button>)}
            </div>
            {(()=>{
              const f=fusions[selFusion];
              if(!f)return <p className="sx-soft">A carregar…</p>;
              const seccoes=Object.entries(f.seccoes||{}) as [string,any][];
              // tem fusão se o backend não disse explicitamente "sem-dados"
              // e devolveu uma contagem (robusto a versões sem campo estado)
              const temFusao=f.estado!=='sem-dados'&&f.pessoas!=null;
              return (
                <>
                  {!temFusao ? (
                    <div className="sx-fusao-empty">
                      <p>Sem dados para {selFusion.toUpperCase()}.</p>
                      <p className="sx-soft">
                        Fontes previstas: {(f.fontes_disponiveis||[]).map(srcLabel).join(' · ')||'—'}
                        {mode==='real'
                          ? ' — instalação no terreno a 11–12 Jun; até lá usa o modo Simulação.'
                          : ''}
                      </p>
                    </div>
                  ) : (
                    <div className="sx-fusao-grid">
                      <div className="sx-fcard">
                        <div className="sx-fbig">{f.pessoas}<span> pessoas</span></div>
                        <div className="sx-fobar"><div className="sx-fofill" style={{width:`${Math.min(100,f.ocupacao_pct)}%`,background:f.ocupacao_pct>=90?'#C25A1A':f.ocupacao_pct>=70?'#D98A4A':'#4A7C59'}}/></div>
                        <div className="sx-soft">{f.ocupacao_pct}% de {f.capacidade_dentro} · fila {f.fila_atual} · espera {f.tempo_espera_min}min</div>
                        <div className={`sx-prov ${f.data_source}`}>{f.data_source==='simulado'?'simulado':f.data_source==='real'?'real':f.data_source==='stale'?'desatualizado':'sem dados'}</div>
                      </div>
                      <div className="sx-fcard">
                        <div className="sx-fs-t">Fontes & pesos · confiança {Math.round((f.confianca||0)*100)}%</div>
                        {Object.entries(f.pesos||{}).map(([src,w]:any)=>(
                          <div key={src} className="sx-fs-row">
                            <div className="sx-fs-l">{srcLabel(src)}</div>
                            <div className="sx-fs-track"><div className="sx-fs-bar" style={{width:`${w*100}%`}}/></div>
                            <div className="sx-fs-v"><b>{Math.round(w*100)}%</b> · {f.estimativas_por_fonte?.[src]??'—'}</div>
                          </div>
                        ))}
                        <p className="sx-soft" style={{marginTop:10,fontSize:12}}>Pesos adaptam-se quando uma fonte cai. Confiança sobe com concordância.</p>
                      </div>
                    </div>
                  )}

                  {/* FUSÃO ROLANTE — cabeças + WiFi por bandas, por secção */}
                  <div className="sx-fs-t" style={{margin:'18px 0 10px'}}>
                    Fusão rolante · contagem de cabeças + WiFi por bandas
                  </div>
                  {seccoes.length===0 ? (
                    <div className="sx-fcard">
                      <p className="sx-soft" style={{margin:0,fontSize:13}}>
                        Ainda sem ingestão para {selFusion.toUpperCase()} — aguarda contagens de
                        cabeças e POSTs WiFi dos nós ({GEO[selFusion]?.uni?'2 nós · secção única':'3 nós por secção M/F'}).
                      </p>
                    </div>
                  ) : (
                    <div className="sx-rol-grid">
                      {seccoes.map(([sec,r])=>(
                        <div key={sec} className="sx-fcard">
                          <div className="sx-rol-head">
                            <b>{secLabel(sec)}</b>
                            {r.flag_anomalia
                              ? <span className="sx-rol-flag warn">anomalia travada</span>
                              : <span className="sx-rol-flag ok">{r.fonte_wifi==='online'?'wifi online':'wifi offline'}</span>}
                          </div>
                          <div className="sx-fbig" style={{fontSize:34}}>{Math.round(r.ocupacao)}<span> dentro · cap {r.capacidade}</span></div>
                          <div className="sx-fobar"><div className="sx-fofill" style={{width:`${Math.min(100,(r.ocupacao/Math.max(r.capacidade,1))*100)}%`,background:(r.ocupacao/Math.max(r.capacidade,1))>=.9?'#C25A1A':(r.ocupacao/Math.max(r.capacidade,1))>=.7?'#D98A4A':'#4A7C59'}}/></div>
                          <div className="sx-rol-rows">
                            <div><span>Fila estimada</span><b>{Math.round(r.fila_estimada)}</b></div>
                            <div><span>Confiança cruzada</span><b>{Math.round((r.confianca_cruzada||0)*100)}%</b></div>
                            <div><span>Coeficiente a</span><b>{r.a_actual}</b></div>
                            <div><span>Âncora (cabeças)</span><b>{idadeLabel(r.idade_ancora_s)}</b></div>
                            <div><span>Nós WiFi</span><b>{r.nos_online}/{r.nos_totais} online</b></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}

        {/* TERMINAL */}
        {tab==='terminal' && (
          <div className="sx-terminal">
            <div className="sx-term-out" ref={termRef}>
              {termLines.map((l,i)=><div key={i} className="sx-term-line">{l}</div>)}
            </div>
            <div className="sx-term-in">
              <span>$</span>
              <input value={termInput} onChange={e=>setTermInput(e.target.value)}
                onKeyDown={e=>{if(e.key==='Enter')sendTerm();}}
                placeholder="scan · status all · ping WC-06 · diagnostics WC-06 · help" autoFocus/>
              <button onClick={sendTerm}>Enviar</button>
            </div>
            <p className="sx-soft" style={{fontSize:12,marginTop:8}}>Ligado ao terminal de dispositivos. Os comandos chegam ao hardware via MQTT (ou respondem em simulação).</p>
          </div>
        )}
      </div>

      {/* DRAWER DO SENSOR — botões que respondem */}
      {selSensor && (
        <div className="sx-drawer-bg" onClick={()=>setSelSensor(null)}>
          <div className="sx-drawer" onClick={e=>e.stopPropagation()}>
            <div className="sx-dr-head">
              <div>
                <div className="sx-dr-id">{selSensor.id}</div>
                <div className="sx-dr-tipo">{tipoLabel(selSensor.tipo)} · {selSensor.cluster?.toUpperCase()}</div>
              </div>
              <button className="sx-x" onClick={()=>setSelSensor(null)}>&times;</button>
            </div>

            {detail ? (
              <div className="sx-dr-rows">
                {detail.modelo&&detail.real&&<div className="sx-dr-badge">{detail.modelo}</div>}
                <div><span>Estado</span><b style={{color:statusColor(detail.status)}}>{statusLabel(detail.status)}</b></div>
                {detail.battery&&<div><span>Bateria</span><b>{detail.battery.pct}% ({detail.battery.fonte})</b></div>}
                {detail.uptime_s!=null&&<div><span>Uptime</span><b>{Math.floor(detail.uptime_s/3600)}h {Math.floor((detail.uptime_s%3600)/60)}m</b></div>}
                {detail.rssi_dbm!=null&&<div><span>Sinal</span><b>{detail.rssi_dbm} dBm</b></div>}
                <div><span>Ligação</span><b>{detail.link||'—'}</b></div>
                <div><span>Alimentação</span><b>{detail.power||'—'}</b></div>
                <div><span>Origem</span><b>{detail.origem||mode}</b></div>
              </div>
            ) : <p className="sx-soft">A carregar detalhe…</p>}

            <div className="sx-dr-cmds-t">Comandos</div>
            <div className="sx-dr-cmds">
              {CMDS.map(([cmd,label])=>(
                <button key={cmd} disabled={busy===cmd} onClick={()=>runCmd(cmd)} className={busy===cmd?'busy':''}>
                  {busy===cmd?'…':label}
                </button>
              ))}
            </div>

            <div className="sx-dr-results">
              {cmdResults.length===0?<div className="sx-soft" style={{fontSize:12}}>Carrega num botão — a resposta aparece aqui.</div>:
                cmdResults.map((cr,i)=>(
                  <div key={i} className="sx-res">
                    <div className="sx-res-head"><b>{cr.cmd}</b><span>{cr.ts}</span></div>
                    {cr.r.resposta && <div className={`sx-res-msg ${cr.r.ok===false?'fail':'ok'}`}>{cr.r.resposta}</div>}
                    {cr.r.diagnostico && (
                      <div className="sx-res-diag">
                        {Object.entries(cr.r.diagnostico).map(([k,v]:any)=>(
                          <div key={k}><span>{k}</span><b>{String(v)}</b></div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              }
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .sx-root{height:calc(100vh - 72px);display:flex;flex-direction:column;overflow:hidden;color:#0D1A0F;}
        .sx-head{display:flex;justify-content:space-between;align-items:flex-end;padding:18px clamp(16px,2.6vw,32px) 4px;flex-shrink:0;}
        .sx-eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#8A938B;}
        .sx-title{font-size:clamp(20px,2.6vw,30px);font-weight:600;margin:2px 0 0;}
        .sx-mode{display:flex;flex-direction:column;align-items:flex-start;border:none;border-radius:12px;padding:8px 18px;cursor:pointer;font-family:inherit;font-size:15px;font-weight:600;color:#fff;transition:all .2s;}
        .sx-mode.sim{background:#1B3A21;} .sx-mode.real{background:#C25A1A;}
        .sx-mode span{font-size:10px;font-weight:400;opacity:.75;}
        .sx-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:10px clamp(16px,2.6vw,32px) 0;flex-shrink:0;}
        .sx-kpi{background:#fff;border:1px solid #E5E8E0;border-radius:10px;padding:10px 12px;}
        .sx-kpi b{display:block;font-size:22px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums;color:#1B3A21;}
        .sx-kpi span{font-size:11px;color:#8A938B;margin-top:3px;display:block;}
        .tsim{color:#1B3A21!important;} .treal{color:#C25A1A!important;}
        .sx-tabs{display:flex;gap:6px;padding:10px clamp(16px,2.6vw,32px);flex-shrink:0;}
        .sx-tab{background:#fff;border:1px solid #E5E8E0;border-radius:999px;padding:7px 16px;font-size:13px;cursor:pointer;color:#0D1A0F;font-family:inherit;}
        .sx-tab.on{background:#1B3A21;border-color:#1B3A21;color:#fff;font-weight:600;}
        .sx-body{flex:1;min-height:0;overflow:hidden;padding:0 clamp(16px,2.6vw,32px) 18px;display:flex;flex-direction:column;}

        .sx-sensores{display:flex;flex-direction:column;min-height:0;flex:1;}
        .sx-filters{display:flex;gap:10px;align-items:center;flex-shrink:0;margin-bottom:10px;flex-wrap:wrap;}
        .sx-filters select{border:1px solid #E5E8E0;border-radius:8px;padding:7px 12px;font-family:inherit;font-size:13px;background:#fff;color:#0D1A0F;}
        .sx-count{font-size:12px;color:#8A938B;}
        .sx-grid{flex:1;min-height:0;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;align-content:start;}
        .sx-card{background:#fff;border:1px solid #E5E8E0;border-radius:12px;padding:11px 12px;cursor:pointer;text-align:left;font-family:inherit;transition:all .14s;display:flex;flex-direction:column;gap:6px;min-height:88px;}
        .sx-card:hover{border-color:#4A7C59;transform:translateY(-1px);box-shadow:0 4px 12px rgba(27,58,33,.08);}
        .sx-card.sel{border-color:#1B3A21;border-width:2px;padding:10px 11px;}
        .sx-card.st-online{background:linear-gradient(180deg,#FAFCF9 0%,#FFFFFF 100%);}
        .sx-card.st-planned{opacity:.78;}
        .sx-card-top{display:flex;align-items:center;gap:6px;}
        .sx-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;box-shadow:0 0 0 2px rgba(74,124,89,.12);}
        .sx-card.st-online .sx-dot{box-shadow:0 0 0 2px rgba(74,124,89,.18),0 0 6px rgba(74,124,89,.35);}
        .sx-card-tipo{font-size:10px;color:#8A938B;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}
        .sx-card-cluster{margin-left:auto;font-size:10px;font-weight:700;color:#1B3A21;background:#E8F1EA;border-radius:4px;padding:1px 6px;font-family:monospace;}
        .sx-card-id{font-family:monospace;font-size:12.5px;font-weight:600;line-height:1.2;color:#0D1A0F;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
        .sx-card-bot{display:flex;justify-content:space-between;align-items:center;margin-top:auto;gap:6px;min-width:0;}
        .sx-card-st{font-size:10.5px;color:#8A938B;flex-shrink:0;}
        .sx-card.st-online .sx-card-st{color:#4A7C59;font-weight:600;}
        .sx-card.st-degraded .sx-card-st{color:#C25A1A;font-weight:600;}
        .sx-card-mod{font-size:10px;background:#E8F1EA;color:#1B3A21;border-radius:5px;padding:2px 7px;font-weight:600;flex-shrink:0;}
        .sx-card-bat{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:600;font-variant-numeric:tabular-nums;color:#4A7C59;flex-shrink:0;}
        .sx-batbar{width:32px;height:5px;background:#F0F2EC;border-radius:3px;overflow:hidden;}
        .sx-batfill{display:block;height:100%;background:linear-gradient(90deg,#4A7C59,#6FAF82);border-radius:3px;}

        .sx-rede{display:flex;flex-direction:column;gap:16px;min-height:0;overflow-y:auto;}
        .sx-flow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
        .sx-flow span{color:#8A938B;}
        .sx-fn{background:#fff;border:1px solid #E5E8E0;border-radius:10px;padding:10px 14px;font-size:13px;text-align:center;display:flex;flex-direction:column;}
        .sx-fn small{color:#8A938B;font-size:10px;}
        .sx-fn.ok{border-color:#4A7C59;} .sx-fn.warn{border-color:#C25A1A;}
        .sx-fcol{display:flex;flex-direction:column;gap:6px;}
        .sx-net-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;}
        .sx-net-card{background:#fff;border:1px solid #E5E8E0;border-radius:12px;padding:12px;}
        .sx-net-id{font-weight:700;margin-bottom:8px;}
        .sx-net-row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0;}
        .sx-net-row span{color:#8A938B;}
        .sx-net-link{font-size:12px;font-weight:500;margin-top:6px;}

        .sx-fusao{display:flex;flex-direction:column;min-height:0;overflow-y:auto;}
        .sx-chip{background:#fff;border:1px solid #E5E8E0;border-radius:999px;padding:5px 12px;font-size:12px;cursor:pointer;color:#0D1A0F;font-family:inherit;}
        .sx-chip.on{background:#1B3A21;border-color:#1B3A21;color:#fff;}
        .sx-fusao-grid{display:grid;grid-template-columns:1fr 1.4fr;gap:14px;}
        .sx-fcard{background:#fff;border:1px solid #E5E8E0;border-radius:14px;padding:16px;position:relative;}
        .sx-fbig{font-size:42px;font-weight:600;line-height:1;color:#1B3A21;font-variant-numeric:tabular-nums;}
        .sx-fbig span{font-size:14px;color:#8A938B;font-weight:400;}
        .sx-fobar{height:10px;background:#F0F2EC;border-radius:5px;overflow:hidden;margin:12px 0 5px;}
        .sx-fofill{height:100%;border-radius:5px;transition:width .6s;}
        .sx-prov{position:absolute;top:14px;right:14px;font-size:11px;font-weight:600;padding:3px 9px;border-radius:6px;}
        .sx-prov.simulado{background:#E8F1EA;color:#1B3A21;} .sx-prov.real{background:#DEF0E4;color:#1B3A21;}
        .sx-prov.stale{background:#F5E6D8;color:#C25A1A;} .sx-prov.none{background:#F0F2EC;color:#8A938B;}
        .sx-fs-t{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#8A938B;margin-bottom:12px;}
        .sx-fs-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;}
        .sx-fs-l{width:90px;font-size:13px;}
        .sx-fs-track{flex:1;height:8px;background:#F0F2EC;border-radius:4px;overflow:hidden;}
        .sx-fs-bar{height:100%;background:#4A7C59;border-radius:4px;transition:width .6s;}
        .sx-fs-v{width:90px;text-align:right;font-size:12px;font-variant-numeric:tabular-nums;}
        .sx-fs-v b{color:#1B3A21;}
        .sx-fusao-empty{padding:30px 0;text-align:center;}
        .sx-rol-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;}
        .sx-rol-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
        .sx-rol-head b{font-size:14px;color:#1B3A21;}
        .sx-rol-flag{font-size:10.5px;font-weight:600;padding:3px 9px;border-radius:6px;}
        .sx-rol-flag.ok{background:#E8F1EA;color:#1B3A21;}
        .sx-rol-flag.warn{background:#F5E6D8;color:#C25A1A;}
        .sx-rol-rows{margin-top:10px;}
        .sx-rol-rows div{display:flex;justify-content:space-between;font-size:12.5px;padding:4px 0;border-bottom:1px solid #F0F2EC;}
        .sx-rol-rows div:last-child{border-bottom:none;}
        .sx-rol-rows span{color:#8A938B;}
        .sx-rol-rows b{font-variant-numeric:tabular-nums;color:#0D1A0F;}

        .sx-terminal{display:flex;flex-direction:column;min-height:0;flex:1;}
        .sx-term-out{flex:1;min-height:0;overflow-y:auto;background:#0D1A0F;border-radius:12px 12px 0 0;padding:14px;font-family:monospace;font-size:13px;color:#BFE0E8;}
        .sx-term-line{white-space:pre-wrap;line-height:1.5;}
        .sx-term-in{display:flex;align-items:center;gap:8px;background:#0A140C;border-radius:0 0 12px 12px;padding:10px 14px;}
        .sx-term-in span{color:#6FAF82;font-family:monospace;}
        .sx-term-in input{flex:1;background:none;border:none;outline:none;color:#fff;font-family:monospace;font-size:13px;}
        .sx-term-in button{background:#1B3A21;color:#fff;border:none;border-radius:8px;padding:7px 16px;font-size:13px;cursor:pointer;font-family:inherit;}

        .sx-soft{color:#8A938B;}
        .sx-drawer-bg{position:fixed;inset:0;background:rgba(13,26,15,.3);z-index:50;display:flex;justify-content:flex-end;}
        .sx-drawer{width:420px;max-width:92vw;background:#fff;height:100%;padding:20px;overflow-y:auto;box-shadow:-8px 0 30px rgba(0,0,0,.12);}
        .sx-dr-head{display:flex;justify-content:space-between;align-items:flex-start;}
        .sx-dr-id{font-family:monospace;font-size:15px;font-weight:700;}
        .sx-dr-tipo{font-size:12px;color:#8A938B;margin-top:2px;}
        .sx-x{background:none;border:none;font-size:22px;cursor:pointer;color:#8A938B;line-height:1;}
        .sx-dr-badge{display:inline-block;background:#E8F1EA;color:#1B3A21;border-radius:6px;padding:3px 10px;font-size:12px;font-weight:600;margin-bottom:8px;}
        .sx-dr-rows{margin-top:14px;}
        .sx-dr-rows div{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F0F2EC;font-size:14px;}
        .sx-dr-rows span{color:#8A938B;}
        .sx-dr-cmds-t{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#8A938B;margin:18px 0 10px;}
        .sx-dr-cmds{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}
        .sx-dr-cmds button{background:#1B3A21;color:#fff;border:none;border-radius:8px;padding:9px;font-size:13px;cursor:pointer;font-family:inherit;transition:all .14s;}
        .sx-dr-cmds button:hover{background:#2A5232;}
        .sx-dr-cmds button.busy{background:#8A938B;}
        .sx-dr-results{margin-top:16px;}
        .sx-res{background:#FAFAF7;border:1px solid #F0F2EC;border-radius:10px;padding:12px;margin-bottom:8px;}
        .sx-res-head{display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;}
        .sx-res-head b{color:#1B3A21;text-transform:capitalize;}
        .sx-res-head span{color:#8A938B;}
        .sx-res-msg{font-size:13px;font-family:monospace;padding:6px 8px;border-radius:6px;}
        .sx-res-msg.ok{background:#E8F1EA;color:#1B3A21;} .sx-res-msg.fail{background:#F5E6D8;color:#C25A1A;}
        .sx-res-diag{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;margin-top:4px;}
        .sx-res-diag div{display:flex;justify-content:space-between;font-size:12px;padding:2px 0;}
        .sx-res-diag span{color:#8A938B;} .sx-res-diag b{font-variant-numeric:tabular-nums;}

        .sx-head-r{display:flex;align-items:center;gap:12px;}
        .sx-upd{font-size:11px;color:#8A938B;font-variant-numeric:tabular-nums;}
        .sx-mode.sw{opacity:.7;}
        .sx-skel{background:linear-gradient(90deg,#F0F2EC 25%,#E5E8E0 50%,#F0F2EC 75%);background-size:200% 100%;animation:sk 1.4s infinite;border:1px solid #E5E8E0;min-height:78px;}
        @keyframes sk{0%{background-position:200% 0;}100%{background-position:-200% 0;}}
        @media (max-width:820px){.sx-kpis{grid-template-columns:repeat(2,1fr);}.sx-fusao-grid{grid-template-columns:1fr;}.sx-head-r{flex-direction:column;align-items:flex-end;gap:4px;}}
      `}</style>
    </div>
  );
}
