'use client';

import Link from 'next/link';
import Image from 'next/image';
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
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      const ss = String(d.getSeconds()).padStart(2, '0');
      setTime(`${hh}:${mm}:${ss}`);
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => { setMobileOpen(false); }, [pathname]);

  const isActive = (href: string) =>
    href === '/v2' ? pathname === '/v2' : pathname.startsWith(href);

  return (
    <>
      <header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          height: 'var(--header-h, 64px)',
          background: 'rgba(255, 255, 255, 0.92)',
          backdropFilter: 'blur(14px)',
          WebkitBackdropFilter: 'blur(14px)',
          borderBottom: '1px solid var(--border)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          gap: 16,
        }}
      >
        {/* LOGO */}
        <Link
          href="/v2"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            textDecoration: 'none',
            flexShrink: 0,
          }}
        >
          <img
            src="/planta-logo.svg"
            alt="Planta Smart Homes"
            width={28}
            height={28}
            style={{ display: 'block' }}
          />
                    <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.05 }}>
            <span
              className="serif"
              style={{
                fontSize: 16,
                fontWeight: 600,
                color: 'var(--ink)',
                letterSpacing: '-0.01em',
                whiteSpace: 'nowrap',
              }}
            >
              Planta Smart Homes
            </span>
          </div>
        </Link>

        {/* Pill projecto */}
        <span
          className="mono"
          style={{
            fontSize: 10,
            color: 'var(--muted)',
            letterSpacing: '0.08em',
            border: '1px solid var(--border)',
            padding: '3px 10px',
            borderRadius: 999,
            flexShrink: 0,
            whiteSpace: 'nowrap',
          }}
        >
          × rock in rio lisboa 2026
        </span>

        {/* NAV desktop */}
        <nav
          className="topbar-desktop"
          style={{
            display: 'flex',
            gap: 2,
            flex: 1,
            overflowX: 'auto',
            scrollbarWidth: 'none',
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
                  borderRadius: 7,
                  textDecoration: 'none',
                  fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  color: active ? 'var(--green)' : 'var(--muted)',
                  background: active ? 'var(--green-pale)' : 'transparent',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.14s',
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right: pill + clock */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexShrink: 0,
          }}
          className="topbar-right"
        >
          <span
            className="pill pill-sim"
            title="Dados simulados até instalação física 11–12 Junho 2026"
          >
            SIMULADO
          </span>
          <span
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--faint)',
              minWidth: 64,
              textAlign: 'right',
            }}
          >
            {time}
          </span>
        </div>

        {/* Mobile burger */}
        <button
          className="topbar-burger"
          onClick={() => setMobileOpen(!mobileOpen)}
          style={{
            display: 'none',
            background: 'transparent',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '6px 10px',
            fontSize: 16,
            cursor: 'pointer',
            color: 'var(--ink)',
          }}
        >
          {mobileOpen ? '✕' : '☰'}
        </button>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="topbar-drawer"
          style={{
            position: 'fixed',
            top: 'var(--header-h, 64px)',
            left: 0,
            right: 0,
            background: 'white',
            borderBottom: '1px solid var(--border)',
            zIndex: 99,
            padding: '12px 18px',
          }}
        >
          {NAV.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: 'block',
                  padding: '10px 12px',
                  fontSize: 14,
                  fontWeight: active ? 700 : 500,
                  color: active ? 'var(--green)' : 'var(--ink)',
                  textDecoration: 'none',
                  borderLeft: active
                    ? '3px solid var(--green)'
                    : '3px solid transparent',
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}

      <style jsx global>{`
        @media (max-width: 920px) {
          .topbar-desktop { display: none !important; }
          .topbar-burger { display: block !important; }
          .topbar-right .pill-sim { display: none; }
        }
        nav::-webkit-scrollbar { display: none; }
      `}</style>
    </>
  );
}
