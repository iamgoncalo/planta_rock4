'use client';

import { useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  ts: number;
}

export default function PlantaSearchBar() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Msg[]>([]);
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open]);

  const send = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || sending) return;
    if (!open) setOpen(true);

    setMessages((m) => [...m, { role: 'user', content, ts: Date.now() }]);
    setInput('');
    setSending(true);

    try {
      const r = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      let reply = 'Desculpa, não consegui processar.';
      if (r.ok) {
        const j = await r.json();
        reply = j.reply || j.message || j.response || j.text || JSON.stringify(j).slice(0, 200);
      } else {
        reply = `Erro do servidor (${r.status}).`;
      }
      setMessages((m) => [...m, { role: 'assistant', content: reply, ts: Date.now() }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: 'Problema de ligação.', ts: Date.now() },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      {/* Painel de mensagens (acima da bar) */}
      {open && messages.length > 0 && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(13, 26, 15, 0.30)',
            backdropFilter: 'blur(6px)',
            WebkitBackdropFilter: 'blur(6px)',
            zIndex: 998,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end',
            paddingBottom: 120,
          }}
        >
          <div
            ref={scrollRef}
            style={{
              maxWidth: 760,
              width: 'calc(100% - 32px)',
              margin: '0 auto',
              maxHeight: 'min(60vh, 520px)',
              overflowY: 'auto',
              padding: '20px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  background: m.role === 'user' ? 'var(--ink)' : 'white',
                  color: m.role === 'user' ? 'white' : 'var(--ink)',
                  padding: '12px 16px',
                  borderRadius: 16,
                  maxWidth: '85%',
                  fontSize: 14.5,
                  lineHeight: 1.55,
                  whiteSpace: 'pre-wrap',
                  boxShadow: '0 4px 18px rgba(13, 26, 15, 0.10)',
                  border:
                    m.role === 'assistant' ? '1px solid var(--border)' : 'none',
                }}
              >
                {m.content}
              </div>
            ))}
            {sending && (
              <div
                style={{
                  alignSelf: 'flex-start',
                  background: 'white',
                  padding: '12px 16px',
                  borderRadius: 16,
                  border: '1px solid var(--border)',
                  fontSize: 13,
                  color: 'var(--muted)',
                  boxShadow: '0 4px 18px rgba(13, 26, 15, 0.10)',
                }}
              >
                <span style={{ animation: 'planta-dots 1.4s infinite' }}>
                  ● ● ●
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SearchBar fixa no fundo */}
      <div
        style={{
          position: 'fixed',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          width: 'min(720px, calc(100% - 32px))',
          zIndex: 999,
        }}
      >
        {open && (
          <button
            onClick={() => {
              setOpen(false);
              setMessages([]);
            }}
            style={{
              position: 'absolute',
              top: -40,
              right: 0,
              background: 'transparent',
              border: 'none',
              fontSize: 22,
              color: 'white',
              cursor: 'pointer',
              padding: 6,
              lineHeight: 1,
              textShadow: '0 1px 3px rgba(0,0,0,0.3)',
            }}
            aria-label="Fechar"
          >
            ✕
          </button>
        )}

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            background: 'white',
            border: '1px solid var(--border-strong)',
            borderRadius: 999,
            padding: '8px 8px 8px 14px',
            boxShadow:
              '0 14px 38px rgba(13, 26, 15, 0.12), 0 2px 6px rgba(13, 26, 15, 0.06)',
          }}
        >
          {/* Microfone */}
          <button
            type="button"
            title="Áudio (brevemente)"
            style={iconBtn}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--ink)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>

          {/* Clip */}
          <button type="button" title="Anexar" style={iconBtn}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--ink)" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>

          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') send();
            }}
            onFocus={() => {
              if (!open) setOpen(true);
            }}
            placeholder="Ask Planta anything about your building…"
            disabled={sending}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              padding: '10px 8px',
              fontSize: 15,
              color: 'var(--ink)',
              minWidth: 0,
              fontFamily: 'inherit',
            }}
          />

          {/* Send */}
          <button
            onClick={() => send()}
            disabled={!input.trim() || sending}
            style={{
              background: input.trim() ? 'var(--ink)' : '#EBE9E2',
              color: input.trim() ? 'white' : '#A0A39A',
              border: 'none',
              borderRadius: '50%',
              width: 38,
              height: 38,
              cursor: input.trim() && !sending ? 'pointer' : 'default',
              transition: 'background 0.15s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
            aria-label="Enviar"
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
            letterSpacing: '0.03em',
          }}
        >
          PlantaOS can make mistakes
        </div>
      </div>

      <style jsx global>{`
        @keyframes planta-dots {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </>
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
  transition: 'background 0.15s',
};
