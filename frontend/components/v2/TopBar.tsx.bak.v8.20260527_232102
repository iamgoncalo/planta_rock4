'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import PlantaLogo from './PlantaLogo';

const NAV_ITEMS = [
  { href: '/v2', label: 'Início' },
  { href: '/v2/twin', label: 'Digital Twin' },
  { href: '/v2/sensors', label: 'Sensores' },
  { href: '/v2/shows', label: 'Shows' },
  { href: '/v2/operations', label: 'Operações' },
  { href: '/v2/chat', label: 'Chat AI' },
];

export default function TopBar() {
  const pathname = usePathname() ?? '/v2';
  const [now, setNow] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const d = new Date();
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      const ss = String(d.getSeconds()).padStart(2, '0');
      setNow(`${hh}:${mm}:${ss}`);
    };
    update();
    const iv = setInterval(update, 1000);
    return () => clearInterval(iv);
  }, []);

  const isActive = (href: string) => {
    if (href === '/v2') return pathname === '/v2';
    return pathname.startsWith(href);
  };

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 56,
        background: 'rgba(255, 255, 255, 0.92)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        borderBottom: '1px solid var(--border)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        padding: '0 22px',
        gap: 16,
      }}
    >
      <Link href="/v2" style={{ textDecoration: 'none', flexShrink: 0 }}>
        <PlantaLogo size={26} />
      </Link>

      <div
        style={{
          fontFamily: 'var(--font-mono), monospace',
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
      </div>

      <nav
        style={{
          display: 'flex',
          gap: 2,
          flex: 1,
          overflowX: 'auto',
          scrollbarWidth: 'none',
        }}
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                padding: '6px 12px',
                borderRadius: 6,
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

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          flexShrink: 0,
        }}
      >
        <span
          className="pill"
          title="Sensores físicos a instalar a 11–12 Junho 2026 · dashboard em modo demonstração até essa data"
          style={{
            background: 'var(--amber-bg, rgba(168,93,0,0.10))',
            color: 'var(--amber, #A85D00)',
            border: '1px solid rgba(168,93,0,0.22)',
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.10em',
            padding: '4px 10px',
            borderRadius: 999,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--amber, #A85D00)',
            }}
          />
          PRÉ-INSTALAÇÃO · 11 JUN
        </span>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--faint)',
            minWidth: 60,
            textAlign: 'right',
          }}
        >
          {now}
        </span>
      </div>
    </header>
  );
}
