'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV = [
  { href: '/v3',          label: 'Início'     },
  { href: '/v3/twin',     label: 'Twin'       },
  { href: '/v3/scor',     label: 'SCOR'       },
  { href: '/v3/flow',     label: 'Flow'       },
  { href: '/v3/screen',   label: 'Screens'    },
  { href: '/v3/install',  label: 'Instalação' },
  { href: '/v3/cleaning', label: 'Limpeza'    },
  { href: '/v3/shows',    label: 'Shows'      },
];

export default function TopBarV3({ connected }: { connected?: boolean }) {
  const pathname = usePathname() || '/v3';
  const [time, setTime] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setTime(
        `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`,
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const isActive = (href: string) =>
    href === '/v3' ? pathname === '/v3' : pathname.startsWith(href);

  return (
    <>
      <header className="v3-header">
        <Link href="/v3" className="v3-header-brand">
          <span className="v3-header-brand-name">PlantaOS</span>
          <span className="v3-header-brand-sub">RiR LX 2026</span>
        </Link>

        <nav className="v3-nav" aria-label="Navegação principal v3">
          {NAV.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`v3-nav-link${isActive(href) ? ' active' : ''}`}
            >
              {label}
            </Link>
          ))}
        </nav>

        <div className="v3-header-right">
          <span className="v3-clock">{time}</span>
          <span
            className={`v3-live-dot${connected === false ? ' offline' : ''}`}
            title={connected === false ? 'Sem ligação' : 'Ao vivo'}
          />
        </div>

        <button
          className="v3-hamburger"
          aria-label="Abrir menu"
          onClick={() => setMenuOpen((o) => !o)}
        >
          {menuOpen ? (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="6" y1="6" x2="18" y2="18" />
              <line x1="18" y1="6" x2="6" y2="18" />
            </svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="4" y1="7"  x2="20" y2="7"  />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="17" x2="20" y2="17" />
            </svg>
          )}
        </button>
      </header>

      <nav className={`v3-mobile-menu${menuOpen ? ' open' : ''}`} aria-label="Menu mobile v3">
        {NAV.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={`v3-nav-link${isActive(href) ? ' active' : ''}`}
            onClick={() => setMenuOpen(false)}
          >
            {label}
          </Link>
        ))}
      </nav>
    </>
  );
}
