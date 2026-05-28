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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Focus input when open
  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const send = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || sending) return;

    // Abrir painel ao enviar primeira mensagem
    if (!open) setOpen(true);

    setMessages(m => [...m, { role: 'user', content, ts: Date.now() }]);
    setInput('');
    setSending(true);

    try {
      const r = await fetch(`${API_BASE}/api/v1/chat/ask`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      let reply = 'Desculpa, não consegui processar.';
      if (r.ok) {
        const j = await r.json();
        reply = j.reply || j.message || j.response || JSON.stringify(j).slice(0, 200);
      } else {
        reply = `Erro do servidor (${r.status}). Tenta novamente.`;
      }
      setMessages(m => [...m, { role: 'assistant', content: reply, ts: Date.now() }]);
    } catch (e) {
      setMessages(m => [...m, {
        role: 'assistant',
        content: 'Problema de ligação. Verifica a tua rede.',
        ts: Date.now(),
      }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      {/* Painel de mensagens (acima da searchbar quando aberto) */}
      {open && messages.length > 0 && (
        <div
          onClick={(e) => {
            // Click no backdrop fecha
            if (e.target === e.currentTarget) setOpen(false);
          }}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.3)',
            backdropFilter: 'blur(4px)',
            WebkitBackdropFilter: 'blur(4px)',
            zIndex: 998,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end',
            paddingBottom: 110,
            pointerEvents: 'auto',
          }}
        >
          <div
            style={{
              maxWidth: 760,
              width: 'calc(100% - 32px)',
              margin: '0 auto',
              maxHeight: 'min(60vh, 500px)',
              overflowY: 'auto',
              padding: 16,
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
                  background: m.role === 'user' ? '#1B3A21' : 'white',
                  color: m.role === 'user' ? 'white' : '#1A1A1A',
                  padding: '10px 14px',
                  borderRadius: 14,
                  maxWidth: '85%',
                  fontSize: 14,
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  border: m.role === 'assistant' ? '1px solid rgba(0,0,0,0.06)' : 'none',
                }}
              >{m.content}</div>
            ))}
            {sending && (
              <div style={{
                alignSelf: 'flex-start',
                background: 'white',
                padding: '10px 14px',
                borderRadius: 14,
                border: '1px solid rgba(0,0,0,0.06)',
                fontSize: 13,
                color: '#888',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              }}>
                <span style={{ animation: 'planta-blink 1.4s infinite' }}>● ● ●</span>
              </div>
            )}
            <div ref={messagesEndRef} />
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
          width: 'min(760px, calc(100% - 32px))',
          zIndex: 999,
        }}
      >
        {/* X close button quando aberto */}
        {open && (
          <button
            onClick={() => { setOpen(false); setMessages([]); }}
            style={{
              position: 'absolute',
              top: -36,
              right: 0,
              background: 'transparent',
              border: 'none',
              fontSize: 22,
              color: '#666',
              cursor: 'pointer',
              padding: 4,
              lineHeight: 1,
            }}
            aria-label="Fechar"
          >✕</button>
        )}

        {/* Input bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'white',
            border: '1px solid rgba(74, 124, 89, 0.35)',
            borderRadius: 999,
            padding: '8px 8px 8px 14px',
            boxShadow: '0 8px 24px rgba(27, 58, 33, 0.10), 0 2px 6px rgba(27, 58, 33, 0.06)',
          }}
        >
          {/* Microphone */}
          <button
            type="button"
            title="Áudio (em breve)"
            style={iconBtnStyle}
            onClick={() => {}}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1B3A21" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          </button>

          {/* Clip / attach */}
          <button
            type="button"
            title="Anexar (em breve)"
            style={iconBtnStyle}
            onClick={() => {}}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1B3A21" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
            onFocus={() => { if (!open) setOpen(true); }}
            placeholder="Ask Planta anything about your building…"
            disabled={sending}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              padding: '8px 8px',
              fontSize: 15,
              color: '#1A1A1A',
              minWidth: 0,
            }}
          />

          {/* Send button */}
          <button
            onClick={() => send()}
            disabled={!input.trim() || sending}
            style={{
              background: input.trim() ? '#1B3A21' : '#E8E5DD',
              color: input.trim() ? 'white' : '#999',
              border: 'none',
              borderRadius: '50%',
              width: 36,
              height: 36,
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
              <line x1="12" y1="19" x2="12" y2="5"/>
              <polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>

        {/* Subtle footer note */}
        <div
          style={{
            textAlign: 'center',
            marginTop: 8,
            fontSize: 11,
            color: '#888',
            fontFamily: 'var(--font-mono), monospace',
            letterSpacing: '0.04em',
          }}
        >
          PlantaOS can make mistakes
        </div>
      </div>

      <style jsx global>{`
        @keyframes planta-blink {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </>
  );
}

const iconBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  width: 32,
  height: 32,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  flexShrink: 0,
  padding: 0,
};
