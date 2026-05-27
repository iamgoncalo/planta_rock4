'use client';

import { useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  ts: number;
}

const SUGGESTIONS = [
  'Qual o cluster mais cheio agora?',
  'Quem está a limpar o WC-04?',
  'Quando é a próxima limpeza?',
  'Quantas pessoas há agora no festival?',
];

export default function PlantaChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Mensagem de boas-vindas ao abrir
  useEffect(() => {
    if (open && messages.length === 0) {
      setMessages([{
        role: 'assistant',
        content: 'Olá! Sou o assistente da Planta Smart Homes. Pergunte-me qualquer coisa sobre o festival, os clusters, ou a operação.',
        ts: Date.now(),
      }]);
    }
  }, [open, messages.length]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const send = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || sending) return;

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
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          style={{
            position: 'fixed',
            bottom: 22,
            right: 22,
            zIndex: 999,
            width: 60,
            height: 60,
            borderRadius: '50%',
            background: '#1B3A21',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 10px 30px rgba(27,58,33,0.35)',
            fontSize: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          aria-label="Abrir chat"
        >
          💬
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div style={{
          position: 'fixed',
          bottom: 22,
          right: 22,
          width: 'min(380px, calc(100vw - 32px))',
          height: 'min(560px, calc(100vh - 120px))',
          background: 'white',
          borderRadius: 16,
          boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
          zIndex: 999,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid var(--color-border)',
        }}>
          {/* Header */}
          <div style={{
            background: '#1B3A21',
            color: 'white',
            padding: '14px 16px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <div>
              <div className="serif" style={{ fontSize: 16, fontWeight: 600, lineHeight: 1 }}>
                Planta Smart Homes
              </div>
              <div className="mono" style={{ fontSize: 10, opacity: 0.7, marginTop: 3, letterSpacing: '0.08em' }}>
                ● online · Gemini 2.5
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                background: 'transparent', border: 'none', color: 'white',
                fontSize: 18, cursor: 'pointer', opacity: 0.7,
              }}
              aria-label="Fechar"
            >✕</button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} style={{
            flex: 1,
            overflowY: 'auto',
            padding: 14,
            background: '#FAFAF7',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}>
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  background: m.role === 'user' ? '#1B3A21' : 'white',
                  color: m.role === 'user' ? 'white' : 'var(--color-ink)',
                  padding: '8px 12px',
                  borderRadius: 12,
                  maxWidth: '85%',
                  fontSize: 13,
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                  border: m.role === 'assistant' ? '1px solid var(--color-border)' : 'none',
                }}
              >{m.content}</div>
            ))}
            {sending && (
              <div style={{
                alignSelf: 'flex-start',
                background: 'white',
                padding: '8px 12px',
                borderRadius: 12,
                border: '1px solid var(--color-border)',
                fontSize: 13,
                color: 'var(--color-muted)',
              }}>
                <span style={{ animation: 'blink 1.4s infinite' }}>● ● ●</span>
              </div>
            )}
          </div>

          {/* Sugestões (só na 1ª mensagem) */}
          {messages.length <= 1 && (
            <div style={{
              padding: '8px 14px',
              display: 'flex', flexWrap: 'wrap', gap: 5,
              borderTop: '1px solid var(--color-border)',
              background: 'white',
            }}>
              {SUGGESTIONS.slice(0, 3).map(s => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  style={{
                    background: '#F4F2EB',
                    border: '1px solid var(--color-border)',
                    borderRadius: 999,
                    padding: '5px 10px',
                    fontSize: 11,
                    cursor: 'pointer',
                    color: 'var(--color-ink)',
                  }}
                >{s}</button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{
            padding: 10,
            borderTop: '1px solid var(--color-border)',
            background: 'white',
            display: 'flex',
            gap: 6,
          }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
              placeholder="Pergunta-me algo..."
              disabled={sending}
              style={{
                flex: 1,
                background: '#FAFAF7',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                padding: '8px 12px',
                fontSize: 13,
                outline: 'none',
              }}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || sending}
              style={{
                background: '#1B3A21',
                color: 'white',
                border: 'none',
                borderRadius: 8,
                padding: '8px 14px',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
                opacity: !input.trim() || sending ? 0.5 : 1,
              }}
            >↑</button>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes blink {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </>
  );
}
