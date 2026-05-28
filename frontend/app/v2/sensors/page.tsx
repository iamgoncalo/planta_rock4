'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  api,
  type BackendSensor,
  type SensorsSummary,
} from '@/lib/v2-api';
import { useLive, type ClusterPayload } from '@/components/v2/LiveContext';
import {
  Wifi, WifiOff, Radio, Activity, ShieldCheck, AlertTriangle,
} from 'lucide-react';

const REFRESH_MS = 15_000;

const CLUSTER_ZONE: Record<string, string> = {
  'wc-01': 'Portal Norte', 'wc-02': 'Central', 'wc-03': 'Portão', 'wc-04': 'Cumeada',
  'wc-05': 'Portão', 'wc-06': 'Central', 'wc-07': 'Lockers', 'wc-08': 'Exterior',
};

type State = 'calmo' | 'activo' | 'intenso';

function occState(occ: number): State {
  if (occ >= 80) return 'intenso';
  if (occ >= 55) return 'activo';
  return 'calmo';
}
const STATE_COLOR: Record<State, string> = {
  calmo: 'var(--green, #1B3A21)',
  activo: 'var(--green-soft, #4A7C59)',
  intenso: 'var(--amber, #C25A1A)',
};
const STATE_LABEL: Record<State, { pt: string; en: string }> = {
  calmo: { pt: 'Calmo', en: 'Calm' },
  activo: { pt: 'Activo', en: 'Active' },
  intenso: { pt: 'Intenso', en: 'Busy' },
};

function clusterNum(id: string): string {
  const m = id.match(/(\d+)/);
  return m ? m[1].padStart(2, '0') : id.toUpperCase();
}

