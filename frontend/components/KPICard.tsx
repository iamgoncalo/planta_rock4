'use client';

interface KPICardProps {
  label: string;
  value: string | number;
  unit?: string;
  highlight?: boolean;
}

export default function KPICard({ label, value, unit, highlight }: KPICardProps) {
  return (
    <div
      style={{
        background: '#FAFAF7',
        border: `1px solid ${highlight ? '#C25A1A' : '#DEE8DE'}`,
        borderRadius: '12px',
        padding: '20px 16px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        minWidth: 0,
      }}
    >
      <div
        style={{
          fontFamily: 'var(--font-ui)',
          fontSize: '14px',
          fontWeight: 500,
          color: '#6B7280',
          letterSpacing: '0.03em',
          textTransform: 'uppercase',
          lineHeight: '1.2',
        }}
      >
        {label}
      </div>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          gap: '6px',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'clamp(48px, 8vw, 64px)',
            lineHeight: '1',
            fontWeight: 400,
            color: highlight ? '#C25A1A' : '#1A1A1A',
          }}
        >
          {value}
        </span>
        {unit && (
          <span
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '20px',
              fontWeight: 400,
              color: '#6B7280',
            }}
          >
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
