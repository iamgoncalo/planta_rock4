'use client';

import { useEffect, useMemo, useState } from 'react';

/* ──────────────────────────────────────────────────────────────────
   ARQUÉTIPOS · pressão de WC por tipo de público
   ────────────────────────────────────────────────────────────────── */

interface Archetype {
  f: number;          // % feminino
  flow: 'BAIXA' | 'MEDIA' | 'ALTA' | 'EXTREMA';
  pre: number;        // minutos antes do fim em que começa o pico
  surge: number;      // multiplicador de pressão
  wc: string[];       // WCs prioritários
}

const ARCHETYPES: Record<string, Archetype> = {
  POP_GLOBAL:   { f: 70, flow: 'ALTA',    pre: 75, surge: 3.8, wc: ['WC-06', 'WC-02', 'WC-03'] },
  POP_LATAM:    { f: 55, flow: 'ALTA',    pre: 60, surge: 3.2, wc: ['WC-06', 'WC-03', 'WC-07'] },
  POP_PT:       { f: 58, flow: 'MEDIA',   pre: 50, surge: 2.8, wc: ['WC-06', 'WC-03', 'WC-02'] },
  POP_FUNK_BR:  { f: 60, flow: 'EXTREMA', pre: 45, surge: 3.5, wc: ['WC-06', 'WC-07', 'WC-03'] },
  KCROSS_POP:   { f: 72, flow: 'ALTA',    pre: 90, surge: 3.6, wc: ['WC-02', 'WC-06', 'WC-03'] },
  ROCK_HEAVY:   { f: 38, flow: 'ALTA',    pre: 30, surge: 4.0, wc: ['WC-07', 'WC-06', 'WC-03'] },
  ROCK_ALT:     { f: 45, flow: 'MEDIA',   pre: 40, surge: 3.4, wc: ['WC-06', 'WC-07', 'WC-03'] },
  ROCK_PT:      { f: 40, flow: 'ALTA',    pre: 30, surge: 3.6, wc: ['WC-07', 'WC-06', 'WC-04'] },
  LEGENDS_INTL: { f: 55, flow: 'MEDIA',   pre: 90, surge: 2.4, wc: ['WC-03', 'WC-06', 'WC-01'] },
  LEGENDS_PT:   { f: 42, flow: 'ALTA',    pre: 60, surge: 3.2, wc: ['WC-07', 'WC-03', 'WC-06'] },
  REGGAE:       { f: 50, flow: 'BAIXA',   pre: 40, surge: 2.0, wc: ['WC-06', 'WC-03', 'WC-07'] },
  SOUL_RNB:     { f: 60, flow: 'MEDIA',   pre: 50, surge: 2.6, wc: ['WC-02', 'WC-06', 'WC-03'] },
  HIPHOP_INTL:  { f: 42, flow: 'EXTREMA', pre: 30, surge: 4.2, wc: ['WC-06', 'WC-07', 'WC-03'] },
  HIPHOP_PT:    { f: 38, flow: 'ALTA',    pre: 35, surge: 3.0, wc: ['WC-07', 'WC-06', 'WC-04'] },
  AFROBEATS:    { f: 55, flow: 'ALTA',    pre: 40, surge: 3.4, wc: ['WC-06', 'WC-07', 'WC-03'] },
  EDM_LATE:     { f: 48, flow: 'EXTREMA', pre: 25, surge: 2.6, wc: ['WC-06', 'WC-03', 'WC-07'] },
};

function pressureLabel(surge: number): { label: string; tone: 'ok' | 'warn' | 'crit' } {
  if (surge >= 4.0) return { label: 'Extrema', tone: 'crit' };
  if (surge >= 3.4) return { label: 'Alta', tone: 'warn' };
  if (surge >= 2.8) return { label: 'Média-alta', tone: 'warn' };
  return { label: 'Moderada', tone: 'ok' };
}

/* ──────────────────────────────────────────────────────────────────
   CALENDÁRIO VERIFICADO · Rock in Rio Lisboa 2026
   ────────────────────────────────────────────────────────────────── */

interface Show {
  time: string;
  artist: string;
  archetype: string;
  headliner?: boolean;
  nextDay?: boolean;
}

