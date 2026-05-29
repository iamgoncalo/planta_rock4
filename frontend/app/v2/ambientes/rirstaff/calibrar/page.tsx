'use client';

import { useEffect, useState, useCallback } from 'react';

type Cfg = { raio_m: number; divisor: number; baseline: number; capacidade: number; contexto: string };
type Casa = {
  cluster: string; nome: string; ocupacao?: number | null; online?: boolean;
  telemoveis_detectados?: number | null; age_s?: number; estado?: string;
};

const API = 'https://api.plantarockinrio.com';
const CLUSTERS = [
  { id: 'rirstaff-f', nome: 'Mulheres', icon: '♀' },
  { id: 'rirstaff-m', nome: 'Homens', icon: '♂' },
];

export default function CalibrarPage() {
  const [autenticado, setAutenticado] = useState(false);
  const [pass, setPass] = useState('');
  const [cluster, setCluster] = useState('rirstaff-f');
  const [cfg, setCfg] = useState<Cfg>({ raio_m: 5, divisor: 3, baseline: 0, capacidade: 8, contexto: 'staff' });
  const [vivo, setVivo] = useState<Casa | null>(null);
  const [msg, setMsg] = useState('');
  const [aGuardar, setAGuardar] = useState(false);

  // carrega config atual do cluster
  const carregarCfg = useCallback(async (cl: string) => {
    try {
      const r = await fetch(`${API}/api/v1/rirstaff/config/${cl}`, { cache: 'no-store' });
      const d = await r.json();
      setCfg({ raio_m: d.raio_m ?? 5, divisor: d.divisor ?? 3, baseline: d.baseline ?? 0,
               capacidade: d.capacidade ?? 8, contexto: d.contexto ?? 'staff' });
    } catch {}
  }, []);

  // estado ao vivo do cluster (para ver enquanto calibras)
  const carregarVivo = useCallback(async (cl: string) => {
    try {
      const r = await fetch(`${API}/api/v1/rirstaff/${cl}`, { cache: 'no-store' });
      const d = await r.json();
      setVivo(d);
    } catch {}
  }, []);

  useEffect(() => { carregarCfg(cluster); }, [cluster, carregarCfg]);
  useEffect(() => {
    carregarVivo(cluster);
    const i = setInterval(() => carregarVivo(cluster), 1500);
    return () => clearInterval(i);
  }, [cluster, carregarVivo]);

  const guardar = async () => {
    setAGuardar(true); setMsg('a guardar…');
    try {
      const r = await fetch(`${API}/api/v1/rirstaff/config/${cluster}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pass, ...cfg }),
      });
      if (r.status === 401) { setMsg('Password errada'); setAGuardar(false); return; }
      const d = await r.json();
      setMsg(d.ok ? 'Guardado. O sensor aplica em ~10s — vê o número ao lado a mudar.' : 'Erro a guardar');
    } catch { setMsg('Sem ligação ao servidor'); }
    setAGuardar(false);
  };

  const entrar = () => {
    if (pass.length >= 4) setAutenticado(true);
    else setMsg('Mete a password');
  };

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

  const pessoas = vivo?.ocupacao ?? null;
  const tlm = vivo?.telemoveis_detectados ?? null;
  const online = vivo?.online ?? false;

  return (
    <div className="cal-wrap">
      <div className="cal-head">
        <div>
          <h1>Calibrar sensor</h1>
          <p>Ajusta e vê o número mudar ao vivo · sem cabo</p>
        </div>
        <a href="/v2/ambientes/rirstaff" className="cal-voltar">← voltar</a>
      </div>

      <div className="cal-tabs">
        {CLUSTERS.map(c => (
          <button key={c.id} className={cluster === c.id ? 'on' : ''} onClick={() => setCluster(c.id)}>
            {c.icon} {c.nome}
          </button>
        ))}
      </div>

      <div className="cal-grid">
        {/* PAINEL AO VIVO */}
        <div className="cal-vivo">
          <div className="cal-vivo-top">
            <span className={`cal-dot ${online ? 'on' : ''}`} />
            {online ? `AO VIVO · ${vivo?.age_s != null ? Math.round(vivo.age_s) : '?'}s` : 'offline'}
          </div>
          <div className="cal-num">{pessoas != null ? pessoas : '—'}</div>
          <div className="cal-num-sub">pessoas agora</div>
          <div className="cal-tlm">{tlm != null ? `${tlm} telemóveis detetados` : 'sem dados'}</div>
          <div className="cal-hint">
            Com a casa de banho <b>vazia</b>, vê quantas pessoas mostra.
            Sobe o <b>baseline</b> até dar 0.
          </div>
        </div>

        {/* CONTROLOS */}
        <div className="cal-ctrl">
          <Slider label="Baseline (ruído a subtrair)" val={cfg.baseline} min={0} max={40}
            onChange={v => setCfg({ ...cfg, baseline: v })} />
          <Slider label="Raio (metros)" val={cfg.raio_m} min={1} max={20}
            onChange={v => setCfg({ ...cfg, raio_m: v })} />
          <Slider label="Divisor (telemóveis por pessoa)" val={cfg.divisor} min={1} max={6}
            onChange={v => setCfg({ ...cfg, divisor: v })} />
          <Slider label="Capacidade" val={cfg.capacidade} min={1} max={30}
            onChange={v => setCfg({ ...cfg, capacidade: v })} />

          <button className="cal-guardar" onClick={guardar} disabled={aGuardar}>
            {aGuardar ? 'a guardar…' : 'Guardar calibração'}
          </button>
          {msg && <div className={`cal-msg ${msg.includes('errada') || msg.includes('Erro') || msg.includes('Sem') ? 'erro' : 'ok'}`}>{msg}</div>}
        </div>
      </div>

      <style jsx>{`
        .cal-wrap { max-width: 900px; margin: 0 auto; padding: 24px; font-family: 'Inter', system-ui, sans-serif; color: #0D1A0F; }
        .cal-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
        h1 { font-size: clamp(22px, 3vw, 30px); margin: 0; font-weight: 600; }
        p { color: #6B756C; font-size: 14px; margin: 4px 0 0; }
        .cal-voltar { color: #4A7C59; font-size: 14px; text-decoration: none; font-weight: 600; }
        .cal-tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .cal-tabs button { flex: 1; padding: 12px; border: 1px solid #E5E8E0; background: #fff; border-radius: 12px; font-size: 15px; font-family: inherit; cursor: pointer; color: #6B756C; }
        .cal-tabs button.on { background: #1B3A21; color: #fff; border-color: #1B3A21; font-weight: 600; }
        .cal-grid { display: grid; grid-template-columns: 1fr 1.3fr; gap: 20px; }
        .cal-vivo { border: 1px solid #E5E8E0; border-radius: 18px; padding: 24px; text-align: center; background: #FAFBF9; }
        .cal-vivo-top { display: inline-flex; align-items: center; gap: 7px; font-size: 12px; font-weight: 700; letter-spacing: .04em; color: #6B756C; text-transform: uppercase; margin-bottom: 16px; }
        .cal-dot { width: 9px; height: 9px; border-radius: 50%; background: #C9CEC4; }
        .cal-dot.on { background: #1B7A3D; box-shadow: 0 0 0 4px rgba(27,122,61,.18); }
        .cal-num { font-size: 72px; font-weight: 700; line-height: 1; color: #1B3A21; }
        .cal-num-sub { font-size: 13px; color: #8A938B; margin-top: 4px; }
        .cal-tlm { font-size: 13px; color: #4A7C59; margin-top: 14px; }
        .cal-hint { font-size: 12px; color: #8A938B; margin-top: 18px; line-height: 1.5; }
        .cal-ctrl { border: 1px solid #E5E8E0; border-radius: 18px; padding: 24px; }
        .cal-guardar { width: 100%; padding: 14px; background: #1B3A21; color: #fff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 8px; }
        .cal-guardar:disabled { opacity: .6; }
        .cal-msg { margin-top: 12px; font-size: 13px; text-align: center; }
        .cal-msg.ok { color: #1B7A3D; }
        .cal-msg.erro { color: #C25A1A; }
        @media (max-width: 720px) { .cal-grid { grid-template-columns: 1fr; } }
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
        .sl { margin-bottom: 20px; }
        .sl-top { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 8px; }
        .sl-top b { color: #1B3A21; font-size: 15px; }
        input { width: 100%; accent-color: #1B3A21; }
      `}</style>
    </div>
  );
}
