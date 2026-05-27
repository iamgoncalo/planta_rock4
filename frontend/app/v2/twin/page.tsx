'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  aggregate,
  CLUSTERS,
  occupancyColor,
  fmtNumber,
  type ClusterLive,
  type ClusterMeta,
} from '@/lib/v2-api';
import Sparkline from '@/components/v2/Sparkline';

const MAP_W = 1684;
const MAP_H = 2384;
const REFRESH_MS = 10_000;

export default function TwinPage() {
  const [clusters, setClusters] = useState<ClusterLive[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const sparkBuf = useRef<Map<string, number[]>>(new Map());

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const data = await api.state();
        if (cancelled) return;
        const agg = aggregate(data.sections ?? []);
        setClusters(agg);
        for (const c of agg) {
          const b = sparkBuf.current.get(c.meta.id) ?? [];
          b.push(c.ocupacao);
          while (b.length > 30) b.shift();
          sparkBuf.current.set(c.meta.id, b);
        }
      } catch {
        /* offline */
      }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  // Read ?cluster=wc-01 from URL once
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const sp = new URLSearchParams(window.location.search);
    const c = sp.get('cluster');
    if (c) setSelectedId(c);
  }, []);

  const clusterById = useMemo(() => {
    const m = new Map<string, ClusterLive>();
    for (const c of clusters) m.set(c.meta.id, c);
    return m;
  }, [clusters]);

  const selected = selectedId ? clusterById.get(selectedId) : null;

  const onMouseDown = (e: React.MouseEvent) => {
    dragRef.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragRef.current) return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    setPan({ x: dragRef.current.px + dx, y: dragRef.current.py + dy });
  };
  const onMouseUp = () => {
    dragRef.current = null;
  };
  const zoomIn = () => setZoom((z) => Math.min(3, z + 0.25));
  const zoomOut = () => setZoom((z) => Math.max(0.4, z - 0.25));
  const reset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 360px',
        height: 'calc(100vh - 56px - 36px)',
      }}
    >
      {/* ============ MAP ============ */}
      <div
        ref={containerRef}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        style={{
          position: 'relative',
          overflow: 'hidden',
          background:
            'radial-gradient(ellipse at center, #FAFAF7 0%, #F4F1E8 100%)',
          cursor: dragRef.current ? 'grabbing' : 'grab',
          borderRight: '1px solid var(--border)',
        }}
      >
        {/* Header overlay */}
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: 16,
            zIndex: 10,
            background: 'rgba(255,255,255,0.92)',
            backdropFilter: 'blur(8px)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: '12px 16px',
            maxWidth: 360,
          }}
        >
          <div className="section-label" style={{ marginBottom: 4 }}>
            Digital Twin · Parque Tejo
          </div>
          <h2
            className="serif"
            style={{ fontSize: 20, fontWeight: 500, color: 'var(--ink)' }}
          >
            8 clusters WC · planta do recinto
          </h2>
          <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 4 }}>
            Clica em qualquer cluster para abrir o painel. Arrasta para mover.
            Roda do rato ou botões para zoom.
          </p>
        </div>

        {/* Controls */}
        <div
          style={{
            position: 'absolute',
            top: 16,
            right: 16,
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <button onClick={zoomIn} className="btn btn-outline btn-sm">
            +
          </button>
          <button onClick={zoomOut} className="btn btn-outline btn-sm">
            −
          </button>
          <button onClick={reset} className="btn btn-outline btn-sm">
            ⌂
          </button>
        </div>

        {/* SVG map */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center center',
            transition: dragRef.current ? 'none' : 'transform 0.2s ease',
            pointerEvents: dragRef.current ? 'none' : 'auto',
          }}
        >
          <svg
            viewBox={`0 0 ${MAP_W} ${MAP_H}`}
            style={{
              width: '70%',
              maxWidth: 920,
              height: 'auto',
              userSelect: 'none',
            }}
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Site outline */}
            <rect
              x={60}
              y={60}
              width={MAP_W - 120}
              height={MAP_H - 120}
              fill="#FFFFFF"
              stroke="#2E7D4F"
              strokeWidth={2}
              strokeOpacity={0.25}
              strokeDasharray="8 6"
              rx={32}
            />

            {/* Stages */}
            <Stage x={500} y={210} label="Palco Mundo" w={420} h={120} />
            <Stage x={300} y={650} label="Music Valley" w={300} h={100} />
            <Stage x={1050} y={1250} label="Palco Super Bock" w={300} h={100} />

            {/* Entrance/exit */}
            <text
              x={1500}
              y={500}
              fontSize={32}
              fill="#3A6040"
              fontFamily="DM Sans, sans-serif"
              fontWeight={600}
              textAnchor="middle"
            >
              entrada
            </text>
            <text
              x={1500}
              y={520}
              fontSize={16}
              fill="#7A9E7E"
              fontFamily="DM Mono, monospace"
              textAnchor="middle"
            >
              norte
            </text>

            {/* Clusters */}
            {CLUSTERS.map((meta) => {
              const c = clusterById.get(meta.id);
              const occ = c?.ocupacao ?? 0;
              const color = c
                ? occupancyColor(occ).replace('var(--critical)', '#C25A1A')
                    .replace('var(--amber)', '#A85D00')
                    .replace('var(--green-light)', '#6FAF82')
                : '#B5C9B9';
              const isSelected = selectedId === meta.id;
              return (
                <g key={meta.id}>
                  {/* halo */}
                  {(c && c.status !== 'ok') && (
                    <circle
                      cx={meta.x}
                      cy={meta.y}
                      r={70}
                      fill={color}
                      opacity={0.15}
                    />
                  )}
                  <circle
                    cx={meta.x}
                    cy={meta.y}
                    r={isSelected ? 48 : 40}
                    fill={color}
                    stroke="#FFFFFF"
                    strokeWidth={3}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedId(meta.id)}
                  />
                  <text
                    x={meta.x}
                    y={meta.y - 4}
                    fontSize={20}
                    fill="#FFFFFF"
                    fontFamily="DM Sans, sans-serif"
                    fontWeight={700}
                    textAnchor="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {meta.code}
                  </text>
                  <text
                    x={meta.x}
                    y={meta.y + 16}
                    fontSize={14}
                    fill="#FFFFFF"
                    fontFamily="DM Mono, monospace"
                    fontWeight={600}
                    textAnchor="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {occ}%
                  </text>
                  {/* Label below */}
                  <text
                    x={meta.x}
                    y={meta.y + 78}
                    fontSize={18}
                    fill="#1A2E1C"
                    fontFamily="DM Sans, sans-serif"
                    fontWeight={600}
                    textAnchor="middle"
                  >
                    {meta.id.toUpperCase()}
                  </text>
                  <text
                    x={meta.x}
                    y={meta.y + 100}
                    fontSize={14}
                    fill="#3A6040"
                    fontFamily="DM Sans, sans-serif"
                    textAnchor="middle"
                  >
                    {meta.zone}
                  </text>
                  <text
                    x={meta.x}
                    y={meta.y + 120}
                    fontSize={12}
                    fill="#7A9E7E"
                    fontFamily="DM Mono, monospace"
                    textAnchor="middle"
                  >
                    {meta.total} lugares · {meta.isUnisex ? 'unisex' : `${meta.male}♂ ${meta.female}♀`}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* ============ DETAIL PANEL ============ */}
      <aside
        style={{
          background: 'var(--card)',
          padding: 0,
          overflowY: 'auto',
        }}
      >
        {!selected ? (
          <EmptyPanel />
        ) : (
          <DetailPanel
            c={selected}
            spark={sparkBuf.current.get(selected.meta.id) ?? []}
            onClose={() => setSelectedId(null)}
          />
        )}
      </aside>
    </div>
  );
}

