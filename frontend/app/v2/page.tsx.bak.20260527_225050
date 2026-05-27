'use client';

import { useEffect, useRef, useState, useMemo } from 'react';
import Link from 'next/link';
import {
  api,
  aggregate,
  CLUSTERS,
  TOTAL_LUGARES,
  fmtNumber,
  type ClusterLive,
  type StateResponse,
} from '@/lib/v2-api';
import ClusterCard from '@/components/v2/ClusterCard';
import Sparkline from '@/components/v2/Sparkline';

const REFRESH_MS = 10_000;

export default function HomePage() {
  const [state, setState] = useState<StateResponse | null>(null);
  const [clusters, setClusters] = useState<ClusterLive[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const sparkBuffers = useRef<Map<string, number[]>>(new Map());
  const kpiPplBuf = useRef<number[]>([]);
  const kpiOccBuf = useRef<number[]>([]);
  const kpiFlowBuf = useRef<number[]>([]);

  useEffect(() => {
    let cancelled = false;

    const fetchTick = async () => {
      try {
        const data = await api.state();
        if (cancelled) return;
        setState(data);
        setError(null);
        setLastUpdate(new Date());
        const agg = aggregate(data.sections ?? []);
        setClusters(agg);
        for (const c of agg) {
          const buf = sparkBuffers.current.get(c.meta.id) ?? [];
          buf.push(c.ocupacao);
          while (buf.length > 30) buf.shift();
          sparkBuffers.current.set(c.meta.id, buf);
        }
        const totalPpl = agg.reduce((a, c) => a + c.pessoas, 0);
        const avgOcc = data.kpis?.avg_ocupacao_pct ?? 0;
        const flowIdx = Math.max(0, Math.round(100 - avgOcc));
        kpiPplBuf.current.push(totalPpl);
        kpiOccBuf.current.push(avgOcc);
        kpiFlowBuf.current.push(flowIdx);
        while (kpiPplBuf.current.length > 30) kpiPplBuf.current.shift();
        while (kpiOccBuf.current.length > 30) kpiOccBuf.current.shift();
        while (kpiFlowBuf.current.length > 30) kpiFlowBuf.current.shift();
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'erro');
        }
      }
    };

    fetchTick();
    const iv = setInterval(fetchTick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  // Metrics
  const totalPeople = useMemo(
    () => clusters.reduce((a, c) => a + c.pessoas, 0),
    [clusters],
  );
  const avgOcc = state?.kpis?.avg_ocupacao_pct ?? 0;
  const critCount = clusters.filter((c) => c.status === 'critical').length;
  const warnCount = clusters.filter((c) => c.status === 'warning').length;
  const totalFila = state?.kpis?.total_fila ?? 0;
  const flowIndex = Math.max(0, Math.round(100 - avgOcc));
  const freeCount = Math.round(TOTAL_LUGARES * (1 - avgOcc / 100));

  return (
    <div>
      {/* ============ HERO ============ */}
      <section
        style={{
          padding: '48px 32px 32px',
          background:
            'linear-gradient(165deg, #FFFFFF 0%, #FAFAF7 60%, #EDF4EF 100%)',
          borderBottom: '1px solid var(--border)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          aria-hidden
          style={{
            position: 'absolute',
            top: -40,
            right: -100,
            width: 480,
            height: 480,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(46,125,79,0.10) 0%, transparent 65%)',
            pointerEvents: 'none',
          }}
        />
        <div className="section-label">
          Rock in Rio Lisboa 2026 · Parque Tejo · 4 dias · 320 000+ visitantes
        </div>
        <h1
          className="serif"
          style={{
            fontSize: 'clamp(34px, 5vw, 56px)',
            fontWeight: 400,
            lineHeight: 1.08,
            marginBottom: 16,
            maxWidth: 980,
            color: 'var(--ink)',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <span style={{ color: 'var(--green)', fontWeight: 600 }}>
            {fmtNumber(totalPeople || 100_000)}+
          </span>{' '}
          pessoas.{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--muted)' }}>
            1 137 lugares WC.
          </em>{' '}
          <strong style={{ fontWeight: 700 }}>Em tempo real.</strong>
        </h1>
        <p
          style={{
            fontSize: 16,
            color: 'var(--muted)',
            lineHeight: 1.65,
            maxWidth: 720,
            marginBottom: 24,
            position: 'relative',
            zIndex: 1,
          }}
        >
          PlantaOS conta pessoas em cada um dos 8 clusters de WC do Parque Tejo,
          mede o fluxo de entrada e saída ao minuto, e recomenda às pessoas a
          casa de banho mais rápida e mais segura agora mesmo. Sem rastreio
          individual. Sem MAC guardado. Só fluxos.
        </p>
        <div
          style={{
            display: 'flex',
            gap: 10,
            flexWrap: 'wrap',
            position: 'relative',
            zIndex: 1,
          }}
        >
          <Link href="/v2/twin" className="btn btn-primary">
            Abrir Digital Twin
          </Link>
          <Link href="/v2/shows" className="btn btn-outline">
            Simular shows
          </Link>
          <Link href="/v2/operations" className="btn btn-outline">
            Operações
          </Link>
          <Link href="/v2/chat" className="btn btn-outline">
            Chat AI
          </Link>
        </div>
      </section>

      {/* ============ KPI ROW ============ */}
      <section
        style={{
          padding: '0 32px',
          marginTop: -24,
          position: 'relative',
          zIndex: 2,
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 12,
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 16,
            padding: 4,
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <KpiTile
            label="Pessoas estimadas"
            value={fmtNumber(totalPeople)}
            spark={kpiPplBuf.current}
          />
          <KpiTile
            label="Ocupação média"
            value={`${Math.round(avgOcc)}%`}
            spark={kpiOccBuf.current}
            color={
              avgOcc >= 80
                ? 'var(--critical)'
                : avgOcc >= 60
                ? 'var(--amber)'
                : 'var(--green)'
            }
          />
          <KpiTile
            label="Lugares livres"
            value={fmtNumber(Math.max(0, freeCount))}
            spark={[]}
            color="var(--green)"
          />
          <KpiTile
            label="Críticos"
            value={String(critCount)}
            spark={[]}
            color={critCount > 0 ? 'var(--critical)' : 'var(--green)'}
          />
          <KpiTile
            label="Avisos"
            value={String(warnCount)}
            spark={[]}
            color={warnCount > 0 ? 'var(--amber)' : 'var(--green)'}
          />
          <KpiTile
            label="Flow Index"
            value={`${flowIndex}/100`}
            spark={kpiFlowBuf.current}
            color={flowIndex >= 60 ? 'var(--green)' : flowIndex >= 35 ? 'var(--amber)' : 'var(--critical)'}
          />
          <KpiTile
            label="Fila total"
            value={fmtNumber(totalFila)}
            spark={[]}
          />
        </div>
      </section>

      {/* ============ 8 WC GRID ============ */}
      <section style={{ padding: '40px 32px 32px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginBottom: 20,
            flexWrap: 'wrap',
            gap: 16,
          }}
        >
          <div>
            <div className="section-label" style={{ marginBottom: 4 }}>
              Inteligência por cluster · ao vivo
            </div>
            <h2
              className="serif"
              style={{
                fontSize: 28,
                fontWeight: 500,
                color: 'var(--ink)',
                letterSpacing: '-0.02em',
              }}
            >
              8 clusters · 1 137 lugares
            </h2>
          </div>
          <div
            style={{
              fontSize: 12,
              color: 'var(--faint)',
              display: 'flex',
              gap: 14,
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            <Legend dot="var(--green-light)" label="Livre <60%" />
            <Legend dot="var(--amber)" label="Atenção 60–80%" />
            <Legend dot="var(--critical)" label="Crítico >80%" />
          </div>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))',
            gap: 14,
          }}
        >
          {(clusters.length ? clusters : CLUSTERS.map((meta) => ({
            meta,
            ocupacao: 0,
            pessoas: 0,
            homens: meta.isUnisex ? null : 0,
            mulheres: meta.isUnisex ? null : 0,
            filaTotal: 0,
            esperaMin: 0,
            entradas: 0,
            saidas: 0,
            confianca: 0.5,
            simulated: true,
            status: 'ok' as const,
          }))).map((c) => (
            <Link
              key={c.meta.id}
              href={`/v2/twin?cluster=${c.meta.id}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <ClusterCard
                c={c}
                spark={sparkBuffers.current.get(c.meta.id) ?? []}
                onClick={() => {}}
              />
            </Link>
          ))}
        </div>
      </section>

      {/* ============ STATUS BAR ============ */}
      <section
        style={{
          padding: '16px 32px 40px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          fontSize: 12,
          color: 'var(--muted)',
          borderTop: '1px solid var(--border)',
          marginTop: 8,
        }}
      >
        <div className="mono">
          {error ? (
            <span style={{ color: 'var(--critical)' }}>● backend offline</span>
          ) : (
            <span style={{ color: 'var(--green)' }}>
              ● actualizado{' '}
              {lastUpdate
                ? lastUpdate.toLocaleTimeString('pt-PT')
                : '—'}
            </span>
          )}
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--faint)' }}>
          api.plantarockinrio.com · publisher SCOR · refresh 10 s
        </div>
      </section>
    </div>
  );
}

function KpiTile({
  label,
  value,
  spark,
  color = 'var(--ink)',
}: {
  label: string;
  value: string;
  spark: number[];
  color?: string;
}) {
  return (
    <div
      style={{
        background: 'var(--card)',
        padding: '16px 18px 14px',
        borderRadius: 12,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        minHeight: 110,
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: 'var(--faint)',
        }}
      >
        {label}
      </div>
      <div
        className="serif"
        style={{
          fontSize: 36,
          fontWeight: 500,
          color,
          lineHeight: 1,
          letterSpacing: '-0.02em',
        }}
      >
        {value}
      </div>
      <div style={{ marginTop: 'auto' }}>
        <Sparkline values={spark} width={180} height={26} color={color} />
      </div>
    </div>
  );
}

function Legend({ dot, label }: { dot: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dot,
          display: 'inline-block',
        }}
      />
      {label}
    </span>
  );
}
