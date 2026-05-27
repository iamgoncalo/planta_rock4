"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { ClusterRow } from "../../components/sensors/ClusterRow";
import { SensorTerminal } from "../../components/sensors/SensorTerminal";
import { CoverageMap } from "../../components/sensors/CoverageMap";
import { AddSensorModal } from "../../components/sensors/AddSensorModal";
import { StatusDot } from "../../components/sensors/StatusDot";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CLUSTERS = ["WC-01", "WC-02", "WC-03", "WC-04", "WC-05", "WC-06", "WC-07", "WC-08"];

interface SensorRecord {
  id: string;
  type: string;
  model: string;
  cluster_id: string | null;
  gpio_pin: number | null;
  is_active: boolean;
  health?: {
    status: string;
    last_seen: string | null;
    last_rssi_dbm: number | null;
    battery_pct: number | null;
    events_today: number;
    updated_at: string | null;
  } | null;
}

interface BatteryInfo {
  hub_id: string;
  cluster_id: string;
  days_left: number;
  battery_pct: number | null;
  status: string;
}

interface CoverageFeature {
  type: string;
  geometry: { coordinates: [number, number] };
  properties: {
    sensor_id: string;
    sensor_type: string;
    cluster_id: string | null;
    radius_m: number;
    status: string;
    model: string;
  };
}

interface InstallCheck {
  cluster_id: string;
  done: boolean;
  checked_by: string;
  checked_at: string | null;
}

