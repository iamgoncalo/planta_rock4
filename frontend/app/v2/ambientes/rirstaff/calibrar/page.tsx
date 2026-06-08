'use client';

import { useEffect, useState, useCallback } from 'react';

type Cfg = { raio_m: number; divisor: number; baseline: number; capacidade: number };
type Casa = { cluster: string; ocupacao?: number | null; online?: boolean; telemoveis_detectados?: number | null; age_s?: number };

const API = process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

export default function CalibrarPage() {
  const [autenticado, setAutenticado] = useState(false);
  const [pass, setPass] = useState('');
  const [alvo, setAlvo] = useState<'ambos' | 'rirstaff-f' | 'rirstaff-m'>('ambos');
  const [cfg, setCfg] = useState<Cfg>({ raio_m: 5, divisor: 3, baseline: 0, capacidade: 8 });
  const [vivoF, setVivoF] = useState<Casa | null>(null);
  const [vivoM, setVivoM] = useState<Casa | null>(null);
  const [msg, setMsg] = useState('');
  const [aGuardar, setAGuardar] = useState(false);

  // estado ao vivo dos dois, ao segundo
  const carregarVivo = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/rirstaff`, { cache: 'no-store' });
      const d = await r.json();
      for (const c of (d.casas_de_banho || [])) {
        if (c.cluster === 'rirstaff-f') setVivoF(c);
        if (c.cluster === 'rirstaff-m') setVivoM(c);
      }
    } catch {}
  }, []);

  useEffect(() => {
    carregarVivo();
    const i = setInterval(carregarVivo, 1000); // AO SEGUNDO
    return () => clearInterval(i);
  }, [carregarVivo]);

  // ao entrar, carrega a config atual (do rirstaff-f como base)
  const carregarCfg = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/rirstaff/config/rirstaff-f`, { cache: 'no-store' });
      const d = await r.json();
      setCfg({ raio_m: d.raio_m ?? 5, divisor: d.divisor ?? 3, baseline: d.baseline ?? 0, capacidade: d.capacidade ?? 8 });
    } catch {}
  }, []);
  useEffect(() => { if (autenticado) carregarCfg(); }, [autenticado, carregarCfg]);

  const guardarUm = async (cluster: string) => {
    const r = await fetch(`${API}/api/v1/rirstaff/config/${cluster}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pass, ...cfg }),
    });
    return r;
  };

  const guardar = async () => {
    setAGuardar(true); setMsg('a guardar…');
    try {
      const alvos = alvo === 'ambos' ? ['rirstaff-f', 'rirstaff-m'] : [alvo];
      let ok = true, erro401 = false;
      for (const cl of alvos) {
        const r = await guardarUm(cl);
        if (r.status === 401) { erro401 = true; ok = false; break; }
        if (!r.ok) ok = false;
      }
      if (erro401) setMsg('Password errada');
      else if (ok) setMsg(alvo === 'ambos'
        ? 'Guardado nos DOIS sensores. Aplicam em ~10s.'
        : 'Guardado. Aplica em ~10s.');
      else setMsg('Erro a guardar');
    } catch { setMsg('Sem ligação ao servidor'); }
    setAGuardar(false);
  };

  const entrar = () => { if (pass.length >= 4) setAutenticado(true); else setMsg('Mete a password'); };

  if (!autenticado) {
    return (
      <div className="cal-login">
        <div className="cal-box">
          <h1>Calibrar sensores</h1>
          <p>Página protegida · Staff PlantaOS</p>
          <input type="password" value={pass} onChange={e => setPass(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && entrar()} placeholder="Password" autoFocus />
          <button onClick={entrar}>Entrar</button>
          {msg && <div className="cal-msg">{msg}</div>}
        </div>
        <style jsx>{`
          .cal-login { min-height: 100dvh; display: flex; align-items: center; justify-content: center; font-family: 'Inter', system-ui, sans-serif; padding: 20px; }
          .cal-box { width: 100%; max-width: 360px; text-align: center; }
          h1 { font-size: 26px; font-weight: 600; color: #0D1A0F; margin: 0 0 6px; }
          p { color: #6B756C; font-size: 13px; margin: 0 0 24px; }
          input { width: 100%; padding: 14px 16px; border: 1px solid #E5E8E0; border-radius: 12px; font-size: 16px; box-sizing: border-box; margin-bottom: 12px; font-family: inherit; }
          input:focus { outline: none; border-color: #1B3A21; }
          button { width: 100%; padding: 14px; background: #1B3A21; color: #fff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; }
          .cal-msg { margin-top: 14px; color: #C25A1A; font-size: 13px; }
        `}</style>
      </div>
    );
  }

  const cartaoVivo = (nome: string, icon: string, v: Casa | null) => (
    <div className="cal-vivo">
      <div className="cal-vivo-top">
        <span className={`cal-dot ${v?.online ? 'on' : ''}`} />
        {icon} {nome} · {v?.online ? `${v?.age_s != null ? Math.round(v.age_s) : '?'}s` : 'offline'}
      </div>
      <div className="cal-num">{v?.ocupacao != null ? v.ocupacao : '—'}</div>
      <div className="cal-tlm">{v?.telemoveis_detectados != null ? `${v.telemoveis_detectados} telemóveis` : 'sem dados'}</div>
    </div>
  );

  return (
    <div className="cal-wrap">
      <div className="cal-head">
        <div>
          <h1>Calibrar sensores</h1>
          <p>Ajusta e vê ao vivo · ao segundo · sem cabo</p>
        </div>
        <a href="/v2/ambientes/rirstaff" className="cal-voltar">← voltar</a>
      </div>

      {/* AO VIVO dos dois */}
      <div className="cal-vivos">
        {cartaoVivo('Mulheres', '♀', vivoF)}
        {cartaoVivo('Homens', '♂', vivoM)}
      </div>

      {/* alvo: ambos ou um */}
      <div className="cal-tabs">
        <button className={alvo === 'ambos' ? 'on' : ''} onClick={() => setAlvo('ambos')}>Os dois</button>
        <button className={alvo === 'rirstaff-f' ? 'on' : ''} onClick={() => setAlvo('rirstaff-f')}>♀ Mulheres</button>
        <button className={alvo === 'rirstaff-m' ? 'on' : ''} onClick={() => setAlvo('rirstaff-m')}>♂ Homens</button>
      </div>

      {/* controlos */}
      <div className="cal-ctrl">
        <Slider label="Baseline (ruído a subtrair)" val={cfg.baseline} min={0} max={40} onChange={v => setCfg({ ...cfg, baseline: v })} />
        <Slider label="Raio (metros)" val={cfg.raio_m} min={1} max={20} onChange={v => setCfg({ ...cfg, raio_m: v })} />
        <Slider label="Divisor (telemóveis por pessoa)" val={cfg.divisor} min={1} max={6} onChange={v => setCfg({ ...cfg, divisor: v })} />
        <Slider label="Capacidade" val={cfg.capacidade} min={1} max={30} onChange={v => setCfg({ ...cfg, capacidade: v })} />
        <button className="cal-guardar" onClick={guardar} disabled={aGuardar}>
          {aGuardar ? 'a guardar…' : alvo === 'ambos' ? 'Guardar nos DOIS' : 'Guardar'}
        </button>
        {msg && <div className={`cal-msg ${msg.includes('errada') || msg.includes('Erro') || msg.includes('Sem') ? 'erro' : 'ok'}`}>{msg}</div>}
      </div>

      <style jsx>{`
        .cal-wrap { max-width: 760px; margin: 0 auto; padding: 20px; font-family: 'Inter', system-ui, sans-serif; color: #0D1A0F; }
        .cal-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }
        h1 { font-size: clamp(20px, 3vw, 28px); margin: 0; font-weight: 600; }
        p { color: #6B756C; font-size: 13px; margin: 4px 0 0; }
        .cal-voltar { color: #4A7C59; font-size: 14px; text-decoration: none; font-weight: 600; }
        .cal-vivos { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
        .cal-vivo { border: 1px solid #E5E8E0; border-radius: 16px; padding: 16px; text-align: center; background: #FAFBF9; }
        .cal-vivo-top { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; letter-spacing: .03em; color: #6B756C; text-transform: uppercase; margin-bottom: 8px; }
        .cal-dot { width: 8px; height: 8px; border-radius: 50%; background: #C9CEC4; }
        .cal-dot.on { background: #1B7A3D; box-shadow: 0 0 0 3px rgba(27,122,61,.18); }
        .cal-num { font-size: 52px; font-weight: 700; line-height: 1; color: #1B3A21; }
        .cal-tlm { font-size: 12px; color: #4A7C59; margin-top: 8px; }
        .cal-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
        .cal-tabs button { flex: 1; padding: 11px; border: 1px solid #E5E8E0; background: #fff; border-radius: 11px; font-size: 14px; font-family: inherit; cursor: pointer; color: #6B756C; }
        .cal-tabs button.on { background: #1B3A21; color: #fff; border-color: #1B3A21; font-weight: 600; }
        .cal-ctrl { border: 1px solid #E5E8E0; border-radius: 16px; padding: 20px; }
        .cal-guardar { width: 100%; padding: 14px; background: #1B3A21; color: #fff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 6px; }
        .cal-guardar:disabled { opacity: .6; }
        .cal-msg { margin-top: 12px; font-size: 13px; text-align: center; }
        .cal-msg.ok { color: #1B7A3D; }
        .cal-msg.erro { color: #C25A1A; }
        @media (max-width: 600px) { .cal-vivos { grid-template-columns: 1fr 1fr; } }
      `}</style>
    </div>
  );
}

function Slider({ label, val, min, max, onChange }: { label: string; val: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <div className="sl">
      <div className="sl-top"><span>{label}</span><b>{val}</b></div>
      <input type="range" min={min} max={max} value={val} onChange={e => onChange(+e.target.value)} />
      <style jsx>{`
        .sl { margin-bottom: 18px; }
        .sl-top { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 8px; }
        .sl-top b { color: #1B3A21; font-size: 15px; }
        input { width: 100%; accent-color: #1B3A21; }
      `}</style>
    </div>
  );
}
