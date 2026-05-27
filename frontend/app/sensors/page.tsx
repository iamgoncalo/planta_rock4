'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '../../lib/api';
import type {
  SensorHealth,
  GatewayStatus,
  BatteryReport,
  MaintenanceItem,
  SensorSummary,
} from '../../lib/types';

// ─── Colour tokens ────────────────────────────────────────────────────────────
const C = {
  online: '#6FAF82',
  degraded: '#D48B3A',
  offline: '#6B7280',
  critical: '#C25A1A',
  surface: '#FAFAF7',
  card: '#fff',
  border: '#DEE8DE',
  ink: '#1A1A1A',
  muted: '#6B7280',
  accent: '#4A7C59',
  accentBg: '#EDF4EF',
} as const;

// ─── Status helpers ───────────────────────────────────────────────────────────
function statusDot(s: 'online' | 'degraded' | 'offline' | string) {
  const col = s === 'online' ? C.online : s === 'degraded' ? C.degraded : C.offline;
  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '50%',
        backgroundColor: col,
        flexShrink: 0,
      }}
      aria-label={s}
    />
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        backgroundColor: color + '22',
        color: color,
        border: `1px solid ${color}44`,
        letterSpacing: '0.03em',
      }}
    >
      {label}
    </span>
  );
}

// ─── Battery widget ───────────────────────────────────────────────────────────
function BatteryWidget({ report }: { report: BatteryReport }) {
  const pct = Math.min(100, (report.estimated_days_remaining / 16) * 100);
  const col = pct > 50 ? C.online : pct > 20 ? C.degraded : C.critical;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: C.ink }}>{report.cluster_id}</span>
        <span style={{ fontSize: 12, color: col, fontWeight: 600 }}>
          {report.estimated_days_remaining}d
        </span>
      </div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: C.border,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            height: '100%',
            width: `${pct}%`,
            background: col,
            borderRadius: 4,
            transition: 'width 1s ease',
          }}
        />
      </div>
      <span style={{ fontSize: 11, color: C.muted }}>
        {report.battery_mah.toLocaleString()} mAh · {report.draw_ma} mA
      </span>
    </div>
  );
}

// ─── Sensor type label map ────────────────────────────────────────────────────
const TYPE_LABEL: Record<string, string> = {
  lilygo: 'HUB',
  ir: 'IR',
  wifi: 'WiFi',
  camera: 'CAM',
  lorawan: 'LoRa',
};

const TYPE_COLOR: Record<string, string> = {
  lilygo: '#4A7C59',
  ir: '#6B7280',
  wifi: '#2563EB',
  camera: '#7C3AED',
  lorawan: '#B45309',
};

