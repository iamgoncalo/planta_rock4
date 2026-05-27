'use client';

import { useEffect, useState } from 'react';
import {
  api,
  groupShowsByDay,
  type BackendShow,
  type ShowDay,
  type DisplayShow,
} from '@/lib/v2-api';

const REFRESH_MS = 60_000;

export default function ShowsPage() {
  const [raw, setRaw] = useState<BackendShow[]>([]);
  const [selectedDay, setSelectedDay] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await api.shows();
        if (cancelled) return;
        setRaw(r.shows ?? []);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'erro');
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

  const days: ShowDay[] = groupShowsByDay(raw);
  const day = days[selectedDay];

  return (
    <div style={{ padding: '40px 32px 48px', maxWidth: 1280, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <div className="section-label">Programa Rock in Rio Lisboa 2026</div>
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
          {days.length || 4} dias.{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--muted)' }}>
            {days.length || 4} picos.
          </em>{' '}
          <strong style={{ fontWeight: 700 }}>Cada um diferente.</strong>
        </h1>
        <p style={{ fontSize: 14, color: 'var(--muted)', maxWidth: 720, lineHeight: 1.65 }}>
          O programa é puxado em tempo real de /api/v1/shows. Cada show traz o
          surge esperado nos WC para a hora seguinte ao fim do espectáculo,
          calculado pelo backend.
        </p>
      </div>

      {loading && !raw.length && (
        <div style={{ padding: 20, color: 'var(--muted)' }}>A carregar shows...</div>
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
            marginBottom: 16,
          }}
        >
          Erro a obter shows: {error}
        </div>
      )}

      {days.length > 0 && (
        <>
          {/* DAY TABS */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(auto-fit, minmax(${Math.max(180, 800 / days.length)}px, 1fr))`,
              gap: 8,
              marginBottom: 24,
            }}
          >
            {days.map((d, i) => {
              const active = i === selectedDay;
              return (
                <button
                  key={d.dayKey}
                  onClick={() => setSelectedDay(i)}
                  style={{
                    textAlign: 'left',
                    background: active ? 'var(--green)' : 'var(--card)',
                    color: active ? '#FFFFFF' : 'var(--ink)',
                    border: active ? '1px solid var(--green)' : '1px solid var(--border)',
                    borderRadius: 12,
                    padding: '14px 16px',
                    cursor: 'pointer',
                    transition: 'all 0.16s',
                    fontFamily: 'inherit',
                  }}
                >
                  <div
                    className="mono"
                    style={{
                      fontSize: 10,
                      letterSpacing: '0.10em',
                      color: active ? 'rgba(255,255,255,0.75)' : 'var(--faint)',
                      textTransform: 'uppercase',
                      fontWeight: 600,
                      marginBottom: 4,
                    }}
                  >
                    {d.dayLabel} · {d.date}
                  </div>
                  <div
                    className="serif"
                    style={{
                      fontSize: 18,
                      fontWeight: 600,
                      letterSpacing: '-0.01em',
                      marginBottom: 2,
                    }}
                  >
                    {d.headliner ? `★ ${d.headliner.name}` : `${d.shows.length} actos`}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: active ? 'rgba(255,255,255,0.85)' : 'var(--muted)',
                    }}
                  >
                    {d.shows.length} actos ·{' '}
                    {d.headliner
                      ? `surge ${d.headliner.surgePct.toFixed(0)}%`
                      : 'sem headliner'}
                  </div>
                </button>
              );
            })}
          </div>

          {/* MAIN GRID */}
          {day && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1.6fr 1fr',
                gap: 20,
              }}
            >
              <ShowSchedule day={day} />
              <ShowImpact day={day} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ShowSchedule({ day }: { day: ShowDay }) {
  const palcos = Array.from(new Set(day.shows.map((s) => s.stage)));
  return (
    <div
      style={{
        background: 'var(--card)',
        border: '1px solid var(--border)',
        borderRadius: 14,
        padding: '20px 22px 22px',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 16,
        }}
      >
        <h2
          className="serif"
          style={{ fontSize: 22, fontWeight: 500, color: 'var(--ink)', margin: 0 }}
        >
          {day.dayLabel}
        </h2>
        <span
          className="mono"
          style={{ fontSize: 11, color: 'var(--faint)', letterSpacing: '0.06em' }}
        >
          {day.date}
        </span>
      </div>

      {palcos.map((palco) => {
        const acts = day.shows
          .filter((s) => s.stage === palco)
          .sort((a, b) => a.time.localeCompare(b.time));
        return (
          <div key={palco} style={{ marginBottom: 16 }}>
            <div className="section-label" style={{ marginBottom: 8, color: 'var(--muted)' }}>
              {palco}
            </div>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
                borderTop: '1px solid var(--border)',
              }}
            >
              {acts.map((act, i) => (
                <div
                  key={`${palco}-${i}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '90px 1fr auto',
                    gap: 14,
                    padding: '10px 4px',
                    borderBottom: '1px solid var(--border)',
                    alignItems: 'baseline',
                    background: act.headliner ? 'var(--green-pale)' : 'transparent',
                  }}
                >
                  <span
                    className="mono"
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: act.headliner ? 'var(--green-dark)' : 'var(--text)',
                    }}
                  >
                    {act.time}–{act.endTime}
                  </span>
                  <div>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: act.headliner ? 700 : 500,
                        color: 'var(--ink)',
                      }}
                    >
                      {act.headliner && (
                        <span style={{ color: 'var(--green)', marginRight: 6 }}>★</span>
                      )}
                      {act.name}
                      {act.headliner && (
                        <span
                          className="mono"
                          style={{
                            marginLeft: 10,
                            fontSize: 9,
                            background: 'var(--green)',
                            color: '#FFFFFF',
                            padding: '2px 7px',
                            borderRadius: 999,
                            letterSpacing: '0.10em',
                            fontWeight: 700,
                            verticalAlign: 'middle',
                          }}
                        >
                          HEADLINER
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className="mono"
                    style={{
                      fontSize: 11,
                      color:
                        act.surgePct >= 80
                          ? 'var(--critical)'
                          : act.surgePct >= 60
                          ? 'var(--amber)'
                          : 'var(--muted)',
                      fontWeight: 600,
                    }}
                  >
                    surge {act.surgePct.toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ShowImpact({ day }: { day: ShowDay }) {
  const headliner = day.headliner;
  // Reconstrói curva de afluência hora-a-hora a partir dos shows
  const hours: Record<number, number> = {};
  for (let h = 14; h <= 26; h++) hours[h % 24] = 0;
  for (const s of day.shows) {
    const hStart = parseInt(s.time.split(':')[0], 10);
    const hEnd = parseInt(s.endTime.split(':')[0], 10);
    const peak = Math.round(50_000 + s.surgePct * 800);
    for (let h = hStart; h <= hEnd; h++) {
      const key = h >= 24 ? h - 24 : h;
      hours[key] = Math.max(hours[key] ?? 0, peak);
    }
  }
  const orderedHours = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2];
  const peakValue = Math.max(...orderedHours.map((h) => hours[h] ?? 0));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {headliner ? (
        <div
          style={{
            background: 'linear-gradient(135deg, var(--green-dark), var(--green-accent))',
            color: '#FFFFFF',
            borderRadius: 14,
            padding: '20px 22px',
          }}
        >
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: 'rgba(255,255,255,0.75)',
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              fontWeight: 600,
              marginBottom: 8,
            }}
          >
            ★ Headliner do dia
          </div>
          <div
            className="serif"
            style={{ fontSize: 32, fontWeight: 600, lineHeight: 1.05, marginBottom: 4 }}
          >
            {headliner.name}
          </div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
            {headliner.stage} · {headliner.time}–{headliner.endTime} · surge esperado{' '}
            {headliner.surgePct.toFixed(0)}%
          </div>
        </div>
      ) : (
        <div
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 14,
            padding: '20px 22px',
            color: 'var(--muted)',
          }}
        >
          Sem headliner declarado neste dia.
        </div>
      )}

      <div
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '16px 18px',
        }}
      >
        <div className="section-label" style={{ marginBottom: 8 }}>
          Carga estimada · hora a hora
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 96 }}>
          {orderedHours.map((h) => {
            const v = hours[h] ?? 0;
            const pct = peakValue ? (v / peakValue) * 100 : 0;
            const isPeak = v === peakValue && v > 0;
            return (
              <div
                key={h}
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  height: '100%',
                }}
                title={`${h}h · ~${v.toLocaleString('pt-PT')} pessoas`}
              >
                <div
                  style={{
                    width: '100%',
                    height: `${pct}%`,
                    background: isPeak ? 'var(--critical)' : 'var(--green-light)',
                    borderRadius: 3,
                    transition: 'height 0.4s',
                  }}
                />
                <div
                  className="mono"
                  style={{
                    fontSize: 9,
                    color: isPeak ? 'var(--critical)' : 'var(--faint)',
                    marginTop: 4,
                    fontWeight: isPeak ? 700 : 500,
                  }}
                >
                  {String(h).padStart(2, '0')}
                </div>
              </div>
            );
          })}
        </div>
        {peakValue > 0 && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 11,
              color: 'var(--muted)',
              marginTop: 10,
              paddingTop: 8,
              borderTop: '1px solid var(--border)',
            }}
          >
            <span>Pico estimado</span>
            <span className="mono">~{peakValue.toLocaleString('pt-PT')} pax</span>
          </div>
        )}
      </div>

      <div
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '16px 18px',
        }}
      >
        <div className="section-label" style={{ marginBottom: 10 }}>
          Impacto previsto nos WC
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {day.shows.map((s) => (
            <ImpactRow key={s.id} show={s} />
          ))}
        </div>
      </div>
    </div>
  );
}

function ImpactRow({ show }: { show: DisplayShow }) {
  const col =
    show.surgePct >= 80
      ? 'var(--critical)'
      : show.surgePct >= 60
      ? 'var(--amber)'
      : 'var(--green)';
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: 12,
        paddingBottom: 8,
        borderBottom: '1px dashed var(--border)',
      }}
    >
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: 12,
            color: 'var(--text)',
            fontWeight: show.headliner ? 700 : 500,
          }}
        >
          {show.headliner && <span style={{ color: 'var(--green)', marginRight: 4 }}>★</span>}
          {show.name}
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
          {show.stage} · {show.time}–{show.endTime}
        </div>
      </div>
      <div
        className="serif"
        style={{
          fontSize: 20,
          fontWeight: 600,
          color: col,
          flexShrink: 0,
          letterSpacing: '-0.01em',
        }}
      >
        {show.surgePct.toFixed(0)}%
      </div>
    </div>
  );
}
