'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/v2-api';
import { envApi } from '@/lib/v2-api-envs';

/* ════════════════════════════════════════════════════════════════════
   /v2/sensors — PAGINA DOS SENSORES (focada).
   Topo: seletor de ambiente. Botao + adicionar sensor. Grelha viva dos
   sensores. Clica num -> painel com Ping/Diagnostico/Identificar/Remover.
   Sem terminal, sem multiplas tabs, sem confusao.
   ════════════════════════════════════════════════════════════════════ */

const TIPOS = [
  { id:'lilygo', label:'LilyGo (gateway)', icone:'⊙' },
  { id:'camera', label:'Câmara (OAK/ESP32-CAM)', icone:'◉' },
  { id:'ir', label:'Infravermelho (porta)', icone:'│' },
  { id:'gateway_lora', label:'Gateway LoRa', icone:'⟜' },
  { id:'ap_wifi', label:'Ponto de acesso WiFi', icone:'≋' },
];
const CMDS: [string,string][] = [
  ['ping','Ping'],['diagnostics','Diagnóstico'],['identify','Identificar'],['restart','Reiniciar'],
];

function tipoLabel(t:string){return ({lilygo:'LilyGo',camera:'Câmara',ir:'Infravermelho',gateway_lora:'Gateway LoRa',ap_wifi:'Ponto WiFi'} as any)[t]||t;}
function statusColor(s:string){return s==='online'?'#4A7C59':s==='degraded'?'#C25A1A':s==='offline'?'#8A938B':'#C9CEC4';}
function statusLabel(s:string){return ({online:'Online',degraded:'Instável',offline:'Offline','sem-dados':'Sem dados',planned:'Planeado'} as any)[s]||s;}

type Env = {id:string; nome:string; modo:string; refresh_ms:number; fixo?:boolean; n_sensores?:number};
type Sensor = {id:string; tipo:string; cluster?:string|null; status?:string; label?:string; battery?:{pct:number;fonte:string}; rssi_dbm?:number; uptime_s?:number; origem?:string; data_origin?:string; age_s?:number};

