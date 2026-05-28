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
  const [mobileOpen, setMobileOpen] = useState(false);

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

  // Fechar drawer ao navegar
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Bloquear scroll do body quando drawer aberto
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [mobileOpen]);

  const isActive = (href: string) =>
    href === '/v2' ? pathname === '/v2' : pathname.startsWith(href);

  return (
    <>
      {/* HEADER FIXO */}
      <header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          height: 'var(--header-h, 72px)',
          background: 'rgba(255, 255, 255, 0.94)',
          backdropFilter: 'blur(16px) saturate(140%)',
          WebkitBackdropFilter: 'blur(16px) saturate(140%)',
          borderBottom: '1px solid var(--border)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          padding: '0 clamp(14px, 3vw, 32px)',
          gap: 'clamp(10px, 2vw, 24px)',
        }}
      >
        {/* LOGO + BRAND */}
        <Link
          href="/v2"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            textDecoration: 'none',
            flexShrink: 0,
            minWidth: 0,
          }}
        >
          <img
            src="/planta-logo.svg"
            alt="Planta Smart Homes"
            style={{
              width: 'clamp(36px, 4vw, 44px)',
              height: 'clamp(36px, 4vw, 44px)',
              display: 'block',
              objectFit: 'contain',
              flexShrink: 0,
            }}
          />
          <span
            className="topbar-brand"
            style={{
              fontSize: 'clamp(14px, 1.4vw, 18px)',
              fontWeight: 600,
              color: 'var(--ink)',
              letterSpacing: '-0.02em',
              whiteSpace: 'nowrap',
              fontFamily: 'var(--font-display, Inter, sans-serif)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            Planta Smart Homes
          </span>
        </Link>

        {/* NAV desktop */}
        <nav
          className="topbar-nav-desktop"
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

        {/* Right cluster — desktop */}
        <div
          className="topbar-right-desktop"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexShrink: 0,
          }}
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

        {/* HAMBURGER mobile (escondido em desktop) */}
        <button
          className="topbar-burger"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label={mobileOpen ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={mobileOpen}
          style={{
            display: 'none',
            width: 42,
            height: 42,
            background: 'transparent',
            border: '1px solid var(--border-strong)',
            borderRadius: 10,
            cursor: 'pointer',
            color: 'var(--ink)',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            padding: 0,
          }}
        >
          {mobileOpen ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          )}
        </button>
      </header>

      {/* MOBILE DRAWER fullscreen */}
      {mobileOpen && (
        <div
          className="topbar-drawer"
          style={{
            position: 'fixed',
            top: 'var(--header-h, 72px)',
            left: 0,
            right: 0,
            bottom: 0,
            background: 'white',
            zIndex: 99,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            padding: '20px 18px 40px',
          }}
        >
          {/* Status pill no topo do drawer */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 10,
            paddingBottom: 16,
            marginBottom: 16,
            borderBottom: '1px solid var(--border)',
          }}>
            <span className="pill pill-sim">SIMULADO</span>
            <span className="mono" style={{ fontSize: 12, color: 'var(--faint)' }}>{time}</span>
          </div>

          {/* Links grandes */}
          <nav style={{ display: 'flex', flexDirection: 'column' }}>
            {NAV.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '18px 4px',
                    fontSize: 22,
                    fontWeight: active ? 600 : 500,
                    color: active ? 'var(--ink)' : 'var(--muted)',
                    textDecoration: 'none',
                    borderBottom: '1px solid var(--border)',
                    letterSpacing: '-0.015em',
                    fontFamily: 'var(--font-display, Inter, sans-serif)',
                  }}
                >
                  <span>{item.label}</span>
                  {active && (
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: 'var(--green-dark, #1B3A21)',
                    }} />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Footer do drawer */}
          <div style={{
            marginTop: 'auto',
            paddingTop: 24,
            fontSize: 11,
            color: 'var(--muted)',
            fontFamily: 'var(--font-mono)',
            letterSpacing: '0.04em',
          }}>
            × Rock in Rio Lisboa 2026 · Parque Tejo · 20–28 Jun
          </div>
        </div>
      )}

      <style jsx global>{`
        .topbar-nav-desktop::-webkit-scrollbar { display: none; }
        
        /* Mobile breakpoint */
        @media (max-width: 920px) {
          .topbar-nav-desktop { display: none !important; }
          .topbar-right-desktop { display: none !important; }
          .topbar-burger { display: flex !important; }
        }

        /* Phone pequeno — brand abreviada via ellipsis se necessário */
        @media (max-width: 380px) {
          .topbar-brand {
            font-size: 13px !important;
            max-width: 130px !important;
          }
        }
      `}</style>
    </>
  );
}