function Stage({ x, y, w, h, label }: { x: number; y: number; w: number; h: number; label: string }) {
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={12}
        fill="#1B3A21"
        opacity={0.85}
      />
      <text
        x={x + w / 2}
        y={y + h / 2 + 8}
        fontSize={30}
        fill="#FFFFFF"
        fontFamily="DM Sans, sans-serif"
        fontWeight={600}
        textAnchor="middle"
      >
        {label}
      </text>
    </g>
  );
}

function EmptyPanel() {
  return (
    <div
      style={{
        padding: '40px 24px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div className="section-label" style={{ marginBottom: 0 }}>
        Painel de detalhe
      </div>
      <h3
        className="serif"
        style={{
          fontSize: 22,
          fontWeight: 500,
          color: 'var(--ink)',
          letterSpacing: '-0.01em',
        }}
      >
        Selecciona um cluster
      </h3>
      <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
        Clica em qualquer círculo do mapa para ver as métricas detalhadas desse
        cluster: ocupação ao vivo, divisão por género, fila actual, tempo de
        espera médio, e a tendência das últimas leituras.
      </p>
      <div style={{ marginTop: 'auto', paddingTop: 24 }}>
        <div className="mono" style={{ fontSize: 11, color: 'var(--faint)' }}>
          1 137 lugares · 8 clusters · refresh 10 s
        </div>
      </div>
    </div>
  );
}

function DetailPanel({
  c,
  spark,
  onClose,
}: {
  c: ClusterLive;
  spark: number[];
  onClose: () => void;
}) {
  return (
    <div style={{ padding: '24px 22px 32px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--green)',
            letterSpacing: '0.08em',
            fontWeight: 600,
          }}
        >
          {c.meta.id.toUpperCase()} · {c.meta.code}
        </span>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: '1px solid var(--border)',
            color: 'var(--muted)',
            width: 28,
            height: 28,
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          ✕
        </button>
      </div>

      <h3
        className="serif"
        style={{
          fontSize: 24,
          fontWeight: 500,
          color: 'var(--ink)',
          marginBottom: 4,
        }}
      >
        {c.meta.zone}
      </h3>
      <div style={{ fontSize: 12, color: 'var(--faint)', marginBottom: 22 }}>
        {c.meta.total} lugares · {c.meta.isUnisex
          ? 'Cluster unisex'
          : `${c.meta.male} masc · ${c.meta.female} fem`}{' '}
        · {c.meta.pmr} PMR
      </div>

      {/* Big metric */}
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: 18,
          marginBottom: 14,
          textAlign: 'center',
        }}
      >
        <div
          className="serif"
          style={{
            fontSize: 56,
            fontWeight: 500,
            color: occupancyColor(c.ocupacao).startsWith('var')
              ? c.ocupacao >= 80
                ? '#C25A1A'
                : c.ocupacao >= 60
                ? '#A85D00'
                : '#2E7D4F'
              : '#2E7D4F',
            lineHeight: 1,
            letterSpacing: '-0.03em',
          }}
        >
          {c.ocupacao}%
        </div>
        <div
          style={{
            fontSize: 10,
            color: 'var(--faint)',
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            marginTop: 8,
            fontWeight: 600,
          }}
        >
          ocupação actual
        </div>
        <div style={{ marginTop: 10 }}>
          <Sparkline values={spark} width={300} height={40} color="#2E7D4F" />
        </div>
      </div>

      {/* Grid metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 8,
          marginBottom: 14,
        }}
      >
        <MetricCell label="Pessoas estimadas" value={fmtNumber(c.pessoas)} />
        <MetricCell label="Fila actual" value={fmtNumber(c.filaTotal)} />
        <MetricCell label="Espera média" value={`${c.esperaMin}m`} />
        <MetricCell
          label="Confiança dados"
          value={`${Math.round(c.confianca * 100)}%`}
        />
      </div>

      {/* M/F split if not unisex */}
      {!c.meta.isUnisex && (
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: '12px 14px',
            marginBottom: 14,
          }}
        >
          <div
            style={{
              fontSize: 10,
              color: 'var(--faint)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              fontWeight: 600,
              marginBottom: 8,
            }}
          >
            divisão por género
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
            <div style={{ flex: 1 }}>
              <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>
                {c.homens ?? 0}
              </div>
              <div style={{ fontSize: 10, color: 'var(--faint)' }}>
                ♂ masc · {c.meta.male} lugares
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>
                {c.mulheres ?? 0}
              </div>
              <div style={{ fontSize: 10, color: 'var(--faint)' }}>
                ♀ fem · {c.meta.female} lugares
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Flow info */}
      <div style={{ marginBottom: 14 }}>
        <div
          style={{
            fontSize: 10,
            color: 'var(--faint)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            fontWeight: 600,
            marginBottom: 6,
          }}
        >
          fluxo agregado (5 min)
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span className="mono" style={{ fontSize: 12, color: 'var(--text)' }}>
            ↑ entradas {c.entradas}
          </span>
          <span className="mono" style={{ fontSize: 12, color: 'var(--text)' }}>
            ↓ saídas {c.saidas}
          </span>
        </div>
      </div>

      {/* GPS */}
      <div
        style={{
          padding: '10px 14px',
          background: 'var(--green-pale)',
          borderRadius: 8,
          fontSize: 11,
          fontFamily: 'var(--font-mono), monospace',
          color: 'var(--muted)',
        }}
      >
        GPS · {c.meta.gpsLat.toFixed(5)}° N · {c.meta.gpsLon.toFixed(5)}° E
        <br />
        Distância ao palco principal: {c.meta.distStageM} m
      </div>
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '10px 12px',
      }}
    >
      <div
        className="mono"
        style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: 9,
          color: 'var(--faint)',
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          marginTop: 2,
          fontWeight: 600,
        }}
      >
        {label}
      </div>
    </div>
  );
}
