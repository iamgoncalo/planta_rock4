'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiV9 as api } from '@/lib/v2-api';
import type {
  CleaningV9Response,
  UnitStatus,
  CleaningHistoryEntry,
} from '@/lib/v2-api';

const REFRESH_MS = 15_000;

const STATUS_STYLES: Record<
  string,
  { bg: string; ink: string; ring: string; label: string; priority: number }
> = {
  urgent:        { bg: '#F8D9C4', ink: '#8B3D0A', ring: '#C25A1A', label: 'URGENTE',     priority: 3 },
  needs_cleaning:{ bg: '#FFF2E0', ink: '#7A5A00', ring: '#A85D00', label: 'A AGUARDAR', priority: 2 },
  in_progress:   { bg: '#FFF7DC', ink: '#7A5A00', ring: '#C29A1A', label: 'EM CURSO',    priority: 1 },
  clean:         { bg: '#E8F1EA', ink: '#1B3A21', ring: '#4A7C59', label: 'LIMPO',       priority: 0 },
};

function fmtMin(m: number | null): string {
  if (m === null || m === undefined) return 'sem registo';
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const rem = m % 60;
  return rem === 0 ? `${h}h` : `${h}h${rem}m`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
}

export default function CleaningPage() {
  const [data, setData] = useState<CleaningV9Response | null>(null);
  const [history, setHistory] = useState<CleaningHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'urgent' | 'pending'>('all');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [openModal, setOpenModal] = useState<string | null>(null);

  const fetchAll = async () => {
    try {
      const [status, hist] = await Promise.all([
        api.cleaningUnitsStatus(),
        api.cleaningHistoryRecent(50),
      ]);
      setData(status);
      setHistory(hist);
      setError(null);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'erro');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(iv);
  }, []);

  const markUnit = async (unit_id: string) => {
    setMarking(unit_id);
    try {
      await api.cleaningUnitDone(unit_id, {
        team: 'Equipa A',
        operator: 'op',
        notes: null,
      });
      await fetchAll();
      setOpenModal(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'erro');
    } finally {
      setMarking(null);
    }
  };

  const units = useMemo(() => {
    if (!data) return [];
    let list = [...data.units];
    if (filter === 'urgent') list = list.filter(u => u.status === 'urgent');
    if (filter === 'pending') list = list.filter(u => u.status !== 'clean');
    // Ordenar: urgentes primeiro, depois needs, depois clean
    list.sort((a, b) => {
      const pa = STATUS_STYLES[a.status]?.priority ?? 0;
      const pb = STATUS_STYLES[b.status]?.priority ?? 0;
      if (pa !== pb) return pb - pa;
      return a.unit_id.localeCompare(b.unit_id);
    });
    return list;
  }, [data, filter]);

  const totalCapacity = data?.units.reduce((a, u) => a + u.capacity_simultaneous, 0) ?? 0;
  const totalEspera = data?.units.reduce((a, u) => a + u.espera, 0) ?? 0;

  return (
    <div style={{ padding: '32px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      {/* HEADER */}
      <div style={{ marginBottom: 20 }}>
        <div className="section-label">Operações · Limpeza · 14 unidades</div>
        <h1
          className="serif"
          style={{
            fontSize: 'clamp(26px, 4vw, 40px)',
            fontWeight: 500,
            color: 'var(--color-ink)',
            lineHeight: 1.1,
            marginBottom: 6,
          }}
        >
          Limpeza
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13, lineHeight: 1.55 }}>
          Limpo &lt; 60min · A aguardar 60–90min · Urgente acima de 90min · cadência alvo 1×/hora.
          {lastUpdate && (
            <span className="mono" style={{ fontSize: 11, marginLeft: 8 }}>
              · {lastUpdate.toLocaleTimeString('pt-PT')}
            </span>
          )}
        </p>
      </div>

      {/* HARD LIMITS BLOCK — sempre visível */}
      <div
        style={{
          background: '#FAFAF7',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          padding: 16,
          marginBottom: 20,
        }}
      >
        <div
          className="mono"
          style={{
            fontSize: 10,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--color-muted)',
            marginBottom: 8,
            fontWeight: 700,
          }}
        >
          ⚠ Hard Limits · Capacidade simultânea (XLSX oficial)
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: 12,
          }}
        >
          <Stat label="Masculino" value={data ? `${data.units.filter(u => u.gender === 'M').reduce((a, u) => a + u.capacity_simultaneous, 0)}` : '...'} sub="lugares" />
          <Stat label="Feminino" value={data ? `${data.units.filter(u => u.gender === 'F').reduce((a, u) => a + u.capacity_simultaneous, 0)}` : '...'} sub="lugares" />
          <Stat label="Unissex" value={data ? `${data.units.filter(u => u.gender === 'U').reduce((a, u) => a + u.capacity_simultaneous, 0)}` : '...'} sub="lugares (WC-05, WC-06)" />
          <Stat label="Espera" value={totalEspera ? `${Math.round(totalEspera)}` : '...'} sub="lugares" />
          <Stat label="Total" value={String(totalCapacity)} sub="lugares simultâneos" />
        </div>
      </div>

      {/* KPI BAR — status actual */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <Kpi label="Limpas" value={data?.clean_count ?? 0} total={14} color="#1B3A21" />
        <Kpi label="A aguardar" value={data?.needs_count ?? 0} total={14} color="#A85D00" />
        <Kpi label="Urgentes" value={data?.urgent_count ?? 0} total={14} color="#C25A1A" />
        <Kpi label="Próx. limpezas/h alvo" value={14} total={14} color="#4A7C59" hint="cadência 1×/h" />
      </div>

      {/* FILTROS */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        {[
          { id: 'all', label: 'Todas (14)' },
          { id: 'pending', label: 'Pendentes' },
          { id: 'urgent', label: 'Apenas urgentes' },
        ].map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id as any)}
            style={{
              background: filter === f.id ? 'var(--color-success, #1B3A21)' : 'white',
              color: filter === f.id ? 'white' : 'var(--color-ink)',
              border: `1px solid ${filter === f.id ? 'var(--color-success)' : 'var(--color-border)'}`,
              borderRadius: 999,
              padding: '5px 14px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div style={{
          padding: 10, marginBottom: 12, fontSize: 13,
          background: '#FDECDC', color: '#8B3D0A', borderRadius: 8,
        }}>
          {error}
        </div>
      )}

      {/* GRID DE 14 UNIDADES */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 12,
          marginBottom: 32,
        }}
      >
        {loading && !data && (
          <div style={{ color: 'var(--color-muted)', padding: 24, gridColumn: '1 / -1' }}>
            A carregar 14 unidades...
          </div>
        )}
        {units.map(u => {
          const sty = STATUS_STYLES[u.status];
          const genderIcon = u.gender === 'M' ? '♂' : u.gender === 'F' ? '♀' : '⚥';
          const genderColor = u.gender === 'M' ? '#1B5A8B' : u.gender === 'F' ? '#A8226F' : '#7A4A8E';
          return (
            <button
              key={u.unit_id}
              onClick={() => setOpenModal(u.unit_id)}
              style={{
                background: 'white',
                border: `1px solid var(--color-border)`,
                borderLeft: `4px solid ${sty.ring}`,
                borderRadius: 10,
                padding: 14,
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                transition: 'all 0.12s',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      fontSize: 16,
                      fontWeight: 700,
                      color: 'var(--color-ink)',
                    }}
                  >
                    <span style={{ color: genderColor, fontSize: 18 }}>{genderIcon}</span>
                    {u.cluster_id}
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: 'var(--color-muted)', marginTop: 2 }}>
                    {u.note || (u.gender === 'M' ? 'masculino' : u.gender === 'F' ? 'feminino' : 'unissex')}
                  </div>
                </div>
                <span style={{
                  background: sty.bg, color: sty.ink,
                  padding: '2px 7px', borderRadius: 999,
                  fontSize: 9, fontWeight: 700, letterSpacing: '0.06em',
                }}>
                  {sty.label}
                </span>
              </div>

              {/* Hard limits */}
              <div style={{
                fontSize: 11,
                color: 'var(--color-muted)',
                paddingTop: 4,
                paddingBottom: 2,
                borderTop: '1px dashed var(--color-border)',
              }}>
                <span style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{u.capacity_simultaneous}</span>
                {' '}lugares · <span className="mono">{Math.round(u.capacity_total)}</span> total
              </div>

              <div style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                {u.minutes_since_clean !== null && u.minutes_since_clean !== undefined
                  ? <>Há <span style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{fmtMin(u.minutes_since_clean)}</span></>
                  : 'sem registo'
                }
              </div>
            </button>
          );
        })}
      </div>

      {/* HISTÓRICO RECENTE — tabela densa */}
      <div style={{ marginBottom: 32 }}>
        <h2 className="serif" style={{ fontSize: 20, fontWeight: 500, color: 'var(--color-ink)', marginBottom: 10 }}>
          Últimas limpezas
        </h2>
        <div style={{
          background: 'white',
          border: '1px solid var(--color-border)',
          borderRadius: 10,
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#FAFAF7', borderBottom: '1px solid var(--color-border)' }}>
                <Th>Hora</Th>
                <Th>Unidade</Th>
                <Th>Equipa</Th>
                <Th>Operador</Th>
                <Th>Notas</Th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 && (
                <tr><td colSpan={5} style={{ padding: 16, textAlign: 'center', color: 'var(--color-muted)' }}>
                  Sem limpezas registadas
                </td></tr>
              )}
              {history.slice(0, 20).map(h => (
                <tr key={h.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                  <Td><span className="mono">{fmtTime(h.cleaned_at)}</span></Td>
                  <Td><span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>{h.cluster_id}</span></Td>
                  <Td>{h.team || '—'}</Td>
                  <Td>{h.operator || '—'}</Td>
                  <Td style={{ color: 'var(--color-muted)' }}>{h.notes || '—'}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL — quando clicas num card */}
      {openModal && data && (() => {
        const u = data.units.find(x => x.unit_id === openModal);
        if (!u) return null;
        const sty = STATUS_STYLES[u.status];
        return (
          <div
            onClick={() => setOpenModal(null)}
            style={{
              position: 'fixed', inset: 0,
              background: 'rgba(0,0,0,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              zIndex: 1000,
              padding: 16,
            }}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                background: 'white',
                borderRadius: 14,
                padding: 24,
                maxWidth: 480,
                width: '100%',
                maxHeight: '90vh',
                overflowY: 'auto',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                <div>
                  <div className="serif" style={{ fontSize: 24, fontWeight: 500, color: 'var(--color-ink)' }}>
                    {u.cluster_id} {u.gender === 'M' ? 'Masculino' : u.gender === 'F' ? 'Feminino' : 'Unissex'}
                  </div>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 4 }}>
                    {u.unit_id} {u.note ? `· ${u.note}` : ''}
                  </div>
                </div>
                <span style={{
                  background: sty.bg, color: sty.ink,
                  padding: '4px 12px', borderRadius: 999,
                  fontSize: 11, fontWeight: 700, letterSpacing: '0.06em',
                }}>{sty.label}</span>
              </div>

              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10,
                marginBottom: 16, padding: 12,
                background: '#FAFAF7', borderRadius: 8,
              }}>
                <div>
                  <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                    Lugares simultâneos
                  </div>
                  <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--color-ink)' }}>
                    {u.capacity_simultaneous}
                  </div>
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                    Capacidade total
                  </div>
                  <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--color-ink)' }}>
                    {Math.round(u.capacity_total)}
                  </div>
                </div>
              </div>

              <div style={{ fontSize: 13, color: 'var(--color-muted)', marginBottom: 16 }}>
                {u.last_cleaned_at ? (
                  <>Última limpeza às <span className="mono">{fmtTime(u.last_cleaned_at)}</span> · há <span style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{fmtMin(u.minutes_since_clean)}</span>
                  {u.last_team && <> · equipa {u.last_team}</>}
                  {u.last_operator && <> · {u.last_operator}</>}
                  </>
                ) : (
                  <>Sem registo de limpeza nesta sessão.</>
                )}
              </div>

              <button
                onClick={() => markUnit(u.unit_id)}
                disabled={marking === u.unit_id}
                style={{
                  width: '100%',
                  background: 'var(--color-success, #1B3A21)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 10,
                  padding: '14px 18px',
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: marking === u.unit_id ? 'wait' : 'pointer',
                  opacity: marking === u.unit_id ? 0.6 : 1,
                  marginBottom: 8,
                }}
              >
                {marking === u.unit_id ? 'A registar…' : `Marcar ${u.label} como limpa`}
              </button>
              <button
                onClick={() => setOpenModal(null)}
                style={{
                  width: '100%',
                  background: 'transparent',
                  color: 'var(--color-muted)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 10,
                  padding: '10px 18px',
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Fechar
              </button>
            </div>
          </div>
        );
      })()}
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 3 }}>
        {label}
      </div>
      <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontSize: 10, color: 'var(--color-muted)', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function Kpi({ label, value, total, color, hint }: { label: string; value: number; total: number; color: string; hint?: string }) {
  return (
    <div style={{ background: 'white', border: '1px solid var(--color-border)', borderRadius: 10, padding: 14 }}>
      <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, color }}>
        <span className="serif" style={{ fontSize: 26, fontWeight: 500, lineHeight: 1 }}>{value}</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--color-muted)' }}>/ {total}</span>
      </div>
      {hint && <div style={{ fontSize: 10, color: 'var(--color-muted)', marginTop: 4 }}>{hint}</div>}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '8px 12px',
  fontSize: 10,
  color: 'var(--color-muted)',
  fontWeight: 600,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
};

const tdStyle: React.CSSProperties = {
  padding: '8px 12px',
  color: 'var(--color-ink)',
};

function Th({ children }: { children: React.ReactNode }) {
  return <th style={thStyle}>{children}</th>;
}

function Td({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <td style={{ ...tdStyle, ...style }}>{children}</td>;
}
