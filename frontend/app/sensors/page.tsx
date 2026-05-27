"use client";

import {
  useState, useEffect, useCallback, useMemo, useRef,
  forwardRef, useImperativeHandle,
} from "react";
import dynamic from "next/dynamic";
import { ClusterRow } from "../../components/sensors/ClusterRow";
import { CoverageMap } from "../../components/sensors/CoverageMap";
import { AddSensorModal } from "../../components/sensors/AddSensorModal";
import { StatusDot } from "../../components/sensors/StatusDot";
import { SensorTerminal } from "../../components/sensors/SensorTerminal";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL  = API_URL.replace(/^http/, "ws");
const CLUSTERS = ["WC-01","WC-02","WC-03","WC-04","WC-05","WC-06","WC-07","WC-08"];

// ── Types ──────────────────────────────────────────────────────────────────

interface SensorRecord {
  id: string; type: string; model: string;
  cluster_id: string | null; gpio_pin: number | null; is_active: boolean;
  health?: { status: string; last_seen: string | null; last_rssi_dbm: number | null;
             battery_pct: number | null; events_today: number; updated_at: string | null; } | null;
}
interface BatteryInfo { hub_id: string; cluster_id: string; days_left: number; battery_pct: number | null; status: string; }
interface CoverageFeature {
  type: string; geometry: { coordinates: [number, number] };
  properties: { sensor_id: string; sensor_type: string; cluster_id: string | null;
                radius_m: number; status: string; model: string; };
}
interface InstallCheck { cluster_id: string; done: boolean; checked_by: string; checked_at: string | null; }
interface DeviceStatus {
  cluster_id: string; status: "online"|"degraded"|"offline"|"unknown";
  age_s: number|null; firmware_ver?: string; ip?: string; rssi_dbm?: number;
  uptime_s?: number; ocupacao_ir?: number; entradas_total?: number;
  saidas_total?: number; wifi_factor?: number; ir_cal?: number; heap_free?: number;
}

// ── Lazy-loaded MQTT terminal (xterm.js — no SSR) ─────────────────────────

const MQTTTerminal = dynamic(() => import("../sensors/MQTTTerminal"), { ssr: false });

// ── Sub-components ─────────────────────────────────────────────────────────

function KpiChip({ label, value, color }: { label: string; value: number|string; color: string }) {
  return (
    <div style={{ display:"inline-flex", alignItems:"center", gap:6, padding:"4px 12px",
      backgroundColor:`${color}15`, border:`1px solid ${color}40`, borderRadius:20, fontSize:13 }}>
      <span style={{ fontWeight:700, color }}>{value}</span>
      <span style={{ color:"#6B7280" }}>{label}</span>
    </div>
  );
}

function SectionHeader({ title, count, style }: { title: string; count?: number; style?: React.CSSProperties }) {
  return (
    <div style={{ display:"flex", alignItems:"baseline", gap:10, marginBottom:12, ...style }}>
      <h2 style={{ margin:0, fontSize:17, fontWeight:700 }}>{title}</h2>
      {count !== undefined && <span style={{ fontSize:13, color:"#9CA3AF" }}>{count}</span>}
    </div>
  );
}

const ST: Record<string,string> = { online:"#4A7C59", degraded:"#BA7517", offline:"#888", unknown:"#aaa" };
const DOT: Record<string,string> = { online:"#6FAF82", degraded:"#D4A020", offline:"#999", unknown:"#ccc" };