export default function SensorsPage() {
  const [sensors, setSensors] = useState<SensorRecord[]>([]);
  const [batteries, setBatteries] = useState<BatteryInfo[]>([]);
  const [coverage, setCoverage] = useState<CoverageFeature[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [checks, setChecks] = useState<Record<string, InstallCheck>>({});
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [sensRes, batRes, covRes, sumRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/sensors`).then((r) => r.json()),
        fetch(`${API_URL}/api/v1/sensors/battery/status`).then((r) => r.json()),
        fetch(`${API_URL}/api/v1/sensors/coverage/geojson`).then((r) => r.json()),
        fetch(`${API_URL}/api/v1/sensors/summary`).then((r) => r.json()),
      ]);
      setSensors(Array.isArray(sensRes) ? sensRes : []);
      setBatteries(Array.isArray(batRes) ? batRes : []);
      setCoverage(Array.isArray(covRes?.features) ? covRes.features : []);
      setSummary(sumRes);
      setLastUpdated(new Date());
    } catch (e) {
      console.error("Failed to fetch sensors:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 30_000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  // Group sensors by cluster
  const byCluster = useMemo(() => {
    const map: Record<string, SensorRecord[]> = {};
    for (const cluster of CLUSTERS) map[cluster] = [];
    for (const s of sensors) {
      if (s.cluster_id && CLUSTERS.includes(s.cluster_id)) {
        map[s.cluster_id].push(s);
      }
    }
    return map;
  }, [sensors]);

  // Gateways and backbone APs (no cluster)
  const gateways = useMemo(
    () => sensors.filter((s) => s.type === "lorawan" || s.cluster_id === null),
    [sensors]
  );

  // KPI stats
  const kpis = useMemo(() => {
    const total = sensors.length;
    const online = sensors.filter((s) => s.health?.status === "online").length;
    const degraded = sensors.filter((s) => s.health?.status === "degraded").length;
    const offline = sensors.filter((s) => s.health?.status === "offline").length;
    const unknown = sensors.filter((s) => !s.health || s.health.status === "unknown").length;
    const avgBat =
      batteries.length > 0
        ? Math.round(batteries.reduce((a, b) => a + (b.battery_pct ?? 0), 0) / batteries.length)
        : null;
    return { total, online, degraded, offline, unknown, avgBat };
  }, [sensors, batteries]);

  const batteryMap = useMemo(() => {
    const m: Record<string, BatteryInfo> = {};
    for (const b of batteries) m[b.cluster_id] = b;
    return m;
  }, [batteries]);

  const isSimulated = useMemo(
    () => sensors.some((s) => !s.health || s.health.status === "unknown"),
    [sensors]
  );

  const handleInstallCheck = async (cluster: string) => {
    const now = new Date().toISOString();
    setChecks((prev) => ({
      ...prev,
      [cluster]: { cluster_id: cluster, done: !prev[cluster]?.done, checked_by: "ops", checked_at: now },
    }));
    if (!checks[cluster]?.done) {
      // Log maintenance for all sensors in this cluster
      const clusterSensors = byCluster[cluster] || [];
      for (const s of clusterSensors.slice(0, 1)) {
        await fetch(`${API_URL}/api/v1/sensors/${s.id}/maintenance`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "check", result: "verified", notes: `Verificação de instalação do cluster ${cluster}`, performed_by: "ops" }),
        }).catch(() => {});
      }
    }
  };

  const handleExportCSV = () => {
    const headers = ["id", "type", "model", "cluster_id", "status", "last_seen", "firmware"];
    const rows = sensors.map((s) => [
      s.id,
      s.type,
      s.model,
      s.cluster_id || "",
      s.health?.status || "unknown",
      s.health?.last_seen || "",
      "",
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sensors_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", fontSize: 18, color: "#6B7280" }}>
        A carregar sensores...
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#F9FAFB", color: "#1F2937" }}>
      {/* Topbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
          padding: "18px 24px",
          backgroundColor: "#fff",
          borderBottom: "1px solid #E5E7EB",
          position: "sticky",
          top: 0,
          zIndex: 100,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, letterSpacing: -0.5 }}>
          Sensores
        </h1>

        {isSimulated && (
          <span
            style={{
              padding: "3px 10px",
              backgroundColor: "#FEF3C7",
              color: "#92400E",
              border: "1px solid #FCD34D",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: 0.5,
            }}
          >
            SIMULADO
          </span>
        )}

        {/* KPI chips */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginLeft: 8 }}>
          <KpiChip label="Total" value={kpis.total} color="#374151" />
          <KpiChip label="Online" value={kpis.online} color="#6FAF82" />
          {kpis.degraded > 0 && <KpiChip label="Degradado" value={kpis.degraded} color="#D48B3A" />}
          {kpis.offline > 0 && <KpiChip label="Offline" value={kpis.offline} color="#6B7280" />}
          {kpis.unknown > 0 && <KpiChip label="Desconhecido" value={kpis.unknown} color="#9CA3AF" />}
          {kpis.avgBat !== null && <KpiChip label="Bat média" value={`${kpis.avgBat}%`} color="#3B82F6" />}
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
          {lastUpdated && (
            <span style={{ fontSize: 12, color: "#9CA3AF", alignSelf: "center" }}>
              Actualizado: {lastUpdated.toLocaleTimeString("pt-PT")}
            </span>
          )}
          <button
            onClick={() => setShowAddModal(true)}
            style={{
              padding: "8px 16px",
              backgroundColor: "#1F2937",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            + Adicionar Sensor
          </button>
          <button
            onClick={handleExportCSV}
            style={{
              padding: "8px 16px",
              backgroundColor: "#fff",
              color: "#374151",
              border: "1px solid #D1D5DB",
              borderRadius: 8,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Main layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "60fr 40fr",
          gap: 0,
          height: "calc(100vh - 73px)",
          overflow: "hidden",
        }}
      >
        {/* LEFT PANEL */}
        <div style={{ overflowY: "auto", padding: 24, borderRight: "1px solid #E5E7EB" }}>
          {/* Section 1: Clusters */}
          <SectionHeader title="Clusters WC" count={CLUSTERS.length} />
          {CLUSTERS.map((cluster) => (
            <ClusterRow
              key={cluster}
              clusterId={cluster}
              sensors={byCluster[cluster] || []}
              battery={batteryMap[cluster] || null}
              onRefresh={fetchAll}
            />
          ))}

          {/* Section 2: Gateways */}
          <SectionHeader title="Gateways & Backbone" count={gateways.length} style={{ marginTop: 28 }} />
          {gateways.length === 0 ? (
            <div style={{ color: "#9CA3AF", fontSize: 14, padding: "12px 0" }}>Sem gateways registados.</div>
          ) : (
            <div style={{ border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
              {gateways.map((gw, i) => (
                <div
                  key={gw.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "12px 16px",
                    gap: 12,
                    borderTop: i > 0 ? "1px solid #F3F4F6" : "none",
                    backgroundColor: "#fff",
                  }}
                >
                  <StatusDot status={gw.health?.status ?? "unknown"} size={10} />
                  <span style={{ fontFamily: "monospace", fontSize: 13, minWidth: 200 }}>{gw.id}</span>
                  <span style={{ fontSize: 12, color: "#6B7280", minWidth: 80 }}>{gw.type}</span>
                  <span style={{ fontSize: 12, color: "#9CA3AF" }}>{gw.model}</span>
                  <span style={{ marginLeft: "auto", fontSize: 12, color: "#9CA3AF" }}>
                    {gw.health?.last_seen
                      ? new Date(gw.health.last_seen).toLocaleTimeString("pt-PT")
                      : "nunca"}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Section 3: Installation checklist */}
          <SectionHeader title="Verificação de Instalação" count={CLUSTERS.length} style={{ marginTop: 28 }} />
          <div style={{ border: "1px solid #E5E7EB", borderRadius: 10, overflow: "hidden" }}>
            {CLUSTERS.map((cluster, i) => {
              const check = checks[cluster];
              const clusterSensors = byCluster[cluster] || [];
              const total = clusterSensors.length;
              const installed = clusterSensors.filter((s) => s.health && s.health.status !== "unknown").length;
              return (
                <div
                  key={cluster}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "11px 16px",
                    gap: 14,
                    borderTop: i > 0 ? "1px solid #F3F4F6" : "none",
                    backgroundColor: check?.done ? "#F0FDF4" : "#fff",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={!!check?.done}
                    onChange={() => handleInstallCheck(cluster)}
                    style={{ width: 18, height: 18, cursor: "pointer" }}
                  />
                  <span style={{ fontWeight: 600, minWidth: 60 }}>{cluster}</span>
                  {cluster === "WC-05" || cluster === "WC-06" ? (
                    <span style={{ fontSize: 12, color: "#6B7280" }}>UNISSEX</span>
                  ) : null}
                  <span style={{ fontSize: 13, color: "#6B7280" }}>
                    {installed}/{total} sensores activos
                  </span>
                  {check?.done && (
                    <span style={{ fontSize: 12, color: "#6FAF82", marginLeft: "auto", fontWeight: 600 }}>
                      Verificado
                    </span>
                  )}
                  {!check?.done && installed < total && (
                    <span style={{ fontSize: 12, color: "#D48B3A", marginLeft: "auto" }}>
                      Pendente
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Section 4: Terminal (top half) */}
          <div style={{ flex: "0 0 50%", padding: "24px 24px 12px 24px", display: "flex", flexDirection: "column" }}>
            <SectionHeader title="Terminal" />
            <div style={{ flex: 1, minHeight: 0 }}>
              <SensorTerminal />
            </div>
          </div>

          {/* Section 5: Coverage map (bottom half) */}
          <div style={{ flex: "0 0 50%", padding: "12px 24px 24px 24px", display: "flex", flexDirection: "column", borderTop: "1px solid #E5E7EB" }}>
            <SectionHeader title="Mapa de Cobertura" />
            <div style={{ flex: 1, minHeight: 0 }}>
              <CoverageMap features={coverage} />
            </div>
          </div>
        </div>
      </div>

      {showAddModal && (
        <AddSensorModal onClose={() => setShowAddModal(false)} onAdded={fetchAll} />
      )}
    </div>
  );
}

function KpiChip({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 12px",
        backgroundColor: `${color}15`,
        border: `1px solid ${color}40`,
        borderRadius: 20,
        fontSize: 13,
      }}
    >
      <span style={{ fontWeight: 700, color }}>{value}</span>
      <span style={{ color: "#6B7280" }}>{label}</span>
    </div>
  );
}

function SectionHeader({ title, count, style }: { title: string; count?: number; style?: React.CSSProperties }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 12, ...style }}>
      <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>{title}</h2>
      {count !== undefined && (
        <span style={{ fontSize: 13, color: "#9CA3AF" }}>{count}</span>
      )}
    </div>
  );
}
