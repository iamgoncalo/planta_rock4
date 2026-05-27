'use client';

interface SimuladoBadgeProps {
  isSimulated: boolean;
}

export default function SimuladoBadge({ isSimulated }: SimuladoBadgeProps) {
  if (!isSimulated) return null;

  return (
    <span
      aria-label="Dados simulados"
      style={{
        display: 'inline-block',
        backgroundColor: '#C25A1A',
        color: '#fff',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        fontWeight: 400,
        letterSpacing: '0.12em',
        padding: '3px 10px',
        borderRadius: '4px',
        verticalAlign: 'middle',
      }}
    >
      SIMULADO
    </span>
  );
}
