'use client';

import Link from 'next/link';
import type { ClusterId } from '@/lib/mural-types';

const ORDER: ClusterId[] = ['01','02','03','04','05','06','07','08'];

function neighbour(id: ClusterId, dir: -1 | 1): ClusterId {
  const i = ORDER.indexOf(id);
  const n = (i + dir + ORDER.length) % ORDER.length;
  return ORDER[n];
}

export default function WcNav({ id }: { id: ClusterId }) {
  const prev = neighbour(id, -1);
  const next = neighbour(id, 1);

  const btn: React.CSSProperties = {
    position: 'fixed',
    top: '50%',
    transform: 'translateY(-50%)',
    width: 'clamp(40px, 6vh, 64px)',
    height: 'clamp(40px, 6vh, 64px)',
    display: 'grid',
    placeItems: 'center',
    borderRadius: '50%',
    textDecoration: 'none',
    color: 'currentColor',
    background: 'rgba(0,0,0,0.04)',
    border: '1px solid rgba(0,0,0,0.06)',
    fontSize: 'clamp(20px, 3vh, 30px)',
    opacity: 0.28,
    transition: 'opacity 0.2s ease, background 0.2s ease',
    zIndex: 50,
    userSelect: 'none',
  };

  const hover = (e: React.MouseEvent<HTMLAnchorElement>, on: boolean) => {
    e.currentTarget.style.opacity = on ? '0.95' : '0.28';
    e.currentTarget.style.background = on ? 'rgba(0,0,0,0.10)' : 'rgba(0,0,0,0.04)';
  };

  return (
    <>
      {/* WC anterior */}
      <Link href={`/wc${prev}`} aria-label={`WC ${prev}`}
        style={{ ...btn, left: 'clamp(12px, 2vw, 28px)' }}
        onMouseEnter={(e) => hover(e, true)} onMouseLeave={(e) => hover(e, false)}>
        ‹
      </Link>

      {/* WC seguinte */}
      <Link href={`/wc${next}`} aria-label={`WC ${next}`}
        style={{ ...btn, right: 'clamp(12px, 2vw, 28px)' }}
        onMouseEnter={(e) => hover(e, true)} onMouseLeave={(e) => hover(e, false)}>
        ›
      </Link>

      {/* Mural completo (canto superior direito) */}
      <Link href="/v2/screen" aria-label="Ver mural completo"
        style={{
          position: 'fixed',
          top: 'clamp(12px, 2vh, 24px)',
          right: 'clamp(12px, 2vw, 28px)',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gridTemplateRows: 'repeat(2, 1fr)',
          gap: '2px',
          width: 'clamp(30px, 4vh, 44px)',
          height: 'clamp(16px, 2.2vh, 24px)',
          padding: '4px',
          borderRadius: 6,
          background: 'rgba(0,0,0,0.04)',
          border: '1px solid rgba(0,0,0,0.06)',
          opacity: 0.3,
          transition: 'opacity 0.2s ease',
          zIndex: 50,
        }}
        onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.95'; }}
        onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.3'; }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <span key={i} style={{ background: 'currentColor', borderRadius: 1 }} />
        ))}
      </Link>
    </>
  );
}
