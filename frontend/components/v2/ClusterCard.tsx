'use client';

import type { ClusterLive } from '@/lib/v2-api';
import { occupancyColor, fmtNumber } from '@/lib/v2-api';
import Sparkline from './Sparkline';

interface Props {
  c: ClusterLive;
  spark?: number[];
  onClick?: () => void;
}

export default function ClusterCard({ c, spark, onClick }: Props) {
  const occCol = occupancyColor(c.ocupacao);
  const isCrit = c.status === 'critical';
  const isWarn = c.status === 'warning';
  const borderCol = isCrit
    ? 'var(--critical)'
    : isWarn
    ? 'var(--amber)'
    : 'var(--border)';

  return (
    <button
      onClick={onClick}
      className="fade-in"
      style={{
        background: 'var(--card)',
        border: `1.5px solid ${borderCol}`,
        borderRadius: 14,
        padding: '20px 20px 18px',
        cursor: onClick ? 'pointer' : 'default',
        textAlign: 'left',
        fontFamily: 'inherit',
        color: 'inherit',
        transition: 'all 0.18s ease',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        minHeight: 290,
      }}
      onMouseEnter={(e) => {
        if (!onClick) return;
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
      }}
      onMouseLeave={(e) => {
        if (!onClick) return;
        e.currentTarget.style.transform = '';
        e.currentTarget.style.boxShadow = '';
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <div>
          <div
            className="serif"
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: 'var(--ink)',
              lineHeight: 1,
            }}
          >
            {c.meta.id.toUpperCase()}
          </div>
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: 'var(--faint)',
              marginTop: 4,
              letterSpacing: '0.06em',
            }}
          >
            {c.meta.code} · {c.meta.zone}
          </div>
        </div>
        <span
          className="pill"
          style={{
            background: c.meta.isUnisex ? 'var(--green-pale)' : 'var(--surface-2)',
            color: c.meta.isUnisex ? 'var(--green-dark)' : 'var(--muted)',
            fontSize: 9,
          }}
        >
          {c.meta.isUnisex ? 'UNISEX' : 'M + F'}
        </span>
      </div>

      {/* Big people number */}
      <div style={{ textAlign: 'center', padding: '4px 0' }}>
        <div
          className="serif"
          style={{
            fontSize: 48,
            fontWeight: 500,
            color: 'var(--ink)',
            lineHeight: 1,
            letterSpacing: '-0.02em',
          }}
        >
          {fmtNumber(c.pessoas)}
        </div>
        <div
          style={{
            fontSize: 10,
            color: 'var(--faint)',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            marginTop: 6,
            fontWeight: 600,
          }}
        >
          pessoas agora
        </div>
      </div>

      {/* M/F split or unisex */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-around',
          padding: '8px 0',
          borderTop: '1px solid var(--border)',
          borderBottom: '1px solid var(--border)',
          fontSize: 13,
        }}
      >
        {c.meta.isUnisex ? (
          <span
            style={{
              color: 'var(--muted)',
              fontStyle: 'italic',
              fontSize: 12,
            }}
          >
            todos os géneros
          </span>
        ) : (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <span className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
                {c.homens ?? '—'}
              </span>
              <span style={{ fontSize: 9, color: 'var(--faint)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                ♂ homens
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <span className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
                {c.mulheres ?? '—'}
              </span>
              <span style={{ fontSize: 9, color: 'var(--faint)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                ♀ mulheres
              </span>
            </div>
          </>
        )}
      </div>

      {/* Occupancy bar */}
      <div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginBottom: 5,
          }}
        >
          <span
            style={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: 'var(--faint)',
            }}
          >
            ocupação
          </span>
          <span className="mono" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
            {c.ocupacao}%
          </span>
        </div>
        <div
          style={{
            height: 6,
            background: 'var(--surface-2)',
            borderRadius: 3,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${Math.min(100, c.ocupacao)}%`,
              height: '100%',
              background: occCol,
              borderRadius: 3,
              transition: 'width 0.6s ease, background 0.3s',
            }}
          />
        </div>
      </div>

      {/* Sparkline */}
      <div>
        <div
          style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: 'var(--faint)',
            marginBottom: 4,
          }}
        >
          últimos 5 min
        </div>
        <Sparkline values={spark ?? []} width={260} height={32} color="#2E7D4F" />
      </div>

      {/* Stats */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 8,
          paddingTop: 4,
          borderTop: '1px dashed var(--border)',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
            {c.filaTotal}
          </div>
          <div style={{ fontSize: 9, color: 'var(--faint)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 1 }}>
            fila
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
            {c.esperaMin}m
          </div>
          <div style={{ fontSize: 9, color: 'var(--faint)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 1 }}>
            espera
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
            {c.meta.total}
          </div>
          <div style={{ fontSize: 9, color: 'var(--faint)', letterSpacing: '0.06em', textTransform: 'uppercase', marginTop: 1 }}>
            lugares
          </div>
        </div>
      </div>
    </button>
  );
}
