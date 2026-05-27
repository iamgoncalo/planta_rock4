'use client';

import { useEffect, useMemo, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const REFRESH_MS = 30_000;

interface ScheduledClean {
  slot_id: string;
  unit_id: string;
  cluster_id: string;
  unit_label: string;
  gender: 'M' | 'F' | 'U';
  scheduled_for_iso: string;
  expected_duration_min: number;
  person_id: string | null;
  person_name: string | null;
  person_phone: string | null;
  team: string | null;
  status: 'planned' | 'in_progress' | 'done' | 'overdue';
}

interface Staff {
  person_id: string;
  name: string;
  phone: string;
  team: string;
  role: string;
  shift: string;
  languages: string[];
}

interface StaffResponse {
  staff: Staff[];
  total: number;
  teams: Record<string, number>;
  active_team_now: string;
}

interface CalendarResponse {
  schedule: ScheduledClean[];
  total_slots: number;
}

const STATUS_META: Record<string, { bg: string; ink: string; label: string }> = {
  done:        { bg: '#E8F1EA', ink: '#1B3A21', label: 'Concluída' },
  in_progress: { bg: '#FFF7DC', ink: '#7A5A00', label: 'Em curso' },
  planned:     { bg: '#FAFAF7', ink: '#1A1A1A', label: 'Planeada' },
  overdue:     { bg: '#F8D9C4', ink: '#8B3D0A', label: 'Atrasada' },
};

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const isToday = d.toDateString() === today.toDateString();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const isTomorrow = d.toDateString() === tomorrow.toDateString();
  if (isToday) return 'hoje';
  if (isTomorrow) return 'amanhã';
  return d.toLocaleDateString('pt-PT', { weekday: 'short', day: '2-digit', month: 'short' });
}

