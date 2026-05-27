'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV = [
  { href: '/v2',           label: 'Início' },
  { href: '/v2/twin',      label: '3D' },
  { href: '/v2/scor',      label: 'SCOR' },
  { href: '/v2/cleaning',  label: 'Limpeza' },
  { href: '/v2/incidents', label: 'Incidentes' },
  { href: '/v2/pipelines', label: 'Pipelines' },
  { href: '/v2/operations',label: 'Operações' },
  { href: '/v2/chat',      label: 'Chat' },
];

export default function TopBar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Fechar drawer ao navegar
  useEffect(() => { setOpen(false); }, [pathname]);

  return (
    <>
      <header style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        background: 'rgba(244,242,235,0.96)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        borderBottom: scrolled ? '1px solid var(--color-border)' : '1px solid transparent',
        transition: 'border-color 0.2s',
      }}>
        <div style={{
          maxWidth: 1400, margin: '0 auto',
          padding: '12px 20px',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          gap: 12,
        }}>
          {/* Logo */}
          <Link href="/v2" style={{
            display: 'flex', alignItems: 'center', gap: 10,
            textDecoration: 'none',
          }}>
            <div style={{
              width: 32, height: 32,
              background: '#1B3A21',
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'white', fontSize: 18, fontWeight: 700,
            }}>P</div>
            <div>
              <div className="serif" style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)', lineHeight: 1 }}>
                PlantaOS
              </div>
              <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', letterSpacing: '0.08em', marginTop: 1 }}>
                Rock in Rio LX26
              </div>
            </div>
          </Link>

          {/* Nav desktop */}
          <nav style={{
            display: 'flex', alignItems: 'center', gap: 6,
            flexWrap: 'wrap',
          }} className="topnav-desktop">
            {NAV.map(item => {
              const active = pathname === item.href ||
                (item.href !== '/v2' && pathname?.startsWith(item.href));
              return (
                <Link key={item.href} href={item.href} style={{
                  padding: '6px 12px',
                  fontSize: 13,
                  fontWeight: active ? 600 : 500,
                  color: active ? 'white' : 'var(--color-ink)',
                  background: active ? '#1B3A21' : 'transparent',
                  borderRadius: 7,
                  textDecoration: 'none',
                  transition: 'all 0.15s',
                }}>{item.label}</Link>
              );
            })}
          </nav>

          {/* Hamburger mobile */}
          <button
            onClick={() => setOpen(!open)}
            className="topnav-burger"
            style={{
              display: 'none',
              background: 'transparent',
              border: '1px solid var(--color-border)',
              borderRadius: 8,
              padding: '6px 10px',
              fontSize: 18,
              cursor: 'pointer',
            }}
          >{open ? '✕' : '☰'}</button>
        </div>

        {/* Drawer mobile */}
        {open && (
          <div style={{
            background: '#F4F2EB',
            borderTop: '1px solid var(--color-border)',
            padding: '10px 16px',
          }} className="topnav-mobile">
            {NAV.map(item => {
              const active = pathname === item.href ||
                (item.href !== '/v2' && pathname?.startsWith(item.href));
              return (
                <Link key={item.href} href={item.href} style={{
                  display: 'block',
                  padding: '10px 12px',
                  fontSize: 14,
                  fontWeight: active ? 700 : 500,
                  color: active ? '#1B3A21' : 'var(--color-ink)',
                  borderLeft: active ? '3px solid #1B3A21' : '3px solid transparent',
                  textDecoration: 'none',
                }}>{item.label}</Link>
              );
            })}
          </div>
        )}
      </header>

      <style jsx global>{`
        @media (max-width: 880px) {
          .topnav-desktop { display: none !important; }
          .topnav-burger { display: block !important; }
        }
      `}</style>
    </>
  );
}