export default function SensorsPage() {
  const { snapshot, connection } = useLive();
  const [sensors, setSensors] = useState<BackendSensor[]>([]);
  const [summary, setSummary] = useState<SensorsSummary | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const [list, sum] = await Promise.all([api.sensors(), api.sensorsSummary()]);
        if (cancelled) return;
        setSensors(list);
        setSummary(sum);
      } catch { /* mantém último estado */ }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  // nós por cluster
  const sensorsByCluster = useMemo(() => {
    const m = new Map<string, BackendSensor[]>();
    for (const s of sensors) {
      const k = (s.cluster_id || '').toLowerCase();
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(s);
    }
    return m;
  }, [sensors]);

  const liveByCluster = useMemo(() => {
    const m = new Map<string, ClusterPayload>();
    for (const c of snapshot?.clusters ?? []) m.set(c.cluster_id.toLowerCase(), c);
    return m;
  }, [snapshot]);

  // lista canónica dos 8
  const clusterIds = useMemo(() => {
    const fromLive = (snapshot?.expected_clusters ?? []).map((c) => c.toLowerCase());
    const base = fromLive.length ? fromLive : ['wc-01','wc-02','wc-03','wc-04','wc-05','wc-06','wc-07','wc-08'];
    return base.slice(0, 8);
  }, [snapshot]);

  // KPIs de rede
  const totalNodes = sensors.length || (summary?.total ?? 0);
  const onlineNodes = sensors.filter((s) => true).length; // saúde detalhada vem do health map abaixo
  const healthMap = summary?.health ?? {};
  const online = healthMap['online'] ?? onlineNodes;
  const degraded = (healthMap['offline'] ?? 0) + (healthMap['degraded'] ?? 0);
  const coverage = totalNodes > 0 ? Math.round((online / totalNodes) * 100) : 100;
  const live = connection === 'sse' || connection === 'polling';

  return (
    <div className="sx-root">
      {/* Faixa de KPIs */}
      <header className="sx-head">
        <div className="sx-title-wrap">
          <div className="sx-eyebrow">PlantaOS · Rede de sensores</div>
          <h1 className="sx-title">Sensores <span className="sx-sub">Sensors</span></h1>
        </div>
        <div className="sx-kpis">
          <Kpi icon={<Radio size={18} strokeWidth={1.5} />} label="Nós" value={String(totalNodes)} />
          <Kpi icon={<ShieldCheck size={18} strokeWidth={1.5} />} label="Cobertura" value={`${coverage}%`} tone={coverage >= 90 ? 'ok' : 'warn'} />
          <Kpi icon={online > 0 ? <Wifi size={18} strokeWidth={1.5} /> : <WifiOff size={18} strokeWidth={1.5} />} label="Online" value={String(online)} />
          <Kpi icon={<Activity size={18} strokeWidth={1.5} />} label="Sinal" value={live ? 'ao vivo' : '—'} tone={live ? 'ok' : 'warn'} live={live} />
        </div>
      </header>

      {/* Grelha 4×2 dos 8 clusters — 100vh, sem scroll */}
      <div className="sx-grid">
        {clusterIds.map((cid) => {
          const nodes = sensorsByCluster.get(cid) ?? [];
          const lc = liveByCluster.get(cid);
          const p = lc?.params;
          const occ = Math.round(p?.ocupacao_instantanea ?? 0);
          const st = occState(occ);
          const conf = Math.round((p?.confianca_cruzada ?? 0) * 100);
          const fila = p?.fila_atual ?? 0;
          const espera = p?.tempo_espera_min ?? 0;
          const unisex = p?.is_unissex;
          const nodeOnline = nodes.length;
          const color = STATE_COLOR[st];

          return (
            <article key={cid} className="sx-card" style={{ ['--accent' as any]: color }}>
              <div className="sx-card-top">
                <div className="sx-card-id">
                  <span className="sx-wc">WC-{clusterNum(cid)}</span>
                  <span className="sx-zone">{unisex ? 'unissexo' : CLUSTER_ZONE[cid] ?? ''}</span>
                </div>
                <div className="sx-state" style={{ color }}>
                  <span className="sx-dot" style={{ background: color }} />
                  {STATE_LABEL[st].pt}
                </div>
              </div>

              <div className="sx-occ">
                <span className="sx-occ-num" style={{ color }}>{occ}</span>
                <span className="sx-occ-pct">%</span>
                <span className="sx-occ-cap">ocupação</span>
              </div>

              {/* barra de ocupação */}
              <div className="sx-bar">
                <div className="sx-bar-fill" style={{ width: `${Math.min(100, occ)}%`, background: color }} />
              </div>

              <div className="sx-metrics">
                <Metric label="fila" value={fila > 0 ? `${fila}` : '—'} />
                <Metric label="espera" value={espera > 0 ? `${espera} min` : 'agora'} />
                <Metric label="nós" value={`${nodeOnline}`} />
                <Metric label="confiança" value={`${conf}%`} tone={conf >= 70 ? undefined : 'warn'} />
              </div>
            </article>
          );
        })}
      </div>

      <style jsx>{`
        .sx-root {
          position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0;
          display: flex; flex-direction: column; background: var(--paper, #FAFAF7);
          color: var(--ink, #0D1A0F); overflow: hidden;
          padding: clamp(12px,1.6vw,22px) clamp(14px,2.4vw,34px) max(14px, env(safe-area-inset-bottom));
        }
        .sx-head { flex-shrink: 0; display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; flex-wrap: wrap; margin-bottom: clamp(12px,1.6vw,20px); }
        .sx-eyebrow { font-size: 10px; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-faint, rgba(13,26,15,0.4)); }
        .sx-title { font-size: clamp(24px,3.4vw,44px); font-weight: 200; letter-spacing: -0.04em; line-height: 1; margin-top: 5px; }
        .sx-sub { font-style: italic; font-weight: 300; font-size: 0.5em; color: var(--ink-soft, rgba(13,26,15,0.55)); letter-spacing: -0.01em; margin-left: 6px; }
        .sx-kpis { display: flex; gap: clamp(10px,1.4vw,22px); }

        .sx-grid {
          flex: 1; min-height: 0; display: grid;
          grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(2, 1fr);
          gap: clamp(8px,1vw,16px);
        }
        .sx-card {
          min-height: 0; min-width: 0; background: #fff; border: 1px solid rgba(13,26,15,0.08);
          border-radius: 18px; padding: clamp(12px,1.4vw,20px); display: flex; flex-direction: column;
          position: relative; overflow: hidden;
          box-shadow: 0 1px 2px rgba(13,26,15,0.03);
        }
        .sx-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent); opacity: 0.9; }
        .sx-card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
        .sx-card-id { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
        .sx-wc { font-size: clamp(15px,1.5vw,20px); font-weight: 600; letter-spacing: -0.02em; }
        .sx-zone { font-size: 11px; font-weight: 500; color: var(--ink-faint, rgba(13,26,15,0.4)); letter-spacing: 0.02em; }
        .sx-state { display: flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 600; letter-spacing: 0.01em; flex-shrink: 0; }
        .sx-dot { width: 7px; height: 7px; border-radius: 50%; animation: sx-pulse 1.8s ease-in-out infinite; }

        .sx-occ { display: flex; align-items: baseline; gap: 4px; margin-top: auto; }
        .sx-occ-num { font-size: clamp(34px,4.4vw,60px); font-weight: 200; letter-spacing: -0.05em; line-height: 0.9; font-variant-numeric: tabular-nums; }
        .sx-occ-pct { font-size: clamp(15px,1.6vw,22px); font-weight: 300; color: var(--ink-soft, rgba(13,26,15,0.55)); }
        .sx-occ-cap { font-size: 11px; color: var(--ink-faint, rgba(13,26,15,0.4)); margin-left: auto; align-self: flex-end; letter-spacing: 0.04em; text-transform: uppercase; }

        .sx-bar { height: 6px; background: #f0eee6; border-radius: 4px; overflow: hidden; margin: 10px 0 12px; }
        .sx-bar-fill { height: 100%; border-radius: 4px; transition: width 0.6s cubic-bezier(0.2,0.7,0.2,1); }

        .sx-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }

        @keyframes sx-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

        @media (max-width: 1000px) {
          .sx-grid { grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(4, 1fr); }
        }
        @media (max-width: 560px) {
          .sx-root { overflow-y: auto; }
          .sx-grid { grid-template-columns: 1fr; grid-template-rows: none; gap: 10px; }
          .sx-card { min-height: 150px; }
          .sx-kpis { gap: 14px; }
        }
        @media (prefers-reduced-motion: reduce) { .sx-dot { animation: none; } .sx-bar-fill { transition: none; } }
      `}</style>
    </div>
  );
}

