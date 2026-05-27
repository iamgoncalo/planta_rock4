'use client';

import SimuladoBadge from './SimuladoBadge';

interface SectionBarProps {
  section_id: string;
  ocupacao_pct: number;
  fila_atual: number;
  tempo_espera_min: number;
  status: 'ok' | 'warning' | 'critical' | 'offline';
  simulated: boolean;
  confidence: number;
  gender?: 'M' | 'F' | 'U';
  fluxo_entrada?: number;
  fluxo_saida?: number;
}

function getBarColor(pct: number, status: string): string {
  if (status === 'offline') return '#6B7280';
  if (pct >= 90) return '#C25A1A';
  if (pct >= 75) return '#D97706';
  return '#4A7C59';
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'ok': return 'OK';
    case 'warning': return 'Atenção';
    case 'critical': return 'Crítico';
    case 'offline': return 'Offline';
    default: return status;
  }
}

function ConfidenceDots({ confidence }: { confidence: number }) {
  const level = confidence >= 0.8 ? 3 : confidence >= 0.5 ? 2 : 1;
  return (
    <span style={{ display: 'inline-flex', gap: '3px', alignItems: 'center' }}>
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: i <= level ? '#4A7C59' : '#DEE8DE',
            display: 'inline-block',
          }}
        />
      ))}
    </span>
  );
}

export default function SectionBar({
  section_id,
  ocupacao_pct,
  fila_atual,
  tempo_espera_min,
  status,
  simulated,
  confidence,
  gender,
  fluxo_entrada,
  fluxo_saida,
}: SectionBarProps) {
  const barColor = getBarColor(ocupacao_pct, status);
  const isOffline = status === 'offline';
  const isCritical = status === 'critical';

  const displayLabel =
    gender === 'U' ? 'Unissexo' : gender === 'M' ? 'Masculino' : gender === 'F' ? 'Feminino' : section_id;

  return (
    <div
      style={{
        border: `1px solid ${isCritical ? '#C25A1A' : '#DEE8DE'}`,
        borderRadius: '10px',
        padding: '14px 16px',
        background: isCritical ? '#FFF5F0' : '#FAFAF7',
        opacity: isOffline ? 0.6 : 1,
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <span
            style={{
              fontFamily: 'var(--font-ui)',
              fontWeight: 600,
              fontSize: '18px',
              color: isCritical ? '#C25A1A' : '#1A1A1A',
              whiteSpace: 'nowrap',
            }}
          >
            {section_id}
          </span>
          {gender && (
            <span
              style={{
                fontFamily: 'var(--font-ui)',
                fontSize: '14px',
                color: '#6B7280',
                fontWeight: 400,
              }}
            >
              {displayLabel}
            </span>
          )}
          <SimuladoBadge isSimulated={simulated} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <ConfidenceDots confidence={confidence} />
          <span
            style={{
              fontFamily: 'var(--font-ui)',
              fontSize: '14px',
              fontWeight: 500,
              color: isCritical ? '#C25A1A' : status === 'warning' ? '#D97706' : isOffline ? '#6B7280' : '#1B3A21',
            }}
          >
            {getStatusLabel(status)}
          </span>
        </div>
      </div>

      {/* Occupancy bar */}
      <div style={{ marginBottom: '10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontFamily: 'var(--font-ui)', fontSize: '14px', color: '#6B7280' }}>Ocupação</span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '20px',
              fontWeight: 400,
              color: isCritical ? '#C25A1A' : '#1A1A1A',
            }}
          >
            {isOffline ? '—' : `${Math.round(ocupacao_pct)}%`}
          </span>
        </div>
        <div
          style={{
            height: '8px',
            borderRadius: '4px',
            background: '#DEE8DE',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${Math.min(100, Math.max(0, ocupacao_pct))}%`,
              backgroundColor: barColor,
              borderRadius: '4px',
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontFamily: 'var(--font-ui)', fontSize: '12px', color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Fila</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', color: '#1A1A1A' }}>
            {isOffline ? '—' : fila_atual}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontFamily: 'var(--font-ui)', fontSize: '12px', color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Espera</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', color: '#1A1A1A' }}>
            {isOffline ? '—' : `${Math.round(tempo_espera_min)} min`}
          </span>
        </div>
        {fluxo_entrada !== undefined && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontFamily: 'var(--font-ui)', fontSize: '12px', color: '#6B7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Entrada/Saída</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '22px', color: '#1A1A1A' }}>
              {isOffline ? '—' : `${fluxo_entrada}/${fluxo_saida ?? 0}`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
