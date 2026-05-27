'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  api,
  aggregate,
  CLUSTERS,
  type ClusterLive,
  type Alert,
  type StateResponse,
} from '@/lib/v2-api';

const REFRESH_MS = 10_000;

interface DerivedAlert {
  id: string;
  severity: 'critical' | 'warning' | 'info';
  cluster: string;
  title: string;
  detail: string;
  ts: number;
}

export default function OperationsPage() {
  const [state, setState] = useState<StateResponse | null>(null);
  const [clusters, setClusters] = useState<ClusterLive[]>([]);
  const [serverAlerts, setServerAlerts] = useState<Alert[]>([]);
  const [lastTick, setLastTick] = useState<Date | null>(null);
  const [tickCount, setTickCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let counter = 0;

    const tick = async () => {
      counter += 1;
      setTickCount(counter);
      try {
        const [s, a] = await Promise.all([
          api.state(),
          api.alerts().catch(() => ({ alerts: [] as Alert[] })),
        ]);
        if (cancelled) return;
        setState(s);
        const agg = aggregate(s.sections ?? []);
        setClusters(agg);
        const aList = Array.isArray(a) ? a : a.alerts ?? [];
        setServerAlerts(aList);
        setLastTick(new Date());
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

  // Derive alerts from cluster state
  const derivedAlerts = useMemo<DerivedAlert[]>(() => {
    const out: DerivedAlert[] = [];
    for (const c of clusters) {
      if (c.status === 'critical') {
        out.push({
          id: `${c.meta.id}-crit`,
          severity: 'critical',
          cluster: c.meta.id.toUpperCase(),
          title: `Ocupação crítica · ${c.ocupacao}%`,
          detail: `${c.meta.zone} · fila ${c.filaTotal} pessoas · espera ${c.esperaMin} min`,
          ts: Date.now(),
        });
      } else if (c.status === 'warning') {
        out.push({
          id: `${c.meta.id}-warn`,
          severity: 'warning',
          cluster: c.meta.id.toUpperCase(),
          title: `Ocupação a subir · ${c.ocupacao}%`,
          detail: `${c.meta.zone} · monitorizar nos próximos 10 min`,
          ts: Date.now(),
        });
      }
    }
    return out;
  }, [clusters]);

  // Routing recommendations: pair critical → free
  const routing = useMemo(() => {
    const crits = clusters.filter((c) => c.status === 'critical');
    const frees = [...clusters]
      .filter((c) => c.status === 'ok')
      .sort((a, b) => a.ocupacao - b.ocupacao);
    return crits.map((from) => ({
      from,
      to: frees[0] ?? null,
    }));
  }, [clusters]);

  return (
    <div style={{ padding: '40px 32px 48px', maxWidth: 1440, margin: '0 auto' }}>
      {/* HEADER */}
      <div style={{ marginBottom: 28 }}>
        <div className="section-label">Operações · sala de controlo</div>
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
          {derivedAlerts.length === 0 ? (
            <>
              Tudo <em style={{ fontStyle: 'italic', color: 'var(--green)' }}>fluído</em>.{' '}
              <span style={{ color: 'var(--muted)' }}>Nada a reportar.</span>
            </>
          ) : (
            <>
              {derivedAlerts.filter((a) => a.severity === 'critical').length}{' '}
              <em style={{ fontStyle: 'italic' }}>críticos.</em>{' '}
              <span style={{ color: 'var(--muted)' }}>
                {derivedAlerts.filter((a) => a.severity === 'warning').length} avisos.
              </span>
            </>
          )}
        </h1>
        <p style={{ fontSize: 13, color: 'var(--muted)' }}>
          Operações é a vista que a Rock World e os supervisores Planta usam ao
          vivo durante o evento. Tudo o que aqui vês também é publicado no SCOR
          Sensaway a cada 10 segundos.
        </p>
      </div>

      {/* KPI BAR */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 10,
          marginBottom: 28,
        }}
      >
        <OpsTile
          label="Críticos agora"
          value={String(derivedAlerts.filter((a) => a.severity === 'critical').length)}
          accent="var(--critical)"
        />
        <OpsTile
          label="Avisos activos"
          value={String(derivedAlerts.filter((a) => a.severity === 'warning').length)}
          accent="var(--amber)"
        />
        <OpsTile
          label="Pessoas total"
          value={clusters
            .reduce((a, c) => a + c.pessoas, 0)
            .toLocaleString('pt-PT')}
        />
        <OpsTile
          label="Ocupação média"
          value={`${Math.round(state?.kpis?.avg_ocupacao_pct ?? 0)}%`}
        />
        <OpsTile
          label="Redirecionadas hoje"
          value={String(state?.kpis?.redirected_count ?? 0)}
          accent="var(--green)"
        />
      </div>

      {/* MAIN 3-COL */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(280px, 1fr) minmax(280px, 1.4fr) minmax(280px, 1fr)',
          gap: 16,
        }}
      >
        {/* COL 1 — ALERTS */}
        <section
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '20px 22px',
          }}
        >
          <div
            className="section-label"
            style={{
              marginBottom: 14,
              color: derivedAlerts.length > 0 ? 'var(--critical)' : 'var(--green)',
            }}
          >
            Alertas activos · {derivedAlerts.length}
          </div>
          {derivedAlerts.length === 0 ? (
            <div
              style={{
                padding: '24px 0',
                textAlign: 'center',
                color: 'var(--muted)',
                fontSize: 13,
              }}
            >
              ✓ Sem alertas activos.
              <br />
              <span style={{ fontSize: 11, color: 'var(--faint)' }}>
                Todos os clusters dentro de parâmetros normais.
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {derivedAlerts.map((a) => (
                <AlertRow key={a.id} a={a} />
              ))}
            </div>
          )}
          {serverAlerts.length > 0 && (
            <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
              <div
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: '0.10em',
                  textTransform: 'uppercase',
                  color: 'var(--faint)',
                  marginBottom: 8,
                }}
              >
                Backend ({serverAlerts.length})
              </div>
              {serverAlerts.slice(0, 5).map((a) => (
                <div
                  key={a.id}
                  style={{
                    fontSize: 11,
                    color: 'var(--muted)',
                    padding: '4px 0',
                  }}
                >
                  • {a.message}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* COL 2 — ROUTING */}
        <section
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '20px 22px',
          }}
        >
          <div className="section-label" style={{ marginBottom: 14 }}>
            Routing recomendado
          </div>
          {routing.length === 0 ? (
            <div
              style={{
                padding: '24px 0',
                textAlign: 'center',
                color: 'var(--muted)',
                fontSize: 13,
              }}
            >
              Nenhum routing necessário neste momento.
              <br />
              <span style={{ fontSize: 11, color: 'var(--faint)' }}>
                Todos os clusters abaixo do limite crítico de 80%.
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {routing.map((r, i) =>
                r.to ? (
                  <RoutingRow key={i} from={r.from} to={r.to} />
                ) : null,
              )}
            </div>
          )}

          {/* Cluster overview mini-grid */}
          <div style={{ marginTop: 22, paddingTop: 18, borderTop: '1px solid var(--border)' }}>
            <div
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.10em',
                textTransform: 'uppercase',
                color: 'var(--faint)',
                marginBottom: 10,
              }}
            >
              Estado dos 8 clusters
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 6,
              }}
            >
              {(clusters.length ? clusters : CLUSTERS.map((m) => ({ meta: m, ocupacao: 0, status: 'ok' as const, pessoas: 0, filaTotal: 0, esperaMin: 0, entradas: 0, saidas: 0, confianca: 0.5, simulated: true, homens: null, mulheres: null }))).map((c) => {
                const col =
                  c.status === 'critical'
                    ? '#C25A1A'
                    : c.status === 'warning'
                    ? '#A85D00'
                    : '#6FAF82';
                return (
                  <div
                    key={c.meta.id}
                    style={{
                      background: 'var(--surface)',
                      border: `1px solid ${col}30`,
                      borderTop: `2px solid ${col}`,
                      borderRadius: 6,
                      padding: '8px 6px',
                      textAlign: 'center',
                    }}
                  >
                    <div
                      style={{
                        fontSize: 10,
                        color: 'var(--faint)',
                        fontWeight: 600,
                        letterSpacing: '0.06em',
                      }}
                    >
                      {c.meta.id.toUpperCase()}
                    </div>
                    <div
                      className="mono"
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: col,
                        marginTop: 2,
                      }}
                    >
                      {c.ocupacao}%
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* COL 3 — SYSTEM STATUS */}
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          <SystemTile
            title="SCOR Sensaway"
            status="online"
            lines={[
              `Último push: ${lastTick ? lastTick.toLocaleTimeString('pt-PT') : '—'}`,
              `Tick #${tickCount}`,
              `Intervalo: 10 s`,
              `Endpoint: /api/v1/telemetry`,
            ]}
          />
          <SystemTile
            title="Backend FastAPI"
            status={state ? 'online' : 'offline'}
            lines={[
              `Host: api.plantarockinrio.com`,
              `Railway: planta_rock4`,
              `Auto-tick: activo`,
              `Modo: simulado (até 11 Jun)`,
            ]}
          />
          <SystemTile
            title="Rede de sensores"
            status="aguarda instalação"
            warn
            lines={[
              `Físico: 11–12 Jun 2026`,
              `Hubs: 8 LILYGO 2G`,
              `IR: 32 E18-D80NK`,
              `LoRa GW: 2 Dragino`,
            ]}
          />
        </section>
      </div>

      {/* TIMELINE */}
      <section
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          padding: '22px 24px',
          marginTop: 16,
        }}
      >
        <div className="section-label" style={{ marginBottom: 12 }}>
          Timeline do evento
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          <TimelineStep date="20 Junho" label="Katy Perry" status="próximo" />
          <TimelineStep date="21 Junho" label="Linkin Park" status="próximo" />
          <TimelineStep date="27 Junho" label="Rod Stewart" status="próximo" />
          <TimelineStep date="28 Junho" label="21 Savage" status="próximo" />
        </div>
        <div
          style={{
            marginTop: 18,
            paddingTop: 14,
            borderTop: '1px solid var(--border)',
            fontSize: 11,
            color: 'var(--faint)',
            fontFamily: 'var(--font-mono), monospace',
            display: 'flex',
            gap: 18,
            flexWrap: 'wrap',
          }}
        >
          <span>11–12 Jun · instalação física dos sensores</span>
          <span>19 Jun · ensaios + validação end-to-end</span>
          <span>20–28 Jun · operação ao vivo</span>
        </div>
      </section>
    </div>
  );
}