// ─── Cluster sensor card ──────────────────────────────────────────────────────
function ClusterCard({ health, summary }: { health: SensorHealth; summary: SensorSummary }) {
  const activeCount = health.active_sources?.length ?? 0;
  const totalSources = 4;
  const healthPct = Math.round((activeCount / totalSources) * 100);
  const cardStatus = health.issues.length === 0 ? 'online' : activeCount > 0 ? 'degraded' : 'offline';
  const borderCol = cardStatus === 'online' ? C.border : cardStatus === 'degraded' ? C.degraded + '66' : C.offline + '66';

  return (
    <div
      style={{
        background: C.card,
        border: `1.5px solid ${borderCol}`,
        borderRadius: 10,
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {statusDot(cardStatus)}
        <span style={{ fontWeight: 700, fontSize: 15, color: C.ink, flex: 1 }}>
          {health.cluster_id}
        </span>
        <span style={{ fontSize: 12, color: C.muted }}>{healthPct}% activo</span>
      </div>

      {/* Sensor type pills */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {(['lilygo', 'ir', 'wifi', 'camera'] as const).map((t) => {
          const isOn =
            t === 'lilygo'
              ? health.lilygo_online
              : t === 'ir'
              ? health.ir_entry_online
              : t === 'wifi'
              ? health.wifi_online
              : health.camera_online;
          return (
            <span
              key={t}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '3px 8px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                background: isOn ? TYPE_COLOR[t] + '18' : '#00000009',
                color: isOn ? TYPE_COLOR[t] : C.offline,
                border: `1px solid ${isOn ? TYPE_COLOR[t] + '40' : '#0000001a'}`,
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: isOn ? TYPE_COLOR[t] : C.offline,
                  display: 'inline-block',
                }}
              />
              {TYPE_LABEL[t]}
            </span>
          );
        })}
      </div>

      {/* Issues */}
      {health.issues.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {health.issues.map((issue) => (
            <span
              key={issue}
              style={{
                fontSize: 11,
                color: C.critical,
                background: C.critical + '10',
                borderRadius: 4,
                padding: '2px 6px',
              }}
            >
              ⚠ {issue}
            </span>
          ))}
        </div>
      )}

      {/* Confidence bar */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, color: C.muted }}>Confiança de fusão</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: C.ink }}>
            {Math.round(health.confidence * 100)}%
          </span>
        </div>
        <div style={{ height: 5, borderRadius: 3, background: C.border, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.round(health.confidence * 100)}%`,
              background:
                health.confidence > 0.7
                  ? C.online
                  : health.confidence > 0.4
                  ? C.degraded
                  : C.critical,
              borderRadius: 3,
              transition: 'width 1s ease',
            }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Gateway card ─────────────────────────────────────────────────────────────
function GatewayCard({ gw }: { gw: GatewayStatus }) {
  return (
    <div
      style={{
        background: C.card,
        border: `1.5px solid ${C.border}`,
        borderRadius: 10,
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {statusDot(gw.status)}
        <span style={{ fontWeight: 700, fontSize: 15, color: C.ink, flex: 1 }}>
          {gw.gateway_id === 'gw_north' ? 'Gateway Norte' : 'Gateway Sul'}
        </span>
        <Badge label="LoRa" color={TYPE_COLOR.lorawan} />
      </div>
      <span style={{ fontSize: 13, color: C.muted }}>{gw.model}</span>
      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: C.muted }}>
        <span>Lat {gw.lat.toFixed(4)}</span>
        <span>Lon {gw.lon.toFixed(4)}</span>
      </div>
      <div style={{ fontSize: 12, color: C.ink }}>
        <span style={{ color: C.muted }}>Hubs ligados: </span>
        {gw.connected_hubs.length > 0
          ? gw.connected_hubs.map((h) => h.replace('lilygo_', 'WC-').toUpperCase()).join(', ')
          : 'Nenhum'}
      </div>
      <div style={{ fontSize: 12, color: C.muted }}>
        Perda de pacotes: {gw.packet_loss_pct.toFixed(1)}%
      </div>
    </div>
  );
}

// ─── Maintenance row ──────────────────────────────────────────────────────────
function Check({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        fontSize: 14,
        color: ok ? C.online : C.critical,
        fontWeight: 700,
      }}
    >
      {ok ? '✓' : '✗'}
    </span>
  );
}

function MaintenanceRow({ item }: { item: MaintenanceItem }) {
  const allOk =
    item.hub_installed &&
    item.ir_count_installed >= item.ir_count_expected &&
    item.wifi_ap_count_installed >= item.wifi_ap_count_expected &&
    item.camera_count_installed >= item.camera_count_expected;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '80px 1fr 1fr 1fr 1fr',
        alignItems: 'center',
        padding: '10px 12px',
        borderRadius: 8,
        background: allOk ? C.online + '08' : C.critical + '08',
        border: `1px solid ${allOk ? C.online + '30' : C.critical + '30'}`,
        gap: 8,
        fontSize: 13,
      }}
    >
      <span style={{ fontWeight: 700, color: C.ink }}>{item.cluster_id}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Check ok={item.hub_installed} /> Hub
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Check ok={item.ir_count_installed >= item.ir_count_expected} />
        <span style={{ color: C.muted }}>
          IR {item.ir_count_installed}/{item.ir_count_expected}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Check ok={item.wifi_ap_count_installed >= item.wifi_ap_count_expected} />
        <span style={{ color: C.muted }}>
          WiFi {item.wifi_ap_count_installed}/{item.wifi_ap_count_expected}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Check ok={item.camera_count_installed >= item.camera_count_expected} />
        <span style={{ color: C.muted }}>
          CAM {item.camera_count_installed}/{item.camera_count_expected}
        </span>
      </div>
    </div>
  );
}

// ─── Static coverage map (SVG schematic) ─────────────────────────────────────
function CoverageMap({ summary }: { summary: SensorSummary | null }) {
  // 8 clusters laid out in a rough festival-ground shape
  const positions = [
    { id: 'WC-01', x: 50, y: 10, label: 'Norte' },
    { id: 'WC-02', x: 80, y: 25, label: 'NE' },
    { id: 'WC-03', x: 50, y: 82, label: 'Sul' },
    { id: 'WC-04', x: 82, y: 55, label: 'Este' },
    { id: 'WC-05', x: 18, y: 55, label: 'Oeste' },
    { id: 'WC-06', x: 75, y: 80, label: 'SE' },
    { id: 'WC-07', x: 18, y: 25, label: 'NO' },
    { id: 'WC-08', x: 50, y: 50, label: 'Centro' },
  ];

  const isUnisex = (id: string) => summary?.unisex_clusters.includes(id) ?? false;

  return (
    <div
      style={{
        background: C.card,
        border: `1.5px solid ${C.border}`,
        borderRadius: 10,
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: 15, color: C.ink }}>Topologia de Cobertura</span>
        {summary && (
          <span style={{ fontSize: 12, color: C.muted }}>
            {summary.total} nós · {summary.clusters.length} clusters
          </span>
        )}
      </div>

      <svg
        viewBox="0 0 100 100"
        style={{ width: '100%', maxHeight: 280, display: 'block' }}
        aria-label="Mapa esquemático dos sensores"
      >
        {/* Venue boundary */}
        <rect
          x="5"
          y="5"
          width="90"
          height="90"
          rx="6"
          fill="#F0F4F0"
          stroke={C.border}
          strokeWidth="0.5"
        />

        {/* Gateway coverage areas */}
        <circle cx="50" cy="20" r="28" fill={TYPE_COLOR.lorawan + '10'} stroke={TYPE_COLOR.lorawan + '30'} strokeWidth="0.4" strokeDasharray="1.5 1" />
        <circle cx="50" cy="80" r="28" fill={TYPE_COLOR.lorawan + '10'} stroke={TYPE_COLOR.lorawan + '30'} strokeWidth="0.4" strokeDasharray="1.5 1" />

        {/* WiFi coverage circles per cluster */}
        {positions.map(({ id, x, y }) => (
          <circle
            key={`wifi-${id}`}
            cx={x}
            cy={y}
            r="6"
            fill={TYPE_COLOR.wifi + '18'}
            stroke={TYPE_COLOR.wifi + '40'}
            strokeWidth="0.4"
          />
        ))}

        {/* Cluster nodes */}
        {positions.map(({ id, x, y, label }) => {
          const unisex = isUnisex(id);
          return (
            <g key={id}>
              <circle
                cx={x}
                cy={y}
                r="4.5"
                fill={unisex ? '#7C3AED22' : C.accentBg}
                stroke={unisex ? '#7C3AED' : C.accent}
                strokeWidth="1"
              />
              <text
                x={x}
                y={y + 0.8}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="2.2"
                fontWeight="bold"
                fill={unisex ? '#7C3AED' : C.accent}
              >
                {id.replace('WC-', '')}
              </text>
              <text
                x={x}
                y={y + 7}
                textAnchor="middle"
                fontSize="2.2"
                fill={C.muted}
              >
                {label}
              </text>
            </g>
          );
        })}

        {/* Gateway markers */}
        {[
          { id: 'gw_north', cx: 50, cy: 8, label: 'GW N' },
          { id: 'gw_south', cx: 50, cy: 92, label: 'GW S' },
        ].map(({ id, cx, cy, label }) => (
          <g key={id}>
            <rect
              x={cx - 5}
              y={cy - 3}
              width={10}
              height={6}
              rx="1.5"
              fill={TYPE_COLOR.lorawan + '22'}
              stroke={TYPE_COLOR.lorawan}
              strokeWidth="0.6"
            />
            <text x={cx} y={cy + 0.8} textAnchor="middle" dominantBaseline="middle" fontSize="2" fontWeight="bold" fill={TYPE_COLOR.lorawan}>
              {label}
            </text>
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 11, color: C.muted }}>
        {[
          { col: C.accent, label: 'Cluster WC' },
          { col: '#7C3AED', label: 'Unissexo' },
          { col: TYPE_COLOR.wifi, label: 'WiFi AP' },
          { col: TYPE_COLOR.lorawan, label: 'Gateway LoRa' },
        ].map(({ col, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: col + '30', border: `1.5px solid ${col}`, display: 'inline-block' }} />
            {label}
          </div>
        ))}
      </div>

      {/* Fusion weights */}
      {summary && (
        <div
          style={{
            display: 'flex',
            gap: 8,
            padding: '8px 10px',
            background: C.accentBg,
            borderRadius: 6,
            fontSize: 12,
          }}
        >
          <span style={{ color: C.muted, flexShrink: 0 }}>Pesos de fusão:</span>
          {Object.entries(summary.fusion_weights).map(([k, v]) => (
            <span key={k} style={{ color: TYPE_COLOR[k] || C.ink, fontWeight: 600 }}>
              {TYPE_LABEL[k] ?? k} {Math.round(v * 100)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────
type Section = 'clusters' | 'gateways' | 'battery' | 'maintenance';

export default function SensorsPage() {
  const [health, setHealth] = useState<SensorHealth[]>([]);
  const [gateways, setGateways] = useState<GatewayStatus[]>([]);
  const [battery, setBattery] = useState<BatteryReport[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceItem[]>([]);
  const [summary, setSummary] = useState<SensorSummary | null>(null);
  const [activeSection, setActiveSection] = useState<Section>('clusters');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [isOffline, setIsOffline] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [h, gw, bat, maint, sum] = await Promise.all([
        api.sensors(),
        api.gateways(),
        api.sensorsBattery(),
        api.sensorsMaintenance(),
        api.sensorsSummary(),
      ]);
      setHealth(h);
      setGateways(gw);
      setBattery(bat);
      setMaintenance(maint);
      setSummary(sum);
      setIsOffline(false);
      setLastUpdate(new Date());
    } catch {
      setIsOffline(true);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 30_000);
    return () => clearInterval(id);
  }, []);

  const onlineClusters = health.filter((h) => h.issues.length === 0).length;
  const degradedClusters = health.filter((h) => h.issues.length > 0 && h.active_sources?.length > 0).length;
  const offlineClusters = health.filter((h) => h.active_sources?.length === 0).length;

  const NAV_TABS: { id: Section; label: string }[] = [
    { id: 'clusters', label: 'Clusters' },
    { id: 'gateways', label: 'Gateways' },
    { id: 'battery', label: 'Bateria' },
    { id: 'maintenance', label: 'Manutenção' },
  ];

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
        <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>
          Sensores
        </h1>
        <p style={{ margin: '4px 0 0', fontSize: 13, opacity: 0.8 }}>
          Rock in Rio Lisboa 2026 · Parque Tejo
        </p>

        {/* KPI strip */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 8,
            marginTop: 14,
          }}
        >
          {[
            { label: 'Total', value: summary?.total ?? 66, col: '#fff' },
            { label: 'Online', value: onlineClusters, col: C.online },
            { label: 'Degradado', value: degradedClusters, col: C.degraded },
            { label: 'Offline', value: offlineClusters, col: C.offline },
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
              <span style={{ fontSize: 20, fontWeight: 700, color: col }}>{value}</span>
              <span style={{ fontSize: 10, opacity: 0.8 }}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Offline banner */}
      {isOffline && (
        <div
          style={{
            background: C.degraded + '18',
            borderBottom: `1px solid ${C.degraded}40`,
            padding: '8px 16px',
            fontSize: 13,
            color: C.degraded,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span>⚠</span> Backend inacessível — a mostrar dados em cache
        </div>
      )}

      {/* Coverage map — always visible */}
      <div style={{ padding: '16px 16px 0' }}>
        <CoverageMap summary={summary} />
      </div>

      {/* Section tabs */}
      <div
        style={{
          display: 'flex',
          gap: 4,
          padding: '12px 16px 0',
          overflowX: 'auto',
          WebkitOverflowScrolling: 'touch' as React.CSSProperties['WebkitOverflowScrolling'],
        }}
      >
        {NAV_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveSection(tab.id)}
            style={{
              padding: '8px 16px',
              borderRadius: 20,
              border: `1.5px solid ${activeSection === tab.id ? C.accent : C.border}`,
              background: activeSection === tab.id ? C.accent : C.card,
              color: activeSection === tab.id ? '#fff' : C.ink,
              fontSize: 13,
              fontWeight: activeSection === tab.id ? 600 : 400,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              minHeight: 44,
              fontFamily: 'var(--font-ui)',
              transition: 'all 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Section content */}
      <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* ── Clusters ── */}
        {activeSection === 'clusters' && (
          <>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 12,
              }}
            >
              {health.length === 0
                ? Array.from({ length: 8 }, (_, i) => (
                    <div
                      key={i}
                      style={{
                        height: 160,
                        borderRadius: 10,
                        background: C.border,
                        animation: 'pulse 1.5s ease infinite',
                      }}
                    />
                  ))
                : health.map((h) => (
                    <ClusterCard key={h.cluster_id} health={h} summary={summary ?? { fusion_weights: { ir: 0.5, wifi: 0.3, camera: 0.2 }, total: 66, lilygo: 8, ir: 32, wifi: 16, camera: 8, lorawan: 2, clusters: [], unisex_clusters: [] }} />
                  ))}
            </div>

            {/* Fusion weights note */}
            {summary && (
              <div
                style={{
                  background: C.card,
                  border: `1px solid ${C.border}`,
                  borderRadius: 8,
                  padding: '10px 14px',
                  fontSize: 12,
                  color: C.muted,
                  lineHeight: 1.5,
                }}
              >
                <strong style={{ color: C.ink }}>Fusão de sensores</strong> — pesos:{' '}
                IR {Math.round(summary.fusion_weights.ir * 100)}% ·{' '}
                WiFi {Math.round(summary.fusion_weights.wifi * 100)}% ·{' '}
                Câmara {Math.round(summary.fusion_weights.camera * 100)}%.{' '}
                F=P/D é uma hipótese em teste — nunca afirmada como lei.
              </div>
            )}
          </>
        )}

        {/* ── Gateways ── */}
        {activeSection === 'gateways' && (
          <>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 12,
              }}
            >
              {gateways.length === 0
                ? [0, 1].map((i) => (
                    <div key={i} style={{ height: 140, borderRadius: 10, background: C.border }} />
                  ))
                : gateways.map((gw) => <GatewayCard key={gw.gateway_id} gw={gw} />)}
            </div>

            {/* Infrastructure summary */}
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
                fontSize: 13,
              }}
            >
              <span style={{ fontWeight: 700, color: C.ink }}>Infra-estrutura</span>
              {summary && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
                    gap: 8,
                  }}
                >
                  {Object.entries(summary).filter(([k]) => ['lilygo', 'ir', 'wifi', 'camera', 'lorawan'].includes(k)).map(([k, v]) => (
                    <div
                      key={k}
                      style={{
                        background: TYPE_COLOR[k] + '10',
                        border: `1px solid ${TYPE_COLOR[k]}30`,
                        borderRadius: 6,
                        padding: '6px 10px',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: 18, fontWeight: 700, color: TYPE_COLOR[k] }}>{v as number}</div>
                      <div style={{ fontSize: 11, color: C.muted }}>{TYPE_LABEL[k] ?? k}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ── Battery ── */}
        {activeSection === 'battery' && (
          <>
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 10,
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: 14,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: 15, color: C.ink }}>LilyGo TTGO Hubs</span>
                <span style={{ fontSize: 12, color: C.muted }}>10 Ah · 22 mA</span>
              </div>
              {battery.length === 0
                ? Array.from({ length: 8 }, (_, i) => (
                    <div key={i} style={{ height: 54, borderRadius: 6, background: C.border }} />
                  ))
                : battery.map((r) => <BatteryWidget key={r.hub_id} report={r} />)}
            </div>

            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 12,
                color: C.muted,
                lineHeight: 1.6,
              }}
            >
              Modelo: 10 000 mAh ÷ 22 mA = 454 h teórico · fator real 0,85 → ~16 dias.
              Alertas: &lt;3 dias = crítico · 3–7 dias = baixo.
            </div>
          </>
        )}

        {/* ── Maintenance ── */}
        {activeSection === 'maintenance' && (
          <>
            <div
              style={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 10,
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <span style={{ fontWeight: 700, fontSize: 15, color: C.ink }}>
                Lista de instalação / manutenção
              </span>

              {/* Column header */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '80px 1fr 1fr 1fr 1fr',
                  padding: '4px 12px',
                  fontSize: 11,
                  color: C.muted,
                  fontWeight: 600,
                  gap: 8,
                }}
              >
                <span>Cluster</span>
                <span>Hub</span>
                <span>IR</span>
                <span>WiFi</span>
                <span>Câmara</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {maintenance.length === 0
                  ? Array.from({ length: 8 }, (_, i) => (
                      <div key={i} style={{ height: 44, borderRadius: 8, background: C.border }} />
                    ))
                  : maintenance.map((item) => <MaintenanceRow key={item.cluster_id} item={item} />)}
              </div>
            </div>

            <div
              style={{
                background: C.accentBg,
                border: `1px solid ${C.accent}30`,
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 12,
                color: C.muted,
                lineHeight: 1.6,
              }}
            >
              <strong style={{ color: C.ink }}>RGPD por design</strong> — contagens agregadas
              apenas. Sem armazenamento de MAC, sem identificação individual, sem
              telemetria GPS recorrente.
            </div>
          </>
        )}
      </div>

      {/* Last update */}
      {lastUpdate && (
        <div
          style={{
            textAlign: 'center',
            padding: '8px 16px 16px',
            fontSize: 11,
            color: C.muted,
          }}
        >
          Actualizado: {lastUpdate.toLocaleTimeString('pt-PT')}
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.8; }
        }
      `}</style>
    </main>
  );
}
