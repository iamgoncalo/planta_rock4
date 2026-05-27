"use client";

import { useState } from "react";
import { STATUS_COLORS } from "./StatusDot";

interface CoverageFeature {
  properties: {
    sensor_id: string;
    sensor_type: string;
    cluster_id: string | null;
    radius_m: number;
    status: string;
    model: string;
  };
  geometry: {
    coordinates: [number, number];
  };
}

interface CoverageMapProps {
  features: CoverageFeature[];
}

// GPS bounding box for venue (Rock in Rio Lisboa approximate area)
const LAT_MIN = 38.775;
const LAT_MAX = 38.790;
const LON_MIN = -9.101;
const LON_MAX = -9.088;

const SVG_W = 460;
const SVG_H = 340;
const PAD = 30;

function gpsToSvg(lat: number, lon: number): [number, number] {
  const x = PAD + ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * (SVG_W - PAD * 2);
  const y = PAD + ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * (SVG_H - PAD * 2);
  return [x, y];
}

// Scale meters to SVG pixels (approx 1° lat ≈ 111km)
function mToSvg(m: number): number {
  const latRange = LAT_MAX - LAT_MIN;
  const pxPerDeg = (SVG_H - PAD * 2) / latRange;
  const pxPerKm = pxPerDeg / 111;
  return m * pxPerKm / 1000;
}

const CLUSTER_LABELS: Record<string, string> = {
  "WC-01": "WC-01\nNorte",
  "WC-02": "WC-02\nNordeste",
  "WC-03": "WC-03\nSul",
  "WC-04": "WC-04\nEste",
  "WC-05": "WC-05\nOeste U",
  "WC-06": "WC-06\nSudeste U",
  "WC-07": "WC-07\nNoroeste",
  "WC-08": "WC-08\nCentro",
};

type LayerKey = "wifi" | "lorawan" | "ir" | "camera";

