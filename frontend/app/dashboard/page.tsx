'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import SparkLine from './SparkLine';
import WCCard, { ClusterDisplay } from './WCCard';

const C = {
  surface: '#FAFAF7',
  card: '#FFFFFF',
  border: '#DEE8DE',
  ink: '#1A1A1A',
  muted: '#6B7280',
  accent: '#4A7C59',
  accentDark: '#1B3A21',
  accentLight: '#6FAF82',
  accentBg: '#EDF4EF',
  critical: '#C25A1A',
  warning: '#D48B3A',
} as const;

const ALL_CLUSTERS = ['wc-01', 'wc-02', 'wc-03', 'wc-04', 'wc-05', 'wc-06', 'wc-07', 'wc-08'] as const;
const UNISEX = new Set(['wc-05', 'wc-06']);

interface Section {
  section_id: string;
  ocupacao_pct?: number;
  fila_atual?: number;
  tempo_espera_min?: number;
  fluxo_entrada_pmin?: number;
  status?: string;
  simulated?: boolean;
  gender?: 'M' | 'F' | 'U';
}

interface KPIs {
  avg_ocupacao_pct?: number;
  total_fila?: number;
  critical_sections?: number;
  redirected_count?: number;
  any_simulated?: boolean;
}

interface State {
  kpis?: KPIs;
  sections?: Section[];
}

function toWcId(sectionId: string): string {
  return sectionId.split('_')[0].toLowerCase();
}

function aggregateClusters(sections: Section[]): Map<string, ClusterDisplay> {
  const acc = new Map<
    string,
    {
      pessoas: number;
      homens: number;
      mulheres: number;
      occList: number[];
      entradas: number;
      saidas: number;
      telemoveis: number;
      prosegur: number;
      critical: boolean;
      simulated: boolean;
    }
  >();

  for (const wc of ALL_CLUSTERS) {
    acc.set(wc, {
      pessoas: 0,
      homens: 0,
      mulheres: 0,
      occList: [],
      entradas: 0,
      saidas: 0,
      telemoveis: 0,
      prosegur: 0,
      critical: false,
      simulated: false,
    });
  }

  for (const s of sections) {
    const wc = toWcId(s.section_id);
    if (!acc.has(wc)) continue;
    const a = acc.get(wc)!;
    const occ = Number(s.ocupacao_pct ?? 0);
    const flux = Number(s.fluxo_entrada_pmin ?? 0);
    const estim = Math.round(flux * 5);
    const gender = s.section_id.endsWith('_F') ? 'F' : s.section_id.endsWith('_M') ? 'M' : 'U';
    if (gender === 'M') a.homens += estim;
    else if (gender === 'F') a.mulheres += estim;
    a.pessoas += estim;
    a.occList.push(occ);
    a.entradas += Math.round(flux * 10);
    a.saidas += Math.round(flux * 9);
    a.telemoveis += Math.round(estim * 1.4);
    a.prosegur += Math.round(estim * 1.1);
    if (s.status === 'critical') a.critical = true;
    if (s.simulated) a.simulated = true;
  }

  const result = new Map<string, ClusterDisplay>();
  for (const wc of ALL_CLUSTERS) {
    const a = acc.get(wc)!;
    const occAvg = a.occList.length
      ? Math.round(a.occList.reduce((x, y) => x + y, 0) / a.occList.length)
      : 0;
    const isUni = UNISEX.has(wc);
    let status: 'ok' | 'warning' | 'critical' = 'ok';
    if (a.critical || occAvg >= 80) status = 'critical';
    else if (occAvg >= 60) status = 'warning';
    result.set(wc, {
      id: wc,
      isUnisex: isUni,
      pessoas: a.pessoas,
      homens: isUni ? null : a.homens,
      mulheres: isUni ? null : a.mulheres,
      ocupacao: occAvg,
      entradas: a.entradas,
      saidas: a.saidas,
      telemoveis: a.telemoveis,
      prosegur: a.prosegur,
      confianca: a.simulated ? 0.5 : 0.92,
      estado: a.simulated ? 'simulado' : 'okay',
      sparkOccupancy: [],
      status,
    });
  }
  return result;
}

