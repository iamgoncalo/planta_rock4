'use client';

import { useEffect, useState } from 'react';

/* ──────────────────────────────────────────────────────────────────
   CALENDÁRIO VERIFICADO · Rock in Rio Lisboa 2026 · Parque Tejo
   ────────────────────────────────────────────────────────────────── */

interface Show {
  time: string;
  artist: string;
  headliner?: boolean;
  nextDay?: boolean; // 01:00 do dia seguinte
}

interface Day {
  id: string;
  date: string;       // 'YYYY-MM-DD'
  dateLabel: string;  // '20 Junho'
  weekday: string;
  theme: string;
  stages: {
    PM: Show[];
    PMV: Show[];
    PSB: Show[];
  };
}

const STAGE_ORDER = ['PM', 'PMV', 'PSB'] as const;
type StageKey = (typeof STAGE_ORDER)[number];

const STAGE_LABEL: Record<StageKey, string> = {
  PM: 'Palco Mundo',
  PMV: 'Music Valley',
  PSB: 'Super Bock',
};

const CALENDAR: Day[] = [
  {
    id: 'D1',
    date: '2026-06-20',
    dateLabel: '20 Junho',
    weekday: 'Sábado',
    theme: 'Pop · Global',
    stages: {
      PM: [
        { time: '17:00', artist: 'Calema' },
        { time: '19:00', artist: 'Pedro Sampaio' },
        { time: '21:15', artist: 'Charlie Puth' },
        { time: '23:15', artist: 'Katy Perry', headliner: true },
      ],
      PMV: [
        { time: '18:00', artist: 'Maninho' },
        { time: '20:15', artist: 'Nena' },
        { time: '22:15', artist: 'Audrey Nuna' },
        { time: '01:00', artist: 'Alok', headliner: true, nextDay: true },
      ],
      PSB: [
        { time: '16:00', artist: 'Sofia Camara' },
        { time: '18:00', artist: 'Napa' },
        { time: '20:15', artist: 'Bebe Rexha' },
        { time: '22:15', artist: 'Bárbara Bandeira', headliner: true },
      ],
    },
  },
  {
    id: 'D2',
    date: '2026-06-21',
    dateLabel: '21 Junho',
    weekday: 'Domingo',
    theme: 'Rock · Pesado',
    stages: {
      PM: [
        { time: '17:00', artist: 'Grandson' },
        { time: '19:00', artist: 'The Pretty Reckless' },
        { time: '21:15', artist: 'Cypress Hill' },
        { time: '23:15', artist: 'Linkin Park', headliner: true },
      ],
      PMV: [
        { time: '16:00', artist: 'Dealema' },
        { time: '18:00', artist: 'Sam the Kid + Orquestra & Orelha Negra' },
        { time: '20:15', artist: 'P.O.D.' },
        { time: '22:15', artist: 'Sepultura', headliner: true },
      ],
      PSB: [
        { time: '16:00', artist: 'Tara Perdida' },
        { time: '18:00', artist: 'Blasted Mechanism' },
        { time: '20:15', artist: 'Kaiser Chiefs' },
        { time: '22:15', artist: 'Hoobastank', headliner: true },
      ],
    },
  },
  {
    id: 'D3',
    date: '2026-06-27',
    dateLabel: '27 Junho',
    weekday: 'Sábado',
    theme: 'Lendas · Clássicos',
    stages: {
      PM: [
        { time: '17:00', artist: '4 Non Blondes' },
        { time: '19:00', artist: 'Shaggy' },
        { time: '21:15', artist: 'Cyndi Lauper' },
        { time: '23:15', artist: 'Rod Stewart', headliner: true },
      ],
      PMV: [
        { time: '16:00', artist: 'Jafumega' },
        { time: '18:00', artist: 'UHF' },
        { time: '20:15', artist: 'GNR' },
        { time: '22:15', artist: 'Xutos & Pontapés', headliner: true },
      ],
      PSB: [
        { time: '15:00', artist: 'Syro' },
        { time: '18:00', artist: 'The Wailers' },
        { time: '20:15', artist: 'Joss Stone' },
        { time: '22:15', artist: 'Belo', headliner: true },
      ],
    },
  },
  {
    id: 'D4',
    date: '2026-06-28',
    dateLabel: '28 Junho',
    weekday: 'Domingo',
    theme: 'Urbano · Hip-Hop',
    stages: {
      PM: [
        { time: '17:00', artist: 'Matuê' },
        { time: '19:00', artist: 'Rema' },
        { time: '21:15', artist: 'Central Cee' },
        { time: '23:15', artist: '21 Savage', headliner: true },
      ],
      PMV: [
        { time: '18:00', artist: 'Irina Barros' },
        { time: '20:15', artist: 'Carlão' },
        { time: '22:15', artist: 'Filipe Ret' },
        { time: '01:00', artist: 'Dennis', headliner: true, nextDay: true },
      ],
      PSB: [
        { time: '16:00', artist: 'Karetus' },
        { time: '18:00', artist: 'Valete' },
        { time: '20:15', artist: 'Lola Índigo' },
        { time: '22:15', artist: 'CeeLo Green', headliner: true },
      ],
    },
  },
];