function OpsTile({ label, value, accent = 'var(--ink)' }: { label: string; value: string; accent?: string }) {
  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: '14px 16px',
      }}
    >
      <div
        style={{
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: 'var(--faint)',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        className="serif"
        style={{
          fontSize: 28,
          fontWeight: 500,
          color: accent,
          lineHeight: 1,
          letterSpacing: '-0.02em',
        }}
      >
        {value}
      </div>
    </div>
  );
}

function AlertRow({ a }: { a: DerivedAlert }) {
  const col = a.severity === 'critical' ? '#C25A1A' : a.severity === 'warning' ? '#A85D00' : '#2563EB';
  const bg = a.severity === 'critical' ? 'var(--critical-bg)' : 'var(--amber-bg)';
  return (
    <div
      style={{
        background: bg,
        border: `1px solid ${col}30`,
        borderLeft: `3px solid ${col}`,
        borderRadius: 8,
        padding: '10px 12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2 }}>
        <span
          className="mono"
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: col,
            letterSpacing: '0.08em',
          }}
        >
          {a.cluster}
        </span>
        <span style={{ fontSize: 10, color: 'var(--faint)' }}>agora</span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
        {a.title}
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
        {a.detail}
      </div>
    </div>
  );
}

function RoutingRow({ from, to }: { from: ClusterLive; to: ClusterLive }) {
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
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 10,
        }}
      >
        <div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--critical)', fontWeight: 600 }}>
            {from.meta.id.toUpperCase()} · {from.ocupacao}%
          </div>
          <div style={{ fontSize: 10, color: 'var(--faint)' }}>
            {from.meta.zone}
          </div>
        </div>
        <span style={{ color: 'var(--green)', fontSize: 18, fontWeight: 600 }}>→</span>
        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: 11, color: 'var(--green)', fontWeight: 600 }}>
            {to.meta.id.toUpperCase()} · {to.ocupacao}%
          </div>
          <div style={{ fontSize: 10, color: 'var(--faint)' }}>
            {to.meta.zone}
          </div>
        </div>
      </div>
      <div
        style={{
          marginTop: 8,
          paddingTop: 8,
          borderTop: '1px dashed var(--border)',
          fontSize: 11,
          color: 'var(--muted)',
        }}
      >
        Walk estimado: {Math.round(Math.abs(from.meta.distStageM - to.meta.distStageM) / 60)} min · 
        Stewards: enviar para {from.meta.id.toUpperCase()}
      </div>
    </div>
  );
}

