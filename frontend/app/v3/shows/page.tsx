'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface Show {
  show_id: string;
  name: string;
  stage: string;
  start_iso: string;
  end_iso: string;
  headliner: boolean;
  expected_surge_pct: number;
}

interface ShowsPayload {
  shows: Show[];
  active_show: Show | null;
  total_shows: number;
}

function fmtDT(iso: string) {
  const d = new Date(iso);
  const date = d.toLocaleDateString('pt-PT', { weekday: 'short', day: '2-digit', month: 'short' });
  const time = d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' });
  return { date, time };
}

function surgeColour(pct: number) {
  if (pct >= 80) return 'var(--v3-amber)';
  if (pct >= 50) return 'var(--v3-blue)';
  return '#22C55E';
}

export default function ShowsPage() {
  const [data, setData] = useState<ShowsPayload | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/shows`, { cache: 'no-store' });
        if (r.ok) setData(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  if (!data) {
    return (
      <div className="v3-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, color: 'var(--v3-muted)' }}>A carregar…</span>
      </div>
    );
  }

  return (
    <div className="v3-page">
      {/* Active show banner */}
      {data.active_show && (
        <div style={{
          marginBottom: 24,
          padding: '16px 20px',
          borderRadius: 'var(--v3-r)',
          background: 'var(--v3-pink-soft)',
          border: '1px solid var(--v3-pink)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
        }}>
          <div>
            <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-pink)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 4 }}>
              A decorrer agora
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--v3-ink)' }}>
              {data.active_show.name}
            </div>
            <div style={{ fontSize: 12, color: 'var(--v3-muted)', marginTop: 2 }}>
              {data.active_show.stage}
            </div>
          </div>
          <div style={{ textAlign: 'right', flexShrink: 0 }}>
            <div style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 22, fontWeight: 700, color: surgeColour(data.active_show.expected_surge_pct) }}>
              +{data.active_show.expected_surge_pct}%
            </div>
            <div style={{ fontSize: 10, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              surge esperado
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Programa · {data.total_shows} shows
        </div>
      </div>

      {/* Shows list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.shows.map((s) => {
          const { date, time } = fmtDT(s.start_iso);
          const { time: endTime } = fmtDT(s.end_iso);
          const isActive = data.active_show?.show_id === s.show_id;
          const colour = surgeColour(s.expected_surge_pct);

          return (
            <div
              key={s.show_id}
              className="v3-card"
              style={isActive ? { borderColor: 'var(--v3-pink)', background: 'var(--v3-pink-soft)' } : undefined}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--v3-ink)' }}>{s.name}</span>
                    {s.headliner && (
                      <span className="v3-badge v3-badge-pink">HEADLINE</span>
                    )}
                    {isActive && (
                      <span className="v3-badge v3-badge-pink">AO VIVO</span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--v3-muted)', display: 'flex', gap: 10 }}>
                    <span>{s.stage}</span>
                    <span>·</span>
                    <span style={{ fontFamily: 'var(--v3-font-mono)' }}>
                      {date} · {time}–{endTime}
                    </span>
                  </div>
                </div>

                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 18, fontWeight: 700, color: colour }}>
                    +{s.expected_surge_pct}%
                  </div>
                  <div style={{ fontSize: 10, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.04em' }}>
                    SURGE
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