interface Day {
  id: string;
  date: string;
  dateLabel: string;
  weekday: string;
  theme: string;
  capacity: number;
  stages: { PM: Show[]; PMV: Show[]; PSB: Show[] };
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
    id: 'D1', date: '2026-06-20', dateLabel: '20 Junho', weekday: 'Sábado',
    theme: 'Pop · Global', capacity: 100000,
    stages: {
      PM: [
        { time: '17:00', artist: 'Calema', archetype: 'POP_LATAM' },
        { time: '19:00', artist: 'Pedro Sampaio', archetype: 'POP_FUNK_BR' },
        { time: '21:15', artist: 'Charlie Puth', archetype: 'POP_GLOBAL' },
        { time: '23:15', artist: 'Katy Perry', archetype: 'POP_GLOBAL', headliner: true },
      ],
      PMV: [
        { time: '18:00', artist: 'Maninho', archetype: 'POP_PT' },
        { time: '20:15', artist: 'Nena', archetype: 'POP_PT' },
        { time: '22:15', artist: 'Audrey Nuna', archetype: 'KCROSS_POP' },
        { time: '01:00', artist: 'Alok', archetype: 'EDM_LATE', headliner: true, nextDay: true },
      ],
      PSB: [
        { time: '16:00', artist: 'Sofia Camara', archetype: 'POP_PT' },
        { time: '18:00', artist: 'Napa', archetype: 'POP_PT' },
        { time: '20:15', artist: 'Bebe Rexha', archetype: 'POP_GLOBAL' },
        { time: '22:15', artist: 'Bárbara Bandeira', archetype: 'POP_PT', headliner: true },
      ],
    },
  },
  {
    id: 'D2', date: '2026-06-21', dateLabel: '21 Junho', weekday: 'Domingo',
    theme: 'Rock · Pesado', capacity: 100000,
    stages: {
      PM: [
        { time: '17:00', artist: 'Grandson', archetype: 'ROCK_ALT' },
        { time: '19:00', artist: 'The Pretty Reckless', archetype: 'ROCK_HEAVY' },
        { time: '21:15', artist: 'Cypress Hill', archetype: 'HIPHOP_INTL' },
        { time: '23:15', artist: 'Linkin Park', archetype: 'ROCK_HEAVY', headliner: true },
      ],
      PMV: [
        { time: '16:00', artist: 'Dealema', archetype: 'HIPHOP_PT' },
        { time: '18:00', artist: 'Sam the Kid + Orquestra & Orelha Negra', archetype: 'HIPHOP_PT' },
        { time: '20:15', artist: 'P.O.D.', archetype: 'ROCK_HEAVY' },
        { time: '22:15', artist: 'Sepultura', archetype: 'ROCK_HEAVY', headliner: true },
      ],
      PSB: [
        { time: '16:00', artist: 'Tara Perdida', archetype: 'ROCK_PT' },
        { time: '18:00', artist: 'Blasted Mechanism', archetype: 'ROCK_PT' },
        { time: '20:15', artist: 'Kaiser Chiefs', archetype: 'ROCK_ALT' },
        { time: '22:15', artist: 'Hoobastank', archetype: 'ROCK_HEAVY', headliner: true },
      ],
    },
  },
  {
    id: 'D3', date: '2026-06-27', dateLabel: '27 Junho', weekday: 'Sábado',
    theme: 'Lendas · Clássicos', capacity: 95000,
    stages: {
      PM: [
        { time: '17:00', artist: '4 Non Blondes', archetype: 'LEGENDS_INTL' },
        { time: '19:00', artist: 'Shaggy', archetype: 'REGGAE' },
        { time: '21:15', artist: 'Cyndi Lauper', archetype: 'LEGENDS_INTL' },
        { time: '23:15', artist: 'Rod Stewart', archetype: 'LEGENDS_INTL', headliner: true },
      ],
      PMV: [
        { time: '16:00', artist: 'Jafumega', archetype: 'LEGENDS_PT' },
        { time: '18:00', artist: 'UHF', archetype: 'LEGENDS_PT' },
        { time: '20:15', artist: 'GNR', archetype: 'LEGENDS_PT' },
        { time: '22:15', artist: 'Xutos & Pontapés', archetype: 'LEGENDS_PT', headliner: true },
      ],
      PSB: [
        { time: '15:00', artist: 'Syro', archetype: 'SOUL_RNB' },
        { time: '18:00', artist: 'The Wailers', archetype: 'REGGAE' },
        { time: '20:15', artist: 'Joss Stone', archetype: 'SOUL_RNB' },
        { time: '22:15', artist: 'Belo', archetype: 'POP_LATAM', headliner: true },
      ],
    },
  },
  {
    id: 'D4', date: '2026-06-28', dateLabel: '28 Junho', weekday: 'Domingo',
    theme: 'Urbano · Hip-Hop', capacity: 100000,
    stages: {
      PM: [
        { time: '17:00', artist: 'Matuê', archetype: 'HIPHOP_INTL' },
        { time: '19:00', artist: 'Rema', archetype: 'AFROBEATS' },
        { time: '21:15', artist: 'Central Cee', archetype: 'HIPHOP_INTL' },
        { time: '23:15', artist: '21 Savage', archetype: 'HIPHOP_INTL', headliner: true },
      ],
      PMV: [
        { time: '18:00', artist: 'Irina Barros', archetype: 'SOUL_RNB' },
        { time: '20:15', artist: 'Carlão', archetype: 'HIPHOP_PT' },
        { time: '22:15', artist: 'Filipe Ret', archetype: 'HIPHOP_INTL' },
        { time: '01:00', artist: 'Dennis', archetype: 'POP_FUNK_BR', headliner: true, nextDay: true },
      ],
      PSB: [
        { time: '16:00', artist: 'Karetus', archetype: 'EDM_LATE' },
        { time: '18:00', artist: 'Valete', archetype: 'HIPHOP_PT' },
        { time: '20:15', artist: 'Lola Índigo', archetype: 'POP_GLOBAL' },
        { time: '22:15', artist: 'CeeLo Green', archetype: 'SOUL_RNB', headliner: true },
      ],
    },
  },
];

