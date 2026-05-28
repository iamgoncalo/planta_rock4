'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function PlantaSearchBar() {
  const router = useRouter();
  const [input, setInput] = useState('');
  const [focused, setFocused] = useState(false);

  const submit = (text?: string) => {
    const content = (text ?? input).trim();
    if (!content) return;
    // Naviga para /v2/chat e passa a mensagem
    router.push(`/v2/chat?q=${encodeURIComponent(content)}`);
    setInput('');
  };

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 22,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(720px, calc(100% - 32px))',
        zIndex: 99,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          background: 'white',
          border: `1px solid ${focused ? 'var(--green-dark)' : 'var(--border-strong)'}`,
          borderRadius: 999,
          padding: '8px 8px 8px 16px',
          boxShadow: focused
            ? '0 18px 48px rgba(27, 58, 33, 0.18), 0 2px 6px rgba(27, 58, 33, 0.08)'
            : '0 14px 38px rgba(13, 26, 15, 0.10), 0 2px 6px rgba(13, 26, 15, 0.04)',
          transition: 'all 0.18s',
        }}
      >
        {/* Microfone */}
        <button type="button" title="Áudio" style={iconBtn} tabIndex={-1}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--ink)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        </button>

        {/* Clip */}
        <button type="button" title="Anexar" style={iconBtn} tabIndex={-1}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--ink)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit();
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ask Planta anything about your building…"
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            padding: '10px 8px',
            fontSize: 15.5,
            color: 'var(--ink)',
            minWidth: 0,
            fontFamily: 'inherit',
            letterSpacing: '-0.005em',
          }}
        />

        {/* Send button — VERDE ESCURO */}
        <button
          onClick={() => submit()}
          disabled={!input.trim()}
          style={{
            background: input.trim() ? 'var(--green-dark, #1B3A21)' : '#EBE9E2',
            color: input.trim() ? 'white' : '#A0A39A',
            border: 'none',
            borderRadius: '50%',
            width: 40,
            height: 40,
            cursor: input.trim() ? 'pointer' : 'default',
            transition: 'background 0.15s, transform 0.15s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
          onMouseEnter={(e) => {
            if (input.trim()) e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
          aria-label="Enviar para chat"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>

      {/* Caption */}
      <div
        style={{
          textAlign: 'center',
          marginTop: 10,
          fontSize: 11,
          color: 'var(--muted)',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.04em',
        }}
      >
        PlantaOS can make mistakes
      </div>
    </div>
  );
}

const iconBtn: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  width: 36,
  height: 36,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  flexShrink: 0,
  padding: 0,
};
