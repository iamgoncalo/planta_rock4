'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLive } from '@/components/v2/LiveContext';
import { api } from '@/lib/v2-api';

/* ──────────────────────────────────────────────────────────────────
   /v2/sensors/fusion — Arquitectura completa de fusao de sensores
   Do sensor ao fluxo: IR + LilyGo (WiFi) + ML/OAK -> WiFi 6E / LoRaWAN
   -> Backhaul 4G -> Railway -> Fusao. Diagrama + estado ao vivo (10s).
   Estilo Planta (Inter, paleta verde, ambar #C25A1A, sem vermelho).
   ────────────────────────────────────────────────────────────────── */

const REFRESH_MS = 10000;

// Capacidades + tipo (fonte: clusters_capacity no backend)
const CLUSTERS: Array<{
  id: string; nome: string; cap: number; unisex: boolean;
  ir: number; lilygo: number; e_m: number; n_m: number;
}> = [
  { id: 'wc-01', nome: 'WC-01', cap: 135, unisex: false, ir: 8, lilygo: 1, e_m: 105, n_m: 327 },
  { id: 'wc-02', nome: 'WC-02', cap: 126, unisex: false, ir: 8, lilygo: 1, e_m: 147, n_m: 286 },
  { id: 'wc-03', nome: 'WC-03', cap: 102, unisex: false, ir: 8, lilygo: 1, e_m: 158, n_m: 195 },
  { id: 'wc-04', nome: 'WC-04', cap: 150, unisex: false, ir: 8, lilygo: 2, e_m: 188, n_m: 289 },
  { id: 'wc-05', nome: 'WC-05', cap: 133, unisex: true,  ir: 0, lilygo: 2, e_m: 158, n_m: 240 },
  { id: 'wc-06', nome: 'WC-06', cap: 208, unisex: true,  ir: 0, lilygo: 3, e_m: 0,   n_m: 84  },
  { id: 'wc-07', nome: 'WC-07', cap: 138, unisex: false, ir: 8, lilygo: 1, e_m: 130, n_m: 154 },
  { id: 'wc-08', nome: 'WC-08', cap: 145, unisex: false, ir: 8, lilygo: 2, e_m: 0,   n_m: 0   },
];

// Camadas de rede (infra partilhada)
const NETWORK = {
  wifi: { modelo: 'TP-Link EAP670 WiFi 6E', aps: 8, raioDenso: 45, raioLivre: 80 },
  lora: { modelo: 'Dragino DLOS8 868MHz', gateways: 2, alcance_m: 3000 },
  backhaul: { primario: 'NOS 4G', secundario: 'Vodafone 4G', failover_s: 5 },
};

// Pesos de fusao
const FUSION = [
  { fonte: 'IR (entrada/saída por porta)', peso: 0.50, nota: 'Mais fiável quando direccional' },
  { fonte: 'LilyGo · WiFi sniffing', peso: 0.30, nota: 'Telemóveis → pessoas (factor por cluster)' },
  { fonte: 'ML · Luxonis OAK', peso: 0.20, nota: 'Contagem por visão · distingue H/M' },
];

type IngestStatus = {
  data_ttl_s: number;
  clusters: Record<string, { data_source: string; age_s: number | null; ts_device: number | null }>;
};

function sourceLabel(s: string): { txt: string; cor: string } {
  if (s === 'real') return { txt: 'A receber', cor: 'var(--green-soft, #4A7C59)' };
  if (s === 'stale') return { txt: 'Sem sinal', cor: 'var(--amber, #C25A1A)' };
  return { txt: 'Simulado', cor: 'var(--color-muted, #8A938B)' };
}

