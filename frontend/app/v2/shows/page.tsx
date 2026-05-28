'use client';

import { useEffect, useMemo, useState } from 'react';

/* ════════════════════════════════════════════════════════════════════
   1 · DADOS ESTÁTICOS
   ════════════════════════════════════════════════════════════════════ */

interface Archetype {
  f: number;          // % feminino
  flow: 'BAIXA' | 'MEDIA' | 'ALTA' | 'EXTREMA';
  pre: number;        // minutos antes do fim em que começa o pico
  surge: number;      // multiplicador de pressão
  wc: string[];       // WCs prioritários (top 3)
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

interface WcMeta {
  id: string;
  zone: string;
  capF: number;   // lugares femininos (ou 0)
  capM: number;   // lugares masculinos (ou 0)
  unisex: boolean;
  total: number;
  dist: number;   // metros ao portão
}

const WCS: WcMeta[] = [
  { id: 'WC-01', zone: 'Portal Norte', capF: 63, capM: 72, unisex: false, total: 135, dist: 130 },
  { id: 'WC-02', zone: 'Central',      capF: 72, capM: 54, unisex: false, total: 126, dist: 74 },
  { id: 'WC-03', zone: 'Portão',       capF: 48, capM: 54, unisex: false, total: 102, dist: 33 },
  { id: 'WC-04', zone: 'Cumeada',      capF: 66, capM: 84, unisex: false, total: 150, dist: 69 },
  { id: 'WC-05', zone: 'Portão',       capF: 0,  capM: 0,  unisex: true,  total: 133, dist: 24 },
  { id: 'WC-06', zone: 'Central',      capF: 0,  capM: 0,  unisex: true,  total: 208, dist: 267 },
  { id: 'WC-07', zone: 'Lockers',      capF: 54, capM: 84, unisex: false, total: 138, dist: 94 },
  { id: 'WC-08', zone: 'Exterior',     capF: 61, capM: 84, unisex: false, total: 145, dist: 364 },
];

interface Show {
  time: string;
  artist: string;
  archetype: string;
  stage: 'PM' | 'PMV' | 'PSB';
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
  shows: Show[];
}

const STAGE_LABEL: Record<string, string> = {
  PM: 'Palco Mundo',
  PMV: 'Music Valley',
  PSB: 'Super Bock',
};

function buildDay(
  base: Omit<Day, 'shows'>,
  pm: Show[],
  pmv: Show[],
  psb: Show[],
): Day {
  const tag = (arr: Show[], stage: Show['stage']) => arr.map((s) => ({ ...s, stage }));
  return { ...base, shows: [...tag(pm, 'PM'), ...tag(pmv, 'PMV'), ...tag(psb, 'PSB')] };
}

const CALENDAR: Day[] = [
  buildDay(
    { id: 'D1', date: '2026-06-20', dateLabel: '20 Junho', weekday: 'Sábado', theme: 'Pop · Global', capacity: 100000 },
    [
      { time: '17:00', artist: 'Calema', archetype: 'POP_LATAM', stage: 'PM' },
      { time: '19:00', artist: 'Pedro Sampaio', archetype: 'POP_FUNK_BR', stage: 'PM' },
      { time: '21:15', artist: 'Charlie Puth', archetype: 'POP_GLOBAL', stage: 'PM' },
      { time: '23:15', artist: 'Katy Perry', archetype: 'POP_GLOBAL', stage: 'PM', headliner: true },
    ],
    [
      { time: '18:00', artist: 'Maninho', archetype: 'POP_PT', stage: 'PMV' },
      { time: '20:15', artist: 'Nena', archetype: 'POP_PT', stage: 'PMV' },
      { time: '22:15', artist: 'Audrey Nuna', archetype: 'KCROSS_POP', stage: 'PMV' },
      { time: '01:00', artist: 'Alok', archetype: 'EDM_LATE', stage: 'PMV', headliner: true, nextDay: true },
    ],
    [
      { time: '16:00', artist: 'Sofia Camara', archetype: 'POP_PT', stage: 'PSB' },
      { time: '18:00', artist: 'Napa', archetype: 'POP_PT', stage: 'PSB' },
      { time: '20:15', artist: 'Bebe Rexha', archetype: 'POP_GLOBAL', stage: 'PSB' },
      { time: '22:15', artist: 'Bárbara Bandeira', archetype: 'POP_PT', stage: 'PSB', headliner: true },
    ],
  ),
  buildDay(
    { id: 'D2', date: '2026-06-21', dateLabel: '21 Junho', weekday: 'Domingo', theme: 'Rock · Pesado', capacity: 100000 },
    [
      { time: '17:00', artist: 'Grandson', archetype: 'ROCK_ALT', stage: 'PM' },
      { time: '19:00', artist: 'The Pretty Reckless', archetype: 'ROCK_HEAVY', stage: 'PM' },
      { time: '21:15', artist: 'Cypress Hill', archetype: 'HIPHOP_INTL', stage: 'PM' },
      { time: '23:15', artist: 'Linkin Park', archetype: 'ROCK_HEAVY', stage: 'PM', headliner: true },
    ],
    [
      { time: '16:00', artist: 'Dealema', archetype: 'HIPHOP_PT', stage: 'PMV' },
      { time: '18:00', artist: 'Sam the Kid + Orquestra & Orelha Negra', archetype: 'HIPHOP_PT', stage: 'PMV' },
      { time: '20:15', artist: 'P.O.D.', archetype: 'ROCK_HEAVY', stage: 'PMV' },
      { time: '22:15', artist: 'Sepultura', archetype: 'ROCK_HEAVY', stage: 'PMV', headliner: true },
    ],
    [
      { time: '16:00', artist: 'Tara Perdida', archetype: 'ROCK_PT', stage: 'PSB' },
      { time: '18:00', artist: 'Blasted Mechanism', archetype: 'ROCK_PT', stage: 'PSB' },
      { time: '20:15', artist: 'Kaiser Chiefs', archetype: 'ROCK_ALT', stage: 'PSB' },
      { time: '22:15', artist: 'Hoobastank', archetype: 'ROCK_HEAVY', stage: 'PSB', headliner: true },
    ],
  ),
  buildDay(
    { id: 'D3', date: '2026-06-27', dateLabel: '27 Junho', weekday: 'Sábado', theme: 'Lendas · Clássicos', capacity: 95000 },
    [
      { time: '17:00', artist: '4 Non Blondes', archetype: 'LEGENDS_INTL', stage: 'PM' },
      { time: '19:00', artist: 'Shaggy', archetype: 'REGGAE', stage: 'PM' },
      { time: '21:15', artist: 'Cyndi Lauper', archetype: 'LEGENDS_INTL', stage: 'PM' },
      { time: '23:15', artist: 'Rod Stewart', archetype: 'LEGENDS_INTL', stage: 'PM', headliner: true },
    ],
    [
      { time: '16:00', artist: 'Jafumega', archetype: 'LEGENDS_PT', stage: 'PMV' },
      { time: '18:00', artist: 'UHF', archetype: 'LEGENDS_PT', stage: 'PMV' },
      { time: '20:15', artist: 'GNR', archetype: 'LEGENDS_PT', stage: 'PMV' },
      { time: '22:15', artist: 'Xutos & Pontapés', archetype: 'LEGENDS_PT', stage: 'PMV', headliner: true },
    ],
    [
      { time: '15:00', artist: 'Syro', archetype: 'SOUL_RNB', stage: 'PSB' },
      { time: '18:00', artist: 'The Wailers', archetype: 'REGGAE', stage: 'PSB' },
      { time: '20:15', artist: 'Joss Stone', archetype: 'SOUL_RNB', stage: 'PSB' },
      { time: '22:15', artist: 'Belo', archetype: 'POP_LATAM', stage: 'PSB', headliner: true },
    ],
  ),
  buildDay(
    { id: 'D4', date: '2026-06-28', dateLabel: '28 Junho', weekday: 'Domingo', theme: 'Urbano · Hip-Hop', capacity: 100000 },
    [
      { time: '17:00', artist: 'Matuê', archetype: 'HIPHOP_INTL', stage: 'PM' },
      { time: '19:00', artist: 'Rema', archetype: 'AFROBEATS', stage: 'PM' },
      { time: '21:15', artist: 'Central Cee', archetype: 'HIPHOP_INTL', stage: 'PM' },
      { time: '23:15', artist: '21 Savage', archetype: 'HIPHOP_INTL', stage: 'PM', headliner: true },
    ],
    [
      { time: '18:00', artist: 'Irina Barros', archetype: 'SOUL_RNB', stage: 'PMV' },
      { time: '20:15', artist: 'Carlão', archetype: 'HIPHOP_PT', stage: 'PMV' },
      { time: '22:15', artist: 'Filipe Ret', archetype: 'HIPHOP_INTL', stage: 'PMV' },
      { time: '01:00', artist: 'Dennis', archetype: 'POP_FUNK_BR', stage: 'PMV', headliner: true, nextDay: true },
    ],
    [
      { time: '16:00', artist: 'Karetus', archetype: 'EDM_LATE', stage: 'PSB' },
      { time: '18:00', artist: 'Valete', archetype: 'HIPHOP_PT', stage: 'PSB' },
      { time: '20:15', artist: 'Lola Índigo', archetype: 'POP_GLOBAL', stage: 'PSB' },
      { time: '22:15', artist: 'CeeLo Green', archetype: 'SOUL_RNB', stage: 'PSB', headliner: true },
    ],
  ),
];

/* ════════════════════════════════════════════════════════════════════
   2 · MODELO DE DISTRIBUIÇÃO (determinístico, puro)
   ════════════════════════════════════════════════════════════════════ */

function toMinutes(time: string, nextDay?: boolean): number {
  const [h, m] = time.split(':').map(Number);
  return (h + (nextDay ? 24 : 0)) * 60 + m;
}
function fmtMinutes(total: number): string {
  const h = Math.floor((total % (24 * 60)) / 60);
  const m = total % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/* Fração da capacidade presente no recinto à hora do show.
   Curva: sobe das 14h, máximo na hora do headliner do Palco Mundo, decai. */
function crowdFraction(day: Day, showMinutes: number): number {
  const pmHead =
    day.shows.find((s) => s.stage === 'PM' && s.headliner) ||
    day.shows.filter((s) => s.stage === 'PM').slice(-1)[0];
  const peak = toMinutes(pmHead.time, pmHead.nextDay);
  const sigma = 190; // largura da curva em minutos
  const d = showMinutes - peak;
  const gauss = Math.exp(-(d * d) / (2 * sigma * sigma));
  // base mínima 0.15 (doors), máximo 1.0 no pico
  return 0.15 + 0.85 * gauss;
}

const MAX_SURGE = 4.2; // HIPHOP_INTL

interface WcLoad {
  id: string;
  zone: string;
  unisex: boolean;
  weight: number;
  occPct: number;     // 0..100+
  people: number;     // pessoas a usar no pico (estimativa)
  status: 'ok' | 'warn' | 'crit';
  priorityRank: number; // 0 = não prioritário, 1..3 = posição na lista do arquétipo
}

interface Distribution {
  loads: WcLoad[];     // ordenado por occPct desc
  presentes: number;   // pessoas no recinto à hora
  pressure: { label: string; tone: 'ok' | 'warn' | 'crit' };
  peakWindow: string;
  femPct: number;
}

function pressureLabel(surge: number): { label: string; tone: 'ok' | 'warn' | 'crit' } {
  if (surge >= 4.0) return { label: 'Extrema', tone: 'crit' };
  if (surge >= 3.4) return { label: 'Alta', tone: 'warn' };
  if (surge >= 2.8) return { label: 'Média-alta', tone: 'warn' };
  return { label: 'Moderada', tone: 'ok' };
}

function statusOf(occ: number): 'ok' | 'warn' | 'crit' {
  if (occ >= 85) return 'crit';
  if (occ >= 65) return 'warn';
  return 'ok';
}

function computeDistribution(show: Show, day: Day): Distribution {
  const arch = ARCHETYPES[show.archetype];
  const showMin = toMinutes(show.time, show.nextDay);
  const frac = crowdFraction(day, showMin);
  const presentes = Math.round(day.capacity * frac);
  const femPct = arch.f;
  const malePct = 100 - arch.f;

  // peso por WC
  const weighted = WCS.map((wc) => {
    // 1. base = capacidade
    const base = wc.total;

    // 2. ajuste de género
    let gfit: number;
    if (wc.unisex) {
      gfit = 1.0;
    } else {
      const fShare = wc.capF / wc.total;
      const mShare = wc.capM / wc.total;
      // quão bem a oferta de género do WC encaixa na procura do público
      gfit = (femPct / 100) * fShare * 2 + (malePct / 100) * mShare * 2;
    }

    // 3. boost de prioridade do arquétipo
    const idx = arch.wc.indexOf(wc.id);
    const prio = idx === 0 ? 1.6 : idx === 1 ? 1.35 : idx === 2 ? 1.18 : 1.0;

    // 4. penalização por distância (suave)
    const distFactor = 1 / (1 + wc.dist / 420);

    const weight = base * gfit * prio * distFactor;
    return { wc, weight, priorityRank: idx === -1 ? 0 : idx + 1 };
  });

  const maxW = Math.max(...weighted.map((w) => w.weight));

  // intensidade global do pico deste show (0..1)
  const intensity = Math.min(1, frac * (arch.surge / MAX_SURGE) * 1.25);
  const peakOcc = 96 * intensity; // ocupação do WC mais carregado

  // procura total de WC neste pico (pessoas)
  const wcSeekers = Math.round(presentes * 0.07 * (arch.surge / MAX_SURGE));

  const loads: WcLoad[] = weighted.map(({ wc, weight, priorityRank }) => {
    const rel = weight / maxW;
    const occPct = Math.round(peakOcc * rel);
    const people = Math.round(wcSeekers * (weight / weighted.reduce((a, w) => a + w.weight, 0)));
    return {
      id: wc.id,
      zone: wc.zone,
      unisex: wc.unisex,
      weight,
      occPct,
      people,
      status: statusOf(occPct),
      priorityRank,
    };
  });

  loads.sort((a, b) => b.occPct - a.occPct);

  const showEnd = showMin + 75;
  const peakWindow = `${fmtMinutes(showMin - arch.pre)}–${fmtMinutes(showEnd + 25)}`;

  return {
    loads,
    presentes,
    pressure: pressureLabel(arch.surge),
    peakWindow,
    femPct,
  };
}

/* ════════════════════════════════════════════════════════════════════
   3 · COMPONENTE
   ════════════════════════════════════════════════════════════════════ */

function initialDayIndex(): number {
  const today = new Date().toISOString().slice(0, 10);
  const idx = CALENDAR.findIndex((d) => d.date >= today);
  return idx === -1 ? 0 : idx;
}

function showKey(s: Show): string {
  return `${s.stage}-${s.time}-${s.artist}`;
}

export default function ShowsPage() {
  const [dayIdx, setDayIdx] = useState(0);
  const [selKey, setSelKey] = useState<string | null>(null);

  useEffect(() => {
    setDayIdx(initialDayIndex());
  }, []);

  const day = CALENDAR[dayIdx];

  // shows ordenados por hora (nextDay vai para o fim)
  const ordered = useMemo(
    () => [...day.shows].sort((a, b) => toMinutes(a.time, a.nextDay) - toMinutes(b.time, b.nextDay)),
    [day],
  );

  // selecção default: o headliner do Palco Mundo
  useEffect(() => {
    const pmHead = day.shows.find((s) => s.stage === 'PM' && s.headliner) || ordered[ordered.length - 1];
    setSelKey(showKey(pmHead));
  }, [day, ordered]);

  const selected = ordered.find((s) => showKey(s) === selKey) || ordered[0];
  const dist = useMemo(() => (selected ? computeDistribution(selected, day) : null), [selected, day]);

  return (
    <div className="sh-root">
      {/* Header */}
      <header className="sh-header">
        <div className="sh-head-row">
          <div>
            <div className="sh-eyebrow">Distribuição de WC por show · Rock in Rio Lisboa 2026</div>
            <h1 className="sh-title">{day.weekday}, {day.dateLabel}</h1>
            <div className="sh-theme">{day.theme} · ≈ {(day.capacity / 1000).toFixed(0)} 000 pessoas/dia</div>
          </div>
          <nav className="sh-daytabs" aria-label="Dias">
            {CALENDAR.map((d, i) => (
              <button key={d.id} className={`sh-daytab ${i === dayIdx ? 'is-active' : ''}`} onClick={() => setDayIdx(i)}>
                <span className="sh-daytab-id">{d.id}</span>
                <span className="sh-daytab-date">{d.dateLabel}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Corpo: timeline (esq) + distribuição (dir) */}
      <div className="sh-body">
        {/* TIMELINE clicável */}
        <aside className="sh-timeline">
          <div className="sh-col-head">Programa · toca para ver a distribuição</div>
          <ol className="sh-shows">
            {ordered.map((s) => {
              const arch = ARCHETYPES[s.archetype];
              const pr = pressureLabel(arch.surge);
              const active = showKey(s) === selKey;
              return (
                <li key={showKey(s)}>
                  <button
                    className={`sh-show ${active ? 'is-active' : ''}`}
                    onClick={() => setSelKey(showKey(s))}
                  >
                    <span className="sh-show-time">
                      {s.time}{s.nextDay && <span className="sh-nextday">+1</span>}
                    </span>
                    <span className="sh-show-main">
                      <span className={`sh-show-artist ${s.headliner ? 'is-hl' : ''}`}>{s.artist}</span>
                      <span className="sh-show-stage">{STAGE_LABEL[s.stage]}</span>
                    </span>
                    <span className={`sh-show-dot tone-${pr.tone}`} title={`Pressão WC: ${pr.label}`} />
                  </button>
                </li>
              );
            })}
          </ol>
        </aside>

        {/* DISTRIBUIÇÃO dos 8 WC */}
        <section className="sh-dist">
          {selected && dist && (
            <>
              <div className="sh-dist-head">
                <div>
                  <div className="sh-col-head">Distribuição prevista pelos 8 banheiros</div>
                  <div className="sh-dist-show">
                    <span className={selected.headliner ? 'is-hl' : ''}>{selected.artist}</span>
                    <span className="sh-dist-meta">{selected.time} · {STAGE_LABEL[selected.stage]}</span>
                  </div>
                </div>
                <div className="sh-dist-kpis">
                  <Kpi label="Presentes" value={`≈ ${(dist.presentes / 1000).toFixed(0)}k`} />
                  <Kpi label="Género" value={`${dist.femPct}♀ ${100 - dist.femPct}♂`} />
                  <Kpi label="Pressão" value={dist.pressure.label} tone={dist.pressure.tone} />
                  <Kpi label="Pico" value={dist.peakWindow} />
                </div>
              </div>

              <ol className="sh-bars">
                {dist.loads.map((l) => (
                  <li key={l.id} className="sh-bar-row">
                    <div className="sh-bar-id">
                      <span className="sh-bar-name">{l.id}</span>
                      <span className="sh-bar-zone">
                        {l.unisex ? 'unissexo' : l.zone}
                        {l.priorityRank > 0 && <span className="sh-bar-prio"> · prioritário</span>}
                      </span>
                    </div>
                    <div className="sh-bar-track">
                      <div className={`sh-bar-fill tone-${l.status}`} style={{ width: `${Math.min(100, l.occPct)}%` }} />
                    </div>
                    <div className={`sh-bar-pct tone-${l.status}`}>{l.occPct}%</div>
                  </li>
                ))}
              </ol>

              <div className="sh-legend">
                <span><i className="dot tone-ok" /> &lt; 65% folgado</span>
                <span><i className="dot tone-warn" /> 65–84% atenção</span>
                <span><i className="dot tone-crit" /> ≥ 85% crítico</span>
              </div>
            </>
          )}
        </section>
      </div>

      <style jsx>{`
        .sh-root {
          position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0;
          display: flex; flex-direction: column; background: #fff; color: #0d1a0f; overflow: hidden;
        }
        /* Header */
        .sh-header { flex-shrink: 0; padding: clamp(14px,2vw,24px) clamp(18px,4vw,56px) clamp(12px,1.4vw,18px); border-bottom: 1px solid #ece7d6; }
        .sh-head-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; flex-wrap: wrap; }
        .sh-eyebrow { font-size: 10px; font-weight: 500; letter-spacing: 0.16em; text-transform: uppercase; color: #a4a89c; }
        .sh-title { font-size: clamp(22px,3vw,42px); font-weight: 200; letter-spacing: -0.035em; line-height: 1; margin: 6px 0 4px; }
        .sh-theme { font-size: clamp(12px,1.2vw,15px); font-weight: 500; color: #4a7c59; }
        .sh-daytabs { display: flex; gap: 6px; }
        .sh-daytab { display: flex; flex-direction: column; align-items: center; gap: 2px; background: transparent; border: 1px solid #ece7d6; border-radius: 12px; padding: clamp(7px,0.9vw,11px) clamp(10px,1.3vw,17px); cursor: pointer; font-family: inherit; color: #0d1a0f; transition: all 0.16s; }
        .sh-daytab:hover { border-color: #4a7c59; }
        .sh-daytab.is-active { background: #1b3a21; border-color: #1b3a21; color: #fff; }
        .sh-daytab-id { font-size: clamp(13px,1.1vw,16px); font-weight: 600; letter-spacing: -0.01em; }
        .sh-daytab-date { font-size: 10px; font-weight: 500; letter-spacing: 0.04em; opacity: 0.7; }

        /* Corpo */
        .sh-body { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(280px, 360px) 1fr; }
        .sh-col-head { font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: #a4a89c; margin-bottom: clamp(8px,1.2vw,14px); }

        /* Timeline */
        .sh-timeline { border-right: 1px solid #ece7d6; padding: clamp(14px,1.8vw,24px) clamp(14px,1.6vw,22px) 120px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #ece7d6 transparent; }
        .sh-timeline::-webkit-scrollbar { width: 7px; }
        .sh-timeline::-webkit-scrollbar-thumb { background: #ece7d6; border-radius: 4px; }
        .sh-shows { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
        .sh-show { width: 100%; display: flex; align-items: center; gap: 12px; background: transparent; border: 1px solid transparent; border-radius: 12px; padding: 11px 12px; cursor: pointer; font-family: inherit; text-align: left; transition: background 0.14s, border-color 0.14s; }
        .sh-show:hover { background: #fafaf7; }
        .sh-show.is-active { background: #f3f6f3; border-color: #1b3a21; }
        .sh-show-time { font-size: 12px; font-weight: 600; color: #a4a89c; font-variant-numeric: tabular-nums; min-width: 42px; display: flex; align-items: center; gap: 4px; }
        .sh-nextday { font-size: 8px; font-weight: 700; color: #c9a961; border: 1px solid #c9a961; border-radius: 3px; padding: 0 3px; }
        .sh-show-main { flex: 1; display: flex; flex-direction: column; gap: 1px; min-width: 0; }
        .sh-show-artist { font-size: clamp(14px,1.2vw,16px); font-weight: 400; color: #0d1a0f; letter-spacing: -0.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .sh-show-artist.is-hl { font-weight: 600; color: #1b3a21; }
        .sh-show-stage { font-size: 10px; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase; color: #a4a89c; }
        .sh-show-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

        /* Distribuição */
        .sh-dist { padding: clamp(16px,2vw,30px) clamp(18px,2.6vw,44px) 120px; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #ece7d6 transparent; }
        .sh-dist::-webkit-scrollbar { width: 7px; }
        .sh-dist::-webkit-scrollbar-thumb { background: #ece7d6; border-radius: 4px; }
        .sh-dist-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; flex-wrap: wrap; margin-bottom: clamp(16px,2vw,28px); }
        .sh-dist-show { font-size: clamp(20px,2.4vw,32px); font-weight: 400; letter-spacing: -0.025em; display: flex; flex-direction: column; gap: 2px; margin-top: 4px; }
        .sh-dist-show .is-hl { font-weight: 600; color: #1b3a21; text-transform: uppercase; }
        .sh-dist-meta { font-size: 13px; font-weight: 500; color: #a4a89c; letter-spacing: 0.01em; }
        .sh-dist-kpis { display: grid; grid-template-columns: repeat(4, auto); gap: clamp(12px,1.6vw,26px); }

        .sh-bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: clamp(8px,1vw,14px); }
        .sh-bar-row { display: grid; grid-template-columns: clamp(96px,12vw,150px) 1fr clamp(46px,5vw,64px); align-items: center; gap: clamp(10px,1.4vw,20px); }
        .sh-bar-id { display: flex; flex-direction: column; gap: 1px; }
        .sh-bar-name { font-size: clamp(14px,1.3vw,18px); font-weight: 600; letter-spacing: -0.01em; }
        .sh-bar-zone { font-size: 10px; font-weight: 500; color: #a4a89c; letter-spacing: 0.02em; }
        .sh-bar-prio { color: #4a7c59; }
        .sh-bar-track { height: clamp(16px,1.8vw,26px); background: #f3f1e8; border-radius: 6px; overflow: hidden; }
        .sh-bar-fill { height: 100%; border-radius: 6px; transition: width 0.5s cubic-bezier(0.32,0.72,0,1); }
        .sh-bar-fill.tone-ok { background: #1b3a21; }
        .sh-bar-fill.tone-warn { background: #c9a961; }
        .sh-bar-fill.tone-crit { background: #c25a1a; }
        .sh-bar-pct { font-size: clamp(15px,1.5vw,21px); font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
        .sh-bar-pct.tone-ok { color: #0d1a0f; }
        .sh-bar-pct.tone-warn { color: #c9a961; }
        .sh-bar-pct.tone-crit { color: #c25a1a; }

        .sh-legend { display: flex; gap: 20px; margin-top: clamp(16px,2vw,26px); padding-top: 14px; border-top: 1px solid #ece7d6; font-size: 11px; color: #a4a89c; flex-wrap: wrap; }
        .sh-legend .dot, .sh-show-dot.tone-ok, .tone-ok .dot { }
        .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; }
        .tone-ok { }
        .sh-show-dot.tone-ok, .dot.tone-ok { background: #4a7c59; }
        .sh-show-dot.tone-warn, .dot.tone-warn { background: #c9a961; }
        .sh-show-dot.tone-crit, .dot.tone-crit { background: #c25a1a; }

        @media (max-width: 860px) {
          .sh-body { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
          .sh-timeline { border-right: none; border-bottom: 1px solid #ece7d6; max-height: 38vh; padding-bottom: 16px; }
          .sh-dist-kpis { grid-template-columns: repeat(2, auto); }
          .sh-daytab-date { display: none; }
        }
      `}</style>
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: 'ok' | 'warn' | 'crit' }) {
  const color = tone === 'crit' ? '#c25a1a' : tone === 'warn' ? '#c9a961' : '#0d1a0f';
  return (
    <div>
      <div style={{ fontSize: 9.5, fontWeight: 500, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#a4a89c', marginBottom: 3 }}>
        {label}
      </div>
      <div style={{ fontSize: 'clamp(14px,1.5vw,20px)', fontWeight: 600, letterSpacing: '-0.02em', color, fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
    </div>
  );
}
