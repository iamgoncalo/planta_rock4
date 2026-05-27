'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '../lib/api';
import type { SensorHealth, GlobalKPIs } from '../lib/types';

const C = {
  surface: '#FAFAF7',
  card: '#fff',
  border: '#DEE8DE',
  ink: '#1A1A1A',
  muted: '#6B7280',
  accent: '#4A7C59',
  accentBg: '#EDF4EF',
  critical: '#C25A1A',
  online: '#6FAF82',
  degraded: '#D48B3A',
} as const;

// Festival days
const FESTIVAL_DAYS = [20, 21, 27, 28]; // June 2026

interface ClusterStatus {
  cluster_id: string;
  avg_occ_pct: number;
  total_fila: number;
  status: string;
  sections_ok: number;
  sections_critical: number;
  confidence: number;
}

function makeSim(): ClusterStatus[] {
  const rng = (seed: number) => (seed * 1664525 + 1013904223) & 0xffffffff;
  let s = 2026;
  const next = (min: number, max: number) => {
    s = rng(s);
    return min + Math.abs(s % (max - min + 1));
  };
  const clusters = ['WC-01', 'WC-02', 'WC-03', 'WC-04', 'WC-05', 'WC-06', 'WC-07', 'WC-08'];
  return clusters.map((id) => {
    const occ = next(30, 95);
    return {
      cluster_id: id,
      avg_occ_pct: occ,
      total_fila: next(0, 40),
      status: occ >= 90 ? 'critical' : occ >= 70 ? 'warning' : 'normal',
      sections_ok: occ < 70 ? 2 : 1,
      sections_critical: occ >= 90 ? 1 : 0,
      confidence: 0.7 + next(0, 25) / 100,
    };
  });
}

function statusColor(s: string) {
  if (s === 'critical') return C.critical;
  if (s === 'warning') return C.degraded;
  return C.online;
}

function OccBar({ pct, status }: { pct: number; status: string }) {
  return (
    <div style={{ height: 6, borderRadius: 3, background: C.border, overflow: 'hidden', marginTop: 4 }}>
      <div
        style={{
          height: '100%',
          width: `${Math.min(100, pct)}%`,
          background: statusColor(status),
          borderRadius: 3,
          transition: 'width 1.5s ease',
        }}
      />
    </div>
  );
}

function ClusterCard({ c }: { c: ClusterStatus }) {
  const col = statusColor(c.status);
  return (
    <Link
      href={`/occupation`}
      style={{
        display: 'block',
        background: C.card,
        border: `1.5px solid ${c.status === 'critical' ? col + '88' : c.status === 'warning' ? col + '55' : C.border}`,
        borderRadius: 10,
        padding: '12px 14px',
        textDecoration: 'none',
        color: 'inherit',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: C.ink }}>{c.cluster_id}</span>
        <span style={{ fontWeight: 700, fontSize: 16, color: col }}>{Math.round(c.avg_occ_pct)}%</span>
      </div>
      <OccBar pct={c.avg_occ_pct} status={c.status} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6, fontSize: 12, color: C.muted }}>
        <span>Fila: {c.total_fila}p</span>
        <span style={{ color: col, fontWeight: c.status !== 'normal' ? 600 : 400 }}>
          {c.status === 'critical' ? '⚠ Crítico' : c.status === 'warning' ? '▲ Atenção' : '● Ok'}
        </span>
      </div>
    </Link>
  );
}

