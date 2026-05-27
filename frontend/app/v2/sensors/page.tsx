'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  api,
  NETWORK_LAYERS,
  SENSOR_CATALOG,
  enrichSensors,
  groupSensorsByCluster,
  sensorTypeLabel,
  sensorHealthColor,
  type BackendSensor,
  type SensorsSummary,
} from '@/lib/v2-api';

const REFRESH_MS = 15_000;

export default function SensorsPage() {
  const [sensors, setSensors] = useState<BackendSensor[]>([]);
  const [summary, setSummary] = useState<SensorsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const [list, sum] = await Promise.all([
          api.sensors(),
          api.sensorsSummary(),
        ]);
        if (cancelled) return;
        setSensors(list);
        setSummary(sum);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'erro');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    tick();
    const iv = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  const enriched = useMemo(() => enrichSensors(sensors), [sensors]);
  const byCluster = useMemo(() => groupSensorsByCluster(sensors), [sensors]);

  const onlineCount = sensors.filter((s) => s.health?.status === 'online').length;
  const unknownCount = sensors.filter((s) => s.health?.status === 'unknown').length;
  const offlineCount = sensors.filter(
    (s) => s.health?.status === 'offline' || s.health?.status === 'degraded',
  ).length;

  const totalCost = SENSOR_CATALOG.reduce((a, s) => {
    const count = summary?.by_type[s.type] ?? 0;
    return a + count * s.unitPrice;
  }, 0);

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
          Quatro camadas de rede redundantes. Seis tipos de sensor com 66 unidades no terreno.
          Tudo edge-only: nenhum MAC guardado, nenhuma imagem partilhada, nenhuma identidade
          construída. Os dados que vês aqui em baixo são lidos directamente do backend em tempo real.
        </p>
      </div>

      {/* SUMMARY METRICS — agora 100% do backend */}
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
          value={summary ? String(summary.total) : '—'}
          sub={`${onlineCount} online · ${unknownCount} a aguardar · ${offlineCount} ko`}
        />
        <SummaryTile
          label="Tipos de sensor"
          value={summary ? String(Object.keys(summary.by_type).length) : '—'}
          sub="6 categorias activas"
        />
        <SummaryTile
          label="Custo de hardware"
          value={`€ ${totalCost.toLocaleString('pt-PT')}`}
          sub="CAPEX once · só hardware"
        />
        <SummaryTile
          label="Buffer offline"
          value="273 h"
          sub="SPIFFS local · zero perda"
        />
      </div>

      {/* SENSOR FUSION WEIGHTS */}
      {summary && summary.fusion_weights && (
        <section
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: '18px 22px',
            marginBottom: 28,
          }}
        >
          <div className="section-label" style={{ marginBottom: 10 }}>
            Pesos de fusão de sensores · backend live
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 12,
            }}
          >
            {Object.entries(summary.fusion_weights).map(([k, v]) => (
              <FusionTile key={k} label={k} weight={v} />
            ))}
          </div>
          <p style={{ fontSize: 11, color: 'var(--faint)', marginTop: 12, lineHeight: 1.55 }}>
            IR é a fonte primária (50%) por ser direccional e contar com precisão.
            WiFi adiciona contexto agregado (30%). Câmara serve de validação cruzada (20%).
            Se uma fonte falha, os pesos redistribuem automaticamente.
          </p>
        </section>
      )}

      {/* CONTAGENS POR TIPO — live */}
      {summary && (
        <section style={{ marginBottom: 36 }}>
          <h2
            className="serif"
            style={{
              fontSize: 22,
              fontWeight: 500,
              color: 'var(--ink)',
              marginBottom: 14,
            }}
          >
            Contagens por tipo · ao vivo
          </h2>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: 10,
            }}
          >
            {Object.entries(summary.by_type)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => {
                const spec = SENSOR_CATALOG.find((s) => s.type === type);
                return (
                  <div
                    key={type}
                    style={{
                      background: 'var(--card)',
                      border: '1px solid var(--border)',
                      borderRadius: 10,
                      padding: '14px 16px',
                    }}
                  >
                    <div
                      className="serif"
                      style={{
                        fontSize: 26,
                        fontWeight: 500,
                        color: 'var(--green)',
                        lineHeight: 1,
                      }}
                    >
                      {count}
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: 'var(--faint)',
                        letterSpacing: '0.10em',
                        textTransform: 'uppercase',
                        fontWeight: 600,
                        marginTop: 4,
                      }}
                    >
                      {sensorTypeLabel(type)}
                    </div>
                    {spec && (
                      <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 3 }}>
                        € {spec.unitPrice} / un
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </section>
      )}

      {/* CLUSTER-BY-CLUSTER SENSOR INVENTORY — live */}
      <section style={{ marginBottom: 36 }}>
        <h2
          className="serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--ink)',
            marginBottom: 14,
          }}
        >
          Inventário por cluster · {byCluster.size} clusters
        </h2>
        {loading && (
          <div style={{ color: 'var(--muted)', fontSize: 13, padding: 20 }}>
            A carregar sensores do backend...
          </div>
        )}
        {error && (
          <div
            style={{
              background: 'var(--critical-bg)',
              border: '1px solid var(--critical)',
              borderRadius: 8,
              padding: '12px 16px',
              color: 'var(--critical)',
              fontSize: 13,
            }}
          >
            Erro: {error}
          </div>
        )}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 12,
          }}
        >
          {Array.from(byCluster.entries())
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([cid, list]) => (
              <ClusterSensorPanel key={cid} clusterId={cid} sensors={list} />
            ))}
        </div>
      </section>

      {/* NETWORK LAYERS */}
      <section style={{ marginBottom: 36 }}>
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
            <NetworkLayerCard key={l.name} l={l} />
          ))}
        </div>
      </section>

      {/* SENSOR CATALOG */}
      <section style={{ marginBottom: 28 }}>
        <h2
          className="serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--ink)',
            marginBottom: 14,
          }}
        >
          Catálogo · {SENSOR_CATALOG.length} categorias
        </h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
            gap: 12,
          }}
        >
          {SENSOR_CATALOG.map((s) => {
            const liveCount = summary?.by_type[s.type] ?? 0;
            return <SensorCard key={s.type} s={s} liveCount={liveCount} />;
          })}
        </div>
      </section>

      {/* PRIVACY NOTE */}
      <section
        style={{
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
        style={{ fontSize: 30, fontWeight: 500, color: 'var(--green)', lineHeight: 1 }}
      >
        {value}
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function FusionTile({ label, weight }: { label: string; weight: number }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '12px 14px',
      }}
    >
      <div
        className="mono"
        style={{ fontSize: 22, fontWeight: 600, color: 'var(--ink)', lineHeight: 1 }}
      >
        {(weight * 100).toFixed(0)}%
      </div>
      <div
        style={{
          fontSize: 10,
          color: 'var(--faint)',
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          fontWeight: 600,
          marginTop: 4,
        }}
      >
        peso · {label}
      </div>
      <div
        style={{
          height: 3,
          background: 'var(--border)',
          borderRadius: 2,
          marginTop: 8,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${weight * 100}%`,
            height: '100%',
            background: 'var(--green)',
          }}
        />
      </div>
    </div>
  );
}

function ClusterSensorPanel({
  clusterId,
  sensors,
}: {
  clusterId: string;
  sensors: BackendSensor[];
}) {
  const byType: Record<string, BackendSensor[]> = {};
  for (const s of sensors) {
    if (!byType[s.type]) byType[s.type] = [];
    byType[s.type].push(s);
  }
  const onlineCount = sensors.filter((s) => s.health?.status === 'online').length;
  const totalCount = sensors.length;
  const isUnisex = clusterId === 'WC-05' || clusterId === 'WC-06';

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
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 10,
        }}
      >
        <div>
          <div
            className="serif"
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: 'var(--ink)',
              lineHeight: 1,
            }}
          >
            {clusterId}
          </div>
          <div
            style={{
              fontSize: 10,
              color: 'var(--faint)',
              marginTop: 3,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
            }}
          >
            {isUnisex ? 'unisex' : 'M + F'}
          </div>
        </div>
        <div className="mono" style={{ fontSize: 12, color: 'var(--muted)' }}>
          {onlineCount}/{totalCount}
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {Object.entries(byType)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([type, list]) => {
            const onl = list.filter((s) => s.health?.status === 'online').length;
            const col = sensorHealthColor(list[0]?.health?.status ?? 'unknown');
            return (
              <div
                key={type}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '6px 10px',
                  background: 'var(--surface)',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      background: col,
                    }}
                  />
                  <span style={{ color: 'var(--text)' }}>{sensorTypeLabel(type)}</span>
                </span>
                <span className="mono" style={{ color: 'var(--muted)', fontSize: 11 }}>
                  {onl}/{list.length}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}

function NetworkLayerCard({ l }: { l: typeof NETWORK_LAYERS[number] }) {
  return (
    <div
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
        {l.tech}
      </div>
      <div
        className="mono"
        style={{ fontSize: 11, color: 'var(--text)', marginBottom: 8 }}
      >
        {l.range} · {l.uptime} · € {l.costEur}
      </div>
      <div style={{ fontSize: 12, color: 'var(--faint)', lineHeight: 1.55 }}>
        {l.note}
      </div>
    </div>
  );
}

function SensorCard({
  s,
  liveCount,
}: {
  s: typeof SENSOR_CATALOG[number];
  liveCount: number;
}) {
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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 6,
        }}
      >
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
          className="mono"
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: 'var(--green)',
            background: 'var(--green-pale)',
            padding: '3px 10px',
            borderRadius: 999,
            flexShrink: 0,
            marginLeft: 8,
          }}
        >
          {liveCount}× live
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
        <Spec label="Total live" value={`€ ${(liveCount * s.unitPrice).toLocaleString('pt-PT')}`} />
        <Spec label="Protocolo" value={s.protocol} />
        <Spec label="Alcance" value={s.range} />
        <Spec label="IP" value={s.ipRating} />
        <Spec label="Instalação" value={`${s.installMin} min`} />
      </div>

      <div style={{ marginTop: 12 }}>
        <div
          style={{
            fontSize: 10,
            color: 'var(--green)',
            fontWeight: 700,
            letterSpacing: '0.10em',
            textTransform: 'uppercase',
            marginBottom: 4,
          }}
        >
          ✓ Pros
        </div>
        <ul
          style={{ fontSize: 11, color: 'var(--text)', listStyle: 'none', padding: 0, margin: 0 }}
        >
          {s.pros.map((p, i) => (
            <li key={i} style={{ marginBottom: 2 }}>
              • {p}
            </li>
          ))}
        </ul>
      </div>

      <div style={{ marginTop: 8 }}>
        <div
          style={{
            fontSize: 10,
            color: 'var(--amber)',
            fontWeight: 700,
            letterSpacing: '0.10em',
            textTransform: 'uppercase',
            marginBottom: 4,
          }}
        >
          ✕ Contras
        </div>
        <ul
          style={{ fontSize: 11, color: 'var(--muted)', listStyle: 'none', padding: 0, margin: 0 }}
        >
          {s.cons.map((p, i) => (
            <li key={i} style={{ marginBottom: 2 }}>
              • {p}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Spec({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div
        style={{
          fontSize: 9,
          color: 'var(--faint)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          fontWeight: 600,
        }}
      >
        {label}
      </div>
      <div className="mono" style={{ fontSize: 11, color: 'var(--text)' }}>
        {value}
      </div>
    </div>
  );
}
