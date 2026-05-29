"use client";
/* ============================================================================
 *  PlantaOS · Rock in Rio Lisboa 2026  —  /v2/ambientes/rirstaff
 *  Estado ao vivo + chat Gemini privado + PAINEL DE CALIBRACAO (password)
 *  Substitui app/v2/ambientes/rirstaff/page.tsx  (frontend Next.js)
 *  Sem scroll, estilo Planta (Inter, branco/ink/green/amber).
 * ========================================================================== */
import { useState, useEffect, useRef } from "react";

const API = "https://api.plantarockinrio.com/api/v1";
const INK = "#0D1A0F", GREEN = "#1B3A21", AMBER = "#C25A1A";
const CHAT_KEY = "planta-rirstaff-chat-v1";

type Cluster = {
  cluster: string; nome: string; capacidade: number; ocupacao: number;
  ocupacao_pct: number; estado: string; entradas_ir: number | null;
  saidas_ir: number | null; online: boolean;
};
const cor = (e: string) => e === "cheio" ? AMBER : e === "quase" ? "#D98A3D" : e === "medio" ? "#7A9B5E" : GREEN;

export default function Page() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [msgs, setMsgs] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [aEscrever, setAEscrever] = useState(false);
  const [calibrar, setCalibrar] = useState(false);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => { try { const h = localStorage.getItem(CHAT_KEY); if (h) setMsgs(JSON.parse(h)); } catch {} }, []);
  useEffect(() => { try { localStorage.setItem(CHAT_KEY, JSON.stringify(msgs.slice(-30))); } catch {}; fim.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  useEffect(() => {
    let on = true;
    const f = async () => {
      try { const r = await fetch(`${API}/rirstaff`); const d = await r.json();
        if (on) setClusters(Array.isArray(d) ? d : (d.clusters || [])); } catch {}
    };
    f(); const t = setInterval(f, 2000); return () => { on = false; clearInterval(t); };
  }, []);

  const enviar = async () => {
    const txt = input.trim(); if (!txt || aEscrever) return;
    const novos = [...msgs, { role: "user", text: txt }];
    setMsgs(novos); setInput(""); setAEscrever(true);
    try {
      const r = await fetch(`${API}/rirstaff/chat`, { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensagem: txt, historico: novos.slice(-10) }) });
      const d = await r.json();
      setMsgs([...novos, { role: "model", text: d.resposta || "..." }]);
    } catch { setMsgs([...novos, { role: "model", text: "Sem ligacao agora." }]); }
    finally { setAEscrever(false); }
  };

  return (
    <div style={{ fontFamily: "Inter, system-ui, sans-serif", color: INK, height: "100dvh",
      display: "flex", flexDirection: "column", padding: 16, boxSizing: "border-box",
      background: "#fff", overflow: "hidden" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <img src="/planta-logo.svg" alt="" width={32} height={32} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>PlantaOS · Staff</div>
          <div style={{ fontSize: 12, opacity: 0.6 }}>Casas de banho · tempo real</div>
        </div>
        <button onClick={() => setCalibrar(!calibrar)} style={{ border: "none", background: "transparent",
          fontSize: 18, cursor: "pointer", opacity: 0.5 }} title="Calibrar">⚙</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
        {clusters.map((c) => {
          const fluxo = (c.entradas_ir ?? 0) - (c.saidas_ir ?? 0);
          return (
            <div key={c.cluster} style={{ border: `2px solid ${cor(c.estado)}`, borderRadius: 16, padding: 14 }}>
              <div style={{ fontSize: 13, fontWeight: 600, opacity: 0.7 }}>{c.nome}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 4, margin: "4px 0" }}>
                <span style={{ fontSize: 40, fontWeight: 800, color: cor(c.estado) }}>{c.ocupacao}</span>
                <span style={{ fontSize: 18, opacity: 0.5 }}>/{c.capacidade}</span>
              </div>
              <div style={{ height: 8, background: "#eee", borderRadius: 4, overflow: "hidden" }}>
                <div style={{ width: `${Math.min(100, c.ocupacao_pct)}%`, height: "100%",
                  background: cor(c.estado), transition: "width 0.6s ease" }} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12 }}>
                <span style={{ fontWeight: 700, color: cor(c.estado), textTransform: "uppercase" }}>{c.estado}</span>
                <span style={{ opacity: 0.6 }}>{c.online ? `fluxo ${fluxo >= 0 ? "+" : ""}${fluxo}` : "offline"}</span>
              </div>
            </div>
          );
        })}
        {clusters.length === 0 && <div style={{ gridColumn: "1/3", textAlign: "center", padding: 24, opacity: 0.5, fontSize: 13 }}>A carregar…</div>}
      </div>

      {calibrar
        ? <PainelCalibrar clusters={clusters} onClose={() => setCalibrar(false)} />
        : <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", border: "1px solid #eee", borderRadius: 16, overflow: "hidden" }}>
            <div style={{ padding: "8px 14px", borderBottom: "1px solid #eee", fontSize: 13, fontWeight: 600 }}>Assistente PlantaOS</div>
            <div style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
              {msgs.length === 0 && <div style={{ opacity: 0.5, fontSize: 13, textAlign: "center", marginTop: 20 }}>Pergunta: "Posso ir a casa de banho agora?"</div>}
              {msgs.map((m, i) => (
                <div key={i} style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "80%",
                  padding: "8px 12px", borderRadius: 14, fontSize: 14, lineHeight: 1.4,
                  background: m.role === "user" ? GREEN : "#f2f2f2", color: m.role === "user" ? "#fff" : INK }}>{m.text}</div>
              ))}
              {aEscrever && <div style={{ alignSelf: "flex-start", opacity: 0.5, fontSize: 13 }}>a escrever…</div>}
              <div ref={fim} />
            </div>
            <div style={{ display: "flex", gap: 8, padding: 10, borderTop: "1px solid #eee" }}>
              <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && enviar()}
                placeholder="Escreve aqui…" style={{ flex: 1, padding: "10px 14px", borderRadius: 12, border: "1px solid #ddd", fontSize: 14, fontFamily: "inherit", outline: "none" }} />
              <button onClick={enviar} disabled={aEscrever} style={{ padding: "10px 18px", borderRadius: 12, border: "none", background: GREEN, color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>Enviar</button>
            </div>
          </div>
      }
    </div>
  );
}