export default function HomePage() {
  const [clusters, setClusters] = useState<ClusterStatus[]>([]);
  const [sortBy, setSortBy] = useState<'occ' | 'q' | 'id'>('occ');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isOffline, setIsOffline] = useState(false);

  const now = new Date();
  const isFestivalDay = FESTIVAL_DAYS.includes(now.getDate()) && now.getMonth() === 5; // June

  useEffect(() => {
    // Hydration-safe: render sim on client, then fetch live
    setClusters(makeSim());

    const fetchData = async () => {
      try {
        const data = await api.state();
        const sectionsByCluster: Record<string, typeof data.sections> = {};
        for (const s of data.sections) {
          const cid = s.cluster_id ?? s.section_id.split('_')[0];
          if (!sectionsByCluster[cid]) sectionsByCluster[cid] = [];
          sectionsByCluster[cid].push(s);
        }
        const derived: ClusterStatus[] = Object.entries(sectionsByCluster).map(([id, secs]) => {
          const avgOcc = secs.reduce((a, s) => a + s.ocupacao_pct, 0) / secs.length;
          const totalFila = secs.reduce((a, s) => a + s.fila_atual, 0);
          const hasCrit = secs.some((s) => s.status === 'critical');
          const hasWarn = secs.some((s) => s.status === 'warning');
          return {
            cluster_id: id,
            avg_occ_pct: avgOcc,
            total_fila: totalFila,
            status: hasCrit ? 'critical' : hasWarn ? 'warning' : 'normal',
            sections_ok: secs.filter((s) => s.status === 'ok' || s.status === 'offline' ? false : s.status !== 'critical' && s.status !== 'warning').length,
            sections_critical: secs.filter((s) => s.status === 'critical').length,
            confidence: secs.reduce((a, s) => a + (s.confidence ?? 0.7), 0) / secs.length,
          };
        });
        setClusters(derived);
        setIsOffline(false);
        setLastUpdate(new Date());
      } catch {
        setIsOffline(true);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 30_000);
    return () => clearInterval(id);
  }, []);

  const sorted = [...clusters].sort((a, b) =>
    sortBy === 'occ'
      ? b.avg_occ_pct - a.avg_occ_pct
      : sortBy === 'q'
      ? b.total_fila - a.total_fila
      : a.cluster_id.localeCompare(b.cluster_id)
  );

  const critCount = clusters.filter((c) => c.status === 'critical').length;
  const avgOcc = clusters.length ? Math.round(clusters.reduce((a, c) => a + c.avg_occ_pct, 0) / clusters.length) : 0;

  return (
    <main style={{ background: C.surface, minHeight: '100vh', fontFamily: 'var(--font-ui)' }}>
      {/* Header */}
      <div
        style={{
          background: 'linear-gradient(135deg, #1B3A21, #4A7C59)',
          color: '#fff',
          padding: '20px 16px 16px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <img
              src="/planta-logo.svg"
              alt="Planta Smart Homes"
              width={130}
              height={101}
              style={{
                display: 'block',
                filter: 'brightness(0) invert(1) drop-shadow(0 2px 8px rgba(0,0,0,0.25))',
              }}
            />
            <p style={{ margin: '6px 0 0', fontSize: 12, opacity: 0.75, color: '#fff' }}>
              Rock in Rio Lisboa 2026 · Parque Tejo
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                background: 'rgba(255,255,255,0.15)',
                borderRadius: 12,
                padding: '3px 10px',
                fontSize: 11,
                fontWeight: 600,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: isOffline ? '#D48B3A' : '#6FAF82',
                  display: 'inline-block',
                }}
              />
              {isOffline ? 'OFFLINE' : 'LIVE'}
            </div>
            {lastUpdate && (
              <div style={{ fontSize: 10, opacity: 0.65, marginTop: 3 }}>
                {lastUpdate.toLocaleTimeString('pt-PT')}
              </div>
            )}
          </div>
        </div>

        {/* KPI bar */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 8,
            marginTop: 14,
          }}
        >
          {[
            { label: 'Clusters', value: clusters.length, col: '#fff' },
            { label: 'Occ. Média', value: `${avgOcc}%`, col: avgOcc > 80 ? '#C25A1A' : avgOcc > 60 ? '#D48B3A' : '#6FAF82' },
            { label: 'Críticos', value: critCount, col: critCount > 0 ? '#C25A1A' : '#6FAF82' },
            { label: 'Fila Total', value: clusters.reduce((a, c) => a + c.total_fila, 0), col: '#fff' },
          ].map(({ label, value, col }) => (
            <div
              key={label}
              style={{
                background: 'rgba(255,255,255,0.12)',
                borderRadius: 8,
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: 18, fontWeight: 700, color: col }}>{value}</span>
              <span style={{ fontSize: 10, opacity: 0.8 }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Festival day alert */}
      {isFestivalDay && (
        <div
          style={{
            background: '#7C3AED18',
            borderBottom: '1px solid #7C3AED30',
            padding: '8px 16px',
            fontSize: 13,
            color: '#7C3AED',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          ♪ Dia de festival — picos de fluxo esperados
        </div>
      )}

      {/* Sort controls */}
      <div style={{ display: 'flex', gap: 6, padding: '12px 16px 8px', alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: C.muted, flexShrink: 0 }}>Ordenar:</span>
        {(['occ', 'q', 'id'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSortBy(s)}
            style={{
              padding: '5px 12px',
              borderRadius: 16,
              border: `1.5px solid ${sortBy === s ? C.accent : C.border}`,
              background: sortBy === s ? C.accent : C.card,
              color: sortBy === s ? '#fff' : C.ink,
              fontSize: 12,
              fontWeight: sortBy === s ? 600 : 400,
              cursor: 'pointer',
              minHeight: 44,
              fontFamily: 'var(--font-ui)',
            }}
          >
            {s === 'occ' ? 'Ocup.' : s === 'q' ? 'Fila' : 'ID'}
          </button>
        ))}
      </div>

      {/* Cluster grid */}
      <div
        style={{
          padding: '0 16px 16px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 10,
        }}
      >
        {sorted.map((c) => (
          <ClusterCard key={c.cluster_id} c={c} />
        ))}
      </div>

      {/* Find nearest CTA */}
      <div
        style={{
          position: 'sticky',
          bottom: 'calc(var(--nav-h) + env(safe-area-inset-bottom, 0px))',
          padding: '8px 16px',
          background: C.surface,
          borderTop: `1px solid ${C.border}`,
        }}
      >
        <Link
          href="/occupation"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            padding: '14px 20px',
            background: 'linear-gradient(135deg, #1B3A21, #4A7C59)',
            color: '#fff',
            borderRadius: 12,
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: 15,
            minHeight: 52,
          }}
        >
          ◎ Encontrar WC mais próxima
        </Link>
      </div>
    </main>
  );
}
