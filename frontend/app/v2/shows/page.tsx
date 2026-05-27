'use client';

import { useState } from 'react';
import { SHOWS, type Show } from '@/lib/v2-api';

export default function ShowsPage() {
  const [selectedDay, setSelectedDay] = useState(0);
  const show = SHOWS[selectedDay];

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
          Quatro dias.{' '}
          <em style={{ fontStyle: 'italic', color: 'var(--muted)' }}>
            Quatro picos.
          </em>{' '}
          <strong style={{ fontWeight: 700 }}>Cada um diferente.</strong>
        </h1>
        <p
          style={{
            fontSize: 14,
            color: 'var(--muted)',
            maxWidth: 720,
            lineHeight: 1.65,
          }}
        >
          Cada headliner gera um padrão diferente de utilização dos clusters WC.
          Selecciona um dia para ver a previsão de carga hora-a-hora e o factor
          de surge esperado no fim do show.
        </p>
      </div>

      {/* DAY TABS */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 8,
          marginBottom: 24,
        }}
      >
        {SHOWS.map((s, i) => {
          const active = i === selectedDay;
          return (
            <button
              key={s.id}
              onClick={() => setSelectedDay(i)}
              style={{
                textAlign: 'left',
                background: active ? 'var(--green)' : 'var(--card)',
                color: active ? '#FFFFFF' : 'var(--ink)',
                border: active
                  ? '1px solid var(--green)'
                  : '1px solid var(--border)',
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
                Dia {i + 1} · {s.date}
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
                ★ {s.headliner}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: active ? 'rgba(255,255,255,0.85)' : 'var(--muted)',
                }}
              >
                {s.dayLabel} · {s.crowd.toLocaleString('pt-PT')} pax
              </div>
            </button>
          );
        })}
      </div>

      {/* MAIN CONTENT */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.6fr 1fr',
          gap: 20,
        }}
      >
        <ShowSchedule show={show} />
        <ShowImpact show={show} />
      </div>
    </div>
  );
}

function ShowSchedule({ show }: { show: Show }) {
  const palcos = Array.from(new Set(show.lineup.map((l) => l.stage)));

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
          style={{
            fontSize: 22,
            fontWeight: 500,
            color: 'var(--ink)',
            margin: 0,
          }}
        >
          {show.dayLabel}
        </h2>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--faint)',
            letterSpacing: '0.06em',
          }}
        >
          {show.date}
        </span>
      </div>

      {palcos.map((palco) => {
        const acts = show.lineup
          .filter((l) => l.stage === palco)
          .sort((a, b) => a.time.localeCompare(b.time));
        return (
          <div key={palco} style={{ marginBottom: 16 }}>
            <div
              className="section-label"
              style={{ marginBottom: 8, color: 'var(--muted)' }}
            >
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
                    gridTemplateColumns: '70px 1fr auto',
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
                    {act.time}
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
                        <span
                          style={{
                            color: 'var(--green)',
                            marginRight: 6,
                          }}
                        >
                          ★
                        </span>
                      )}
                      {act.artist}
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
                    style={{
                      fontSize: 11,
                      color: 'var(--faint)',
                      fontStyle: 'italic',
                    }}
                  >
                    {act.genre}
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

function ShowImpact({ show }: { show: Show }) {
  const hours = Object.keys(show.crowdCurve)
    .map(Number)
    .sort((a, b) => (a < 14 ? a + 24 : a) - (b < 14 ? b + 24 : b));
  const maxCrowd = Math.max(...Object.values(show.crowdCurve));

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      {/* Headliner card */}
      <div
        style={{
          background:
            'linear-gradient(135deg, var(--green-dark), var(--green-accent))',
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
          ★ Headliner principal
        </div>
        <div
          className="serif"
          style={{
            fontSize: 32,
            fontWeight: 600,
            lineHeight: 1.05,
            marginBottom: 4,
          }}
        >
          {show.headliner}
        </div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
          {show.date} · {show.crowd.toLocaleString('pt-PT')} pessoas estimadas
        </div>
      </div>

      {/* Crowd curve */}
      <div
        style={{
          background: 'var(--card)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '16px 18px',
        }}
      >
        <div className="section-label" style={{ marginBottom: 8 }}>
          Curva de afluência · hora a hora
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 96 }}>
          {hours.map((h) => {
            const v = show.crowdCurve[h];
            const pct = (v / maxCrowd) * 100;
            const isPeak = h === show.peakHour;
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
                title={`${h}h · ${v.toLocaleString('pt-PT')} pessoas`}
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
          <span>Pico às {show.peakHour}h</span>
          <span className="mono">{maxCrowd.toLocaleString('pt-PT')} pax</span>
        </div>
      </div>

      {/* Predictions */}
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
          <ImpactRow
            label="Surge factor pós-show"
            value={`${show.surgeFactor.toFixed(1)}×`}
            sub={`Fim de show entre ${show.peakHour + 1}h e ${show.peakHour + 2}h`}
            critical={show.surgeFactor >= 4}
          />
          <ImpactRow
            label="Visitas por pessoa"
            value={`${show.visitsPerHead}×`}
            sub={`${Math.round(show.crowd * show.visitsPerHead).toLocaleString('pt-PT')} visitas totais ao WC`}
          />
          <ImpactRow
            label="Cluster sob pressão"
            value="WC-04 · WC-05"
            sub="Proximidade aos palcos principais"
          />
          <ImpactRow
            label="Cluster recomendado"
            value="WC-06"
            sub="208 lugares · maior cluster · zona sul"
            ok
          />
        </div>
      </div>
    </div>
  );
}

function ImpactRow({
  label,
  value,
  sub,
  critical,
  ok,
}: {
  label: string;
  value: string;
  sub: string;
  critical?: boolean;
  ok?: boolean;
}) {
  const col = critical
    ? 'var(--critical)'
    : ok
    ? 'var(--green)'
    : 'var(--text)';
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
        <div style={{ fontSize: 11, color: 'var(--faint)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
          {label}
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
          {sub}
        </div>
      </div>
      <div
        className="serif"
        style={{
          fontSize: 18,
          fontWeight: 600,
          color: col,
          flexShrink: 0,
          letterSpacing: '-0.01em',
        }}
      >
        {value}
      </div>
    </div>
  );
}