/* ===== Painel de calibracao remota (password) ===== */
function PainelCalibrar({ clusters, onClose }: { clusters: Cluster[]; onClose: () => void }) {
  const [pass, setPass] = useState("");
  const [cluster, setCluster] = useState("rirstaff-f");
  const [raio, setRaio] = useState(5);
  const [divisor, setDivisor] = useState(3);
  const [baseline, setBaseline] = useState(0);
  const [cap, setCap] = useState(8);
  const [msg, setMsg] = useState("");

  const guardar = async () => {
    setMsg("a guardar…");
    try {
      const r = await fetch(`${API}/rirstaff/config/${cluster}`, { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: pass, raio_m: raio, divisor, baseline, capacidade: cap }) });
      if (r.status === 401) { setMsg("Password errada"); return; }
      const d = await r.json();
      setMsg(d.ok ? "Guardado! O sensor aplica no proximo ciclo (~7s)." : "Erro");
    } catch { setMsg("Sem ligacao"); }
  };
  const campo = (label: string, val: number, set: (n: number) => void, min: number, max: number) => (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
        <span>{label}</span><strong>{val}</strong>
      </div>
      <input type="range" min={min} max={max} value={val} onChange={(e) => set(+e.target.value)} style={{ width: "100%" }} />
    </div>
  );
  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto", border: "1px solid #eee", borderRadius: 16, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <strong style={{ fontSize: 15 }}>Calibrar sensor</strong>
        <button onClick={onClose} style={{ border: "none", background: "transparent", cursor: "pointer", opacity: 0.5 }}>✕</button>
      </div>
      <select value={cluster} onChange={(e) => setCluster(e.target.value)} style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd", marginBottom: 12, fontSize: 14 }}>
        <option value="rirstaff-f">Mulheres</option>
        <option value="rirstaff-m">Homens</option>
      </select>
      {campo("Raio (metros)", raio, setRaio, 1, 20)}
      {campo("Divisor (dispositivos por pessoa)", divisor, setDivisor, 1, 6)}
      {campo("Baseline (ruido a subtrair)", baseline, setBaseline, 0, 40)}
      {campo("Capacidade", cap, setCap, 1, 30)}
      <input type="password" value={pass} onChange={(e) => setPass(e.target.value)} placeholder="Password"
        style={{ width: "100%", padding: 10, borderRadius: 10, border: "1px solid #ddd", marginBottom: 10, fontSize: 14, boxSizing: "border-box" }} />
      <button onClick={guardar} style={{ width: "100%", padding: 12, borderRadius: 10, border: "none", background: GREEN, color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer" }}>Guardar calibracao</button>
      {msg && <div style={{ marginTop: 10, fontSize: 13, textAlign: "center", color: msg.includes("errada") || msg.includes("Erro") ? AMBER : GREEN }}>{msg}</div>}
      <div style={{ marginTop: 12, fontSize: 12, opacity: 0.6, lineHeight: 1.5 }}>
        Dica: com a casa de banho vazia, vê quantas "pessoas" mostra. Mete esse valor × divisor no <strong>baseline</strong> para passar a mostrar 0.
      </div>
    </div>
  );
}
