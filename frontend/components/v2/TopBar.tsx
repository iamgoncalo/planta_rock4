'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLive } from './LiveContext';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const RECENTS_KEY = 'planta-recent-paths-v1';

interface NavItem {
  href: string;
  label: string;
  hint: string;
}

const NAV: NavItem[] = [
  { href: '/v2/chat2',      label: 'Chat',       hint: 'G ?' },
  { href: '/v2/twin',       label: 'Twin',       hint: 'G T' },
  { href: '/v2/flow',       label: 'Flow',       hint: 'G F' },
  { href: '/v2/sensors',    label: 'Sensores',   hint: 'G S' },
  { href: '/v2/screen',     label: 'Screens',    hint: 'G E' },
  { href: '/v2/shows',      label: 'Shows',      hint: 'G W' },
  { href: '/v2/cleaning',   label: 'Limpeza',    hint: 'G L' },
  { href: '/v2/scor',       label: 'SCOR',       hint: 'G C' },
];

function readRecents(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(RECENTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function pushRecent(path: string) {
  if (typeof window === 'undefined') return;
  try {
    const cur = readRecents().filter((p) => p !== path);
    cur.unshift(path);
    localStorage.setItem(RECENTS_KEY, JSON.stringify(cur.slice(0, 4)));
  } catch {}
}

export default function TopBar() {
  const pathname = usePathname() || '/v2';
  const [time, setTime] = useState('');
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [recents, setRecents] = useState<string[]>([]);
  // KPIs live via useLive() — single source of truth do v2/layout LiveProvider
  const { totalPessoas: livePeople, avgOcc: liveOcc, connection } = useLive();
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const tick = () => {
      const d = new Date();
      setTime(`${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`);
    };
    tick();
    const iv = setInterval(tick, 1000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (pathname && pathname !== '/v2') pushRecent(pathname);
    setRecents(readRecents());
  }, [pathname]);

  useEffect(() => {
    setOpen(false);
    setSearch('');
  }, [pathname]);

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
      setTimeout(() => searchRef.current?.focus(), 220);
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const isActive = useCallback((href: string) =>
    href === '/v2' ? pathname === '/v2' : pathname.startsWith(href),
  [pathname]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return NAV;
    return NAV.filter((n) =>
      n.label.toLowerCase().includes(q) || n.href.toLowerCase().includes(q)
    );
  }, [search]);

  const recentItems = useMemo(() => {
    return recents
      .map((path) => NAV.find((n) => n.href === path))
      .filter(Boolean) as NavItem[];
  }, [recents]);

  return (
    <>
      <header
        style={{
          position: 'fixed', top: 0, left: 0, right: 0,
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
        {/* LOGO + BRAND — sempre à esquerda */}
        <Link
          href="/v2"
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            textDecoration: 'none', flexShrink: 0, minWidth: 0,
          }}
        >
          <img
            src="/planta-logo.svg"
            alt="Planta Smart Homes"
            style={{
              width: 'clamp(36px, 4vw, 44px)',
              height: 'clamp(36px, 4vw, 44px)',
              display: 'block', objectFit: 'contain', flexShrink: 0,
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
              overflow: 'hidden', textOverflow: 'ellipsis',
            }}
          >
            Planta Smart Homes
          </span>
        </Link>

        {/* Nav desktop OU spacer flex em mobile */}
        <nav
          className="topbar-nav-desktop"
          style={{
            display: 'flex', gap: 2, flex: 1,
            overflowX: 'auto',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            justifyContent: 'flex-end',
          }}
        >
          {NAV.slice(0, 9).map((item) => {
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

        {/* Spacer apenas em mobile — empurra hamburger para a direita */}
        <span
          className="topbar-mobile-spacer"
          style={{ display: 'none', flex: 1 }}
          aria-hidden="true"
        />

        {/* Right cluster desktop */}
        <div
          className="topbar-right-desktop"
          style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}
        >
          <span
            className="mono"
            style={{
              fontSize: 11.5,
              color: 'var(--amber, #C25A1A)',
              fontWeight: 600,
              minWidth: 64,
              textAlign: 'right',
              fontVariantNumeric: 'tabular-nums',
              letterSpacing: '0.02em',
            }}
          >
            {time}
          </span>
        </div>

        {/* HAMBURGER VEGGIE — verde escuro Planta com linhas creme — à DIREITA */}
        <button
          className="topbar-burger"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? 'Fechar menu' : 'Abrir menu'}
          aria-expanded={open}
          style={{
            display: 'none',
            width: 44, height: 44,
            background: open ? 'var(--ink, #0D1A0F)' : 'var(--green-dark, #1B3A21)',
            border: 'none',
            borderRadius: 12,
            cursor: 'pointer',
            color: '#F5F3EC',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            padding: 0,
            position: 'relative',
            boxShadow: open
              ? '0 4px 14px rgba(13, 26, 15, 0.28)'
              : '0 2px 10px rgba(27, 58, 33, 0.22)',
            transition: 'background 0.24s, box-shadow 0.24s, transform 0.18s',
          }}
          onMouseDown={(e) => { e.currentTarget.style.transform = 'scale(0.94)'; }}
          onMouseUp={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
        >
          <BurgerIcon open={open} />
        </button>
      </header>

      {/* BACKDROP */}
      <div
        className="topbar-backdrop"
        onClick={() => setOpen(false)}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(13, 26, 15, 0.42)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          zIndex: 98,
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 0.28s cubic-bezier(0.32, 0.72, 0, 1)',
        }}
        aria-hidden="true"
      />

      {/* DRAWER — agora vem da DIREITA porque o hamburger está à direita */}
      <aside
        className="topbar-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Menu de navegação"
        style={{
          position: 'fixed',
          top: 0, right: 0, bottom: 0,
          width: 'min(360px, 90vw)',
          background: 'white',
          zIndex: 99,
          boxShadow: open ? '-10px 0 60px rgba(13, 26, 15, 0.18)' : 'none',
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.32s cubic-bezier(0.32, 0.72, 0, 1)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* TOPO — logo + close */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '18px 20px 14px',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img src="/planta-logo.svg" alt="" style={{ width: 32, height: 32 }} />
            <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
              <span style={{
                fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em',
                fontFamily: 'var(--font-display)',
              }}>Planta</span>
              <span style={{
                fontSize: 10.5,
                color: 'var(--muted)',
                fontFamily: 'var(--font-mono)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
              }}>Smart Homes</span>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            aria-label="Fechar"
            style={{
              width: 32, height: 32,
              background: 'transparent',
              border: '1px solid var(--border)',
              borderRadius: 8,
              cursor: 'pointer',
              color: 'var(--muted)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 0,
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* KPIs LIVE */}
        <div style={{
          padding: '14px 20px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-soft)',
        }}>
          <div className="mono" style={{
            fontSize: 9.5, letterSpacing: '0.18em',
            textTransform: 'uppercase', color: 'var(--muted)',
            marginBottom: 8,
          }}>
            Agora · ao segundo
          </div>
          <div style={{ display: 'flex', gap: 18, alignItems: 'baseline' }}>
            <div>
              <div style={{
                fontSize: 24, fontWeight: 600,
                letterSpacing: '-0.025em',
                lineHeight: 1,
                color: 'var(--ink)',
                fontFamily: 'var(--font-display)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {livePeople > 0 ? livePeople.toLocaleString('pt-PT') : '—'}
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 2, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                pessoas
              </div>
            </div>
            <div>
              <div style={{
                fontSize: 24, fontWeight: 600,
                letterSpacing: '-0.025em',
                lineHeight: 1,
                color: 'var(--green-dark)',
                fontFamily: 'var(--font-display)',
                fontVariantNumeric: 'tabular-nums',
              }}>
                {liveOcc > 0 ? `${liveOcc.toFixed(0)}%` : '—'}
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 2, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                ocup
              </div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <span className={connection === "sse" ? "pill pill-live" : "pill pill-sim"} style={{ fontSize: 9 }}>{connection === "sse" ? "LIVE" : connection === "polling" ? "2s" : "..."}</span>
            </div>
          </div>
        </div>

        {/* SEARCH */}
        <div style={{
          padding: '12px 20px',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--bg-soft)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: '8px 12px',
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Procurar…"
              style={{
                flex: 1,
                border: 'none',
                outline: 'none',
                background: 'transparent',
                fontSize: 14,
                fontFamily: 'inherit',
                padding: 0,
                color: 'var(--ink)',
                minWidth: 0,
              }}
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                aria-label="Limpar"
                style={{
                  background: 'transparent', border: 'none',
                  cursor: 'pointer', color: 'var(--muted)',
                  fontSize: 11, padding: 0,
                  fontFamily: 'var(--font-mono)',
                }}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* LISTA navegável */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px 12px 20px',
        }}>
          {!search && recentItems.length > 0 && (
            <div style={{ marginBottom: 12, padding: '0 8px' }}>
              <div className="mono" style={{
                fontSize: 9.5, letterSpacing: '0.18em',
                textTransform: 'uppercase', color: 'var(--muted)',
                margin: '6px 0 6px',
              }}>
                Recentes
              </div>
              {recentItems.slice(0, 3).map((item) => (
                <DrawerLink key={`r-${item.href}`} item={item} active={isActive(item.href)} small />
              ))}
            </div>
          )}

          {!search && recentItems.length > 0 && (
            <div className="mono" style={{
              fontSize: 9.5, letterSpacing: '0.18em',
              textTransform: 'uppercase', color: 'var(--muted)',
              padding: '6px 16px 6px',
            }}>
              Tudo
            </div>
          )}

          {filtered.length === 0 && (
            <div style={{
              padding: '40px 20px',
              textAlign: 'center',
              color: 'var(--muted)',
              fontSize: 13,
            }}>
              Sem resultados para "{search}"
            </div>
          )}

          {filtered.map((item) => (
            <DrawerLink key={item.href} item={item} active={isActive(item.href)} />
          ))}
        </div>

        {/* FOOTER */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-soft)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 11,
          color: 'var(--muted)',
          fontFamily: 'var(--font-mono)',
        }}>
          <span style={{ letterSpacing: '0.04em' }}>
            ESC fecha · {time}
          </span>
          
        </div>
      </aside>

      <style jsx global>{`
        .topbar-nav-desktop::-webkit-scrollbar { display: none; }

        @media (max-width: 920px) {
          .topbar-nav-desktop { display: none !important; }
          .topbar-right-desktop { display: none !important; }
          .topbar-mobile-spacer { display: block !important; }
          .topbar-burger { display: flex !important; }
        }

        @media (max-width: 380px) {
          .topbar-brand {
            font-size: 13px !important;
            max-width: 140px !important;
          }
        }

        @keyframes pulse-soft {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.85); }
        }
      `}</style>
    </>
  );
}

/* ──── Hamburger Veggie ─────────────────────────────────────────────
   3 linhas creme (#F5F3EC) sobre fundo verde escuro Planta.
   Cada linha com largura diferente: 18px, 14px, 18px — toque orgânico.
   Ao abrir, animação fluida para X.
   ─────────────────────────────────────────────────────────────────── */
function BurgerIcon({ open }: { open: boolean }) {
  const baseLine: React.CSSProperties = {
    position: 'absolute',
    height: 2,
    background: '#F5F3EC',
    borderRadius: 2,
    transition: 'all 0.34s cubic-bezier(0.32, 0.72, 0, 1)',
    transformOrigin: 'center',
  };
  return (
    <span style={{ position: 'relative', width: 22, height: 14, display: 'inline-block' }}>
      {/* Linha de cima */}
      <span style={{
        ...baseLine,
        top: open ? 6 : 0,
        left: open ? 0 : 0,
        width: open ? 22 : 18,
        transform: open ? 'rotate(45deg)' : 'rotate(0)',
      }} />
      {/* Linha do meio — mais curta (toque orgânico) */}
      <span style={{
        ...baseLine,
        top: 6,
        left: open ? 0 : 4,
        width: open ? 0 : 14,
        opacity: open ? 0 : 1,
      }} />
      {/* Linha de baixo */}
      <span style={{
        ...baseLine,
        top: open ? 6 : 12,
        left: open ? 0 : 0,
        width: open ? 22 : 18,
        transform: open ? 'rotate(-45deg)' : 'rotate(0)',
      }} />
    </span>
  );
}

function DrawerLink({ item, active, small }: { item: NavItem; active: boolean; small?: boolean }) {
  return (
    <Link
      href={item.href}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: small ? '8px 8px' : '12px 8px',
        borderRadius: 8,
        textDecoration: 'none',
        background: active ? 'var(--green-pale)' : 'transparent',
        transition: 'background 0.14s',
        marginBottom: 1,
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.background = 'var(--bg-soft)';
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = 'transparent';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: active ? 'var(--green-dark)' : 'var(--faint)',
          flexShrink: 0,
          opacity: active ? 1 : 0.4,
          animation: active ? 'pulse-soft 1.6s ease-in-out infinite' : 'none',
        }} />
        <span style={{
          fontSize: small ? 14 : 16,
          fontWeight: active ? 600 : 500,
          color: 'var(--ink)',
          letterSpacing: '-0.01em',
          fontFamily: 'var(--font-display)',
        }}>
          {item.label}
        </span>
      </div>
      <span style={{
        fontSize: 10,
        color: 'var(--faint)',
        fontFamily: 'var(--font-mono)',
        letterSpacing: '0.06em',
        padding: '2px 6px',
        borderRadius: 4,
        border: '1px solid var(--border)',
        background: 'white',
        flexShrink: 0,
      }}>
        {item.hint}
      </span>
    </Link>
  );
}
