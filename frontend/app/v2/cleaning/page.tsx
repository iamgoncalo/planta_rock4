'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const REFRESH_MS = 30000;

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

const STATUS_META: Record<string, { bg: string; ink: string; ring: string; label: string }> = {
  done:        { bg: '#E8F1EA', ink: '#1B3A21', ring: '#4A7C59', label: 'Concluida' },
  in_progress: { bg: '#FFF7DC', ink: '#7A5A00', ring: '#C9A227', label: 'Em curso' },
  planned:     { bg: '#F4F4F0', ink: '#3A3A36', ring: '#C9C9C0', label: 'Planeada' },
  overdue:     { bg: '#FDECDC', ink: '#8B3D0A', ring: '#C25A1A', label: 'Atrasada' },
};

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return 'hoje';
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (d.toDateString() === tomorrow.toDateString()) return 'amanha';
  return d.toLocaleDateString('pt-PT', { weekday: 'short', day: '2-digit', month: 'short' });
}

function genderMark(g: string): string {
  if (g === 'M') return 'M';
  if (g === 'F') return 'F';
  return 'U';
}

export default function CleaningPage() {
  const [schedule, setSchedule] = useState<ScheduledClean[]>([]);
  const [staff, setStaff] = useState<Staff[]>([]);
  const [activeTeam, setActiveTeam] = useState<string>('--');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openSlot, setOpenSlot] = useState<ScheduledClean | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [calRes, staffRes] = await Promise.all([
        fetch(API_BASE + '/api/v1/cleaning/calendar?hours=24').then(r => r.json() as Promise<CalendarResponse>),
        fetch(API_BASE + '/api/v1/cleaning/staff').then(r => r.json() as Promise<StaffResponse>),
      ]);
      setSchedule(calRes.schedule || []);
      setStaff(staffRes.staff || []);
      setActiveTeam(staffRes.active_team_now || '--');
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'erro');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, REFRESH_MS);
    return () => clearInterval(iv);
  }, [fetchAll]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpenSlot(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const counts = useMemo(() => {
    const c = { done: 0, in_progress: 0, planned: 0, overdue: 0 };
    schedule.forEach(s => { if (s.status in c) (c as Record<string, number>)[s.status]++; });
    return c;
  }, [schedule]);

  const next = useMemo(() => {
    const fut = schedule.filter(s => s.status === 'planned' || s.status === 'in_progress');
    if (!fut.length) return null;
    return fut.sort((a, b) => new Date(a.scheduled_for_iso).getTime() - new Date(b.scheduled_for_iso).getTime())[0];
  }, [schedule]);

  // proxima limpeza por unidade (uma linha por WC, sem timeline infinita)
  const perUnit = useMemo(() => {
    const map = new Map<string, ScheduledClean>();
    const now = Date.now();
    [...schedule]
      .sort((a, b) => new Date(a.scheduled_for_iso).getTime() - new Date(b.scheduled_for_iso).getTime())
      .forEach(s => {
        const t = new Date(s.scheduled_for_iso).getTime();
        const cur = map.get(s.unit_id);
        const isUpcoming = s.status === 'planned' || s.status === 'in_progress' || s.status === 'overdue';
        if (!cur) { map.set(s.unit_id, s); return; }
        const curUpcoming = cur.status === 'planned' || cur.status === 'in_progress' || cur.status === 'overdue';
        if (isUpcoming && !curUpcoming) map.set(s.unit_id, s);
        else if (isUpcoming && curUpcoming && t < new Date(cur.scheduled_for_iso).getTime() && t >= now - 3600000) map.set(s.unit_id, s);
      });
    return Array.from(map.values()).sort((a, b) => a.unit_id.localeCompare(b.unit_id));
  }, [schedule]);

  const teamA = staff.filter(p => p.team === 'A');
  const teamB = staff.filter(p => p.team === 'B');

  return (
    <div style={{
      position: 'fixed', inset: 0, top: 72,
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden', background: 'var(--color-bg, #FAFAF7)',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      {/* CABECALHO + KPIs */}
      <div style={{ flexShrink: 0, padding: '14px clamp(16px,3vw,32px) 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-muted,#6B6B63)' }}>
              Operacoes · Limpeza · Calendario preditivo
            </div>
            <h1 style={{ fontSize: 'clamp(20px,3vw,30px)', fontWeight: 600, color: 'var(--color-ink,#0D1A0F)', lineHeight: 1.1, margin: '2px 0 0' }}>
              Limpeza
            </h1>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Kpi label="Concluidas" value={counts.done} ring="#4A7C59" />
            <Kpi label="Em curso" value={counts.in_progress} ring="#C9A227" />
            <Kpi label="Planeadas" value={counts.planned} ring="#C9C9C0" />
            <Kpi label="Atrasadas" value={counts.overdue} ring="#C25A1A" highlight={counts.overdue > 0} />
            <div style={{ padding: '6px 12px', borderRadius: 10, background: '#1B3A21', color: 'white', textAlign: 'center' }}>
              <div style={{ fontSize: 9, letterSpacing: '0.08em', textTransform: 'uppercase', opacity: 0.7 }}>Equipa agora</div>
              <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1 }}>{activeTeam}</div>
            </div>
          </div>
        </div>
        {error && (
          <div role="alert" style={{ marginTop: 8, padding: 8, background: '#FDECDC', color: '#8B3D0A', borderRadius: 8, fontSize: 12 }}>
            Erro a carregar: {error}
          </div>
        )}
      </div>

      {/* CORPO: equipas (esq) + grelha de unidades (dir) */}
      <div style={{
        flex: 1, minHeight: 0, display: 'grid',
        gridTemplateColumns: 'minmax(220px, 0.9fr) 2.4fr',
        gap: 'clamp(8px,1.5vw,16px)', padding: '0 clamp(16px,3vw,32px) 14px',
        overflow: 'hidden',
      }}>
        {/* EQUIPAS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minHeight: 0, overflow: 'hidden' }}>
          {next && (
            <div style={{ background: 'linear-gradient(135deg,#1B3A21,#2D5938)', color: 'white', borderRadius: 12, padding: 12, flexShrink: 0 }}>
              <div style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', opacity: 0.7 }}>Proxima limpeza</div>
              <div style={{ fontSize: 16, fontWeight: 600, margin: '3px 0', lineHeight: 1.15 }}>
                {next.unit_label} · {fmtTime(next.scheduled_for_iso)}
              </div>
              {next.person_name && (
                <div style={{ fontSize: 12, opacity: 0.9 }}>
                  {next.person_name} (equipa {next.team})
                  {next.person_phone && <> · <a href={'tel:' + next.person_phone} style={{ color: '#A8E6BC' }}>{next.person_phone}</a></>}
                </div>
              )}
            </div>
          )}
          <div style={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateRows: '1fr 1fr', gap: 10 }}>
            <TeamCard letter="A" name="Tarde" range="14:00-22:00" people={teamA} isActive={activeTeam === 'A'} />
            <TeamCard letter="B" name="Noite" range="22:00-06:00" people={teamB} isActive={activeTeam === 'B'} />
          </div>
        </div>

        {/* GRELHA POR UNIDADE */}
        <div style={{
          background: 'white', border: '1px solid var(--color-border,#E5E5DF)', borderRadius: 12,
          padding: 12, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}>
          <div style={{ fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-muted,#6B6B63)', marginBottom: 8, flexShrink: 0 }}>
            Proxima limpeza por unidade · {perUnit.length} unidades
          </div>
          {loading ? (
            <div style={{ color: 'var(--color-muted,#6B6B63)', fontSize: 13 }}>A carregar...</div>
          ) : (
            <div style={{
              flex: 1, minHeight: 0, overflowY: 'auto',
              display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
              gap: 8, alignContent: 'start',
            }}>
              {perUnit.map(s => {
                const st = STATUS_META[s.status] || STATUS_META.planned;
                return (
                  <button
                    key={s.unit_id}
                    onClick={() => setOpenSlot(s)}
                    aria-label={'Limpeza ' + s.unit_label + ' as ' + fmtTime(s.scheduled_for_iso) + ', estado ' + st.label}
                    style={{
                      textAlign: 'left', cursor: 'pointer',
                      background: st.bg, color: st.ink,
                      border: '1px solid ' + st.ring, borderRadius: 10, padding: '9px 11px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 13, fontWeight: 700 }}>{s.cluster_id}</span>
                      <span style={{ fontSize: 9, fontWeight: 700, opacity: 0.7 }}>{genderMark(s.gender)}</span>
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 700, margin: '2px 0' }}>{fmtTime(s.scheduled_for_iso)}</div>
                    <div style={{ fontSize: 10, opacity: 0.85 }}>{st.label} · {fmtDate(s.scheduled_for_iso)}</div>
                    <div style={{ fontSize: 10, opacity: 0.7, marginTop: 1 }}>{s.person_name ? s.person_name.split(' ')[0] : '--'}</div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* DRAWER LATERAL (coerente com /v2/scor) */}
      {openSlot && (
        <>
          <div onClick={() => setOpenSlot(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', backdropFilter: 'blur(2px)', zIndex: 900 }} />
          <aside
            role="dialog" aria-modal="true" aria-label={'Detalhe da limpeza ' + openSlot.unit_label}
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0, width: 'min(420px, 92vw)',
              background: 'white', zIndex: 901, padding: 24, overflowY: 'auto',
              boxShadow: '-8px 0 32px rgba(0,0,0,0.18)', fontFamily: 'Inter, system-ui, sans-serif',
            }}
          >
            <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--color-muted,#6B6B63)' }}>
              Limpeza programada
            </div>
            <h2 style={{ fontSize: 24, fontWeight: 700, margin: '4px 0 12px', color: 'var(--color-ink,#0D1A0F)' }}>
              {openSlot.unit_label}
            </h2>
            <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--color-ink,#0D1A0F)', marginBottom: 16 }}>
              <strong>{fmtTime(openSlot.scheduled_for_iso)}</strong> · {fmtDate(openSlot.scheduled_for_iso)}<br />
              Duracao esperada: {openSlot.expected_duration_min} min<br />
              Estado: {(STATUS_META[openSlot.status] || STATUS_META.planned).label}
            </div>
            {openSlot.person_name && (
              <div style={{ background: '#F4F4F0', padding: 14, borderRadius: 10, marginBottom: 16 }}>
                <div style={{ fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-muted,#6B6B63)', marginBottom: 4 }}>Atribuida a</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-ink,#0D1A0F)' }}>{openSlot.person_name}</div>
                <div style={{ fontSize: 12, color: 'var(--color-muted,#6B6B63)', marginTop: 2 }}>Equipa {openSlot.team}</div>
                {openSlot.person_phone && (
                  <a href={'tel:' + openSlot.person_phone} style={{ display: 'inline-block', marginTop: 8, fontSize: 13, color: '#4A7C59', textDecoration: 'none', fontWeight: 600 }}>
                    Ligar: {openSlot.person_phone}
                  </a>
                )}
              </div>
            )}
            <button onClick={() => setOpenSlot(null)} autoFocus style={{
              width: '100%', background: 'transparent', border: '1px solid var(--color-border,#E5E5DF)',
              borderRadius: 10, padding: '11px 18px', fontSize: 13, cursor: 'pointer', color: 'var(--color-muted,#6B6B63)',
            }}>Fechar</button>
          </aside>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value, ring, highlight }: { label: string; value: number; ring: string; highlight?: boolean }) {
  return (
    <div style={{
      padding: '6px 12px', borderRadius: 10, background: 'white',
      border: '1px solid ' + (highlight ? '#C25A1A' : 'var(--color-border,#E5E5DF)'),
      textAlign: 'center', minWidth: 64,
    }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: highlight ? '#C25A1A' : 'var(--color-ink,#0D1A0F)', lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 9, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-muted,#6B6B63)', marginTop: 3 }}>
        <span aria-hidden="true" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: 999, background: ring, marginRight: 4, verticalAlign: 'middle' }} />
        {label}
      </div>
    </div>
  );
}

function TeamCard({ letter, name, range, people, isActive }: {
  letter: string; name: string; range: string; people: Staff[]; isActive: boolean;
}) {
  return (
    <div style={{
      background: isActive ? '#E8F1EA' : 'white',
      border: '1px solid ' + (isActive ? '#4A7C59' : 'var(--color-border,#E5E5DF)'),
      borderRadius: 12, padding: 12, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexShrink: 0 }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-ink,#0D1A0F)' }}>Equipa {letter} · {name}</div>
          <div style={{ fontSize: 10, color: 'var(--color-muted,#6B6B63)', marginTop: 1 }}>{range}</div>
        </div>
        {isActive && (
          <span style={{ background: '#1B3A21', color: 'white', padding: '3px 9px', borderRadius: 999, fontSize: 9, fontWeight: 700, letterSpacing: '0.08em' }}>ACTIVA</span>
        )}
      </div>
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 5 }}>
        {people.map(p => (
          <div key={p.person_id} style={{ display: 'grid', gridTemplateColumns: '1fr auto', fontSize: 12, paddingBottom: 4, borderBottom: '1px dashed var(--color-border,#E5E5DF)' }}>
            <div>
              <span style={{ fontWeight: 600, color: 'var(--color-ink,#0D1A0F)' }}>{p.name}</span>
              <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--color-muted,#6B6B63)', textTransform: 'capitalize' }}>{p.role}</span>
            </div>
            <a href={'tel:' + p.phone} style={{ fontSize: 11, color: '#4A7C59', textDecoration: 'none' }}>{p.phone}</a>
          </div>
        ))}
      </div>
    </div>
  );
}
