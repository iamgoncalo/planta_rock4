'use client';
import { useEffect, useState, useCallback } from 'react';

type Casa = {
  cluster: string; nome: string; genero: string; capacidade: number;
  data_origin: string; online?: boolean; ocupacao?: number | null;
  ocupacao_pct?: number | null; estado?: string; age_s?: number;
  entradas_ir?: number | null; saidas_ir?: number | null; ocupacao_ir?: number | null;
  pessoas_estimadas?: number | null; telemoveis_detectados?: number | null;
  homens?: number | null; mulheres?: number | null;
  confianca_cruzada?: number | null; estado_sensor?: string;
  rssi_dbm?: number | null; fw?: string; mensagem?: string;
  fontes?: Record<string, number>;
};

const API = 'https://api.plantarockinrio.com';

function corEstado(estado?: string) {
  if (estado === 'cheio') return '#C25A1A';
  if (estado === 'quase cheio') return '#D08A4A';
  if (estado === 'moderado') return '#4A7C59';
  return '#6FAF82';
}

export default function RirStaffPage() {
  const [casas, setCasas] = useState<Casa[]>([]);
  const [ts, setTs] = useState<number>(0);
  const [erro, setErro] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/rirstaff`, { cache: 'no-store' });
      const d = await r.json();
      setCasas(d.casas_de_banho || []);
      setTs(d.ts || Date.now() / 1000);
      setErro(false);
    } catch { setErro(true); }
  }, []);

  useEffect(() => {
    load();
    const i = setInterval(load, 1000); // ao segundo
    return () => clearInterval(i);
  }, [load]);

  const calibrar = async (cluster: string, valor: number) => {
    await fetch(`${API}/api/v1/rirstaff/${cluster}/capacidade?valor=${valor}`, { method: 'POST' });
    load();
  };

  return (
    <div className="rs-wrap">
      <div className="rs-head">
        <div>
          <h1>Casas de banho · Staff</h1>
          <p className="rs-sub">Rock in Rio Lisboa 2026 · contagem ao vivo · ocupação em tempo real</p>
        </div>
        <div className="rs-live">
          <span className={`rs-pulse ${casas.some(c => c.online) ? 'on' : ''}`} />
          {casas.some(c => c.online) ? 'AO VIVO' : 'à espera dos sensores'}
        </div>
      </div>

      <div className="rs-grid">
        {casas.map((c) => {
          const real = c.data_origin === 'real';
          const pct = c.ocupacao_pct ?? 0;
          return (
            <div key={c.cluster} className={`rs-card ${real ? 'real' : 'esperar'}`}>
              <div className="rs-card-head">
                <span className="rs-genero">{c.genero === 'M' ? '♂' : '♀'}</span>
                <div>
                  <div className="rs-nome">{c.nome}</div>
                  <div className="rs-origem">
                    {real
                      ? <span className="rs-real">● REAL · {c.age_s != null ? Math.round(c.age_s) : '?'}s</span>
                      : <span className="rs-esperar">◌ à espera do LilyGo</span>}
                  </div>
                </div>
              </div>

              {real ? (
                <>
                  <div className="rs-big">
                    <span className="rs-ocup" style={{ color: corEstado(c.estado) }}>{c.ocupacao ?? '—'}</span>
                    <span className="rs-cap">/ {c.capacidade}</span>
                  </div>
                  <div className="rs-estado" style={{ color: corEstado(c.estado) }}>{(c.estado || '').toUpperCase()}</div>
                  <div className="rs-bar">
                    <div className="rs-bar-fill" style={{ width: `${Math.min(100, pct)}%`, background: corEstado(c.estado) }} />
                  </div>

                  <div className="rs-kpis">
                    <div className="rs-kpi"><span>Entradas</span><b>{c.entradas_ir ?? '—'}</b></div>
                    <div className="rs-kpi"><span>Saídas</span><b>{c.saidas_ir ?? '—'}</b></div>
                    <div className="rs-kpi"><span>Confiança</span><b>{c.confianca_cruzada != null ? Math.round(c.confianca_cruzada * 100) + '%' : '—'}</b></div>
                    <div className="rs-kpi"><span>Sinal</span><b>{c.rssi_dbm != null ? c.rssi_dbm + ' dBm' : '—'}</b></div>
                  </div>

                  {(c.pessoas_estimadas != null || c.telemoveis_detectados != null || c.homens != null) && (
                    <div className="rs-extra">
                      {c.pessoas_estimadas != null && <span>câmara: {c.pessoas_estimadas}</span>}
                      {c.telemoveis_detectados != null && <span>wifi: {c.telemoveis_detectados}</span>}
                      {c.homens != null && <span>♂{c.homens} ♀{c.mulheres}</span>}
                    </div>
                  )}

                  <div className="rs-cal">
                    <span>capacidade</span>
                    {[5, 6, 8, 10].map(v => (
                      <button key={v} className={c.capacidade === v ? 'on' : ''} onClick={() => calibrar(c.cluster, v)}>{v}</button>
                    ))}
                  </div>
                </>
              ) : (
                <div className="rs-wait">
                  <p>{c.mensagem || 'À espera do primeiro dado do LilyGo.'}</p>
                  <p className="rs-wait-sub">Capacidade configurada: {c.capacidade} pessoas</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {erro && <div className="rs-erro">Sem ligação ao servidor — a tentar de novo…</div>}

      <style jsx>{`
        .rs-wrap { max-width: 1100px; margin: 0 auto; padding: 24px; font-family: 'Inter', system-ui, sans-serif; color: #0D1A0F; }
        .rs-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
        h1 { font-size: clamp(22px, 3vw, 32px); margin: 0; font-weight: 600; }
        .rs-sub { color: #6B756C; font-size: 14px; margin: 4px 0 0; }
        .rs-live { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 700; letter-spacing: .05em; color: #6B756C; text-transform: uppercase; }
        .rs-pulse { width: 9px; height: 9px; border-radius: 50%; background: #C9CEC4; }
        .rs-pulse.on { background: #1B7A3D; box-shadow: 0 0 0 4px rgba(27,122,61,.18); animation: pulse 1.6s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .4; } }
        .rs-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .rs-card { border: 1px solid #E5E8E0; border-radius: 18px; padding: 22px; background: #fff; }
        .rs-card.real { border-left: 4px solid #1B7A3D; }
        .rs-card.esperar { border-left: 4px dashed #C9CEC4; background: #FAFBF9; }
        .rs-card-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
        .rs-genero { font-size: 34px; line-height: 1; color: #1B3A21; }
        .rs-nome { font-size: 17px; font-weight: 600; }
        .rs-origem { font-size: 11px; margin-top: 2px; }
        .rs-real { color: #1B7A3D; font-weight: 700; }
        .rs-esperar { color: #8A938B; }
        .rs-big { display: flex; align-items: baseline; gap: 8px; margin: 8px 0 2px; }
        .rs-ocup { font-size: clamp(48px, 9vw, 76px); font-weight: 700; line-height: 1; }
        .rs-cap { font-size: 26px; color: #8A938B; font-weight: 500; }
        .rs-estado { font-size: 13px; font-weight: 700; letter-spacing: .06em; margin-bottom: 12px; }
        .rs-bar { height: 8px; background: #F0F2EC; border-radius: 99px; overflow: hidden; margin-bottom: 16px; }
        .rs-bar-fill { height: 100%; border-radius: 99px; transition: width .5s ease; }
        .rs-kpis { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px; }
        .rs-kpi { background: #F7F9F5; border-radius: 10px; padding: 8px 6px; text-align: center; }
        .rs-kpi span { display: block; font-size: 10px; color: #8A938B; text-transform: uppercase; letter-spacing: .03em; }
        .rs-kpi b { font-size: 16px; }
        .rs-extra { display: flex; gap: 12px; font-size: 12px; color: #4A7C59; margin-bottom: 14px; }
        .rs-cal { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #8A938B; }
        .rs-cal span { margin-right: 4px; text-transform: uppercase; letter-spacing: .03em; }
        .rs-cal button { border: 1px solid #E5E8E0; background: #fff; border-radius: 8px; padding: 5px 11px; cursor: pointer; font-family: inherit; font-size: 13px; }
        .rs-cal button.on { background: #1B3A21; color: #fff; border-color: #1B3A21; font-weight: 600; }
        .rs-wait { padding: 24px 4px; text-align: center; color: #8A938B; }
        .rs-wait p { margin: 4px 0; }
        .rs-wait-sub { font-size: 12px; }
        .rs-erro { margin-top: 16px; padding: 10px; background: #FFF6ED; border: 1px solid #F0D9BE; border-radius: 10px; color: #7A4A1E; font-size: 13px; text-align: center; }
        @media (max-width: 720px) { .rs-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}