export default function FusionPage() {
  const { snapshot } = useLive();
  const [ingest, setIngest] = useState<IngestStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await api.ingestStatus();
        if (!cancelled) setIngest(s);
      } catch { /* mantém último */ }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  const totals = useMemo(() => {
    const ir = CLUSTERS.reduce((a, c) => a + c.ir, 0);
    const lilygo = CLUSTERS.reduce((a, c) => a + c.lilygo, 0);
    return { ir, lilygo, aps: NETWORK.wifi.aps, gateways: NETWORK.lora.gateways };
  }, []);

  // mapa a escala (coordenadas em metros, origem wc-08)
  const VB = 1000;
  const PAD = 80;
  const maxE = Math.max(...CLUSTERS.map((c) => c.e_m));
  const maxN = Math.max(...CLUSTERS.map((c) => c.n_m));
  const sx = (e: number) => PAD + (e / Math.max(1, maxE)) * (VB - 2 * PAD);
  const sy = (n: number) => VB - PAD - (n / Math.max(1, maxN)) * (VB - 2 * PAD);

  return (
    <div className="fx-root">
      <header className="fx-head">
        <div className="fx-eyebrow">PlantaOS · Arquitectura de fluxos</div>
        <h1 className="fx-title">Fusão de sensores</h1>
        <p className="fx-lead">
          Do sensor ao fluxo. Cada cluster cruza três fontes — infravermelhos por porta,
          deteção WiFi do LilyGo e visão por máquina — e a rede leva tudo ao backend.
          Estado ao vivo, actualizado a cada 10&nbsp;segundos.
        </p>
        <div className="fx-kpis">
          <div className="fx-kpi"><b>{totals.ir}</b><span>sensores IR</span></div>
          <div className="fx-kpi"><b>{totals.lilygo}</b><span>hubs LilyGo</span></div>
          <div className="fx-kpi"><b>{totals.aps}</b><span>pontos WiFi 6E</span></div>
          <div className="fx-kpi"><b>{totals.gateways}</b><span>gateways LoRa</span></div>
        </div>
      </header>

      {/* CAMADA 1 — Sensores no terreno */}
      <section className="fx-sec">
        <div className="fx-sec-label">Camada 1 · Sensores no terreno</div>
        <h2 className="fx-h2">O que mede cada cluster</h2>
        <div className="fx-grid">
          {CLUSTERS.map((c) => {
            const st = ingest?.clusters?.[c.id]?.data_source ?? 'none';
            const sl = sourceLabel(st);
            const age = ingest?.clusters?.[c.id]?.age_s;
            return (
              <article key={c.id} className="fx-card">
                <div className="fx-card-top">
                  <span className="fx-card-id">{c.nome}</span>
                  <span className="fx-dot" style={{ background: sl.cor }} title={sl.txt} />
                </div>
                <div className="fx-card-meta">
                  {c.unisex ? 'Unissexo' : 'Masc + Fem'} · cap. {c.cap}
                </div>
                <ul className="fx-card-list">
                  <li><span>Infravermelhos</span><b>{c.ir > 0 ? `${c.ir} (4/porta)` : '—'}</b></li>
                  <li><span>Hub LilyGo</span><b>{c.lilygo}</b></li>
                  <li><span>Visão ML</span><b className="fx-soft">planeado</b></li>
                </ul>
                <div className="fx-card-foot" style={{ color: sl.cor }}>
                  {sl.txt}{age != null ? ` · há ${Math.round(age)}s` : ''}
                </div>
              </article>
            );
          })}
        </div>
        <p className="fx-note">
          Os clusters unissexo (WC-05 e WC-06) não têm infravermelhos por porta —
          a contagem vem do LilyGo e, quando disponível, da visão por máquina, sem separação por género.
        </p>
      </section>

      {/* CAMADA 2 — LilyGo */}
      <section className="fx-sec">
        <div className="fx-sec-label">Camada 2 · Hub LilyGo</div>
        <h2 className="fx-h2">O cérebro de cada cluster</h2>
        <p className="fx-body">
          Cada hub LilyGo (ESP32) faz duas coisas: lê os sensores de infravermelhos para contar
          entradas e saídas por porta, e escuta passivamente o ambiente WiFi para estimar quantas
          pessoas estão por perto. Nunca guarda identificadores — apenas conta. O factor de conversão
          telemóveis→pessoas é calibrado por cluster.
        </p>
        <div className="fx-rows">
          <div className="fx-row"><span>Interior denso (WC-05, WC-06)</span><b>factor 1.8</b></div>
          <div className="fx-row"><span>Exterior semi-aberto (restantes)</span><b>factor 2.5</b></div>
          <div className="fx-row"><span>Envio</span><b>cada 60s · WiFi primário</b></div>
        </div>
      </section>

      {/* CAMADA 3 — WiFi 6E */}
      <section className="fx-sec">
        <div className="fx-sec-label">Camada 3 · Rede WiFi 6E</div>
        <h2 className="fx-h2">Alcance e cobertura</h2>
        <p className="fx-body">
          A nuvem de clusters estende-se por cerca de 327&nbsp;m (Norte-Sul) e 298&nbsp;m (Este-Oeste).
          Em multidão densa, cada ponto WiFi cobre um raio de ~{NETWORK.wifi.raioDenso}&nbsp;m;
          em espaço livre, até ~{NETWORK.wifi.raioLivre}&nbsp;m. Por isso usamos {NETWORK.wifi.aps} pontos
          para garantir todos os clusters com redundância.
        </p>
        <div className="fx-rows">
          <div className="fx-row"><span>Equipamento</span><b>{NETWORK.wifi.modelo}</b></div>
          <div className="fx-row"><span>Grupo central (WC-01 a 05, 07)</span><b>todos a &lt;180m · mesh</b></div>
          <div className="fx-row fx-row-warn"><span>WC-06 e WC-08 · isolados</span><b>ponto dedicado cada um</b></div>
        </div>
      </section>

      {/* CAMADA 4 — LoRaWAN */}
      <section className="fx-sec">
        <div className="fx-sec-label">Camada 4 · LoRaWAN 868MHz</div>
        <h2 className="fx-h2">A espinha dorsal de longo alcance</h2>
        <p className="fx-body">
          Onde o WiFi não chega, entra o LoRaWAN — alcance até {(NETWORK.lora.alcance_m / 1000).toFixed(0)}&nbsp;km.
          É o caminho de segurança para os pontos mais afastados, em especial o WC-08, que fica a mais de
          400&nbsp;m do centro e nunca seria coberto por mesh WiFi. Se um hub perde o WiFi, cai
          automaticamente para LoRaWAN.
        </p>
        <div className="fx-rows">
          <div className="fx-row"><span>Equipamento</span><b>{NETWORK.lora.modelo}</b></div>
          <div className="fx-row"><span>Gateways</span><b>{NETWORK.lora.gateways}</b></div>
          <div className="fx-row"><span>Função</span><b>fallback automático</b></div>
        </div>
      </section>

      {/* CAMADA 5 — Backhaul */}
      <section className="fx-sec">
        <div className="fx-sec-label">Camada 5 · Backhaul 4G</div>
        <h2 className="fx-h2">Ligação à nuvem</h2>
        <p className="fx-body">
          Do recinto para o backend, dois operadores em paralelo. Se um falha, o outro assume
          em poucos segundos — sem interromper o fluxo de dados.
        </p>
        <div className="fx-rows">
          <div className="fx-row"><span>Primário</span><b>{NETWORK.backhaul.primario}</b></div>
          <div className="fx-row"><span>Secundário</span><b>{NETWORK.backhaul.secundario}</b></div>
          <div className="fx-row"><span>Comutação</span><b>~{NETWORK.backhaul.failover_s}s</b></div>
        </div>
      </section>

      {/* CAMADA 6 — Fusao */}
      <section className="fx-sec">
        <div className="fx-sec-label">Camada 6 · Fusão</div>
        <h2 className="fx-h2">Como as fontes se cruzam</h2>
        <p className="fx-body">
          No backend, as três fontes combinam-se com pesos. Se uma fonte falha, o peso
          redistribui-se pelas restantes — nunca há divisão por zero, e a confiança baixa
          de forma transparente. Quanto mais as fontes concordam, maior a confiança.
        </p>
        <div className="fx-fusion">
          {FUSION.map((f) => (
            <div key={f.fonte} className="fx-fusion-row">
              <div className="fx-fusion-bar-wrap">
                <div className="fx-fusion-bar" style={{ width: `${f.peso * 100}%` }} />
              </div>
              <div className="fx-fusion-txt">
                <b>{Math.round(f.peso * 100)}%</b> {f.fonte}
                <span className="fx-fusion-note">{f.nota}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* MAPA DE COBERTURA */}
      <section className="fx-sec">
        <div className="fx-sec-label">Mapa · Cobertura à escala</div>
        <h2 className="fx-h2">Os 8 clusters e o seu alcance</h2>
        <div className="fx-map">
          <svg viewBox={`0 0 ${VB} ${VB}`} width="100%" preserveAspectRatio="xMidYMid meet">
            {/* raios WiFi denso */}
            {CLUSTERS.map((c) => (
              <circle key={`r-${c.id}`} cx={sx(c.e_m)} cy={sy(c.n_m)}
                r={(NETWORK.wifi.raioDenso / Math.max(1, maxE)) * (VB - 2 * PAD)}
                fill="var(--green-soft, #4A7C59)" opacity={0.07} />
            ))}
            {/* clusters */}
            {CLUSTERS.map((c) => {
              const st = ingest?.clusters?.[c.id]?.data_source ?? 'none';
              const sl = sourceLabel(st);
              return (
                <g key={c.id}>
                  <circle cx={sx(c.e_m)} cy={sy(c.n_m)} r={14}
                    fill={sl.cor} opacity={0.9} />
                  <text x={sx(c.e_m)} y={sy(c.n_m) - 22} textAnchor="middle"
                    fontSize={20} fill="var(--color-ink, #0D1A0F)" fontWeight={600}>
                    {c.nome}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
        <p className="fx-note">
          O verde indica clusters a receber dados reais; o âmbar, sensores em silêncio;
          o cinza, ainda em modo simulado. WC-06 e WC-08 (em baixo) ficam afastados do grupo central.
        </p>
      </section>

      <style jsx>{`
        .fx-root { max-width: 1100px; margin: 0 auto; padding: 32px 20px 120px; }
        .fx-head { margin-bottom: 40px; }
        .fx-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
          text-transform: uppercase; color: var(--color-muted, #8A938B); margin-bottom: 8px; }
        .fx-title { font-size: clamp(30px, 5vw, 48px); font-weight: 600;
          color: var(--color-ink, #0D1A0F); line-height: 1.05; margin: 0 0 12px; }
        .fx-lead { font-size: 15px; line-height: 1.6; color: var(--color-ink, #0D1A0F);
          max-width: 620px; opacity: 0.8; }
        .fx-kpis { display: flex; flex-wrap: wrap; gap: 24px; margin-top: 24px; }
        .fx-kpi { display: flex; flex-direction: column; }
        .fx-kpi b { font-size: 28px; font-weight: 600; color: var(--green-dark, #1B3A21);
          font-variant-numeric: tabular-nums; line-height: 1; }
        .fx-kpi span { font-size: 12px; color: var(--color-muted, #8A938B); margin-top: 4px; }

        .fx-sec { margin: 56px 0; }
        .fx-sec-label { font-size: 11px; font-weight: 700; letter-spacing: 0.06em;
          text-transform: uppercase; color: var(--green-soft, #4A7C59); margin-bottom: 8px; }
        .fx-h2 { font-size: clamp(22px, 3vw, 30px); font-weight: 600;
          color: var(--color-ink, #0D1A0F); margin: 0 0 16px; }
        .fx-body { font-size: 15px; line-height: 1.65; color: var(--color-ink, #0D1A0F);
          opacity: 0.82; max-width: 640px; margin: 0 0 20px; }
        .fx-note { font-size: 13px; line-height: 1.55; color: var(--color-muted, #8A938B);
          margin-top: 16px; max-width: 640px; }

        .fx-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; }
        .fx-card { background: white; border: 1px solid var(--color-border, #E5E8E0);
          border-radius: 14px; padding: 16px; }
        .fx-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .fx-card-id { font-size: 17px; font-weight: 700; color: var(--color-ink, #0D1A0F); }
        .fx-dot { width: 10px; height: 10px; border-radius: 50%; }
        .fx-card-meta { font-size: 12px; color: var(--color-muted, #8A938B); margin-bottom: 12px; }
        .fx-card-list { list-style: none; margin: 0; padding: 0; }
        .fx-card-list li { display: flex; justify-content: space-between; font-size: 13px;
          padding: 5px 0; border-bottom: 1px solid var(--color-paper, #FAFAF7); }
        .fx-card-list li:last-child { border-bottom: none; }
        .fx-card-list span { color: var(--color-muted, #8A938B); }
        .fx-card-list b { color: var(--color-ink, #0D1A0F); font-variant-numeric: tabular-nums; }
        .fx-soft { color: var(--color-muted, #8A938B) !important; font-weight: 500; }
        .fx-card-foot { font-size: 12px; font-weight: 600; margin-top: 12px; }

        .fx-rows { display: flex; flex-direction: column; gap: 1px;
          background: var(--color-border, #E5E8E0); border-radius: 12px; overflow: hidden;
          border: 1px solid var(--color-border, #E5E8E0); max-width: 560px; }
        .fx-row { display: flex; justify-content: space-between; align-items: center;
          background: white; padding: 12px 16px; font-size: 14px; }
        .fx-row span { color: var(--color-muted, #8A938B); }
        .fx-row b { color: var(--color-ink, #0D1A0F); font-weight: 600; }
        .fx-row-warn b { color: var(--amber, #C25A1A); }

        .fx-fusion { display: flex; flex-direction: column; gap: 16px; max-width: 600px; }
        .fx-fusion-row { display: flex; align-items: center; gap: 16px; }
        .fx-fusion-bar-wrap { width: 120px; height: 8px; background: var(--color-paper, #FAFAF7);
          border-radius: 4px; overflow: hidden; flex-shrink: 0; }
        .fx-fusion-bar { height: 100%; background: var(--green-soft, #4A7C59); border-radius: 4px; }
        .fx-fusion-txt { font-size: 14px; color: var(--color-ink, #0D1A0F); }
        .fx-fusion-txt b { color: var(--green-dark, #1B3A21); font-variant-numeric: tabular-nums; }
        .fx-fusion-note { display: block; font-size: 12px; color: var(--color-muted, #8A938B); margin-top: 2px; }

        .fx-map { background: white; border: 1px solid var(--color-border, #E5E8E0);
          border-radius: 16px; padding: 16px; }

        @media (max-width: 640px) {
          .fx-kpis { gap: 16px; }
          .fx-kpi b { font-size: 22px; }
        }
      `}</style>
    </div>
  );
}
