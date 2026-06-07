'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import type { ClusterId } from '@/lib/mural-types';

const ORDER: ClusterId[] = ['01','02','03','04','05','06','07','08'];

const arrow: React.CSSProperties = {
  width: 'clamp(34px,3vw,46px)', height: 'clamp(34px,3vw,46px)',
  display: 'grid', placeItems: 'center', borderRadius: '50%', cursor: 'pointer',
  fontSize: 'clamp(1.1rem,1.6vw,1.6rem)', color: '#28351C',
  background: 'rgba(0,0,0,0.05)', border: '1px solid rgba(0,0,0,0.10)',
};

export default function WcNav({ id }: { id: ClusterId }) {
  const router = useRouter();
  const i = ORDER.indexOf(id);
  const prev = ORDER[(i - 1 + ORDER.length) % ORDER.length];
  const next = ORDER[(i + 1) % ORDER.length];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft')  router.push(`/wc${prev}`);
      if (e.key === 'ArrowRight') router.push(`/wc${next}`);
      if (e.key === 'Escape' || e.key === 'ArrowUp') router.push('/v2/screen');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [router, prev, next]);

  return (
    <nav
      aria-label="Navegacao entre casas de banho"
      style={{
        position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 100,
        display: 'flex', alignItems: 'center', gap: 'clamp(6px, 0.8vw, 14px)',
        padding: 'clamp(10px, 1.4vh, 20px) clamp(12px, 2vw, 32px)',
        background: 'rgba(255,255,255,0.55)',
        backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
        borderTop: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      <button onClick={() => router.push('/v2/screen')} aria-label="Ver mural completo"
        style={{
          display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gridTemplateRows: 'repeat(2,1fr)',
          gap: 2, width: 'clamp(34px,3vw,46px)', height: 'clamp(20px,1.8vh,28px)',
          padding: 4, borderRadius: 8, cursor: 'pointer',
          background: 'rgba(0,0,0,0.05)', border: '1px solid rgba(0,0,0,0.10)', flexShrink: 0,
        }}>
        {Array.from({ length: 8 }).map((_, k) => (
          <span key={k} style={{ background: '#28351C', borderRadius: 1, opacity: 0.7 }} />
        ))}
      </button>

      <div style={{ width: 1, height: 'clamp(20px,3vh,32px)', background: 'rgba(0,0,0,0.12)', flexShrink: 0 }} />

      <div style={{ display: 'flex', gap: 'clamp(4px,0.6vw,10px)', flex: 1, justifyContent: 'center' }}>
        {ORDER.map((c) => {
          const active = c === id;
          return (
            <button key={c} onClick={() => router.push(`/wc${c}`)}
              aria-label={`WC-${c}`} aria-current={active ? 'page' : undefined}
              style={{
                fontFamily: "'Inter', system-ui, sans-serif",
                fontSize: 'clamp(0.7rem, 1vw, 1rem)', fontWeight: active ? 700 : 500,
                fontVariantNumeric: 'tabular-nums', letterSpacing: '0.04em',
                padding: 'clamp(6px,0.8vh,10px) clamp(8px,1vw,16px)', borderRadius: 999, cursor: 'pointer',
                color: active ? '#fff' : '#28351C',
                background: active ? '#28351C' : 'rgba(0,0,0,0.05)',
                border: '1px solid ' + (active ? '#28351C' : 'rgba(0,0,0,0.10)'),
                transition: 'all 0.16s ease',
              }}>
              {c}
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', gap: 'clamp(4px,0.6vw,10px)', flexShrink: 0 }}>
        <button onClick={() => router.push(`/wc${prev}`)} aria-label={`WC ${prev}`} style={arrow}>{'\u2039'}</button>
        <button onClick={() => router.push(`/wc${next}`)} aria-label={`WC ${next}`} style={arrow}>{'\u203A'}</button>
      </div>
    </nav>
  );
}