function Kpi({ icon, label, value, tone, live }: { icon: React.ReactNode; label: string; value: string; tone?: 'ok' | 'warn'; live?: boolean }) {
  const color = tone === 'warn' ? 'var(--amber, #C25A1A)' : 'var(--ink, #0D1A0F)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
      <span style={{ color: tone === 'warn' ? 'var(--amber, #C25A1A)' : 'var(--green-soft, #4A7C59)', display: 'flex' }}>{icon}</span>
      <div>
        <div style={{ fontSize: 9.5, fontWeight: 500, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-faint, rgba(13,26,15,0.4))' }}>{label}</div>
        <div style={{ fontSize: 'clamp(15px,1.6vw,22px)', fontWeight: 600, letterSpacing: '-0.02em', color, fontVariantNumeric: 'tabular-nums', display: 'flex', alignItems: 'center', gap: 6 }}>
          {value}
          {live && <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green-soft, #4A7C59)', animation: 'sx-pulse 1.8s ease-in-out infinite' }} />}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'warn' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
      <span style={{ fontSize: 9, fontWeight: 500, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--ink-faint, rgba(13,26,15,0.38))' }}>{label}</span>
      <span style={{ fontSize: 'clamp(12px,1.2vw,15px)', fontWeight: 600, letterSpacing: '-0.01em', color: tone === 'warn' ? 'var(--amber, #C25A1A)' : 'var(--ink, #0D1A0F)', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</span>
    </div>
  );
}
