'use client';

import { useEffect, useState } from 'react';
import { NETWORK_LAYERS, SENSORS, api, type SensorNode } from '@/lib/v2-api';

const REFRESH_MS = 15_000;

export default function SensorsPage() {
  const [sensors, setSensors] = useState<SensorNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const data = await api.sensors();
        if (cancelled) return;
        const list = Array.isArray(data) ? data : data.sensors ?? [];
        setSensors(list);
      } catch {
        /* offline */
      } finally {
        setLoading(false);
      }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  const totalCost = SENSORS.reduce((a, s) => a + s.totalCost, 0);
  const totalUnits = SENSORS.reduce((a, s) => a + s.unitsProject, 0);
  const onlineCount = sensors.filter((s) => s.online).length;

  return (
    <div style={{ padding: '40px 32px 48px', maxWidth: 1280, margin: '0 auto' }}>
      {/* HEADER */}
      <div style={{ marginBottom: 28 }}>
        <div className="section-label">Sensores · arquitectura de rede</div>
        <h1
          className="serif"
          style={{
            fontSize: 'clamp(28px, 4vw, 44px)',
            fontWeight: 500,
            color: 'var(--ink)',
            lineHeight: 1.1,
            marginBottom: 8,
          }}
        >
          Como contamos pessoas <em style={{ fontStyle: 'italic' }}>sem</em> rastrear ninguém.
        </h1>
        <p style={{ fontSize: 14, color: 'var(--muted)', maxWidth: 760, lineHeight: 1.65 }}>
          Quatro camadas de rede redundantes. Sete categorias de sensor avaliadas. Tudo
          edge-only: nenhum MAC guardado, nenhuma imagem partilhada, nenhuma identidade
          construída. 30% de dados bem recolhidos vale mais do que 100% mal recolhidos.
        </p>
      </div>

      {/* SUMMARY METRICS */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
          marginBottom: 36,
        }}
      >
        <SummaryTile
          label="Sensores no terreno"
          value={String(totalUnits)}
          sub={`${onlineCount} online agora`}
        />
        <SummaryTile
          label="Custo total de hardware"
          value={`€ ${totalCost.toLocaleString('pt-PT')}`}
          sub="CAPEX once"
        />
        <SummaryTile
          label="Uptime esperado"
          value="99.96%"
          sub="4 camadas redundantes"
        />
        <SummaryTile
          label="Buffer offline"
          value="273 h"
          sub="SPIFFS local zero perda"
        />
      </div>

      {/* NETWORK LAYERS */}
      <section style={{ marginBottom: 40 }}>
        <h2
          className="serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--ink)',
            marginBottom: 14,
          }}
        >
          Arquitectura de rede · 4 camadas
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 12,
          }}
        >
          {NETWORK_LAYERS.map((l) => (
            <div
              key={l.name}
              style={{
                background: 'var(--card)',
                border: '1px solid var(--border)',
                borderLeft: `4px solid ${l.accent}`,
                borderRadius: 12,
                padding: '18px 18px 16px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: 8,
                }}
              >
                <h3
                  className="serif"
                  style={{
                    fontSize: 17,
                    fontWeight: 600,
                    color: 'var(--ink)',
                    margin: 0,
                  }}
                >
                  {l.name}
                </h3>
                <span
                  className="mono"
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: l.accent,
                    background: `${l.accent}15`,
                    padding: '3px 8px',
                    borderRadius: 6,
                  }}
                >
                  {l.role}
                </span>
              </div>
              <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>
                {l.tech} · {l.units} unidades
              </div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--text)', marginBottom: 8 }}>
                Alcance: {l.range} · Uptime: {l.uptime} · € {l.costEur}
              </div>
              <div style={{ fontSize: 12, color: 'var(--faint)', lineHeight: 1.55 }}>
                {l.note}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* HARDWARE CHAIN DIAGRAM */}
      <section style={{ marginBottom: 40 }}>
        <h2
          className="serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--ink)',
            marginBottom: 14,
          }}
        >
          Cadeia de hardware
        </h2>
        <div
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '28px 32px',
          }}
        >
          <svg viewBox="0 0 1200 360" style={{ width: '100%', height: 'auto' }} xmlns="http://www.w3.org/2000/svg">
            {/* L1 — Sensors */}
            <ChainLayer x={20} y={20} w={300} h={140} label="L1 · Terreno · cada cluster" lines={[
              '4× IR E18-D80NK (entrada + saída)',
              '1× LILYGO ESP32 hub (WiFi sniff)',
              '1× câmara Prosegur (validação)',
            ]} />

            <ChainLayer x={360} y={20} w={280} h={140} label="L2 · Servidor local · Pi 5" lines={[
              'FastAPI + SQLite + Redis cache',
              'Fusão IR (0.5) + WiFi (0.3) + Cam (0.2)',
              'Publica SCOR a cada 10 s',
            ]} />

            <ChainLayer x={680} y={20} w={280} h={140} label="L3 · Cloud" lines={[
              'Railway (FastAPI público)',
              'Vercel (Next.js dashboard)',
              'SCOR Sensaway (KPIs + telemetria)',
            ]} />

            <ChainLayer x={1000} y={20} w={180} h={140} label="L4 · Operações" lines={[
              'Rock World + Planta',
              'Alerts · Chat AI',
              'PWA visitante',
            ]} />

            {/* arrows */}
            <Arrow x1={320} y1={90} x2={360} y2={90} label="MQTT" />
            <Arrow x1={640} y1={90} x2={680} y2={90} label="HTTP 10s" />
            <Arrow x1={960} y1={90} x2={1000} y2={90} label="WS / SSE" />

            {/* Bottom: 8 clusters */}
            <text x={600} y={210} fontSize={11} fill="#3A6040" fontFamily="DM Sans" fontWeight={600} textAnchor="middle" letterSpacing="0.10em">
              REPLICADO POR 8 CLUSTERS · WC-01 A WC-08
            </text>
            <g transform="translate(180, 230)">
              {Array.from({ length: 8 }).map((_, i) => (
                <g key={i} transform={`translate(${i * 110}, 0)`}>
                  <rect width={92} height={64} rx={8} fill="#FAFAF7" stroke="#2E7D4F" strokeOpacity={0.3} />
                  <text x={46} y={26} fontSize={13} fill="#0D1A0F" fontFamily="DM Sans" fontWeight={600} textAnchor="middle">
                    WC-0{i + 1}
                  </text>
                  <text x={46} y={48} fontSize={10} fill="#7A9E7E" fontFamily="DM Mono" textAnchor="middle">
                    {i === 4 || i === 5 ? 'unisex' : 'M + F'}
                  </text>
                </g>
              ))}
            </g>
          </svg>
        </div>
      </section>

      {/* SENSOR CATALOG */}
      <section>
        <h2
          className="serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--ink)',
            marginBottom: 14,
          }}
        >
          Catálogo · {SENSORS.length} opções avaliadas
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
            gap: 12,
          }}
        >
          {SENSORS.map((s) => (
            <SensorCard key={s.id} s={s} />
          ))}
        </div>
      </section>

      {/* PRIVACY NOTE */}
      <section
        style={{
          marginTop: 36,
          padding: '20px 24px',
          background: 'var(--green-pale)',
          border: '1px solid rgba(46,125,79,0.25)',
          borderRadius: 12,
        }}
      >
        <div className="section-label" style={{ marginBottom: 6 }}>
          Privacidade by design
        </div>
        <p style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.7, margin: 0 }}>
          <strong>Zero rastreio individual.</strong> Nenhum endereço MAC é
          guardado. Nenhuma imagem deixa a câmara. Nenhuma identidade é
          construída ou inferida. Cada cluster produz apenas 5 valores: pessoas
          estimadas, ocupação %, fila actual, tempo de espera, fluxo de
          entrada por minuto. RGPD nativo, edge-only.
        </p>
      </section>
    </div>
  );
}

