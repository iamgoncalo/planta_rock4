'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV = [
  { href: '/v2',           label: 'Início' },
  { href: '/v2/twin',      label: 'Twin' },
  { href: '/v2/sensors',   label: 'Sensores' },
  { href: '/v2/shows',     label: 'Shows' },
  { href: '/v2/operations',label: 'Operações' },
  { href: '/v2/cleaning',  label: 'Limpeza' },
  { href: '/v2/incidents', label: 'Incidentes' },
  { href: '/v2/scor',      label: 'SCOR' },
  { href: '/v2/pipelines', label: 'Pipelines' },
];

export default function TopBar() {
  const pathname = usePathname() || '/v2';
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setTime(
        `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`,
      );
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, []);

  const isActive = (href: string) =>
    href === '/v2' ? pathname === '/v2' : pathname.startsWith(href);

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 'var(--header-h, 72px)',
        background: 'rgba(255, 255, 255, 0.92)',
        backdropFilter: 'blur(16px) saturate(140%)',
        WebkitBackdropFilter: 'blur(16px) saturate(140%)',
        borderBottom: '1px solid var(--border)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        padding: '0 clamp(18px, 3vw, 32px)',
        gap: 'clamp(12px, 2vw, 24px)',
      }}
    >
      {/* LOGO + BRAND */}
      <Link
        href="/v2"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          textDecoration: 'none',
          flexShrink: 0,
        }}
      >
        <img
          src="/planta-logo.svg"
          alt="Planta Smart Homes"
          style={{
            width: 44,
            height: 44,
            display: 'block',
            objectFit: 'contain',
          }}
        />
        <span
          style={{
            fontSize: 'clamp(15px, 1.4vw, 18px)',
            fontWeight: 600,
            color: 'var(--ink)',
            letterSpacing: '-0.02em',
            whiteSpace: 'nowrap',
            fontFamily: 'var(--font-display, Inter, sans-serif)',
          }}
        >
          Planta Smart Homes
        </span>
      </Link>

      {/* NAV — horizontal scroll quando estreito */}
      <nav
        className="topbar-nav"
        style={{
          display: 'flex',
          gap: 2,
          flex: 1,
          overflowX: 'auto',
          scrollbarWidth: 'none',
          msOverflowStyle: 'none',
          justifyContent: 'flex-end',
        }}
      >
        {NAV.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: '6px 12px',
                borderRadius: 8,
                textDecoration: 'none',
                fontSize: 13.5,
                fontWeight: active ? 600 : 500,
                color: active ? 'var(--ink)' : 'var(--muted)',
                background: active ? 'var(--bg-soft)' : 'transparent',
                whiteSpace: 'nowrap',
                letterSpacing: '-0.005em',
                transition: 'color 0.14s, background 0.14s',
              }}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Right cluster */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexShrink: 0,
        }}
        className="topbar-right"
      >
        <span className="pill pill-sim" title="Dados simulados até instalação física 11–12 Junho 2026">
          SIMULADO
        </span>
        <span
          className="mono"
          style={{
            fontSize: 11.5,
            color: 'var(--faint)',
            minWidth: 64,
            textAlign: 'right',
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {time}
        </span>
      </div>

      <style jsx global>{`
        .topbar-nav::-webkit-scrollbar { display: none; }
        @media (max-width: 720px) {
          .topbar-right .pill-sim { display: none; }
          .topbar-right .mono { display: none; }
        }
      `}</style>
    </header>
  );
}