function SystemTile({
  title,
  status,
  lines,
  warn,
}: {
  title: string;
  status: string;
  lines: string[];
  warn?: boolean;
}) {
  const dotCol = status === 'online' ? '#2E7D4F' : warn ? '#A85D00' : '#C25A1A';
  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '14px 16px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
          {title}
        </span>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            fontSize: 10,
            color: dotCol,
            fontFamily: 'var(--font-mono), monospace',
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: dotCol,
              animation: status === 'online' ? 'pulse 1.6s ease-in-out infinite' : undefined,
            }}
          />
          {status}
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        {lines.map((l, i) => (
          <div
            key={i}
            style={{
              fontSize: 11,
              color: 'var(--muted)',
              fontFamily: 'var(--font-mono), monospace',
            }}
          >
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}

function TimelineStep({ date, label, status }: { date: string; label: string; status: string }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: '12px 14px',
      }}
    >
      <div
        className="mono"
        style={{
          fontSize: 10,
          color: 'var(--faint)',
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          fontWeight: 600,
        }}
      >
        {date}
      </div>
      <div
        className="serif"
        style={{
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--ink)',
          marginTop: 2,
          letterSpacing: '-0.01em',
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 10, color: 'var(--green)', marginTop: 3, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        {status}
      </div>
    </div>
  );
}