/* Dia inicial: o primeiro dia >= hoje, senão o primeiro. */
function initialDayIndex(): number {
  const today = new Date().toISOString().slice(0, 10);
  const idx = CALENDAR.findIndex((d) => d.date >= today);
  return idx === -1 ? 0 : idx;
}

export default function ShowsPage() {
  const [dayIdx, setDayIdx] = useState(0);
  const [stageIdx, setStageIdx] = useState(0); // só usado em mobile

  useEffect(() => {
    setDayIdx(initialDayIndex());
  }, []);

  const day = CALENDAR[dayIdx];
  const mobileStage = STAGE_ORDER[stageIdx];

  return (
    <div className="shows-root">
      {/* Cabeçalho: tabs de dia + tema */}
      <header className="shows-header">
        <div className="shows-head-row">
          <div>
            <div className="shows-eyebrow">Programa · Rock in Rio Lisboa 2026</div>
            <h1 className="shows-title">
              {day.weekday}, {day.dateLabel}
            </h1>
            <div className="shows-theme">{day.theme}</div>
          </div>

          <nav className="shows-daytabs" aria-label="Dias">
            {CALENDAR.map((d, i) => (
              <button
                key={d.id}
                className={`shows-daytab ${i === dayIdx ? 'is-active' : ''}`}
                onClick={() => setDayIdx(i)}
              >
                <span className="shows-daytab-id">{d.id}</span>
                <span className="shows-daytab-date">{d.dateLabel}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tabs de palco — só visíveis em mobile */}
        <nav className="shows-stagetabs" aria-label="Palcos">
          {STAGE_ORDER.map((s, i) => (
            <button
              key={s}
              className={`shows-stagetab ${i === stageIdx ? 'is-active' : ''}`}
              onClick={() => setStageIdx(i)}
            >
              {STAGE_LABEL[s]}
            </button>
          ))}
        </nav>
      </header>

      {/* Grelha dos 3 palcos */}
      <div className="shows-grid">
        {STAGE_ORDER.map((stage) => (
          <section
            key={stage}
            className={`shows-col ${stage === mobileStage ? 'is-mobile-active' : ''}`}
            aria-label={STAGE_LABEL[stage]}
          >
            <div className="shows-col-head">{STAGE_LABEL[stage]}</div>
            <ol className="shows-list">
              {day.stages[stage].map((show, i) => (
                <li
                  key={`${stage}-${i}`}
                  className={`shows-item ${show.headliner ? 'is-headliner' : ''}`}
                >
                  <div className="shows-time">
                    {show.time}
                    {show.nextDay && <span className="shows-nextday">+1</span>}
                  </div>
                  {show.headliner && <div className="shows-hl-label">Headliner</div>}
                  <div className="shows-artist">{show.artist}</div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <style jsx>{`
        .shows-root {
          position: fixed;
          top: var(--topbar-h, 72px);
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          background: #ffffff;
          overflow: hidden;
          color: #0d1a0f;
        }

        /* ── Header ── */
        .shows-header {
          flex-shrink: 0;
          padding: clamp(16px, 2.4vw, 30px) clamp(18px, 4vw, 56px) clamp(10px, 1.4vw, 18px);
          border-bottom: 1px solid #ece7d6;
        }
        .shows-head-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 20px;
          flex-wrap: wrap;
        }
        .shows-eyebrow {
          font-size: 10px;
          font-weight: 500;
          letter-spacing: 0.16em;
          text-transform: uppercase;
          color: #a4a89c;
        }
        .shows-title {
          font-size: clamp(26px, 3.6vw, 52px);
          font-weight: 200;
          letter-spacing: -0.035em;
          line-height: 1;
          margin: 6px 0 4px;
          color: #0d1a0f;
        }
        .shows-theme {
          font-size: clamp(13px, 1.3vw, 16px);
          font-weight: 500;
          color: #4a7c59;
          letter-spacing: 0.01em;
        }

        .shows-daytabs {
          display: flex;
          gap: 6px;
        }
        .shows-daytab {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
          background: transparent;
          border: 1px solid #ece7d6;
          border-radius: 12px;
          padding: clamp(8px, 1vw, 12px) clamp(10px, 1.4vw, 18px);
          cursor: pointer;
          transition: background 0.16s, border-color 0.16s, color 0.16s;
          font-family: inherit;
          color: #0d1a0f;
        }
        .shows-daytab:hover {
          border-color: #4a7c59;
        }
        .shows-daytab.is-active {
          background: #1b3a21;
          border-color: #1b3a21;
          color: #ffffff;
        }
        .shows-daytab-id {
          font-size: clamp(13px, 1.2vw, 16px);
          font-weight: 600;
          letter-spacing: -0.01em;
        }
        .shows-daytab-date {
          font-size: 10px;
          font-weight: 500;
          letter-spacing: 0.04em;
          opacity: 0.7;
        }

        .shows-stagetabs {
          display: none;
          gap: 6px;
          margin-top: 14px;
        }
        .shows-stagetab {
          flex: 1;
          background: transparent;
          border: 1px solid #ece7d6;
          border-radius: 10px;
          padding: 9px 8px;
          font-size: 12px;
          font-weight: 500;
          letter-spacing: 0.04em;
          cursor: pointer;
          font-family: inherit;
          color: #0d1a0f;
          transition: background 0.16s, border-color 0.16s, color 0.16s;
        }
        .shows-stagetab.is-active {
          background: #1b3a21;
          border-color: #1b3a21;
          color: #ffffff;
        }

        /* ── Grelha ── */
        .shows-grid {
          flex: 1;
          min-height: 0;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1px;
          background: #ece7d6;
        }
        .shows-col {
          background: #ffffff;
          padding: clamp(14px, 1.8vw, 26px) clamp(16px, 2.2vw, 36px);
          display: flex;
          flex-direction: column;
          min-height: 0;
          overflow: hidden;
        }
        .shows-col-head {
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          color: #a4a89c;
          padding-bottom: clamp(10px, 1.4vw, 18px);
          margin-bottom: clamp(8px, 1.2vw, 16px);
          border-bottom: 1px solid #ece7d6;
          flex-shrink: 0;
        }
        .shows-list {
          list-style: none;
          margin: 0;
          padding: 0;
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          min-height: 0;
        }
        .shows-item {
          padding: clamp(4px, 0.6vw, 8px) 0;
        }
        .shows-time {
          font-size: clamp(12px, 1vw, 14px);
          font-weight: 500;
          color: #a4a89c;
          font-variant-numeric: tabular-nums;
          font-feature-settings: 'tnum';
          letter-spacing: 0.02em;
          display: flex;
          align-items: baseline;
          gap: 6px;
        }
        .shows-nextday {
          font-size: 9px;
          font-weight: 600;
          letter-spacing: 0.08em;
          color: #c9a961;
          border: 1px solid #c9a961;
          border-radius: 4px;
          padding: 0 4px;
          line-height: 1.4;
        }
        .shows-hl-label {
          font-size: 9px;
          font-weight: 600;
          letter-spacing: 0.16em;
          text-transform: uppercase;
          color: #4a7c59;
          margin-top: 4px;
        }
        .shows-artist {
          font-size: clamp(15px, 1.5vw, 22px);
          font-weight: 400;
          letter-spacing: -0.015em;
          line-height: 1.15;
          color: #0d1a0f;
          margin-top: 3px;
        }
        .shows-item.is-headliner .shows-artist {
          font-size: clamp(20px, 2.2vw, 34px);
          font-weight: 600;
          letter-spacing: -0.025em;
          text-transform: uppercase;
          color: #1b3a21;
        }

        /* ── Mobile: 1 palco de cada vez ── */
        @media (max-width: 760px) {
          .shows-stagetabs {
            display: flex;
          }
          .shows-grid {
            grid-template-columns: 1fr;
            gap: 0;
            background: #ffffff;
          }
          .shows-col {
            display: none;
          }
          .shows-col.is-mobile-active {
            display: flex;
          }
          .shows-daytab-date {
            display: none;
          }
        }
      `}</style>
    </div>
  );
}