function initialDayIndex(): number {
  const today = new Date().toISOString().slice(0, 10);
  const idx = CALENDAR.findIndex((d) => d.date >= today);
  return idx === -1 ? 0 : idx;
}

/* Minutos a partir de "HH:MM"; trata madrugada (nextDay) somando 24h */
function toMinutes(time: string, nextDay?: boolean): number {
  const [h, m] = time.split(':').map(Number);
  return (h + (nextDay ? 24 : 0)) * 60 + m;
}

function fmtMinutes(total: number): string {
  const h = Math.floor((total % (24 * 60)) / 60);
  const m = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/* KPIs do dia: pessoas, pico de afluência, género dominante, pressão máxima */
function dayIntel(day: Day) {
  const headliners = STAGE_ORDER.flatMap((s) =>
    day.stages[s].filter((sh) => sh.headliner),
  );
  // O headliner do Palco Mundo define o pico principal de afluência
  const pmHead = day.stages.PM.find((s) => s.headliner) || day.stages.PM[day.stages.PM.length - 1];
  const arch = ARCHETYPES[pmHead.archetype];
  const showEnd = toMinutes(pmHead.time, pmHead.nextDay) + 75;
  const peakStart = toMinutes(pmHead.time, pmHead.nextDay) - arch.pre;

  // Género dominante (média ponderada simples dos headliners)
  const femAvg =
    headliners.reduce((acc, h) => acc + ARCHETYPES[h.archetype].f, 0) /
    Math.max(1, headliners.length);

  // Pressão máxima do dia
  const maxSurge = Math.max(
    ...STAGE_ORDER.flatMap((s) => day.stages[s].map((sh) => ARCHETYPES[sh.archetype].surge)),
  );

  return {
    capacity: day.capacity,
    peakStart: fmtMinutes(peakStart),
    peakEnd: fmtMinutes(showEnd + 25),
    femAvg: Math.round(femAvg),
    maxPressure: pressureLabel(maxSurge),
    headlinerCount: headliners.length,
  };
}

export default function ShowsPage() {
  const [dayIdx, setDayIdx] = useState(0);
  const [stageIdx, setStageIdx] = useState(0);

  useEffect(() => {
    setDayIdx(initialDayIndex());
  }, []);

  const day = CALENDAR[dayIdx];
  const mobileStage = STAGE_ORDER[stageIdx];
  const intel = useMemo(() => dayIntel(day), [day]);

  return (
    <div className="shows-root">
      {/* ── Cabeçalho fixo ── */}
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

        {/* Faixa de inteligência do dia */}
        <div className="shows-intel">
          <Kpi label="Pessoas esperadas" value={`≈ ${(intel.capacity / 1000).toFixed(0)} 000`} />
          <Kpi label="Pico de afluência" value={`${intel.peakStart}–${intel.peakEnd}`} />
          <Kpi label="Género dominante" value={`${intel.femAvg}% ♀ · ${100 - intel.femAvg}% ♂`} />
          <Kpi label="Pressão WC máxima" value={intel.maxPressure.label} tone={intel.maxPressure.tone} />
        </div>

        {/* Tabs de palco — só mobile */}
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

      {/* ── Conteúdo com scroll interno suave ── */}
      <div className="shows-scroll">
        <div className="shows-grid">
          {STAGE_ORDER.map((stage) => (
            <section
              key={stage}
              className={`shows-col ${stage === mobileStage ? 'is-mobile-active' : ''}`}
              aria-label={STAGE_LABEL[stage]}
            >
              <div className="shows-col-head">{STAGE_LABEL[stage]}</div>
              <ol className="shows-list">
                {day.stages[stage].map((show, i) => {
                  const arch = ARCHETYPES[show.archetype];
                  const pr = pressureLabel(arch.surge);
                  const peakStart = fmtMinutes(toMinutes(show.time, show.nextDay) - arch.pre);
                  const peakEnd = fmtMinutes(toMinutes(show.time, show.nextDay) + 75 + 25);
                  return (
                    <li
                      key={`${stage}-${i}`}
                      className={`shows-item ${show.headliner ? 'is-headliner' : ''}`}
                    >
                      <div className="shows-time">
                        {show.time}
                        {show.nextDay && <span className="shows-nextday">+1</span>}
                        {!show.headliner && (
                          <span className={`shows-dot tone-${pr.tone}`} title={`Pressão WC: ${pr.label}`} />
                        )}
                      </div>

                      {show.headliner && <div className="shows-hl-label">Headliner</div>}
                      <div className="shows-artist">{show.artist}</div>

                      {show.headliner && (
                        <div className="shows-wc">
                          <div className="shows-wc-row">
                            <span className="shows-wc-key">Pressão WC</span>
                            <span className={`shows-wc-val tone-${pr.tone}`}>{pr.label}</span>
                          </div>
                          <div className="shows-wc-row">
                            <span className="shows-wc-key">Vai a</span>
                            <span className="shows-wc-val">{arch.wc.join(' · ')}</span>
                          </div>
                          <div className="shows-wc-row">
                            <span className="shows-wc-key">Pico</span>
                            <span className="shows-wc-val">{peakStart}–{peakEnd}</span>
                          </div>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ol>
            </section>
          ))}
        </div>
      </div>

      <style jsx>{`
        .shows-root {
          position: fixed;
          top: var(--topbar-h, 72px);
          left: 0; right: 0; bottom: 0;
          display: flex;
          flex-direction: column;
          background: #ffffff;
          color: #0d1a0f;
          overflow: hidden;
        }

        /* Header */
        .shows-header {
          flex-shrink: 0;
          padding: clamp(14px, 2vw, 26px) clamp(18px, 4vw, 56px) clamp(10px, 1.2vw, 16px);
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
          font-size: 10px; font-weight: 500; letter-spacing: 0.16em;
          text-transform: uppercase; color: #a4a89c;
        }
        .shows-title {
          font-size: clamp(24px, 3.2vw, 46px); font-weight: 200;
          letter-spacing: -0.035em; line-height: 1; margin: 6px 0 4px; color: #0d1a0f;
        }
        .shows-theme {
          font-size: clamp(12px, 1.2vw, 15px); font-weight: 500; color: #4a7c59;
        }
        .shows-daytabs { display: flex; gap: 6px; }
        .shows-daytab {
          display: flex; flex-direction: column; align-items: center; gap: 2px;
          background: transparent; border: 1px solid #ece7d6; border-radius: 12px;
          padding: clamp(7px, 0.9vw, 11px) clamp(10px, 1.3vw, 17px);
          cursor: pointer; font-family: inherit; color: #0d1a0f;
          transition: background 0.16s, border-color 0.16s, color 0.16s;
        }
        .shows-daytab:hover { border-color: #4a7c59; }
        .shows-daytab.is-active { background: #1b3a21; border-color: #1b3a21; color: #fff; }
        .shows-daytab-id { font-size: clamp(13px, 1.1vw, 16px); font-weight: 600; letter-spacing: -0.01em; }
        .shows-daytab-date { font-size: 10px; font-weight: 500; letter-spacing: 0.04em; opacity: 0.7; }

        /* Faixa de inteligência */
        .shows-intel {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: clamp(10px, 2vw, 32px);
          margin-top: clamp(12px, 1.6vw, 20px);
          padding-top: clamp(12px, 1.6vw, 18px);
          border-top: 1px solid #ece7d6;
        }

        .shows-stagetabs { display: none; gap: 6px; margin-top: 14px; }
        .shows-stagetab {
          flex: 1; background: transparent; border: 1px solid #ece7d6; border-radius: 10px;
          padding: 9px 8px; font-size: 12px; font-weight: 500; letter-spacing: 0.04em;
          cursor: pointer; font-family: inherit; color: #0d1a0f;
          transition: background 0.16s, border-color 0.16s, color 0.16s;
        }
        .shows-stagetab.is-active { background: #1b3a21; border-color: #1b3a21; color: #fff; }

        /* Scroll interno */
        .shows-scroll {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          overflow-x: hidden;
          scrollbar-width: thin;
          scrollbar-color: #ece7d6 transparent;
        }
        .shows-scroll::-webkit-scrollbar { width: 8px; }
        .shows-scroll::-webkit-scrollbar-thumb { background: #ece7d6; border-radius: 4px; }
        .shows-scroll::-webkit-scrollbar-track { background: transparent; }

        .shows-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1px;
          background: #ece7d6;
          /* padding inferior para nunca ficar atras da searchbar global */
          padding-bottom: 120px;
        }
        .shows-col {
          background: #ffffff;
          padding: clamp(14px, 1.8vw, 26px) clamp(16px, 2.2vw, 36px) 0;
          display: flex; flex-direction: column;
        }
        .shows-col-head {
          font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase;
          color: #a4a89c; padding-bottom: clamp(8px, 1.2vw, 14px);
          margin-bottom: clamp(8px, 1.2vw, 14px); border-bottom: 1px solid #ece7d6;
          position: sticky; top: 0; background: #fff; z-index: 1;
        }
        .shows-list { list-style: none; margin: 0; padding: 0; }
        .shows-item { padding: clamp(8px, 1vw, 14px) 0; }
        .shows-time {
          font-size: clamp(12px, 1vw, 14px); font-weight: 500; color: #a4a89c;
          font-variant-numeric: tabular-nums; font-feature-settings: 'tnum'; letter-spacing: 0.02em;
          display: flex; align-items: center; gap: 8px;
        }
        .shows-nextday {
          font-size: 9px; font-weight: 600; letter-spacing: 0.08em; color: #c9a961;
          border: 1px solid #c9a961; border-radius: 4px; padding: 0 4px; line-height: 1.5;
        }
        .shows-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
        .shows-dot.tone-ok { background: #4a7c59; }
        .shows-dot.tone-warn { background: #c9a961; }
        .shows-dot.tone-crit { background: #c25a1a; }
        .shows-hl-label {
          font-size: 9px; font-weight: 600; letter-spacing: 0.16em; text-transform: uppercase;
          color: #4a7c59; margin-top: 5px;
        }
        .shows-artist {
          font-size: clamp(15px, 1.4vw, 21px); font-weight: 400; letter-spacing: -0.015em;
          line-height: 1.15; color: #0d1a0f; margin-top: 3px;
        }
        .shows-item.is-headliner .shows-artist {
          font-size: clamp(22px, 2.3vw, 34px); font-weight: 600; letter-spacing: -0.025em;
          text-transform: uppercase; color: #1b3a21;
        }

        /* Bloco de inteligência WC do headliner */
        .shows-wc {
          margin-top: 12px;
          border: 1px solid #ece7d6;
          border-radius: 12px;
          padding: clamp(10px, 1.2vw, 16px);
          background: #fcfcf9;
          display: flex; flex-direction: column; gap: 7px;
        }
        .shows-wc-row {
          display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
        }
        .shows-wc-key {
          font-size: 10px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase;
          color: #a4a89c; flex-shrink: 0;
        }
        .shows-wc-val {
          font-size: clamp(12px, 1.1vw, 14px); font-weight: 600; color: #0d1a0f;
          text-align: right; font-variant-numeric: tabular-nums;
        }
        .shows-wc-val.tone-ok { color: #4a7c59; }
        .shows-wc-val.tone-warn { color: #c9a961; }
        .shows-wc-val.tone-crit { color: #c25a1a; }

        /* Mobile */
        @media (max-width: 760px) {
          .shows-stagetabs { display: flex; }
          .shows-intel { grid-template-columns: repeat(2, 1fr); }
          .shows-grid { grid-template-columns: 1fr; gap: 0; background: #fff; }
          .shows-col { display: none; }
          .shows-col.is-mobile-active { display: flex; }
          .shows-daytab-date { display: none; }
        }
      `}</style>
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: 'ok' | 'warn' | 'crit' }) {
  const color = tone === 'crit' ? '#c25a1a' : tone === 'warn' ? '#c9a961' : '#0d1a0f';
  return (
    <div>
      <div
        style={{
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: '#a4a89c',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 'clamp(16px, 1.7vw, 24px)',
          fontWeight: 600,
          letterSpacing: '-0.02em',
          color,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {value}
      </div>
    </div>
  );
}