function SummaryTile({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '16px 18px',
      }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: 'var(--faint)',
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      <div
        className="serif"
        style={{
          fontSize: 30,
          fontWeight: 500,
          color: 'var(--green)',
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
        {sub}
      </div>
    </div>
  );
}

function SensorCard({ s }: { s: (typeof SENSORS)[number] }) {
  const recColor = s.recommended ? 'var(--green)' : 'var(--faint)';
  return (
    <div
      style={{
        background: 'var(--card)',
        border: s.recommended
          ? '1.5px solid rgba(46,125,79,0.30)'
          : '1px solid var(--border)',
        borderRadius: 12,
        padding: '18px 18px 16px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <h3
          className="serif"
          style={{
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--ink)',
            margin: 0,
            lineHeight: 1.3,
          }}
        >
          {s.name}
        </h3>
        <span
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.10em',
            textTransform: 'uppercase',
            color: recColor,
            background: s.recommended ? 'rgba(46,125,79,0.10)' : 'transparent',
            padding: '2px 8px',
            borderRadius: 999,
            border: s.recommended ? 'none' : '1px solid var(--border)',
            flexShrink: 0,
            marginLeft: 8,
          }}
        >
          {s.recommended ? '✓ recomendado' : 'avaliado'}
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--faint)', marginBottom: 12 }}>
        {s.category} · {s.vendor}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 6,
          padding: '10px 0',
          borderTop: '1px solid var(--border)',
          borderBottom: '1px solid var(--border)',
          fontSize: 11,
        }}
      >
        <Spec label="Preço unidade" value={`€ ${s.unitPrice}`} />
        <Spec label="Total projecto" value={`€ ${s.totalCost} (${s.unitsProject}×)`} />
        <Spec label="Protocolo" value={s.protocol} />
        <Spec label="Alcance" value={s.range} />
        <Spec label="IP" value={s.ipRating} />
        <Spec label="Instalação" value={`${s.installMin} min`} />
      </div>

      <div style={{ marginTop: 12 }}>
        <div style={{ fontSize: 10, color: 'var(--green)', fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', marginBottom: 4 }}>
          ✓ Pros
        </div>
        <ul style={{ fontSize: 11, color: 'var(--text)', listStyle: 'none', padding: 0, margin: 0 }}>
          {s.pros.map((p, i) => (
            <li key={i} style={{ marginBottom: 2 }}>• {p}</li>
          ))}
        </ul>
      </div>

      <div style={{ marginTop: 8 }}>
        <div style={{ fontSize: 10, color: 'var(--amber)', fontWeight: 700, letterSpacing: '0.10em', textTransform: 'uppercase', marginBottom: 4 }}>
          ✕ Contras
        </div>
        <ul style={{ fontSize: 11, color: 'var(--muted)', listStyle: 'none', padding: 0, margin: 0 }}>
          {s.cons.map((p, i) => (
            <li key={i} style={{ marginBottom: 2 }}>• {p}</li>
          ))}
        </ul>
      </div>

      {s.note && (
        <div
          style={{
            marginTop: 10,
            padding: '8px 10px',
            background: 'var(--amber-bg)',
            borderRadius: 6,
            fontSize: 11,
            color: 'var(--amber)',
            fontStyle: 'italic',
            lineHeight: 1.5,
          }}
        >
          {s.note}
        </div>
      )}
    </div>
  );
}

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 9, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 11, color: 'var(--text)' }}>
        {value}
      </div>
    </div>
  );
}

function ChainLayer({ x, y, w, h, label, lines }: { x: number; y: number; w: number; h: number; label: string; lines: string[] }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={10} fill="#FAFAF7" stroke="#2E7D4F" strokeOpacity={0.30} strokeWidth={1.5} />
      <text x={x + 16} y={y + 24} fontSize={12} fontFamily="DM Sans" fontWeight={700} fill="#2E7D4F" letterSpacing="0.08em">
        {label.toUpperCase()}
      </text>
      {lines.map((l, i) => (
        <text key={i} x={x + 16} y={y + 50 + i * 22} fontSize={13} fontFamily="DM Sans" fill="#1A2E1C">
          • {l}
        </text>
      ))}
    </g>
  );
}

function Arrow({ x1, y1, x2, y2, label }: { x1: number; y1: number; x2: number; y2: number; label: string }) {
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2 - 6} y2={y2} stroke="#2E7D4F" strokeWidth={2} markerEnd="url(#arr)" />
      <text x={(x1 + x2) / 2} y={y1 - 8} fontSize={10} fill="#3A6040" fontFamily="DM Mono" textAnchor="middle">
        {label}
      </text>
      <defs>
        <marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="#2E7D4F" />
        </marker>
      </defs>
    </g>
  );
}
