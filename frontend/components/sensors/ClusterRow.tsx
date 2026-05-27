"use client";

import { useState } from "react";
import { StatusDot } from "./StatusDot";
import { BatteryBar } from "./BatteryBar";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SensorRecord {
  id: string;
  type: string;
  model: string;
  cluster_id: string | null;
  gpio_pin: number | null;
  health?: {
    status: string;
    last_seen: string | null;
    last_rssi_dbm: number | null;
    battery_pct: number | null;
    events_today: number;
  } | null;
}

interface BatteryInfo {
  hub_id: string;
  days_left: number;
  battery_pct: number | null;
}

interface ClusterRowProps {
  clusterId: string;
  sensors: SensorRecord[];
  battery?: BatteryInfo | null;
  onRefresh: () => void;
}

export function ClusterRow({ clusterId, sensors, battery, onRefresh }: ClusterRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [pingTarget, setPingTarget] = useState<string | null>(null);
  const [noteTarget, setNoteTarget] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");

  const total = sensors.length;
  const online = sensors.filter((s) => s.health?.status === "online").length;
  const degraded = sensors.filter((s) => s.health?.status === "degraded").length;
  const offline = sensors.filter((s) => s.health?.status === "offline" || s.health?.status === "unknown").length;

  const clusterStatus = online === total ? "online" : degraded > 0 ? "degraded" : offline === total ? "offline" : "degraded";

  const handlePing = async (sensorId: string) => {
    setPingTarget(sensorId);
    try {
      await fetch(`${API_URL}/api/v1/sensors/${sensorId}/ping`, { method: "POST" });
      onRefresh();
    } finally {
      setPingTarget(null);
    }
  };

  const handleNote = async (sensorId: string) => {
    if (!noteText.trim()) return;
    try {
      await fetch(`${API_URL}/api/v1/sensors/${sensorId}/maintenance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "note", notes: noteText, performed_by: "ops" }),
      });
      setNoteTarget(null);
      setNoteText("");
    } catch (e) {
      console.error(e);
    }
  };

  const isUnisex = clusterId === "WC-05" || clusterId === "WC-06";

  return (
    <div
      style={{
        border: "1px solid #E5E7EB",
        borderRadius: 10,
        overflow: "hidden",
        marginBottom: 10,
      }}
    >
      {/* Cluster Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          backgroundColor: "#F9FAFB",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <StatusDot status={clusterStatus} size={12} />
          <span style={{ fontWeight: 700, fontSize: 16 }}>
            {clusterId}
            {isUnisex && (
              <span style={{ fontSize: 12, fontWeight: 500, color: "#6B7280", marginLeft: 8 }}>UNISSEX</span>
            )}
          </span>
          <span style={{ fontSize: 13, color: "#6B7280" }}>
            {online}/{total} online
            {degraded > 0 && <span style={{ color: "#D48B3A", marginLeft: 6 }}>{degraded} degradado</span>}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {battery && (
            <div style={{ width: 120 }}>
              <BatteryBar pct={battery.battery_pct} daysLeft={battery.days_left} />
            </div>
          )}
          <span style={{ fontSize: 14, color: "#9CA3AF", transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.2s" }}>
            ▼
          </span>
        </div>
      </button>

      {/* Expanded sensor list */}
      {expanded && (
        <div style={{ backgroundColor: "#fff" }}>
          {sensors.map((s) => {
            const status = s.health?.status ?? "unknown";
            const lastSeen = s.health?.last_seen
              ? new Date(s.health.last_seen).toLocaleTimeString("pt-PT")
              : "nunca";
            const rssi = s.health?.last_rssi_dbm ?? null;

            return (
              <div
                key={s.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "10px 16px",
                  borderTop: "1px solid #F3F4F6",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <StatusDot status={status} size={9} />
                <span style={{ fontSize: 13, fontFamily: "monospace", minWidth: 220 }}>{s.id}</span>
                <span style={{ fontSize: 12, color: "#6B7280", minWidth: 80 }}>{s.model}</span>
                {s.gpio_pin !== null && (
                  <span style={{ fontSize: 11, color: "#9CA3AF" }}>GPIO {s.gpio_pin}</span>
                )}
                <span style={{ fontSize: 12, color: "#9CA3AF", marginLeft: "auto" }}>
                  {lastSeen}
                </span>
                {rssi !== null && (
                  <span style={{ fontSize: 11, color: "#9CA3AF" }}>{rssi} dBm</span>
                )}

                {/* Actions */}
                <div style={{ display: "flex", gap: 6 }}>
                  <button
                    onClick={() => handlePing(s.id)}
                    disabled={pingTarget === s.id}
                    style={{
                      padding: "3px 10px",
                      fontSize: 11,
                      border: "1px solid #D1D5DB",
                      borderRadius: 5,
                      cursor: "pointer",
                      backgroundColor: "#fff",
                    }}
                  >
                    {pingTarget === s.id ? "..." : "Ping"}
                  </button>
                  <button
                    onClick={() => setNoteTarget(noteTarget === s.id ? null : s.id)}
                    style={{
                      padding: "3px 10px",
                      fontSize: 11,
                      border: "1px solid #D1D5DB",
                      borderRadius: 5,
                      cursor: "pointer",
                      backgroundColor: "#fff",
                    }}
                  >
                    Nota
                  </button>
                  <a
                    href={`/sensors/${s.id}`}
                    style={{
                      padding: "3px 10px",
                      fontSize: 11,
                      border: "1px solid #D1D5DB",
                      borderRadius: 5,
                      textDecoration: "none",
                      color: "#374151",
                      backgroundColor: "#fff",
                    }}
                  >
                    Ver
                  </a>
                </div>

                {/* Inline note form */}
                {noteTarget === s.id && (
                  <div
                    style={{
                      width: "100%",
                      display: "flex",
                      gap: 8,
                      marginTop: 6,
                      paddingLeft: 22,
                    }}
                  >
                    <input
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") handleNote(s.id); }}
                      placeholder="Escreva uma nota..."
                      style={{
                        flex: 1,
                        padding: "5px 10px",
                        border: "1px solid #D1D5DB",
                        borderRadius: 5,
                        fontSize: 13,
                      }}
                      autoFocus
                    />
                    <button
                      onClick={() => handleNote(s.id)}
                      style={{
                        padding: "5px 12px",
                        backgroundColor: "#1F2937",
                        color: "#fff",
                        border: "none",
                        borderRadius: 5,
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                    >
                      Guardar
                    </button>
                    <button
                      onClick={() => { setNoteTarget(null); setNoteText(""); }}
                      style={{
                        padding: "5px 12px",
                        border: "1px solid #D1D5DB",
                        borderRadius: 5,
                        fontSize: 12,
                        cursor: "pointer",
                        backgroundColor: "#fff",
                      }}
                    >
                      Cancelar
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
