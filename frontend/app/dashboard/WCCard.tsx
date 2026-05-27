'use client';

import SparkLine from './SparkLine';

const C = {
  card: '#FFFFFF',
  border: '#DEE8DE',
  ink: '#1A1A1A',
  muted: '#6B7280',
  accent: '#4A7C59',
  accentDark: '#1B3A21',
  accentLight: '#6FAF82',
  critical: '#C25A1A',
  warning: '#D48B3A',
} as const;

export interface ClusterDisplay {
  id: string;
  isUnisex: boolean;
  pessoas: number;
  homens: number | null;
  mulheres: number | null;
  ocupacao: number;
  entradas: number;
  saidas: number;
  telemoveis: number;
  prosegur: number;
  confianca: number;
  estado: string;
  sparkOccupancy: number[];
  status: 'ok' | 'warning' | 'critical';
}

function statusBorder(s: string) {
  if (s === 'critical') return C.critical;
  if (s === 'warning') return C.warning;
  return C.border;
}

function occBarColor(p: number) {
  if (p >= 80) return C.critical;
  if (p >= 60) return C.warning;
  return C.accentLight;
}

export default function WCCard({ c }: { c: ClusterDisplay }) {
  const borderCol = statusBorder(c.status);
  const barCol = occBarColor(c.ocupacao);

  return (
    <div
      style={{
        background: C.card,
        border: `1.5px solid ${borderCol}`,
        borderRadius: 14,
        padding: '18px 18px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        minHeight: 280,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h3
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: '-0.01em',
            color: C.accentDark,
          }}
        >
          {c.id}
        </h3>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.08em',
            padding: '3px 8px',
            borderRadius: 999,
            background: c.isUnisex ? '#1B3A2110' : '#EDF4EF',
            color: c.isUnisex ? C.accentDark : C.accent,
          }}
        >
          {c.isUnisex ? 'UNISEX' : 'M + F'}
        </span>
      </div>

      <div style={{ textAlign: 'center', padding: '4px 0' }}>
        <div
          style={{
            fontSize: 42,
            fontWeight: 600,
            color: C.ink,
            lineHeight: 1,
            fontFamily: 'Georgia, serif',
          }}
        >
          {c.pessoas}
        </div>
        <div
          style={{
            fontSize: 11,
            color: C.muted,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            marginTop: 4,
          }}
        >
          pessoas
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-around',
          fontSize: 13,
          color: C.ink,
          padding: '6px 0',
          borderTop: `1px solid ${C.border}`,
          borderBottom: `1px solid ${C.border}`,
        }}
      >
        {c.isUnisex ? (
          <span style={{ color: C.muted }}>todos os generos</span>
        ) : (
          <>
            <span>
              <span style={{ color: C.muted }}>H </span>
              {c.homens ?? '-'}
            </span>
            <span>
              <span style={{ color: C.muted }}>M </span>
              {c.mulheres ?? '-'}
            </span>
          </>
        )}
      </div>

      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            fontSize: 11,
            color: C.muted,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            marginBottom: 4,
          }}
        >
          <span>ocupacao</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: C.ink, textTransform: 'none', letterSpacing: 0 }}>
            {c.ocupacao}%
          </span>
        </div>
        <div style={{ width: '100%', height: 6, background: '#F4F1E8', borderRadius: 3, overflow: 'hidden' }}>
          <div
            style={{
              width: `${Math.min(100, c.ocupacao)}%`,
              height: '100%',
              background: barCol,
              transition: 'width 0.6s ease',
            }}
          />
        </div>
      </div>

      <div>
        <div
          style={{
            fontSize: 10,
            color: C.muted,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            marginBottom: 2,
          }}
        >
          ultimos 5 min
        </div>
        <SparkLine values={c.sparkOccupancy} width={240} height={32} color={C.accent} />
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 12,
          color: C.muted,
        }}
      >
        <span>in {c.entradas}</span>
        <span>out {c.saidas}</span>
      </div>
    </div>
  );
}