export function CoverageMap({ features }: CoverageMapProps) {
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
    wifi: true,
    lorawan: true,
    ir: false,
    camera: false,
  });

  const toggleLayer = (key: LayerKey) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Group by cluster for labels
  const clusterPositions: Record<string, [number, number]> = {};
  const clusterStatuses: Record<string, string[]> = {};

  for (const f of features) {
    const { cluster_id, sensor_type, status } = f.properties;
    const [lon, lat] = f.geometry.coordinates;
    if (cluster_id && sensor_type === "wifi") {
      if (!clusterPositions[cluster_id]) {
        clusterPositions[cluster_id] = gpsToSvg(lat, lon);
      }
    }
    if (cluster_id) {
      if (!clusterStatuses[cluster_id]) clusterStatuses[cluster_id] = [];
      clusterStatuses[cluster_id].push(status);
    }
  }

  const getClusterStatus = (id: string): string => {
    const statuses = clusterStatuses[id] || [];
    if (statuses.every((s) => s === "online")) return "online";
    if (statuses.some((s) => s === "online")) return "degraded";
    if (statuses.every((s) => s === "unknown")) return "unknown";
    return "offline";
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Toggle buttons */}
      <div style={{ display: "flex", gap: 8, padding: "10px 0 8px 0", flexWrap: "wrap" }}>
        {(["wifi", "lorawan", "ir", "camera"] as LayerKey[]).map((key) => (
          <button
            key={key}
            onClick={() => toggleLayer(key)}
            style={{
              padding: "4px 12px",
              fontSize: 12,
              border: "1px solid #D1D5DB",
              borderRadius: 20,
              cursor: "pointer",
              fontWeight: 600,
              backgroundColor: layers[key] ? (
                key === "wifi" ? "#3B82F620" :
                key === "lorawan" ? "#F5A62320" :
                key === "ir" ? "#6FAF8220" :
                "#9CA3AF20"
              ) : "#fff",
              color: layers[key] ? (
                key === "wifi" ? "#3B82F6" :
                key === "lorawan" ? "#D48B3A" :
                key === "ir" ? "#6FAF82" :
                "#6B7280"
              ) : "#9CA3AF",
              borderColor: layers[key] ? "currentColor" : "#E5E7EB",
            }}
          >
            {key === "wifi" ? "APs" : key === "lorawan" ? "LoRa" : key === "ir" ? "IR" : "Câmaras"}
          </button>
        ))}
      </div>

      {/* SVG Map */}
      <div style={{ flex: 1, overflow: "hidden", borderRadius: 8, border: "1px solid #E5E7EB", backgroundColor: "#F9FAFB" }}>
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          style={{ display: "block" }}
        >
          {/* Background */}
          <rect x={PAD} y={PAD} width={SVG_W - PAD * 2} height={SVG_H - PAD * 2} fill="#EFF6FF" rx={4} />

          {/* Coverage circles */}
          {features.map((f, i) => {
            const { sensor_type, status, sensor_id } = f.properties;
            const [lon, lat] = f.geometry.coordinates;
            const r = mToSvg(f.properties.radius_m);
            const [cx, cy] = gpsToSvg(lat, lon);
            const color = STATUS_COLORS[status] ?? STATUS_COLORS.unknown;

            if (sensor_type === "wifi" && layers.wifi) {
              return (
                <circle
                  key={sensor_id}
                  cx={cx} cy={cy} r={Math.max(r, 8)}
                  fill={`${color}18`}
                  stroke="#3B82F6"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  opacity={0.8}
                />
              );
            }
            if (sensor_type === "lorawan" && layers.lorawan) {
              return (
                <circle
                  key={sensor_id}
                  cx={cx} cy={cy} r={Math.min(Math.max(r, 80), 150)}
                  fill="#F5A62312"
                  stroke="#D48B3A"
                  strokeWidth={2}
                  strokeDasharray="8 4"
                  opacity={0.7}
                />
              );
            }
            if (sensor_type === "ir" && layers.ir) {
              return (
                <circle
                  key={sensor_id}
                  cx={cx} cy={cy} r={5}
                  fill={color}
                  opacity={0.9}
                />
              );
            }
            if (sensor_type === "camera" && layers.camera) {
              return (
                <circle
                  key={sensor_id}
                  cx={cx} cy={cy} r={Math.max(r, 10)}
                  fill="#9CA3AF20"
                  stroke="#9CA3AF"
                  strokeWidth={1}
                  opacity={0.7}
                />
              );
            }
            return null;
          })}

          {/* Cluster nodes */}
          {Object.entries(clusterPositions).map(([id, [cx, cy]]) => {
            const status = getClusterStatus(id);
            const color = STATUS_COLORS[status] ?? STATUS_COLORS.unknown;
            const label = CLUSTER_LABELS[id] || id;
            const lines = label.split("\n");
            return (
              <g key={id}>
                <circle cx={cx} cy={cy} r={14} fill={color} opacity={0.9} />
                <circle cx={cx} cy={cy} r={14} fill="none" stroke="#fff" strokeWidth={2} />
                {lines.map((line, li) => (
                  <text
                    key={li}
                    x={cx}
                    y={cy + 26 + li * 13}
                    textAnchor="middle"
                    fontSize={li === 0 ? 11 : 9}
                    fontWeight={li === 0 ? 700 : 400}
                    fill="#374151"
                  >
                    {line}
                  </text>
                ))}
              </g>
            );
          })}

          {/* Gateway markers */}
          {features
            .filter((f) => f.properties.sensor_type === "lorawan")
            .map((f) => {
              const [lon, lat] = f.geometry.coordinates;
              const [cx, cy] = gpsToSvg(lat, lon);
              return (
                <g key={f.properties.sensor_id}>
                  <polygon
                    points={`${cx},${cy - 12} ${cx + 10},${cy + 8} ${cx - 10},${cy + 8}`}
                    fill="#D48B3A"
                    opacity={0.9}
                  />
                  <text x={cx} y={cy + 22} textAnchor="middle" fontSize={9} fill="#D48B3A" fontWeight={600}>
                    {f.properties.sensor_id === "gw_north" ? "GW-Norte" : "GW-Sul"}
                  </text>
                </g>
              );
            })}

          {/* Legend */}
          <g transform={`translate(${SVG_W - PAD - 90}, ${PAD + 8})`}>
            <rect x={-4} y={-4} width={94} height={72} fill="#fff" rx={4} opacity={0.85} />
            <circle cx={8} cy={8} r={6} fill="#3B82F640" stroke="#3B82F6" strokeWidth={1} strokeDasharray="3 2" />
            <text x={18} y={12} fontSize={9} fill="#374151">WiFi AP</text>
            <circle cx={8} cy={24} r={6} fill="#F5A62330" stroke="#D48B3A" strokeWidth={1} strokeDasharray="4 2" />
            <text x={18} y={28} fontSize={9} fill="#374151">LoRa GW</text>
            <circle cx={8} cy={40} r={5} fill="#6FAF82" />
            <text x={18} y={44} fontSize={9} fill="#374151">Online</text>
            <circle cx={8} cy={56} r={5} fill="#6B7280" />
            <text x={18} y={60} fontSize={9} fill="#374151">Offline/Desconhecido</text>
          </g>
        </svg>
      </div>
    </div>
  );
}