export default function SensorsPage(){
  const [envs,setEnvs]=useState<Env[]>([]);
  const [activeEnv,setActiveEnv]=useState<string>('rock-in-rio');
  const [sensors,setSensors]=useState<Sensor[]>([]);
  const [loading,setLoading]=useState(true);
  const [lastUpdate,setLastUpdate]=useState<Date|null>(null);
  // dialogs
  const [showAdd,setShowAdd]=useState(false);
  const [showNewEnv,setShowNewEnv]=useState(false);
  // sensor selecionado
  const [selSensor,setSelSensor]=useState<Sensor|null>(null);
  const [detail,setDetail]=useState<any>(null);
  const [cmdResults,setCmdResults]=useState<any[]>([]);
  const [busy,setBusy]=useState<string|null>(null);
  // confirmar remoção
  const [confirmRemove,setConfirmRemove]=useState<string|null>(null);
  // toast
  const [toast,setToast]=useState<{msg:string;kind:'ok'|'erro'}|null>(null);
  // bulk add
  const [showBulk,setShowBulk]=useState(false);
  const [bulkTab,setBulkTab]=useState<'gen'|'list'>('gen');
  const [bulkGen,setBulkGen]=useState({prefixo:'wc-02',tipo:'ir',quantidade:8});
  const [bulkText,setBulkText]=useState('');
  // capacidades do sensor
  const [caps,setCaps]=useState<any>(null);
  // modo demo (hora)
  const [demoHour,setDemoHour]=useState<number|null>(null);

  const toastIt=(msg:string,kind:'ok'|'erro'='ok')=>{
    setToast({msg,kind});setTimeout(()=>setToast(null),3000);
  };

  // carregar ambientes
  const loadEnvs=async()=>{
    try{
      const r=await envApi.list();
      const list=r.envs||[];
      setEnvs(list);
      if(!list.find((e:Env)=>e.id===activeEnv) && list.length>0){
        setActiveEnv(list[0].id);
      }
    }catch{toastIt('erro a carregar ambientes','erro');}
  };

  // carregar sensores do ambiente ativo
  const loadSensors=async()=>{
    try{
      const r=await envApi.fleet(activeEnv);
      setSensors(r.sensors||[]);
      setLastUpdate(new Date());
      setLoading(false);
    }catch(e:any){
      setSensors([]);setLoading(false);
      toastIt(`erro a carregar sensores: ${String(e?.message||e).slice(0,40)}`,'erro');
    }
  };

  useEffect(()=>{loadEnvs();envApi.getDemoHour().then((r:any)=>setDemoHour(r.hora_forcada)).catch(()=>{});},[]);
  useEffect(()=>{
    if(!activeEnv)return;
    setLoading(true);
    loadSensors();
    // polling com refresh do ambiente
    const env=envs.find(e=>e.id===activeEnv);
    const ms=env?.refresh_ms||3000;
    const iv=setInterval(loadSensors,ms);
    return()=>clearInterval(iv);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[activeEnv,envs.length]);

  // detalhe do sensor
  useEffect(()=>{
    if(!selSensor)return;
    setDetail(null);setCmdResults([]);
    api.sensorDetail(selSensor.id).then(setDetail).catch(()=>setDetail({erro:'sem detalhe'}));
    setCaps(null);
    envApi.caps(selSensor.id, selSensor.tipo, selSensor.cluster||undefined, selSensor.rssi_dbm)
      .then(setCaps).catch(()=>{});
  },[selSensor]);

  const runCmd=async(cmd:string)=>{
    if(!selSensor)return;
    setBusy(cmd);
    try{
      const r=await api.sensorCmd(selSensor.id,cmd);
      setCmdResults((l)=>[{cmd,ts:new Date().toLocaleTimeString(),r},...l].slice(0,6));
    }catch{
      setCmdResults((l)=>[{cmd,ts:new Date().toLocaleTimeString(),r:{ok:false,resposta:'erro de rede'}},...l].slice(0,6));
    }
    setBusy(null);
  };

  const env=envs.find(e=>e.id===activeEnv);
  const fixo=env?.fixo;

  const stats=useMemo(()=>{
    const total=sensors.length;
    const reais=sensors.filter(s=>s.data_origin==='real').length;
    const sim=sensors.filter(s=>s.data_origin==='simulado').length;
    const mudos=sensors.filter(s=>s.data_origin==='real-mudo').length;
    const bats=sensors.filter(s=>s.battery).map(s=>s.battery!.pct);
    const batAvg=bats.length?Math.round(bats.reduce((a,b)=>a+b,0)/bats.length):null;
    return {total,reais,sim,mudos,batAvg};
  },[sensors]);

  // adicionar sensor
  const [newSensor,setNewSensor]=useState({id:'',tipo:'lilygo',label:''});
  const submitAdd=async()=>{
    if(!newSensor.id.trim()){toastIt('ID em falta','erro');return;}
    try{
      await envApi.addSensor(activeEnv,{id:newSensor.id.trim(),tipo:newSensor.tipo,label:newSensor.label.trim()});
      toastIt(`sensor ${newSensor.id} adicionado`);
      setShowAdd(false);setNewSensor({id:'',tipo:'lilygo',label:''});
      loadSensors();loadEnvs();
    }catch(e:any){toastIt(`erro: ${String(e?.message||e).slice(0,40)}`,'erro');}
  };
  // remover sensor
  const doRemove=async(sid:string)=>{
    try{
      await envApi.removeSensor(activeEnv,sid);
      toastIt(`removido ${sid}`);
      setConfirmRemove(null);setSelSensor(null);
      loadSensors();loadEnvs();
    }catch(e:any){toastIt(`erro: ${String(e?.message||e).slice(0,40)}`,'erro');}
  };

  // adicionar em massa — gerar
  const submitBulkGen=async()=>{
    try{
      const r=await envApi.bulkGen(activeEnv,{prefixo:bulkGen.prefixo.trim(),tipo:bulkGen.tipo,quantidade:bulkGen.quantidade});
      toastIt(`${r.adicionados.length} sensores criados${r.ignorados.length?` (${r.ignorados.length} já existiam)`:''}`);
      setShowBulk(false);loadSensors();loadEnvs();
    }catch(e:any){toastIt(`erro: ${String(e?.message||e).slice(0,40)}`,'erro');}
  };
  // adicionar em massa — colar lista
  const submitBulkList=async()=>{
    const linhas=bulkText.split('\n').map(l=>l.trim()).filter(Boolean);
    if(linhas.length===0){toastIt('lista vazia','erro');return;}
    const sensores=linhas.map(linha=>{
      const partes=linha.split(/[,;\s]+/);
      const id=partes[0];
      let tipo='lilygo';
      const low=id.toLowerCase();
      if(low.includes('cam'))tipo='camera';else if(low.includes('ir'))tipo='ir';
      else if(low.includes('lora')||low.includes('gateway'))tipo='gateway_lora';
      else if(low.includes('wifi')||low.includes('ap'))tipo='ap_wifi';
      if(partes[1])tipo=partes[1];
      return {id,tipo};
    });
    try{
      const r=await envApi.bulkList(activeEnv,sensores);
      toastIt(`${r.adicionados.length} adicionados${r.ignorados.length?` · ${r.ignorados.length} ignorados`:''}`);
      setShowBulk(false);setBulkText('');loadSensors();loadEnvs();
    }catch(e:any){toastIt(`erro: ${String(e?.message||e).slice(0,40)}`,'erro');}
  };
  // modo demo
  const toggleDemoHour=async(h:number|null)=>{
    try{
      const r=await envApi.setDemoHour(h==null?-1:h);
      setDemoHour(r.hora_forcada);
      toastIt(h==null?'hora real':`hora forçada: ${h}h`);
      loadSensors();
    }catch(e:any){toastIt('erro a mudar hora','erro');}
  };

  // criar ambiente
  const [newEnv,setNewEnv]=useState({nome:'',refresh_ms:1500,modo:'real'});
  const submitNewEnv=async()=>{
    if(!newEnv.nome.trim()){toastIt('nome em falta','erro');return;}
    try{
      const r=await envApi.create({nome:newEnv.nome.trim(),modo:newEnv.modo,refresh_ms:newEnv.refresh_ms});
      toastIt(`ambiente "${r.nome}" criado`);
      setShowNewEnv(false);setNewEnv({nome:'',refresh_ms:1500,modo:'real'});
      await loadEnvs();
      setActiveEnv(r.id);
    }catch(e:any){toastIt(`erro: ${String(e?.message||e).slice(0,40)}`,'erro');}
  };

  return (
    <div className="sn-root">
      <div className="sn-head">
        <div>
          <div className="sn-eyebrow">PlantaOS · Sensores</div>
          <h1 className="sn-title">Os meus sensores</h1>
        </div>
        {lastUpdate && <div className="sn-upd">atualizado {lastUpdate.toLocaleTimeString()}</div>}
      </div>

      {/* SELETOR DE AMBIENTES */}
      <div className="sn-envs">
        <div className="sn-envs-label">Ambiente</div>
        <div className="sn-envs-tabs">
          {envs.map(e=>(
            <button key={e.id} className={`sn-env ${activeEnv===e.id?'on':''} ${e.fixo?'fixo':''}`} onClick={()=>setActiveEnv(e.id)}>
              <span className="sn-env-nome">{e.nome}</span>
              <span className="sn-env-meta">{e.n_sensores ?? '—'} sensores · {e.refresh_ms}ms</span>
            </button>
          ))}
          <button className="sn-env-new" onClick={()=>setShowNewEnv(true)}>＋ novo ambiente</button>
        </div>
      </div>

      {/* KPIs */}
      <div className="sn-kpis">
        <div className="sn-kpi"><b>{stats.total}</b><span>sensores neste ambiente</span></div>
        <div className="sn-kpi sn-kpi-real"><b>{stats.reais}</b><span>REAIS (dados verdadeiros)</span></div>
        <div className="sn-kpi sn-kpi-sim"><b>{stats.sim}</b><span>simulados (demo)</span></div>
        <div className="sn-kpi"><b style={{color:stats.mudos>0?'#C25A1A':'#0D1A0F'}}>{stats.mudos}</b><span>reais sem transmitir</span></div>
      </div>
      {stats.total>0 && stats.reais===0 && (
        <div className="sn-banner">
          <b>Nenhum sensor real ligado.</b> Tudo o que vês abaixo é <b>simulado</b> (demonstração). Quando ligares um sensor físico que transmita, ele aparece marcado como REAL.
        </div>
      )}
      {stats.reais>0 && stats.sim>0 && (
        <div className="sn-banner sn-banner-mix">
          <b>{stats.reais} sensor(es) REAL a transmitir</b> · os restantes {stats.sim} são simulados. Os reais estão marcados com selo cheio.
        </div>
      )}

      {/* AÇÕES */}
      <div className="sn-actions">
        <button className="sn-add" disabled={fixo} onClick={()=>setShowAdd(true)} title={fixo?'ambiente fixo — usa um custom':''}>
          ＋ Adicionar sensor
        </button>
        <button className="sn-add-sec" disabled={fixo} onClick={()=>setShowBulk(true)}>
          ＋＋ Em massa
        </button>
        <div className="sn-demo">
          <span className="sn-demo-label">Hora festival</span>
          <button className={demoHour===null?'on':''} onClick={()=>toggleDemoHour(null)}>real</button>
          <button className={demoHour===20?'on':''} onClick={()=>toggleDemoHour(20)}>20h</button>
          <button className={demoHour===22?'on':''} onClick={()=>toggleDemoHour(22)}>22h pico</button>
          <button className={demoHour===23.8?'on':''} onClick={()=>toggleDemoHour(23.8)}>surto</button>
        </div>
        {fixo && <span className="sn-help">Ambiente fixo. Cria um novo para adicionar sensores.</span>}
      </div>

      {/* GRELHA DE SENSORES */}
      <div className="sn-grid-wrap">
        {loading && <div className="sn-loading">A carregar…</div>}
        {!loading && sensors.length===0 && (
          <div className="sn-empty">
            <p>Nenhum sensor neste ambiente ainda.</p>
            {!fixo && <p className="sn-soft">Carrega em <b>＋ Adicionar sensor</b> para o primeiro.</p>}
          </div>
        )}
        <div className="sn-grid">
          {sensors.map(s=>(
            <button key={s.id} className={`sn-card ${selSensor?.id===s.id?'sel':''} st-${s.status||'unknown'} origin-${s.data_origin||'simulado'}`} onClick={()=>setSelSensor(s)}>
              <div className="sn-card-top">
                <span className="sn-dot" style={{background:statusColor(s.status||'')}}/>
                <span className="sn-card-tipo">{tipoLabel(s.tipo)}</span>
                {s.cluster && <span className="sn-card-cluster">{s.cluster.replace('wc-','').toUpperCase()}</span>}
              </div>
              <div className="sn-card-id">{s.label||s.id}</div>
              {s.label && s.id!==s.label && <div className="sn-card-sub">{s.id}</div>}
              <div className="sn-origin-badge">
                {s.data_origin==='real'?<span className="ob ob-real">● REAL{s.age_s!=null?` · ${Math.round(s.age_s)}s`:''}</span>
                 :s.data_origin==='real-mudo'?<span className="ob ob-mudo">○ real (mudo)</span>
                 :<span className="ob ob-sim">◌ SIMULADO</span>}
              </div>
              <div className="sn-card-bot">
                <span className="sn-card-st">{statusLabel(s.status||'sem-dados')}</span>
                {s.battery && (
                  <span className="sn-card-bat">
                    <span className="sn-batbar"><span className="sn-batfill" style={{width:`${s.battery.pct}%`}}/></span>
                    {s.battery.pct}%
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* PAINEL DO SENSOR (drawer) */}
      {selSensor && (
        <div className="sn-drawer-bg" onClick={()=>setSelSensor(null)}>
          <div className="sn-drawer" onClick={e=>e.stopPropagation()}>
            <div className="sn-dr-head">
              <div>
                <div className="sn-dr-id">{selSensor.label||selSensor.id}</div>
                <div className="sn-dr-tipo">{tipoLabel(selSensor.tipo)} {selSensor.cluster && `· ${selSensor.cluster.toUpperCase()}`}</div>
                {selSensor.label && selSensor.id!==selSensor.label && <div className="sn-dr-rawid">{selSensor.id}</div>}
              </div>
              <button className="sn-x" onClick={()=>setSelSensor(null)}>&times;</button>
            </div>

            {selSensor.data_origin==='real'?(
              <div className="sn-origin-box real">Dados REAIS — última transmissão há {selSensor.age_s!=null?Math.round(selSensor.age_s):'?'}s</div>
            ):selSensor.data_origin==='real-mudo'?(
              <div className="sn-origin-box mudo">Sensor real configurado, mas SEM TRANSMITIR. À espera de dados do hardware.</div>
            ):(
              <div className="sn-origin-box sim">Dados SIMULADOS — este sensor não está fisicamente ligado.</div>
            )}
            {detail ? (
              detail.erro ? <p className="sn-soft">Sem detalhe disponível.</p> :
              <div className="sn-dr-rows">
                <div><span>Estado</span><b style={{color:statusColor(detail.status||'')}}>{statusLabel(detail.status||'')}</b></div>
                {detail.battery && <div><span>Bateria</span><b>{detail.battery.pct}% ({detail.battery.fonte})</b></div>}
                {detail.uptime_s!=null && <div><span>Uptime</span><b>{Math.floor(detail.uptime_s/3600)}h {Math.floor((detail.uptime_s%3600)/60)}m</b></div>}
                {detail.rssi_dbm!=null && <div><span>Sinal</span><b>{detail.rssi_dbm} dBm</b></div>}
                {detail.link && <div><span>Ligação</span><b>{detail.link}</b></div>}
                {detail.origem && <div><span>Origem</span><b>{detail.origem}</b></div>}
              </div>
            ) : <p className="sn-soft">A carregar detalhe…</p>}

            <div className="sn-dr-cmds-t">Testar o sensor</div>
            <div className="sn-dr-cmds">
              {CMDS.map(([cmd,label])=>(
                <button key={cmd} disabled={busy===cmd} onClick={()=>runCmd(cmd)} className={busy===cmd?'busy':''}>
                  {busy===cmd?'…':label}
                </button>
              ))}
            </div>
            <div className="sn-dr-results">
              {cmdResults.length===0?<div className="sn-soft" style={{fontSize:12}}>Carrega num botão para testar.</div>:
                cmdResults.map((cr,i)=>(
                  <div key={i} className="sn-res">
                    <div className="sn-res-head"><b>{cr.cmd}</b><span>{cr.ts}</span></div>
                    {cr.r.resposta && <div className={`sn-res-msg ${cr.r.ok===false?'fail':'ok'}`}>{cr.r.resposta}</div>}
                    {cr.r.diagnostico && (
                      <div className="sn-res-diag">
                        {Object.entries(cr.r.diagnostico).map(([k,v]:any)=>(
                          <div key={k}><span>{k}</span><b>{String(v)}</b></div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              }
            </div>

            {caps && (
              <div className="sn-caps">
                <div className="sn-dr-cmds-t">Capacidades & alcance</div>
                <div className="sn-caps-rows">
                  <div><span>Modelo</span><b>{caps.modelo}</b></div>
                  <div><span>Função</span><b className="sn-caps-fn">{caps.funcao}</b></div>
                  <div><span>Ligação</span><b>{caps.ligacao_principal}</b></div>
                  {caps.margem_db!=null && <div><span>Sinal</span><b style={{color:caps.saude_ligacao==='boa'?'#4A7C59':caps.saude_ligacao==='fraca'?'#C25A1A':'#0D1A0F'}}>{caps.rssi_dbm}dBm · {caps.saude_ligacao} (margem {caps.margem_db}dB)</b></div>}
                  {caps.distancia_ao_palco_m!=null && <div><span>Distância ao palco</span><b>{caps.distancia_ao_palco_m}m</b></div>}
                  {caps.alcance_m && Object.entries(caps.alcance_m).map(([k,v]:any)=>(
                    <div key={k}><span>Alcance · {k.replace(/_/g,' ')}</span><b>{v}m</b></div>
                  ))}
                  <div><span>Alimentação</span><b>{caps.alimentacao}</b></div>
                  {caps.rgpd && <div><span>RGPD</span><b className="sn-caps-fn">{caps.rgpd}</b></div>}
                </div>
                <div className="sn-caps-fonte">fonte: {caps.fonte_specs}</div>
              </div>
            )}

            {!fixo && (
              <div className="sn-dr-remove">
                {confirmRemove===selSensor.id?(
                  <div className="sn-confirm">
                    <span>Remover {selSensor.id}?</span>
                    <button className="sn-btn-rm" onClick={()=>doRemove(selSensor.id)}>Sim, remover</button>
                    <button className="sn-btn-cancel" onClick={()=>setConfirmRemove(null)}>Cancelar</button>
                  </div>
                ):(
                  <button className="sn-btn-rm-link" onClick={()=>setConfirmRemove(selSensor.id)}>Remover sensor deste ambiente</button>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* DIALOG ADICIONAR SENSOR */}
      {showAdd && (
        <div className="sn-modal-bg" onClick={()=>setShowAdd(false)}>
          <div className="sn-modal" onClick={e=>e.stopPropagation()}>
            <h3>Adicionar sensor a "{env?.nome}"</h3>
            <label>ID do sensor</label>
            <input value={newSensor.id} onChange={e=>setNewSensor({...newSensor,id:e.target.value})} placeholder="ex: bancada-lilygo-1" autoFocus/>
            <label>Tipo</label>
            <select value={newSensor.tipo} onChange={e=>setNewSensor({...newSensor,tipo:e.target.value})}>
              {TIPOS.map(t=><option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
            <label>Nome amigável (opcional)</label>
            <input value={newSensor.label} onChange={e=>setNewSensor({...newSensor,label:e.target.value})} placeholder="ex: LilyGo bancada"/>
            <div className="sn-modal-buttons">
              <button className="sn-btn-cancel" onClick={()=>setShowAdd(false)}>Cancelar</button>
              <button className="sn-btn-ok" onClick={submitAdd}>Adicionar</button>
            </div>
          </div>
        </div>
      )}

      {/* DIALOG ADICIONAR EM MASSA */}
      {showBulk && (
        <div className="sn-modal-bg" onClick={()=>setShowBulk(false)}>
          <div className="sn-modal" onClick={e=>e.stopPropagation()}>
            <h3>Adicionar em massa a "{env?.nome}"</h3>
            <div className="sn-bulk-tabs">
              <button className={bulkTab==='gen'?'on':''} onClick={()=>setBulkTab('gen')}>Gerar automático</button>
              <button className={bulkTab==='list'?'on':''} onClick={()=>setBulkTab('list')}>Colar lista</button>
            </div>
            {bulkTab==='gen'?(
              <div>
                <label>Prefixo (cluster ou nome)</label>
                <input value={bulkGen.prefixo} onChange={e=>setBulkGen({...bulkGen,prefixo:e.target.value})} placeholder="ex: wc-02"/>
                <label>Tipo</label>
                <select value={bulkGen.tipo} onChange={e=>setBulkGen({...bulkGen,tipo:e.target.value})}>
                  {TIPOS.map(t=><option key={t.id} value={t.id}>{t.label}</option>)}
                </select>
                <label>Quantidade ({bulkGen.quantidade})</label>
                <input type="range" min={1} max={20} value={bulkGen.quantidade} onChange={e=>setBulkGen({...bulkGen,quantidade:Number(e.target.value)})}/>
                <p className="sn-soft" style={{fontSize:12,marginTop:8}}>Vai criar: <b>{bulkGen.prefixo}-{bulkGen.tipo}-1</b> até <b>{bulkGen.prefixo}-{bulkGen.tipo}-{bulkGen.quantidade}</b></p>
                <div className="sn-modal-buttons">
                  <button className="sn-btn-cancel" onClick={()=>setShowBulk(false)}>Cancelar</button>
                  <button className="sn-btn-ok" onClick={submitBulkGen}>Criar {bulkGen.quantidade}</button>
                </div>
              </div>
            ):(
              <div>
                <label>Cola os IDs (um por linha)</label>
                <textarea value={bulkText} onChange={e=>setBulkText(e.target.value)} rows={7}
                  placeholder={'staff-lilygo-1\nstaff-cam-1\nstaff-ir-1\n...'}/>
                <p className="sn-soft" style={{fontSize:12,marginTop:6}}>O tipo é inferido pelo nome (lilygo/cam/ir/wifi). {bulkText.split('\n').filter(l=>l.trim()).length} linhas.</p>
                <div className="sn-modal-buttons">
                  <button className="sn-btn-cancel" onClick={()=>setShowBulk(false)}>Cancelar</button>
                  <button className="sn-btn-ok" onClick={submitBulkList}>Adicionar lista</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* DIALOG NOVO AMBIENTE */}
      {showNewEnv && (
        <div className="sn-modal-bg" onClick={()=>setShowNewEnv(false)}>
          <div className="sn-modal" onClick={e=>e.stopPropagation()}>
            <h3>Novo ambiente</h3>
            <label>Nome</label>
            <input value={newEnv.nome} onChange={e=>setNewEnv({...newEnv,nome:e.target.value})} placeholder="ex: Bancada Porto" autoFocus/>
            <label>Modo</label>
            <select value={newEnv.modo} onChange={e=>setNewEnv({...newEnv,modo:e.target.value})}>
              <option value="real">Real (sensores físicos)</option>
              <option value="sim">Simulação</option>
            </select>
            <label>Cadência ({newEnv.refresh_ms}ms)</label>
            <input type="range" min={500} max={6000} step={500} value={newEnv.refresh_ms} onChange={e=>setNewEnv({...newEnv,refresh_ms:Number(e.target.value)})}/>
            <div className="sn-modal-buttons">
              <button className="sn-btn-cancel" onClick={()=>setShowNewEnv(false)}>Cancelar</button>
              <button className="sn-btn-ok" onClick={submitNewEnv}>Criar</button>
            </div>
          </div>
        </div>
      )}

      {/* TOAST */}
      {toast && <div className={`sn-toast ${toast.kind}`}>{toast.msg}</div>}

      {/* LINK CONSOLA TÉCNICA */}
      <div className="sn-footer">
        <a href="/v2/sensors/fusion" className="sn-tec">consola técnica →</a>
      </div>

      <style jsx>{`
        .sn-root{padding:18px clamp(16px,2.6vw,32px);color:#0D1A0F;min-height:calc(100vh - 72px);}
        .sn-head{display:flex;justify-content:space-between;align-items:flex-end;}
        .sn-eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#8A938B;}
        .sn-title{font-size:clamp(22px,2.6vw,30px);font-weight:600;margin:2px 0 0;}
        .sn-upd{font-size:11px;color:#8A938B;font-variant-numeric:tabular-nums;}

        .sn-envs{margin-top:18px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;}
        .sn-envs-label{font-size:11px;font-weight:700;text-transform:uppercase;color:#8A938B;letter-spacing:.06em;}
        .sn-envs-tabs{display:flex;gap:8px;flex-wrap:wrap;}
        .sn-env{background:#fff;border:1px solid #E5E8E0;border-radius:10px;padding:8px 14px;cursor:pointer;font-family:inherit;text-align:left;display:flex;flex-direction:column;gap:2px;transition:all .14s;}
        .sn-env:hover{border-color:#4A7C59;}
        .sn-env.on{background:#1B3A21;border-color:#1B3A21;color:#fff;}
        .sn-env.on .sn-env-meta{color:rgba(255,255,255,.7);}
        .sn-env.fixo .sn-env-nome::after{content:' ⌁';opacity:.6;}
        .sn-env-nome{font-size:13px;font-weight:600;}
        .sn-env-meta{font-size:10px;color:#8A938B;}
        .sn-env-new{background:transparent;border:1px dashed #C9CEC4;color:#4A7C59;border-radius:10px;padding:8px 14px;cursor:pointer;font-size:12px;font-family:inherit;font-weight:600;}
        .sn-env-new:hover{border-color:#4A7C59;background:#FAFCF9;}

        .sn-kpis{margin-top:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
        .sn-kpi{background:#fff;border:1px solid #E5E8E0;border-radius:10px;padding:10px 12px;}
        .sn-kpi b{display:block;font-size:24px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums;color:#1B3A21;}
        .sn-kpi span{font-size:11px;color:#8A938B;margin-top:3px;display:block;}

        .sn-actions{margin-top:14px;display:flex;align-items:center;gap:14px;}
        .sn-add{background:#1B3A21;color:#fff;border:none;border-radius:10px;padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;}
        .sn-add:hover{background:#2A5232;}
        .sn-add:disabled{background:#C9CEC4;cursor:not-allowed;}
        .sn-help{font-size:12px;color:#8A938B;}

        .sn-grid-wrap{margin-top:14px;}
        .sn-loading{padding:30px;text-align:center;color:#8A938B;}
        .sn-empty{padding:40px;text-align:center;background:#FAFCF9;border:1px dashed #E5E8E0;border-radius:12px;}
        .sn-empty p{margin:6px 0;}
        .sn-soft{color:#8A938B;}
        .sn-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;}
        .sn-card{background:#fff;border:1px solid #E5E8E0;border-radius:12px;padding:12px;cursor:pointer;text-align:left;font-family:inherit;transition:all .14s;display:flex;flex-direction:column;gap:6px;min-height:96px;}
        .sn-card:hover{border-color:#4A7C59;transform:translateY(-1px);box-shadow:0 4px 12px rgba(27,58,33,.08);}
        .sn-card.sel{border-color:#1B3A21;border-width:2px;padding:11px;}
        .sn-card.st-online{background:linear-gradient(180deg,#FAFCF9 0%,#FFFFFF 100%);}
        .sn-card-top{display:flex;align-items:center;gap:6px;}
        .sn-dot{width:9px;height:9px;border-radius:50%;flex-shrink:0;box-shadow:0 0 0 2px rgba(74,124,89,.12);}
        .sn-card.st-online .sn-dot{box-shadow:0 0 0 2px rgba(74,124,89,.18),0 0 6px rgba(74,124,89,.35);}
        .sn-card-tipo{font-size:10px;color:#8A938B;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}
        .sn-card-cluster{margin-left:auto;font-size:10px;font-weight:700;color:#1B3A21;background:#E8F1EA;border-radius:4px;padding:1px 6px;font-family:monospace;}
        .sn-card-id{font-size:13.5px;font-weight:600;line-height:1.2;color:#0D1A0F;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
        .sn-card-sub{font-family:monospace;font-size:10.5px;color:#8A938B;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
        .sn-card-bot{display:flex;justify-content:space-between;align-items:center;margin-top:auto;gap:6px;}
        .sn-card-st{font-size:11px;color:#8A938B;}
        .sn-card.st-online .sn-card-st{color:#4A7C59;font-weight:600;}
        .sn-card.st-degraded .sn-card-st{color:#C25A1A;font-weight:600;}
        .sn-card-bat{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:600;color:#4A7C59;font-variant-numeric:tabular-nums;}
        .sn-batbar{width:30px;height:5px;background:#F0F2EC;border-radius:3px;overflow:hidden;}
        .sn-batfill{display:block;height:100%;background:linear-gradient(90deg,#4A7C59,#6FAF82);border-radius:3px;}

        .sn-drawer-bg{position:fixed;inset:0;background:rgba(13,26,15,.3);z-index:50;display:flex;justify-content:flex-end;}
        .sn-drawer{width:440px;max-width:92vw;background:#fff;height:100%;padding:22px;overflow-y:auto;box-shadow:-8px 0 30px rgba(0,0,0,.12);}
        .sn-dr-head{display:flex;justify-content:space-between;align-items:flex-start;}
        .sn-dr-id{font-size:16px;font-weight:700;}
        .sn-dr-tipo{font-size:12px;color:#8A938B;margin-top:2px;}
        .sn-dr-rawid{font-family:monospace;font-size:11px;color:#8A938B;margin-top:2px;}
        .sn-x{background:none;border:none;font-size:22px;cursor:pointer;color:#8A938B;line-height:1;}
        .sn-dr-rows{margin-top:14px;}
        .sn-dr-rows>div{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #F0F2EC;font-size:14px;}
        .sn-dr-rows span{color:#8A938B;}
        .sn-dr-cmds-t{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#8A938B;margin:20px 0 10px;}
        .sn-dr-cmds{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;}
        .sn-dr-cmds button{background:#1B3A21;color:#fff;border:none;border-radius:8px;padding:11px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .14s;}
        .sn-dr-cmds button:hover{background:#2A5232;}
        .sn-dr-cmds button.busy{background:#8A938B;}
        .sn-dr-results{margin-top:14px;}
        .sn-res{background:#FAFAF7;border:1px solid #F0F2EC;border-radius:10px;padding:12px;margin-bottom:8px;}
        .sn-res-head{display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;}
        .sn-res-head b{color:#1B3A21;text-transform:capitalize;}
        .sn-res-head span{color:#8A938B;}
        .sn-res-msg{font-size:13px;font-family:monospace;padding:7px 9px;border-radius:6px;}
        .sn-res-msg.ok{background:#E8F1EA;color:#1B3A21;}
        .sn-res-msg.fail{background:#F5E6D8;color:#C25A1A;}
        .sn-res-diag{display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;margin-top:4px;}
        .sn-res-diag div{display:flex;justify-content:space-between;font-size:12px;padding:2px 0;}
        .sn-res-diag span{color:#8A938B;}
        .sn-res-diag b{font-variant-numeric:tabular-nums;}
        .sn-dr-remove{margin-top:24px;padding-top:14px;border-top:1px solid #F0F2EC;}
        .sn-btn-rm-link{background:none;border:none;color:#C25A1A;cursor:pointer;font-family:inherit;font-size:13px;}
        .sn-btn-rm-link:hover{text-decoration:underline;}
        .sn-confirm{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#F5E6D8;padding:10px 12px;border-radius:8px;}
        .sn-confirm span{font-size:13px;flex:1;min-width:150px;}
        .sn-btn-rm{background:#C25A1A;color:#fff;border:none;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:12px;font-family:inherit;font-weight:600;}
        .sn-btn-cancel{background:transparent;color:#0D1A0F;border:1px solid #C9CEC4;border-radius:6px;padding:6px 14px;cursor:pointer;font-size:12px;font-family:inherit;}

        .sn-modal-bg{position:fixed;inset:0;background:rgba(13,26,15,.5);z-index:60;display:flex;align-items:center;justify-content:center;padding:20px;}
        .sn-modal{background:#fff;border-radius:14px;padding:24px;width:100%;max-width:420px;}
        .sn-modal h3{margin:0 0 16px;font-size:17px;}
        .sn-modal label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;color:#8A938B;letter-spacing:.05em;margin-top:12px;margin-bottom:5px;}
        .sn-modal input,.sn-modal select{width:100%;border:1px solid #E5E8E0;border-radius:8px;padding:10px 12px;font-family:inherit;font-size:14px;background:#fff;color:#0D1A0F;box-sizing:border-box;}
        .sn-modal input[type=range]{padding:0;}
        .sn-modal input:focus,.sn-modal select:focus{outline:none;border-color:#1B3A21;}
        .sn-modal-buttons{display:flex;justify-content:flex-end;gap:8px;margin-top:20px;}
        .sn-btn-ok{background:#1B3A21;color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:14px;cursor:pointer;font-family:inherit;font-weight:600;}

        .sn-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1B3A21;color:#fff;padding:10px 18px;border-radius:10px;font-size:13px;z-index:70;box-shadow:0 6px 20px rgba(0,0,0,.18);}
        .sn-toast.erro{background:#C25A1A;}

        .sn-footer{margin-top:30px;padding-top:14px;border-top:1px solid #F0F2EC;text-align:right;}
        .sn-tec{font-size:11px;color:#8A938B;text-decoration:none;}
        .sn-tec:hover{color:#1B3A21;}

        .sn-kpi-real b{color:#1B7A3D!important;}
        .sn-kpi-real{border-color:#B8E0C4;background:linear-gradient(180deg,#F2FBF5,#fff);}
        .sn-kpi-sim b{color:#8A938B!important;}
        .sn-banner{margin-top:12px;padding:11px 14px;border-radius:10px;font-size:13px;background:#FFF6ED;border:1px solid #F0D9BE;color:#7A4A1E;}
        .sn-banner-mix{background:#F2FBF5;border-color:#B8E0C4;color:#1B5A2E;}
        .sn-origin-badge{margin-top:2px;}
        .ob{font-size:10px;font-weight:700;letter-spacing:.03em;padding:1px 6px;border-radius:4px;}
        .ob-real{color:#1B7A3D;background:#E2F5E9;}
        .ob-mudo{color:#C25A1A;background:#F8EADB;}
        .ob-sim{color:#8A938B;background:#F0F2EC;}
        .sn-card.origin-real{border-left:3px solid #1B7A3D;}
        .sn-card.origin-real .sn-dot{box-shadow:0 0 0 2px rgba(27,122,61,.25),0 0 8px rgba(27,122,61,.5);}
        .sn-card.origin-simulado{border-left:3px dashed #C9CEC4;}
        .sn-card.origin-real-mudo{border-left:3px solid #C25A1A;}
        .sn-origin-box{margin-top:14px;padding:10px 12px;border-radius:8px;font-size:12.5px;font-weight:600;}
        .sn-origin-box.real{background:#E2F5E9;color:#1B7A3D;}
        .sn-origin-box.mudo{background:#F8EADB;color:#C25A1A;}
        .sn-origin-box.sim{background:#F0F2EC;color:#8A938B;}
        .sn-add-sec{background:#fff;color:#1B3A21;border:1px solid #1B3A21;border-radius:10px;padding:10px 16px;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;}
        .sn-add-sec:hover{background:#F0F5F1;}
        .sn-add-sec:disabled{color:#C9CEC4;border-color:#E5E8E0;cursor:not-allowed;}
        .sn-demo{display:flex;align-items:center;gap:4px;margin-left:auto;background:#fff;border:1px solid #E5E8E0;border-radius:10px;padding:4px 8px;}
        .sn-demo-label{font-size:11px;color:#8A938B;margin-right:4px;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}
        .sn-demo button{background:transparent;border:none;border-radius:6px;padding:5px 10px;font-size:12px;cursor:pointer;font-family:inherit;color:#0D1A0F;}
        .sn-demo button.on{background:#1B3A21;color:#fff;font-weight:600;}
        .sn-bulk-tabs{display:flex;gap:6px;margin-bottom:14px;}
        .sn-bulk-tabs button{flex:1;background:#F0F2EC;border:none;border-radius:8px;padding:9px;font-size:13px;cursor:pointer;font-family:inherit;color:#0D1A0F;}
        .sn-bulk-tabs button.on{background:#1B3A21;color:#fff;font-weight:600;}
        .sn-modal textarea{width:100%;border:1px solid #E5E8E0;border-radius:8px;padding:10px 12px;font-family:monospace;font-size:13px;box-sizing:border-box;resize:vertical;}
        .sn-caps{margin-top:18px;}
        .sn-caps-rows>div{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid #F0F2EC;font-size:13px;}
        .sn-caps-rows span{color:#8A938B;flex-shrink:0;}
        .sn-caps-rows b{text-align:right;}
        .sn-caps-fn{font-weight:400!important;font-size:12px;color:#4A7C59!important;}
        .sn-caps-fonte{font-size:10px;color:#C9CEC4;margin-top:8px;text-transform:uppercase;letter-spacing:.05em;}
        @media (max-width:680px){
          .sn-kpis{grid-template-columns:repeat(2,1fr);}
          .sn-grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));}
          .sn-drawer{width:100%;max-width:none;}
        }
      `}</style>
    </div>
  );
}
