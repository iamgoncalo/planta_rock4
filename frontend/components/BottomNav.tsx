'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const TABS = [
  {
    href: '/',
    label: 'Início',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M3 12L12 3L21 12V21H15V15H9V21H3V12Z"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill={active ? '#4A7C5922' : 'none'}
        />
      </svg>
    ),
  },
  {
    href: '/occupation',
    label: 'WCs',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect
          x="3"
          y="3"
          width="8"
          height="8"
          rx="1"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
          fill={active ? '#4A7C5922' : 'none'}
        />
        <rect
          x="13"
          y="3"
          width="8"
          height="8"
          rx="1"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
          fill={active ? '#4A7C5922' : 'none'}
        />
        <rect
          x="3"
          y="13"
          width="8"
          height="8"
          rx="1"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
          fill={active ? '#4A7C5922' : 'none'}
        />
        <rect
          x="13"
          y="13"
          width="8"
          height="8"
          rx="1"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
          fill={active ? '#4A7C5922' : 'none'}
        />
      </svg>
    ),
  },
  {
    href: '/sensors',
    label: 'Sensores',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="3" stroke={active ? '#4A7C59' : '#6B7280'} strokeWidth="2" fill={active ? '#4A7C5922' : 'none'} />
        <path d="M6.34 6.34A8 8 0 0 0 12 20a8 8 0 0 0 5.66-13.66" stroke={active ? '#4A7C59' : '#6B7280'} strokeWidth="2" strokeLinecap="round" />
        <path d="M8.46 8.46A5 5 0 0 0 12 18a5 5 0 0 0 3.54-8.54" stroke={active ? '#4A7C59' : '#6B7280'} strokeWidth="2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    href: '/chat',
    label: 'Chat',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill={active ? '#4A7C5922' : 'none'}
        />
      </svg>
    ),
  },
  {
    href: '/ops',
    label: 'Ops',
    icon: (active: boolean) => (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="3" stroke={active ? '#4A7C59' : '#6B7280'} strokeWidth="2" />
        <path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
          stroke={active ? '#4A7C59' : '#6B7280'}
          strokeWidth="2"
        />
      </svg>
    ),
  },
];

export default function BottomNav() {
  const pathname = usePathname();

  // Don't show on TV or app pages (full-screen views)
  if (pathname.startsWith('/tv/') || pathname === '/app') {
    return null;
  }

  return (
    <nav
      aria-label="Navegação principal"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 'var(--nav-h)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        backgroundColor: '#fff',
        borderTop: '1px solid #DEE8DE',
        display: 'flex',
        alignItems: 'stretch',
        zIndex: 50,
      }}
    >
      {TABS.map((tab) => {
        const isActive =
          tab.href === '/'
            ? pathname === '/'
            : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={isActive ? 'page' : undefined}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
              minHeight: '44px',
              textDecoration: 'none',
              color: isActive ? '#4A7C59' : '#6B7280',
              fontFamily: 'var(--font-ui)',
              fontSize: '12px',
              fontWeight: isActive ? 600 : 400,
              transition: 'color 0.15s',
            }}
          >
            {tab.icon(isActive)}
            <span style={{ fontSize: '11px', lineHeight: '1' }}>{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
