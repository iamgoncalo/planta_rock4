'use client';

interface Props {
  size?: number;
  showText?: boolean;
}

export default function PlantaLogo({ size = 28, showText = true }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        textDecoration: 'none',
      }}
    >
      <svg
        viewBox="0 0 64 64"
        width={size}
        height={size}
        aria-label="Planta"
        style={{ flexShrink: 0 }}
      >
        <circle cx="32" cy="32" r="30" fill="#1B3A21" />
        {/* leaf */}
        <path
          d="M 22 36 Q 32 16 42 36 Q 32 32 22 36 Z"
          fill="#6FAF82"
          opacity="0.95"
        />
        {/* stem */}
        <line
          x1="32"
          y1="36"
          x2="32"
          y2="50"
          stroke="#6FAF82"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        {/* highlight */}
        <ellipse
          cx="32"
          cy="26"
          rx="4"
          ry="2"
          fill="#FFFFFF"
          opacity="0.20"
        />
      </svg>
      {showText && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            lineHeight: 1.05,
          }}
        >
          <span
            className="serif"
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#0D1A0F',
              letterSpacing: '-0.01em',
            }}
          >
            planta
          </span>
          <span
            style={{
              fontSize: 9,
              color: '#3A6040',
              letterSpacing: '0.14em',
              fontWeight: 500,
              textTransform: 'lowercase',
            }}
          >
            smart homes
          </span>
        </div>
      )}
    </div>
  );
}