function DeviceCard({ d, onCmd }: { d: DeviceStatus; onCmd: (cmd: string) => void }) {
  const [exp, setExp] = useState(false);
  const color = ST[d.status] ?? "#888";
  const dot   = DOT[d.status] ?? "#ccc";
  const age   = d.age_s != null ? `há ${d.age_s}s` : "nunca visto";

  return (
    <div style={{ border:`1px solid #e0e8e0`, borderRadius:8, padding:"10px 12px",
      background:"#fafcfa", marginBottom:6 }}>
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:5 }}>
        <span style={{ width:9, height:9, borderRadius:"50%", background:dot, flexShrink:0,
          boxShadow:d.status==="online"?`0 0 5px ${dot}`:"none" }} />
        <strong style={{ fontSize:14, color:"#1B3A21" }}>{d.cluster_id}</strong>
        <span style={{ marginLeft:"auto", fontSize:10, fontWeight:700, color,
          textTransform:"uppercase", letterSpacing:".04em" }}>{d.status}</span>
      </div>
      <div style={{ fontSize:11, color:"#556655", lineHeight:1.75 }}>
        <div>IP: <b>{d.ip ?? "—"}</b> &nbsp;·&nbsp; FW: <b>{d.firmware_ver ?? "—"}</b></div>
        <div>RSSI: <b>{d.rssi_dbm != null ? `${d.rssi_dbm} dBm` : "—"}</b> &nbsp;·&nbsp; {age}</div>
      </div>
      <div style={{ display:"flex", gap:4, marginTop:7, flexWrap:"wrap" }}>
        {["ping","serial on","diagnostics","reset"].map(cmd => (
          <button key={cmd} onClick={() => onCmd(`${cmd} ${d.cluster_id}`)}
            style={{ fontSize:10, padding:"2px 6px", borderRadius:4, border:"1px solid #c8dcc8",
              background:"#fff", cursor:"pointer", color:"#1B3A21", fontFamily:"monospace" }}>
            {cmd}
          </button>
        ))}
        <button onClick={() => setExp(x => !x)}
          style={{ fontSize:10, padding:"2px 6px", borderRadius:4, border:"1px solid #c8dcc8",
            background:"#fff", cursor:"pointer", color:"#1B3A21", marginLeft:"auto" }}>
          {exp ? "▲" : "▼"}
        </button>
      </div>
      {exp && (
        <div style={{ marginTop:8, padding:"7px 9px", background:"#eaf2ea", borderRadius:6,
          fontSize:11, fontFamily:"monospace", color:"#2a4a2a", lineHeight:1.8 }}>
          <div>Ocupação IR: {d.ocupacao_ir ?? "—"} pax</div>
          <div>Entradas: {d.entradas_total ?? "—"} · Saídas: {d.saidas_total ?? "—"}</div>
          <div>wifi_factor: {d.wifi_factor ?? "—"} · ir_cal: {d.ir_cal ?? "—"}</div>
          <div>Heap: {d.heap_free != null ? `${Math.round(d.heap_free/1024)}kB` : "—"}</div>
        </div>
      )}
    </div>
  );
}

