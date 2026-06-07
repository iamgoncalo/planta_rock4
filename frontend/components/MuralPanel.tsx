'use client';

import { useEffect, useRef, useState } from 'react';
import type { ClusterId, ClusterState, PanelData } from '@/lib/mural-types';
import { CLUSTER_COPY, CLUSTER_META, getPhrase, poolLength } from '@/lib/mural-copy';
import styles from './MuralPanel.module.css';

// ── Palette per cluster ──────────────────────────────────────────────────────
const PALETTE: Record<ClusterId, { bg: string; fg: string }> = {
  '01': { bg: '#EFE7D5', fg: '#28351C' },
  '02': { bg: '#D0DCC0', fg: '#4A3521' },
  '03': { bg: '#28351C', fg: '#EFE7D5' },
  '04': { bg: '#E5EAD8', fg: '#4A3521' },
  '05': { bg: '#4A3521', fg: '#EFE7D5' },
  '06': { bg: '#D8E2C5', fg: '#28351C' },
  '07': { bg: '#F2EBD8', fg: '#4A3521' },
  '08': { bg: '#28351C', fg: '#D0DCC0' },
};

const AMBER = '#C25A1A';
const ROTATE_MS = 11000;
const FADE_MS = 900;

// ── Sub-component: occupancy bar ─────────────────────────────────────────────
function OccBar({
  label,
  pct,
  isSolo,
}: {
  label: string;
  pct: number;
  isSolo: boolean;
}) {
  const isHigh = pct >= 80;
  const barH = isSolo ? '0.7vh' : '0.55vh';
  const fontSize = isSolo
    ? 'clamp(1.8vh, 2.2vh, 2.6vh)'
    : 'clamp(1.4vh, 1.6vh, 1.9vh)';

  return (
    <div
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={
        label === 'M'
          ? `ocupação homens: ${pct}%`
          : label === 'F'
          ? `ocupação mulheres: ${pct}%`
          : `ocupação: ${pct}%`
      }
      style={{
        display: 'grid',
        gridTemplateColumns: '2.6vw 1fr 4.2vw',
        alignItems: 'center',
        gap: '1vw',
        fontSize,
        fontWeight: 500,
        letterSpacing: '0.1em',
      }}
    >
      <span style={{ textTransform: 'uppercase', opacity: 0.72 }}>{label}</span>
      <div style={{ position: 'relative', height: barH }}>
        {/* track */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'currentColor',
            opacity: 0.14,
          }}
          aria-hidden="true"
        />
        {/* fill */}
        <div
          className={styles.barFill}
          style={{
            position: 'absolute',
            inset: '0 auto 0 0',
            width: `${pct}%`,
            background: isHigh ? AMBER : 'currentColor',
          }}
          aria-hidden="true"
        />
      </div>
      <span
        className={styles.barPct}
        style={{
          textAlign: 'right',
          fontVariantNumeric: 'tabular-nums',
          fontWeight: isHigh ? 600 : 500,
          letterSpacing: '0.04em',
          opacity: isHigh ? 1 : 0.85,
          color: isHigh ? AMBER : 'inherit',
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────
interface MuralPanelProps {
  id: ClusterId;
  data: PanelData | null;
  mode: 'mural' | 'solo';
  staggerDelayMs?: number;
}

export default function MuralPanel({
  id,
  data,
  mode,
  staggerDelayMs = 0,
}: MuralPanelProps) {
  const isSolo = mode === 'solo';
  const meta = CLUSTER_META[id];
  const palette = PALETTE[id];

  // ── Phrase state ────────────────────────────────────────────────────────────
  const [msg, setMsg] = useState<[string, string] | null>(null);
  const [fadingOut, setFadingOut] = useState(false);
  const msgStateRef = useRef<{ state: ClusterState; idx: number } | null>(null);
  const dataRef = useRef<PanelData | null>(data);
  const timerStartedRef = useRef(false);

  useEffect(() => {
    dataRef.current = data;
  }, [data]);

  // Initialize first phrase
  useEffect(() => {
    if (!data || msg !== null) return;
    const phrase = getPhrase(id, data.state, 0);
    msgStateRef.current = { state: data.state, idx: 0 };
    setMsg(phrase);
  }, [data, id, msg]);

  // Start rotation after stagger
  useEffect(() => {
    if (msg === null || timerStartedRef.current) return;
    timerStartedRef.current = true;

    let intervalId: ReturnType<typeof setInterval>;

    const staggerId = setTimeout(() => {
      const tick = () => {
        const d = dataRef.current;
        if (!d) return;

        const prev = msgStateRef.current;
        const stateChanged = !prev || prev.state !== d.state;
        const nextIdx = stateChanged ? 0 : (prev.idx + 1) % poolLength(id, d.state);

        msgStateRef.current = { state: d.state, idx: nextIdx };

        setFadingOut(true);
        setTimeout(() => {
          setMsg(getPhrase(id, d.state, nextIdx));
          setFadingOut(false);
        }, FADE_MS);
      };

      intervalId = setInterval(tick, ROTATE_MS);
    }, staggerDelayMs);

    return () => {
      clearTimeout(staggerId);
      clearInterval(intervalId);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msg !== null]);

  // ── Typography sizes (mural vs solo) ────────────────────────────────────────
  const sz = isSolo
    ? {
        padding: '4vh 3vw 3.5vh',
        wcId: 'clamp(3vh, 4vh, 5vh)',
        gender: 'clamp(2.4vh, 3vh, 3.6vh)',
        wait: 'clamp(2vh, 2.5vh, 3vh)',
        pt: 'clamp(5vh, 6.5vh, 8vh)',
        en: 'clamp(2.5vh, 3vh, 3.6vh)',
        bodyGap: '3.5vh',
        barsGap: '1.4vh',
        landmark: 'clamp(1.6vh, 2vh, 2.4vh)',
        footGap: '2.5vh',
      }
    : {
        padding: '3.2vh 2vw 2.8vh',
        wcId: 'clamp(1.7vh, 2vh, 2.4vh)',
        gender: 'clamp(1.4vh, 1.6vh, 1.9vh)',
        wait: 'clamp(1.5vh, 1.75vh, 2vh)',
        pt: 'clamp(2.5vh, 3.4vh, 4.2vh)',
        en: 'clamp(1.7vh, 2vh, 2.4vh)',
        bodyGap: '2vh',
        barsGap: '0.9vh',
        landmark: 'clamp(1.2vh, 1.4vh, 1.6vh)',
        footGap: '1.6vh',
      };

  const isOffline = data === null;

  return (
    <section
      className={styles.panel}
      style={{
        background: palette.bg,
        color: palette.fg,
        padding: sz.padding,
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        fontFeatureSettings: "'ss01', 'cv11', 'tnum'",
        WebkitFontSmoothing: 'antialiased',
      }}
      role="region"
      aria-label={`${meta.labelPt} · ${meta.genderLabel}`}
    >
      {/* ambient gradient overlay */}
      <div
        className={`${styles.ambient} ${styles.inner}`}
        style={{
          background: `radial-gradient(circle at ${meta.ax} ${meta.ay}, rgba(255,255,255,0.06), transparent 55%)`,
        }}
        aria-hidden="true"
      />

      {/* ── HEADER ──────────────────────────────────────────────────────── */}
      <header
        className={styles.inner}
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto',
          alignItems: 'baseline',
          gap: '1vw',
          marginBottom: '1vh',
        }}
      >
        <div
          style={{
            fontSize: sz.wcId,
            fontWeight: 600,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {meta.labelPt}
          <span
            style={{
              marginLeft: '0.6vw',
              fontWeight: 400,
              opacity: 0.65,
              fontSize: sz.gender,
            }}
          >
            · {meta.genderLabel}
          </span>
        </div>
        <div
          style={{
            fontSize: sz.wait,
            fontWeight: 500,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            opacity: isOffline ? 0.4 : 0.72,
            fontVariantNumeric: 'tabular-nums',
            textAlign: 'right',
          }}
          aria-live="polite"
          aria-atomic="true"
        >
          {data === null
            ? '—'
            : data.wait_min === 0
            ? 'sem fila'
            : `${data.wait_min} min`}
        </div>
      </header>

      {/* ── BODY · phrase ───────────────────────────────────────────────── */}
      <div
        className={styles.inner}
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '2vh 0',
          minHeight: 0,
          gap: sz.bodyGap,
        }}
      >
        <p
          className={`${styles.phraseText} ${fadingOut ? styles.phraseOut : ''}`}
          lang="pt-PT"
          style={{
            fontSize: sz.pt,
            fontWeight: 400,
            lineHeight: 1.08,
            letterSpacing: '-0.022em',
            textWrap: 'balance' as React.CSSProperties['textWrap'],
            margin: 0,
          }}
        >
          {msg ? msg[0] : '—'}
        </p>
        <p
          className={`${styles.phraseText} ${fadingOut ? styles.phraseOut : ''}`}
          lang="en"
          style={{
            fontSize: sz.en,
            fontWeight: 300,
            fontStyle: 'italic',
            lineHeight: 1.2,
            opacity: 0.62,
            letterSpacing: '-0.005em',
            textWrap: 'balance' as React.CSSProperties['textWrap'],
            margin: 0,
          }}
        >
          {msg ? msg[1] : '—'}
        </p>
      </div>

      {/* ── FOOTER · bars + landmark ─────────────────────────────────────── */}
      <footer
        className={styles.inner}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: sz.footGap,
        }}
      >
        {/* occupancy bars */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: sz.barsGap }}>
          {data?.isUnissex ? (
            <OccBar label="●" pct={data.U_pct} isSolo={isSolo} />
          ) : (
            <>
              <OccBar label="M" pct={data?.M_pct ?? 0} isSolo={isSolo} />
              <OccBar label="F" pct={data?.F_pct ?? 0} isSolo={isSolo} />
            </>
          )}
        </div>

        {/* landmark */}
        <div
          style={{
            fontSize: sz.landmark,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            fontWeight: 500,
            opacity: 0.55,
            paddingTop: '1.4vh',
            lineHeight: 1.35,
            position: 'relative',
          }}
        >
          {/* hairline rule */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              right: 0,
              top: 0,
              height: '1px',
              background: 'currentColor',
              opacity: 0.18,
            }}
            aria-hidden="true"
          />
          <span lang="pt-PT">{meta.landmarkPt}</span>
          <br />
          <span
            lang="en"
            style={{
              fontStyle: 'italic',
              fontWeight: 400,
              opacity: 0.75,
              letterSpacing: '0.08em',
              textTransform: 'none',
            }}
          >
            {meta.landmarkEn}
          </span>
        </div>
      </footer>
    </section>
  );
}
