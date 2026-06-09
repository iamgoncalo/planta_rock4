'use client';

import { useEffect, useState } from 'react';

/* ════════════════════════════════════════════════════════════════════
   Vista STEWARD (onda 7f) — o frontend NUNCA decide, só renderiza:
   recusas_estimadas, secções em WARN/CRIT, sugestão de pré-posicionamento
   e comando cluster_fechado com confirmação (auditado no decision_log).
   Dados exclusivamente de /api/v1 (state, sections/estado, sections PUT).
   ════════════════════════════════════════════════════════════════════ */

const API = process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';
const CLUSTERS = ['wc-01','wc-02','wc-03','wc-04','wc-05','wc-06','wc-07','wc-08'];
// Secções que saturam primeiro no D2 (simulação 4 dias) — pré-posicionar
const PRE_POSICIONAR = ['WC-03_M','WC-07_M','WC-08_M','WC-04_F','WC-07_F','WC-06'];

export default function StewardPanel(){
  const [estado,setEstado]=useState<any>(null);
  const [sections,setSections]=useState<any[]>([]);
  const [confirm,setConfirm]=useState<string|null>(null);
  const [user,setUser]=useState('');
  const [busy,setBusy]=useState(false);

  useEffect(()=>{
    let cancel=false;
    const load=async()=>{
      try{
        const [e,s]=await Promise.all([
          fetch(`${API}/api/v1/sections/estado`,{cache:'no-store'}).then(r=>r.json()),
          fetch(`${API}/api/v1/state`,{cache:'no-store'}).then(r=>r.json()),
        ]);
        if(cancel)return;
        setEstado(e);
        setSections(s.sections||[]);
      }catch{}
    };
    load();const iv=setInterval(load,8000);
    return()=>{cancel=true;clearInterval(iv);};
  },[]);

  const toggle=async(cid:string,fechar:boolean)=>{
    if(!user.trim()){alert('Identifica-te (nome do steward) antes de fechar/reabrir.');return;}
    setBusy(true);
    try{
      await fetch(`${API}/api/v1/sections/${cid}/estado`,{
        method:'PUT',headers:{'content-type':'application/json'},
        body:JSON.stringify({fechado:fechar,utilizador:user.trim(),
          justificacao:fechar?'fecho operacional via vista steward':'reabertura via vista steward'}),
      });
      const e=await fetch(`${API}/api/v1/sections/estado`,{cache:'no-store'}).then(r=>r.json());
      setEstado(e);
    }catch{}
    setBusy(false);setConfirm(null);
  };

  const recusas=estado?.recusas_estimadas;
  const fechados=estado?.fechados||{};
  const crit=sections.filter(s=>s.alerta_fila==='CRIT');
  const warn=sections.filter(s=>s.alerta_fila==='WARN');

  return (
    <div className="stw-root">
      <div className="stw-title">Vista steward · decisões do motor</div>
      <div className="stw-grid">
        <div className="stw-card">
          <div className="stw-l">Recusas estimadas (sem fila disponível)</div>
          <div className="stw-big">{recusas?Math.round(recusas.total):'—'}<span> pessoas</span></div>
          {recusas&&<div className="stw-sub">F {Math.round(recusas.f)} · M {Math.round(recusas.m)} · Uni {Math.round(recusas.u)}</div>}
        </div>
        <div className="stw-card">
          <div className="stw-l">Secções em alerta de fila</div>
          {crit.length===0&&warn.length===0
            ? <div className="stw-ok">tudo dentro da capacidade de espera</div>
            : <div className="stw-tags">
                {crit.map(s=><span key={s.section_id} className="stw-tag crit">{s.section_id} CRIT</span>)}
                {warn.map(s=><span key={s.section_id} className="stw-tag warn">{s.section_id} WARN</span>)}
              </div>}
        </div>
        <div className="stw-card">
          <div className="stw-l">Pré-posicionamento sugerido (saturam primeiro)</div>
          <div className="stw-tags">{PRE_POSICIONAR.map(s=><span key={s} className="stw-tag pre">{s}</span>)}</div>
        </div>
      </div>

      <div className="stw-fechos">
        <input placeholder="o teu nome (auditado)" value={user} onChange={e=>setUser(e.target.value)}/>
        {CLUSTERS.map(c=>{
          const f=fechados[c]?.fechado;
          return confirm===c ? (
            <span key={c} className="stw-confirm">
              {f?'Reabrir':'FECHAR'} {c.toUpperCase()}?
              <button disabled={busy} onClick={()=>toggle(c,!f)}>{busy?'…':'confirmo'}</button>
              <button onClick={()=>setConfirm(null)}>cancelar</button>
            </span>
          ) : (
            <button key={c} className={`stw-cl ${f?'closed':''}`} onClick={()=>setConfirm(c)}>
              {c.toUpperCase()}{f?' · FECHADO':''}
            </button>
          );
        })}
      </div>

      <style jsx>{`
        .stw-root{margin-top:18px;border-top:1px solid #ECE9E2;padding-top:14px;}
        .stw-title{font-size:11px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#6B7268;margin-bottom:10px;}
        .stw-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;}
        .stw-card{background:#fff;border:1px solid #ECE9E2;border-radius:12px;padding:12px;}
        .stw-l{font-size:11px;color:#6B7268;margin-bottom:6px;}
        .stw-big{font-size:28px;font-weight:600;color:#1B3A21;font-variant-numeric:tabular-nums;line-height:1;}
        .stw-big span{font-size:12px;color:#6B7268;font-weight:400;}
        .stw-sub{font-size:11.5px;color:#6B7268;margin-top:5px;font-variant-numeric:tabular-nums;}
        .stw-ok{font-size:13px;color:#2E7D4F;}
        .stw-tags{display:flex;flex-wrap:wrap;gap:5px;}
        .stw-tag{font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:6px;font-family:monospace;}
        .stw-tag.crit{background:#C25A1A;color:#fff;}
        .stw-tag.warn{background:#F5E6D8;color:#C25A1A;}
        .stw-tag.pre{background:#EDF4EF;color:#1B3A21;}
        .stw-fechos{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;align-items:center;}
        .stw-fechos input{border:1px solid #ECE9E2;border-radius:8px;padding:6px 10px;font-family:inherit;font-size:12.5px;width:170px;}
        .stw-cl{border:1px solid #ECE9E2;background:#fff;border-radius:8px;padding:6px 10px;font-size:11.5px;font-family:monospace;cursor:pointer;color:#0D1A0F;}
        .stw-cl.closed{background:#C25A1A;border-color:#C25A1A;color:#fff;font-weight:700;}
        .stw-confirm{display:inline-flex;gap:6px;align-items:center;font-size:12px;background:#FAFAF8;border:1px solid #C25A1A;border-radius:8px;padding:5px 9px;color:#C25A1A;font-weight:600;}
        .stw-confirm button{border:none;border-radius:6px;padding:4px 9px;font-size:11.5px;cursor:pointer;font-family:inherit;}
        .stw-confirm button:first-of-type{background:#C25A1A;color:#fff;}
      `}</style>
    </div>
  );
}