function FirmwareTable({ devices, onCmd }: { devices: DeviceStatus[]; onCmd: (cmd: string) => void }) {
  const LATEST = "6.0.0";
  return (
    <div style={{ marginTop:20, border:"1px solid #d8e8d8", borderRadius:10, overflow:"hidden" }}>
      <div style={{ background:"#1B3A21", color:"#fff", padding:"8px 14px",
        fontWeight:700, fontSize:12, display:"flex", alignItems:"center", gap:10 }}>
        Firmware Manager — latest v{LATEST}
        <button onClick={() => CLUSTERS.forEach(c => onCmd(`flash ${c}`))}
          style={{ fontSize:10, padding:"2px 10px", borderRadius:4, border:"none",
            background:"#4A7C59", color:"#fff", cursor:"pointer" }}>
          Flash All
        </button>
      </div>
      <table style={{ width:"100%", borderCollapse:"collapse", fontSize:11 }}>
        <thead>
          <tr style={{ background:"#f2f8f2", borderBottom:"1px solid #d8e8d8" }}>
            {["Device","FW actual","Latest","Estado",""].map(h => (
              <th key={h} style={{ padding:"5px 10px", textAlign:"left",
                fontWeight:600, color:"#2a4a2a" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {devices.map((d,i) => {
            const ok = d.firmware_ver === LATEST;
            return (
              <tr key={d.cluster_id} style={{ borderBottom:"1px solid #eef4ee",
                background:i%2?"#fafcfa":"#fff" }}>
                <td style={{ padding:"5px 10px", fontWeight:600 }}>{d.cluster_id}</td>
                <td style={{ padding:"5px 10px", fontFamily:"monospace",
                  color:ok?"#4A7C59":"#C25A1A" }}>{d.firmware_ver ?? "?"}</td>
                <td style={{ padding:"5px 10px", fontFamily:"monospace", color:"#4A7C59" }}>{LATEST}</td>
                <td style={{ padding:"5px 10px" }}>
                  <span style={{ padding:"2px 7px", borderRadius:10, fontSize:10,
                    background:ok?"#e0f2e8":"#fff3e0", color:ok?"#2a6a2a":"#C25A1A", fontWeight:600 }}>
                    {ok?"ok":"desactualizado"}
                  </span>
                </td>
                <td style={{ padding:"5px 10px" }}>
                  <button onClick={() => onCmd(`flash ${d.cluster_id}`)} disabled={ok}
                    style={{ fontSize:10, padding:"2px 7px", borderRadius:4,
                      border:`1px solid ${ok?"#e0e0e0":"#4A7C59"}`,
                      background:ok?"#f5f5f5":"#4A7C59", color:ok?"#bbb":"#fff",
                      cursor:ok?"not-allowed":"pointer" }}>
                    Flash
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function SensorsPage() {
  // DB sensor data
  const [sensors,  setSensors]  = useState<SensorRecord[]>([]);
  const [batteries,setBatteries]= useState<BatteryInfo[]>([]);
  const [coverage, setCoverage] = useState<CoverageFeature[]>([]);
  const [summary,  setSummary]  = useState<Record<string,unknown>|null>(null);
  const [loading,  setLoading]  = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [checks,   setChecks]   = useState<Record<string,InstallCheck>>({});
  const [lastUpdated, setLastUpdated] = useState<Date|null>(null);

  // Live device (MQTT) data
  const [devices,  setDevices]  = useState<DeviceStatus[]>(
    CLUSTERS.map(id => ({ cluster_id:id, status:"unknown", age_s:null }))
  );
  const [rightTab, setRightTab] = useState<"mqtt"|"db"|"coverage">("mqtt");

  // ref to send commands from device card buttons into the MQTT terminal
  const mqttTermRef = useRef<{ sendCmd: (s: string) => void } | null>(null);
  const sendMqttCmd = useCallback((cmd: string) => {
    mqttTermRef.current?.sendCmd(cmd);
    if (rightTab !== "mqtt") setRightTab("mqtt");
  }, [rightTab]);

  // Fetch DB sensors every 30s
  const fetchAll = useCallback(async () => {
    try {
      const [sensRes, batRes, covRes, sumRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/sensors`).then(r => r.json()),
        fetch(`${API_URL}/api/v1/sensors/battery/status`).then(r => r.json()),
        fetch(`${API_URL}/api/v1/sensors/coverage/geojson`).then(r => r.json()),
        fetch(`${API_URL}/api/v1/sensors/summary`).then(r => r.json()),
      ]);
      setSensors(Array.isArray(sensRes) ? sensRes : []);
      setBatteries(Array.isArray(batRes) ? batRes : []);
      setCoverage(Array.isArray(covRes?.features) ? covRes.features : []);
      setSummary(sumRes);
      setLastUpdated(new Date());
    } catch { /* backend offline */ } finally { setLoading(false); }
  }, []);

  // Fetch MQTT device statuses every 10s
  const fetchDevices = useCallback(async () => {
    try {
      const r  = await fetch(`${API_URL}/api/v1/devices`);
      const d  = await r.json();
      if (Array.isArray(d.devices)) setDevices(d.devices);
    } catch { /* mqtt bridge not up */ }
  }, []);

  useEffect(() => {
    fetchAll();
    fetchDevices();
    const t1 = setInterval(fetchAll,    30_000);
    const t2 = setInterval(fetchDevices, 10_000);
    return () => { clearInterval(t1); clearInterval(t2); };
  }, [fetchAll, fetchDevices]);

  // Derived values
  const byCluster = useMemo(() => {
    const map: Record<string,SensorRecord[]> = {};
    for (const c of CLUSTERS) map[c] = [];
    for (const s of sensors)
      if (s.cluster_id && CLUSTERS.includes(s.cluster_id)) map[s.cluster_id].push(s);
    return map;
  }, [sensors]);

  const gateways = useMemo(
    () => sensors.filter(s => s.type === "lorawan" || s.cluster_id === null),
    [sensors]
  );

  const kpis = useMemo(() => {
    const total    = sensors.length;
    const online   = sensors.filter(s => s.health?.status === "online").length;
    const degraded = sensors.filter(s => s.health?.status === "degraded").length;
    const offline  = sensors.filter(s => s.health?.status === "offline").length;
    const unknown  = sensors.filter(s => !s.health || s.health.status === "unknown").length;
    const avgBat   = batteries.length
      ? Math.round(batteries.reduce((a,b) => a+(b.battery_pct??0),0)/batteries.length)
      : null;
    return { total, online, degraded, offline, unknown, avgBat };
  }, [sensors, batteries]);

  const devicesOnline = useMemo(
    () => devices.filter(d => d.status === "online").length, [devices]
  );

  const batteryMap = useMemo(() => {
    const m: Record<string,BatteryInfo> = {};
    for (const b of batteries) m[b.cluster_id] = b;
    return m;
  }, [batteries]);

  const isSimulated = useMemo(
    () => sensors.some(s => !s.health || s.health.status === "unknown"),
    [sensors]
  );

  const handleInstallCheck = async (cluster: string) => {
    const now = new Date().toISOString();
    setChecks(prev => ({
      ...prev,
      [cluster]: { cluster_id:cluster, done:!prev[cluster]?.done, checked_by:"ops", checked_at:now },
    }));
    if (!checks[cluster]?.done) {
      const first = (byCluster[cluster]||[])[0];
      if (first) {
        await fetch(`${API_URL}/api/v1/sensors/${first.id}/maintenance`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ action:"check", result:"verified",
            notes:`Verificação de instalação ${cluster}`, performed_by:"ops" }),
        }).catch(() => {});
      }
    }
  };

  const handleExportCSV = () => {
    const headers = ["id","type","model","cluster_id","status","last_seen"];
    const rows = sensors.map(s => [
      s.id,s.type,s.model,s.cluster_id||"",
      s.health?.status||"unknown",s.health?.last_seen||"",
    ]);
    const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csv],{type:"text/csv"});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href=url; a.download=`sensors_${new Date().toISOString().slice(0,10)}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return (
    <div style={{ display:"flex",alignItems:"center",justifyContent:"center",
      height:"100vh",fontSize:18,color:"#6B7280" }}>
      A carregar sensores...
    </div>
  );

  const TAB_STYLE = (active: boolean) => ({
    padding:"7px 16px", fontSize:13, fontWeight:active?700:500,
    border:"none", borderBottom:active?"2px solid #1B3A21":"2px solid transparent",
    background:"none", cursor:"pointer", color:active?"#1B3A21":"#6B7280",
  });

  return (
    <div style={{ minHeight:"100vh", backgroundColor:"#F9FAFB", color:"#1F2937" }}>

      {/* ── TOPBAR ──────────────────────────────────────────────────────── */}
      <div style={{ display:"flex", alignItems:"center", flexWrap:"wrap", gap:14,
        padding:"16px 24px", backgroundColor:"#fff", borderBottom:"1px solid #E5E7EB",
        position:"sticky", top:0, zIndex:100 }}>
        <img
          src="/planta-logo.svg"
          alt="Planta"
          width={90}
          height={70}
          style={{ display: 'block', filter: 'drop-shadow(0 1px 2px rgba(27,58,33,0.12))' }}
        />
        <div style={{ width: 1, height: 36, background: '#E5E7EB', flexShrink: 0 }} />
        <h1 style={{ margin:0, fontSize:24, fontWeight:800, letterSpacing:-0.5 }}>
          Sensores
        </h1>

        {isSimulated && (
          <span style={{ padding:"3px 10px", backgroundColor:"#FEF3C7", color:"#92400E",
            border:"1px solid #FCD34D", borderRadius:20, fontSize:11, fontWeight:700 }}>
            SIMULADO
          </span>
        )}

        {/* DB sensor KPIs */}
        <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
          <KpiChip label="Sensores" value={kpis.total}   color="#374151" />
          <KpiChip label="Online"   value={kpis.online}  color="#6FAF82" />
          {kpis.degraded>0 && <KpiChip label="Degradado" value={kpis.degraded} color="#D48B3A" />}
          {kpis.offline>0  && <KpiChip label="Offline"   value={kpis.offline}  color="#6B7280" />}
          {kpis.avgBat!=null && <KpiChip label="Bat média" value={`${kpis.avgBat}%`} color="#3B82F6" />}
        </div>

        {/* MQTT device KPIs */}
        <div style={{ height:20, width:1, background:"#E5E7EB" }} />
        <div style={{ display:"flex", gap:8, alignItems:"center" }}>
          <span style={{ fontSize:11, fontWeight:700, color:"#556655",
            textTransform:"uppercase", letterSpacing:".05em" }}>MQTT</span>
          <KpiChip label="HW online" value={`${devicesOnline}/8`}
            color={devicesOnline>0?"#4A7C59":"#888"} />
        </div>

        <div style={{ marginLeft:"auto", display:"flex", gap:8 }}>
          {lastUpdated && (
            <span style={{ fontSize:11, color:"#9CA3AF", alignSelf:"center" }}>
              {lastUpdated.toLocaleTimeString("pt-PT")}
            </span>
          )}
          <button onClick={() => setShowAddModal(true)}
            style={{ padding:"7px 14px", backgroundColor:"#1B3A21", color:"#fff",
              border:"none", borderRadius:8, fontSize:13, fontWeight:600, cursor:"pointer" }}>
            + Sensor
          </button>
          <button onClick={handleExportCSV}
            style={{ padding:"7px 14px", backgroundColor:"#fff", color:"#374151",
              border:"1px solid #D1D5DB", borderRadius:8, fontSize:13, cursor:"pointer" }}>
            CSV
          </button>
        </div>
      </div>

      {/* ── MAIN GRID ────────────────────────────────────────────────────── */}
      <div style={{ display:"grid", gridTemplateColumns:"58fr 42fr", gap:0,
        height:"calc(100vh - 65px)", overflow:"hidden" }}>

        {/* LEFT — DB sensors */}
        <div style={{ overflowY:"auto", padding:22, borderRight:"1px solid #E5E7EB" }}>

          <SectionHeader title="Clusters WC" count={CLUSTERS.length} />
          {CLUSTERS.map(cluster => (
            <ClusterRow key={cluster} clusterId={cluster}
              sensors={byCluster[cluster]||[]}
              battery={batteryMap[cluster]||null}
              onRefresh={fetchAll} />
          ))}

          <SectionHeader title="Gateways" count={gateways.length} style={{ marginTop:24 }} />
          {gateways.length === 0 ? (
            <div style={{ color:"#9CA3AF", fontSize:13, padding:"10px 0" }}>Sem gateways.</div>
          ) : (
            <div style={{ border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
              {gateways.map((gw,i) => (
                <div key={gw.id} style={{ display:"flex", alignItems:"center", padding:"10px 14px",
                  gap:12, borderTop:i>0?"1px solid #F3F4F6":"none", backgroundColor:"#fff" }}>
                  <StatusDot status={gw.health?.status??"unknown"} size={10} />
                  <span style={{ fontFamily:"monospace", fontSize:12, minWidth:180 }}>{gw.id}</span>
                  <span style={{ fontSize:12, color:"#6B7280" }}>{gw.type}</span>
                  <span style={{ marginLeft:"auto", fontSize:11, color:"#9CA3AF" }}>
                    {gw.health?.last_seen
                      ? new Date(gw.health.last_seen).toLocaleTimeString("pt-PT")
                      : "nunca"}
                  </span>
                </div>
              ))}
            </div>
          )}

          <SectionHeader title="Verificação de Instalação" count={CLUSTERS.length} style={{ marginTop:24 }} />
          <div style={{ border:"1px solid #E5E7EB", borderRadius:10, overflow:"hidden" }}>
            {CLUSTERS.map((cluster,i) => {
              const check         = checks[cluster];
              const clusterSensors = byCluster[cluster]||[];
              const installed     = clusterSensors.filter(s => s.health?.status !== "unknown").length;
              return (
                <div key={cluster} style={{ display:"flex", alignItems:"center", padding:"10px 14px",
                  gap:12, borderTop:i>0?"1px solid #F3F4F6":"none",
                  backgroundColor:check?.done?"#F0FDF4":"#fff" }}>
                  <input type="checkbox" checked={!!check?.done}
                    onChange={() => handleInstallCheck(cluster)}
                    style={{ width:16, height:16, cursor:"pointer" }} />
                  <span style={{ fontWeight:600, minWidth:56 }}>{cluster}</span>
                  {(cluster==="WC-05"||cluster==="WC-06") &&
                    <span style={{ fontSize:11, color:"#6B7280" }}>UNISSEX</span>}
                  <span style={{ fontSize:12, color:"#6B7280" }}>
                    {installed}/{clusterSensors.length} activos
                  </span>
                  <span style={{ marginLeft:"auto", fontSize:11,
                    color:check?.done?"#6FAF82":"#D48B3A", fontWeight:600 }}>
                    {check?.done ? "✓ Verificado" : "Pendente"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT — tabs: MQTT Control | DB Terminal | Coverage */}
        <div style={{ display:"flex", flexDirection:"column", overflow:"hidden" }}>

          {/* Tab bar */}
          <div style={{ display:"flex", borderBottom:"1px solid #E5E7EB",
            background:"#fff", padding:"0 16px" }}>
            <button style={TAB_STYLE(rightTab==="mqtt")} onClick={() => setRightTab("mqtt")}>
              ⚡ Controlo MQTT
            </button>
            <button style={TAB_STYLE(rightTab==="db")} onClick={() => setRightTab("db")}>
              🖥 Terminal DB
            </button>
            <button style={TAB_STYLE(rightTab==="coverage")} onClick={() => setRightTab("coverage")}>
              📡 Cobertura
            </button>
          </div>

          {/* Tab content */}
          <div style={{ flex:1, overflow:"hidden", display:"flex", flexDirection:"column" }}>

            {/* ── MQTT Control tab ─────────────────────────────────────── */}
            {rightTab === "mqtt" && (
              <div style={{ flex:1, overflow:"auto", padding:16,
                display:"flex", flexDirection:"column", gap:12 }}>

                {/* Device grid */}
                <div>
                  <div style={{ fontWeight:700, fontSize:12, color:"#1B3A21",
                    textTransform:"uppercase", letterSpacing:".06em", marginBottom:8 }}>
                    Hardware físico — {devicesOnline}/8 online
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6 }}>
                    {devices.map(d => (
                      <DeviceCard key={d.cluster_id} d={d} onCmd={sendMqttCmd} />
                    ))}
                  </div>
                </div>

                {/* MQTT terminal */}
                <div style={{ flex:1 }}>
                  <div style={{ fontWeight:700, fontSize:12, color:"#1B3A21",
                    textTransform:"uppercase", letterSpacing:".06em", marginBottom:8 }}>
                    Terminal MQTT
                  </div>
                  <MQTTTerminal
                    wsUrl={`${WS_URL}/api/v1/devices/terminal`}
                    ref={mqttTermRef}
                  />
                </div>

                {/* Firmware manager */}
                <FirmwareTable devices={devices} onCmd={sendMqttCmd} />
              </div>
            )}

            {/* ── DB Terminal tab ───────────────────────────────────────── */}
            {rightTab === "db" && (
              <div style={{ flex:1, padding:16, display:"flex", flexDirection:"column" }}>
                <SectionHeader title="Terminal DB (sensor registry)" />
                <div style={{ flex:1, minHeight:0 }}>
                  <SensorTerminal />
                </div>
              </div>
            )}

            {/* ── Coverage Map tab ─────────────────────────────────────── */}
            {rightTab === "coverage" && (
              <div style={{ flex:1, padding:16, display:"flex", flexDirection:"column" }}>
                <SectionHeader title={`Cobertura (${coverage.length} sensores com GPS)`} />
                <div style={{ flex:1, minHeight:0 }}>
                  <CoverageMap features={coverage} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showAddModal && (
        <AddSensorModal onClose={() => setShowAddModal(false)} onAdded={fetchAll} />
      )}
    </div>
  );
}