export default function CleaningPage() {
  const [schedule, setSchedule] = useState<ScheduledClean[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [activeTeam, setActiveTeam] = useState<string>('—');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterUnit, setFilterUnit] = useState<string>('all');
  const [openSlot, setOpenSlot] = useState<ScheduledClean | null>(null);

  const fetchAll = async () => {
    try {
      const [calRes, staffRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/cleaning/calendar?hours=24`).then(r => r.json() as Promise<CalendarResponse>),
        fetch(`${API_BASE}/api/v1/cleaning/staff`).then(r => r.json() as Promise<StaffResponse>),
      ]);
      setSchedule(calRes.schedule);
      setStaff(staffRes.staff);
      setActiveTeam(staffRes.active_team_now);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'erro');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(iv);
  }, []);

  // Lista de units únicos no schedule
  const uniqueUnits = useMemo(() => {
    const s = new Set(schedule.map(x => x.unit_id));
    return Array.from(s).sort();
  }, [schedule]);

  // Filtragem
  const filtered = useMemo(() => {
    if (filterUnit === 'all') return schedule;
    return schedule.filter(s => s.unit_id === filterUnit);
  }, [schedule, filterUnit]);

  // Próxima limpeza (a mais próxima planned ou in_progress)
  const next = useMemo(() => {
    const future = schedule.filter(s => s.status === 'planned' || s.status === 'in_progress');
    if (future.length === 0) return null;
    return future.sort((a, b) =>
      new Date(a.scheduled_for_iso).getTime() - new Date(b.scheduled_for_iso).getTime()
    )[0];
  }, [schedule]);

  // Por equipa
  const teamA = staff.filter(p => p.team === 'A');
  const teamB = staff.filter(p => p.team === 'B');

  // Agrupar schedule por hora para timeline
  const byHour = useMemo(() => {
    const map = new Map<string, ScheduledClean[]>();
    filtered.forEach(s => {
      const d = new Date(s.scheduled_for_iso);
      const key = `${d.toISOString().slice(0, 13)}:00`;  // YYYY-MM-DDTHH:00
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(s);
    });
    return Array.from(map.entries()).sort();
  }, [filtered]);

  return (
    <div style={{ padding: '32px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 18 }}>
        <div className="section-label">Operações · Limpeza · Calendário preditivo</div>
        <h1 className="serif" style={{
          fontSize: 'clamp(26px, 4vw, 40px)',
          fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.1, marginBottom: 6,
        }}>
          Limpeza
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13, lineHeight: 1.55 }}>
          Calendário preditivo · próximas 24h · 14 unidades × cadência 1×/h ·{' '}
          2 equipas (A: tarde · B: noite) · equipa activa agora{' '}
          <strong style={{ color: 'var(--color-ink)' }}>{activeTeam}</strong>
        </p>
      </div>

      {error && (
        <div style={{ padding: 10, marginBottom: 12, background: '#FDECDC', color: '#8B3D0A', borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {/* PRÓXIMA LIMPEZA — banner grande */}
      {next && (
        <div style={{
          background: 'linear-gradient(135deg, #1B3A21 0%, #2D5938 100%)',
          color: 'white', borderRadius: 12, padding: 18, marginBottom: 16,
          display: 'grid', gridTemplateColumns: '1fr auto', gap: 14, alignItems: 'center',
        }}>
          <div>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', opacity: 0.7, marginBottom: 4 }}>
              Próxima limpeza
            </div>
            <div className="serif" style={{ fontSize: 22, fontWeight: 500, marginBottom: 6, lineHeight: 1.15 }}>
              {next.unit_label} · {fmtTime(next.scheduled_for_iso)}
            </div>
            <div style={{ fontSize: 13, opacity: 0.85 }}>
              {next.person_name && (
                <>
                  Atribuída a <strong>{next.person_name}</strong> (equipa {next.team})
                  {next.person_phone && (
                    <> · <a href={`tel:${next.person_phone}`} style={{ color: '#A8E6BC' }}>{next.person_phone}</a></>
                  )}
                </>
              )}
            </div>
          </div>
          <span style={{
            background: 'rgba(255,255,255,0.18)',
            padding: '6px 14px', borderRadius: 999,
            fontSize: 11, fontWeight: 700, letterSpacing: '0.08em',
          }}>
            {next.status === 'in_progress' ? 'EM CURSO' : 'PLANEADA'}
          </span>
        </div>
      )}

      {/* EQUIPAS */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr',
        gap: 12, marginBottom: 16,
      }}>
        <TeamCard letter="A" name="Tarde" range="14:00–22:00" people={teamA} isActive={activeTeam === 'A'} />
        <TeamCard letter="B" name="Noite" range="22:00–06:00" people={teamB} isActive={activeTeam === 'B'} />
      </div>

      {/* FILTRO */}
      <div style={{
        display: 'flex', gap: 8, marginBottom: 14, alignItems: 'center', flexWrap: 'wrap',
      }}>
        <span className="mono" style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-muted)' }}>
          Filtrar:
        </span>
        <button
          onClick={() => setFilterUnit('all')}
          style={chipStyle(filterUnit === 'all')}
        >Todas ({schedule.length})</button>
        {uniqueUnits.map(u => (
          <button key={u} onClick={() => setFilterUnit(u)} style={chipStyle(filterUnit === u)}>
            {u.replace('_', ' ').replace('M', '♂').replace('F', '♀')}
          </button>
        ))}
      </div>

      {/* TIMELINE — por hora */}
      <div style={{
        background: 'white',
        border: '1px solid var(--color-border)',
        borderRadius: 10,
        marginBottom: 24,
      }}>
        {loading && (
          <div style={{ padding: 24, color: 'var(--color-muted)' }}>A carregar calendário...</div>
        )}
        {byHour.map(([hour, slots]) => (
          <div key={hour} style={{
            display: 'grid',
            gridTemplateColumns: '110px 1fr',
            borderBottom: '1px solid var(--color-border)',
          }}>
            <div style={{
              background: '#FAFAF7',
              padding: '10px 12px',
              fontSize: 11,
              color: 'var(--color-muted)',
              borderRight: '1px solid var(--color-border)',
            }}>
              <div className="mono" style={{ fontSize: 14, color: 'var(--color-ink)', fontWeight: 600 }}>
                {fmtTime(hour)}
              </div>
              <div className="mono" style={{ fontSize: 9, marginTop: 2 }}>{fmtDate(hour)}</div>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, padding: 6 }}>
              {slots.map(s => {
                const st = STATUS_META[s.status] || STATUS_META.planned;
                return (
                  <button
                    key={s.slot_id}
                    onClick={() => setOpenSlot(s)}
                    style={{
                      background: st.bg,
                      color: st.ink,
                      border: '1px solid transparent',
                      borderRadius: 6,
                      padding: '6px 9px',
                      fontSize: 10,
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                  >
                    <div style={{ fontSize: 11, fontWeight: 700 }}>
                      {fmtTime(s.scheduled_for_iso)} · {s.unit_id.replace('_M', '♂').replace('_F', '♀')}
                    </div>
                    <div className="mono" style={{ fontSize: 9, marginTop: 1, opacity: 0.7 }}>
                      {s.person_name?.split(' ')[0] || '—'}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* MODAL */}
      {openSlot && (
        <div
          onClick={() => setOpenSlot(null)}
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: 16,
          }}
        >
          <div onClick={(e) => e.stopPropagation()} style={{
            background: 'white', borderRadius: 14, padding: 24,
            maxWidth: 440, width: '100%',
          }}>
            <div className="mono" style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 4 }}>
              Limpeza programada
            </div>
            <h2 className="serif" style={{ fontSize: 24, fontWeight: 500, marginBottom: 10 }}>
              {openSlot.unit_label}
            </h2>
            <div style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--color-ink)', marginBottom: 16 }}>
              <strong>{fmtTime(openSlot.scheduled_for_iso)}</strong> · {fmtDate(openSlot.scheduled_for_iso)}<br />
              Duração esperada: {openSlot.expected_duration_min} min<br />
              Estado: {STATUS_META[openSlot.status]?.label}
            </div>
            {openSlot.person_name && (
              <div style={{
                background: '#FAFAF7', padding: 14, borderRadius: 10, marginBottom: 14,
              }}>
                <div className="mono" style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-muted)', marginBottom: 4 }}>
                  Atribuída a
                </div>
                <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--color-ink)' }}>
                  {openSlot.person_name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 2 }}>
                  Equipa {openSlot.team}
                </div>
                {openSlot.person_phone && (
                  <a href={`tel:${openSlot.person_phone}`} style={{
                    display: 'inline-block', marginTop: 8,
                    fontSize: 13, color: '#4A7C59', textDecoration: 'none',
                  }}>
                    📞 {openSlot.person_phone}
                  </a>
                )}
              </div>
            )}
            <button onClick={() => setOpenSlot(null)} style={{
              width: '100%',
              background: 'transparent',
              border: '1px solid var(--color-border)',
              borderRadius: 10,
              padding: '10px 18px',
              fontSize: 13, cursor: 'pointer',
              color: 'var(--color-muted)',
            }}>Fechar</button>
          </div>
        </div>
      )}
    </div>
  );
}

function TeamCard({ letter, name, range, people, isActive }: {
  letter: string; name: string; range: string;
  people: Staff[]; isActive: boolean;
}) {
  return (
    <div style={{
      background: isActive ? '#E8F1EA' : 'white',
      border: `1px solid ${isActive ? '#4A7C59' : 'var(--color-border)'}`,
      borderRadius: 10, padding: 14,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <div>
          <div className="serif" style={{ fontSize: 22, fontWeight: 500, color: 'var(--color-ink)' }}>
            Equipa {letter} · {name}
          </div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 2 }}>
            {range}
          </div>
        </div>
        {isActive && (
          <span style={{
            background: '#1B3A21', color: 'white',
            padding: '3px 10px', borderRadius: 999,
            fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
            height: 'fit-content',
          }}>● ACTIVA</span>
        )}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {people.map(p => (
          <div key={p.person_id} style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto',
            fontSize: 12,
            paddingBottom: 4,
            borderBottom: '1px dashed var(--color-border)',
          }}>
            <div>
              <span style={{ fontWeight: 600, color: 'var(--color-ink)' }}>{p.name}</span>
              <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--color-muted)', textTransform: 'capitalize' }}>{p.role}</span>
            </div>
            <a href={`tel:${p.phone}`} className="mono" style={{
              fontSize: 11, color: '#4A7C59', textDecoration: 'none',
            }}>{p.phone}</a>
          </div>
        ))}
      </div>
    </div>
  );
}

function chipStyle(active: boolean): React.CSSProperties {
  return {
    background: active ? '#1B3A21' : 'white',
    color: active ? 'white' : 'var(--color-ink)',
    border: `1px solid ${active ? '#1B3A21' : 'var(--color-border)'}`,
    borderRadius: 999,
    padding: '4px 10px',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
  };
}
