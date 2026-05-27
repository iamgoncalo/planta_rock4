"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const CLUSTERS = ["WC-01", "WC-02", "WC-03", "WC-04", "WC-05", "WC-06", "WC-07", "WC-08"];
const TYPES = ["ir", "wifi", "camera", "lilygo", "lorawan"];
const PROTOCOLS = ["gpio", "wifi6", "lorawan", "rtsp", "ethernet"];

interface AddSensorModalProps {
  onClose: () => void;
  onAdded: () => void;
}

export function AddSensorModal({ onClose, onAdded }: AddSensorModalProps) {
  const [form, setForm] = useState({
    id: "",
    cluster_id: "",
    type: "ir",
    model: "",
    protocol: "gpio",
    location_desc: "",
    gps_lat: "",
    gps_lon: "",
    has_battery: false,
    battery_mah: "",
    powered_by: "",
    ip_rating: "",
    firmware: "",
    cost_eur: "",
    installed_by: "",
    notes: "",
    critical_note: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? (e.target as HTMLInputElement).checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const body: Record<string, unknown> = { ...form };
    if (body.gps_lat) body.gps_lat = parseFloat(body.gps_lat as string);
    else delete body.gps_lat;
    if (body.gps_lon) body.gps_lon = parseFloat(body.gps_lon as string);
    else delete body.gps_lon;
    if (body.battery_mah) body.battery_mah = parseInt(body.battery_mah as string, 10);
    else delete body.battery_mah;
    if (body.cost_eur) body.cost_eur = parseFloat(body.cost_eur as string);
    else delete body.cost_eur;
    if (!body.cluster_id) delete body.cluster_id;
    if (!body.id) delete body.id;

    try {
      const res = await fetch(`${API_URL}/api/v1/sensors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      onAdded();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    padding: "7px 10px",
    border: "1px solid #D1D5DB",
    borderRadius: 6,
    fontSize: 14,
    boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    color: "#374151",
    marginBottom: 4,
  };

  const fieldStyle: React.CSSProperties = {
    marginBottom: 14,
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.4)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          backgroundColor: "#fff",
          borderRadius: 12,
          padding: 28,
          width: "100%",
          maxWidth: 560,
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Adicionar Sensor</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#6B7280" }}>×</button>
        </div>

        {error && (
          <div style={{ padding: "10px 14px", backgroundColor: "#FEF2F2", border: "1px solid #C25A1A", borderRadius: 6, marginBottom: 16, color: "#C25A1A", fontSize: 14 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
            <div style={fieldStyle}>
              <label style={labelStyle}>ID (opcional)</label>
              <input name="id" value={form.id} onChange={handleChange} style={inputStyle} placeholder="auto-gerado" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Cluster</label>
              <select name="cluster_id" value={form.cluster_id} onChange={handleChange} style={inputStyle}>
                <option value="">— Sem cluster —</option>
                {CLUSTERS.map((c) => <option key={c} value={c}>{c}{c === "WC-05" || c === "WC-06" ? " UNISSEX" : ""}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Tipo *</label>
              <select name="type" value={form.type} onChange={handleChange} style={inputStyle} required>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Modelo *</label>
              <input name="model" value={form.model} onChange={handleChange} style={inputStyle} required placeholder="Ex: E18-D80NK" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Protocolo</label>
              <select name="protocol" value={form.protocol} onChange={handleChange} style={inputStyle}>
                {PROTOCOLS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Firmware</label>
              <input name="firmware" value={form.firmware} onChange={handleChange} style={inputStyle} placeholder="Ex: v1.0.0" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Latitude GPS</label>
              <input name="gps_lat" value={form.gps_lat} onChange={handleChange} style={inputStyle} type="number" step="any" placeholder="38.7870" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Longitude GPS</label>
              <input name="gps_lon" value={form.gps_lon} onChange={handleChange} style={inputStyle} type="number" step="any" placeholder="-9.0950" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Alimentação</label>
              <input name="powered_by" value={form.powered_by} onChange={handleChange} style={inputStyle} placeholder="Ex: 5V via LilyGo" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>IP Rating</label>
              <input name="ip_rating" value={form.ip_rating} onChange={handleChange} style={inputStyle} placeholder="Ex: IP67" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Custo (€)</label>
              <input name="cost_eur" value={form.cost_eur} onChange={handleChange} style={inputStyle} type="number" step="0.01" placeholder="0.00" />
            </div>
            <div style={fieldStyle}>
              <label style={labelStyle}>Instalado por</label>
              <input name="installed_by" value={form.installed_by} onChange={handleChange} style={inputStyle} placeholder="Nome do técnico" />
            </div>
          </div>

          <div style={{ ...fieldStyle, display: "flex", alignItems: "center", gap: 10 }}>
            <input type="checkbox" name="has_battery" checked={form.has_battery} onChange={handleChange} id="has_battery" />
            <label htmlFor="has_battery" style={{ fontSize: 14, cursor: "pointer" }}>Tem bateria</label>
            {form.has_battery && (
              <input name="battery_mah" value={form.battery_mah} onChange={handleChange} style={{ ...inputStyle, width: 120 }} type="number" placeholder="mAh" />
            )}
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Localização</label>
            <input name="location_desc" value={form.location_desc} onChange={handleChange} style={inputStyle} placeholder="Ex: Porta M entrada, altura 120cm" />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Notas</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} style={{ ...inputStyle, minHeight: 72, resize: "vertical" }} placeholder="Notas de instalação..." />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Nota crítica</label>
            <textarea name="critical_note" value={form.critical_note} onChange={handleChange} style={{ ...inputStyle, minHeight: 48, resize: "vertical" }} placeholder="Apenas para alertas críticos..." />
          </div>

          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 8 }}>
            <button type="button" onClick={onClose} style={{ padding: "9px 20px", border: "1px solid #D1D5DB", borderRadius: 8, backgroundColor: "#fff", fontSize: 14, cursor: "pointer" }}>
              Cancelar
            </button>
            <button type="submit" disabled={loading} style={{ padding: "9px 20px", backgroundColor: "#1F2937", color: "#fff", border: "none", borderRadius: 8, fontSize: 14, cursor: loading ? "default" : "pointer", opacity: loading ? 0.7 : 1 }}>
              {loading ? "A criar..." : "Criar Sensor"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