function PlantaLogo() {
  return (
    <img
      src="/planta-logo.svg"
      alt="Planta Smart Homes"
      width={140}
      height={109}
      style={{
        display: 'block',
        filter: 'drop-shadow(0 1px 3px rgba(27,58,33,0.15))',
      }}
    />
  );
}

function KpiCard({
  label,
  value,
  suffix,
  sparkline,
}: {
  label: string;
  value: string | number;
  suffix?: string;
  sparkline?: number[];
}) {
  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 16,
        padding: '20px 22px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div
        style={{
          fontSize: 11,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: C.muted,
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span
          style={{
            fontSize: 52,
            fontWeight: 500,
            color: C.ink,
            lineHeight: 1,
            letterSpacing: '-0.02em',
            fontFamily: 'Georgia, serif',
          }}
        >
          {value}
        </span>
        {suffix && (
          <span style={{ fontSize: 18, color: C.muted }}>{suffix}</span>
        )}
      </div>
      <div style={{ marginTop: 4, minHeight: 32 }}>
        <SparkLine values={sparkline ?? []} width={220} height={32} color={C.accent} />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [tickSec, setTickSec] = useState(0);

  const clusterBuffers = useRef<Map<string, number[]>>(new Map());
  const kpi01Buffer = useRef<number[]>([]);
  const kpi02Buffer = useRef<number[]>([]);

  useEffect(() => {
    let cancelled = false;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

    async function fetchOnce() {
      try {
        const r = await fetch(`${apiBase}/api/v1/state`, { cache: 'no-store' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data: State = await r.json();
        if (cancelled) return;
        setState(data);
        setLastUpdate(new Date());
        setError(null);

        const sections = data.sections ?? [];
        const agg = aggregateClusters(sections);
        for (const [id, c] of agg) {
          const buf = clusterBuffers.current.get(id) ?? [];
          buf.push(c.ocupacao);
          while (buf.length > 30) buf.shift();
          clusterBuffers.current.set(id, buf);
        }
        const k = data.kpis ?? {};
        const k02 = Number(k.avg_ocupacao_pct ?? 0);
        const k01 = Math.max(0, Math.round(100 - k02));
        kpi01Buffer.current.push(k01);
        kpi02Buffer.current.push(k02);
        while (kpi01Buffer.current.length > 30) kpi01Buffer.current.shift();
        while (kpi02Buffer.current.length > 30) kpi02Buffer.current.shift();
      } catch (e: unknown) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'erro';
          setError(msg);
        }
      }
    }

    fetchOnce();
    const iv = setInterval(fetchOnce, 10_000);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  useEffect(() => {
    const iv = setInterval(() => {
      if (lastUpdate) {
        setTickSec(Math.floor((Date.now() - lastUpdate.getTime()) / 1000));
      }
    }, 1000);
    return () => clearInterval(iv);
  }, [lastUpdate]);

  const clusters = useMemo<ClusterDisplay[]>(() => {
    if (!state?.sections) return [];
    const agg = aggregateClusters(state.sections);
    return ALL_CLUSTERS.map((wc) => {
      const c = agg.get(wc)!;
      return { ...c, sparkOccupancy: clusterBuffers.current.get(wc) ?? [] };
    });
  }, [state]);

  const k = state?.kpis ?? {};
  const kpi02 = Math.round((Number(k.avg_ocupacao_pct ?? 0)) * 10) / 10;
  const kpi01 = Math.max(0, Math.round(100 - kpi02));
  const kpi03 = Number(k.critical_sections ?? 0);
  const kpi04 = Number(k.redirected_count ?? 0);
  const anySimulated = Boolean(k.any_simulated ?? true);

  return (
    <main style={{ background: C.surface, minHeight: '100vh', color: C.ink }}>
      <header
        style={{
          background: '#FFFFFF',
          borderBottom: `1px solid ${C.border}`,
          padding: '28px 32px 22px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <PlantaLogo />
          <div>
            <h1
              style={{
                margin: 0,
                fontSize: 28,
                fontWeight: 500,
                letterSpacing: '-0.02em',
                color: C.accentDark,
                fontFamily: 'Georgia, serif',
              }}
            >
              Operations Dashboard
            </h1>
            <p style={{ margin: '3px 0 0', fontSize: 13, color: C.muted }}>
              Rock in Rio Lisboa 2026 · Parque Tejo · 8 WCs
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {/* anySimulated intencionalmente omitido — label proibida em UI pública */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: error ? C.critical : C.accentLight,
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: 12, color: C.muted }}>
              {error ? 'offline' : `updated ${tickSec}s ago`}
            </span>
          </div>
        </div>
      </header>

      <section
        style={{
          padding: '28px 32px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 14,
        }}
      >
        <KpiCard label="Flow Index" value={kpi01} suffix="/100" sparkline={kpi01Buffer.current} />
        <KpiCard label="Avg Occupancy" value={kpi02} suffix="%" sparkline={kpi02Buffer.current} />
        <KpiCard label="Critical Alerts" value={kpi03} sparkline={[]} />
        <KpiCard label="Redirected (day)" value={kpi04} sparkline={[]} />
      </section>

      <section
        style={{
          padding: '0 32px 32px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 14,
        }}
      >
        {clusters.map((c) => (
          <WCCard key={c.id} c={c} />
        ))}
      </section>

      <section style={{ padding: '0 32px 40px' }}>
        <div
          style={{
            background: C.card,
            border: `1px solid ${C.border}`,
            borderRadius: 14,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              padding: '16px 22px',
              borderBottom: `1px solid ${C.border}`,
              fontSize: 12,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: C.muted,
              fontWeight: 600,
            }}
          >
            Detalhe tecnico — parametros publicados ao SCOR
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: C.accentBg, color: C.accentDark }}>
                  {['Cluster', 'Pessoas', 'H', 'M', 'Ocup%', 'In', 'Out', 'Tel', 'Pros', 'Conf', 'Estado'].map(
                    (h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: 'left',
                          padding: '10px 14px',
                          fontWeight: 600,
                        }}
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {clusters.map((c) => (
                  <tr key={c.id} style={{ borderTop: `1px solid ${C.border}` }}>
                    <td style={{ padding: '10px 14px', fontWeight: 600, color: C.accentDark }}>
                      {c.id}
                    </td>
                    <td style={{ padding: '10px 14px' }}>{c.pessoas}</td>
                    <td style={{ padding: '10px 14px', color: c.isUnisex ? C.muted : C.ink }}>
                      {c.isUnisex ? '—' : c.homens}
                    </td>
                    <td style={{ padding: '10px 14px', color: c.isUnisex ? C.muted : C.ink }}>
                      {c.isUnisex ? '—' : c.mulheres}
                    </td>
                    <td style={{ padding: '10px 14px' }}>{c.ocupacao}%</td>
                    <td style={{ padding: '10px 14px' }}>{c.entradas}</td>
                    <td style={{ padding: '10px 14px' }}>{c.saidas}</td>
                    <td style={{ padding: '10px 14px' }}>{c.telemoveis}</td>
                    <td style={{ padding: '10px 14px' }}>{c.prosegur}</td>
                    <td style={{ padding: '10px 14px' }}>{c.confianca.toFixed(2)}</td>
                    <td style={{ padding: '10px 14px' }}>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: 999,
                          fontSize: 11,
                          background: c.estado === 'simulado' ? '#D48B3A20' : '#6FAF8220',
                          color: c.estado === 'simulado' ? C.warning : C.accent,
                        }}
                      >
                        {c.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <footer
        style={{
          padding: '24px 32px 40px',
          fontSize: 12,
          color: C.muted,
          textAlign: 'center',
          borderTop: `1px solid ${C.border}`,
          background: C.card,
        }}
      >
        <div style={{ marginBottom: 6 }}>
          PlantaOS · Planta Smart Homes · Porto ·{' '}
          <a href="https://plantasmarthomes.com" style={{ color: C.accent }}>
            plantasmarthomes.com
          </a>
        </div>
        <div style={{ fontSize: 11 }}>
          FCT 2025.00020.AIVLAB.DEUCALION · Deucalion Supercomputer · MACC · Guimaraes
        </div>
        <div style={{ marginTop: 14, display: 'flex', justifyContent: 'center', gap: 16, fontSize: 11 }}>
          <Link href="/" style={{ color: C.muted }}>Home</Link>
          <Link href="/twin" style={{ color: C.muted }}>Twin</Link>
          <Link href="/sensors" style={{ color: C.muted }}>Sensors</Link>
          <Link href="/ops" style={{ color: C.muted }}>Ops</Link>
        </div>
      </footer>
    </main>
  );
}
