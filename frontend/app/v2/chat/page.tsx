'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const STORAGE_KEY = 'planta-chat-history-v1';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  ts: number;
}

function loadHistory(): Msg[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    return [];
  } catch {
    return [];
  }
}

function saveHistory(msgs: Msg[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-200)));
  } catch {}
}

// Inner component que USA useSearchParams — tem de estar dentro de Suspense
function ChatInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const handledQuery = useRef<string | null>(null);

  useEffect(() => {
    setMessages(loadHistory());
    // v20: aceitar imagem anexada via sessionStorage
    try {
      const raw = sessionStorage.getItem('planta-pending-image');
      if (raw) {
        const data = JSON.parse(raw);
        sessionStorage.removeItem('planta-pending-image');
        if (data && data.dataUrl) {
          const imgMsg = {
            role: 'user' as const,
            content: data.dataUrl,
            ts: Date.now(),
          };
          setMessages((prev) => [...prev, imgMsg]);
        }
      }
    } catch {}
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    const q = params?.get('q');
    if (q && handledQuery.current !== q) {
      handledQuery.current = q;
      send(q);
      router.replace('/v2/chat', { scroll: false });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const send = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || sending) return;
    const userMsg: Msg = { role: 'user', content, ts: Date.now() };
    setMessages((m) => {
      const next = [...m, userMsg];
      saveHistory(next);
      return next;
    });
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
      const aiMsg: Msg = { role: 'assistant', content: reply, ts: Date.now() };
      setMessages((m) => {
        const next = [...m, aiMsg];
        saveHistory(next);
        return next;
      });
    } catch (e) {
      const errMsg: Msg = {
        role: 'assistant',
        content: 'Problema de ligação. Verifica a rede.',
        ts: Date.now(),
      };
      setMessages((m) => {
        const next = [...m, errMsg];
        saveHistory(next);
        return next;
      });
    } finally {
      setSending(false);
    }
  };

  const clearHistory = () => {
    if (confirm('Limpar todo o histórico de conversa?')) {
      setMessages([]);
      saveHistory([]);
    }
  };

  return (
    <div className="page" style={{ maxWidth: 820, paddingBottom: 32 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-end',
          marginBottom: 24,
          borderBottom: '1px solid var(--border)',
          paddingBottom: 18,
        }}
      >
        <div>
          <div className="section-label">Chat · Planta Smart Homes</div>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(28px, 4vw, 44px)',
              fontWeight: 500,
              letterSpacing: '-0.03em',
              lineHeight: 1,
              marginTop: 6,
            }}
          >
            Ask Planta anything
          </h2>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-strong)',
              borderRadius: 999,
              padding: '6px 14px',
              fontSize: 12,
              color: 'var(--muted)',
              cursor: 'pointer',
            }}
          >
            Limpar histórico
          </button>
        )}
      </div>

      {messages.length === 0 && (
        <div style={{ padding: '40px 0 20px', color: 'var(--muted)' }}>
          <p style={{ fontSize: 17, lineHeight: 1.55, maxWidth: 560, marginBottom: 18 }}>
            Sou o assistente da Planta Smart Homes. Pergunta-me sobre clusters, ocupação,
            limpeza, equipas, sensores ou qualquer coisa do festival.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {[
              'Qual o cluster mais cheio agora?',
              'Quem está a limpar o WC-04?',
              'Quando é a próxima limpeza?',
              'Quantas pessoas há agora no festival?',
            ].map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                style={{
                  background: 'var(--bg-soft)',
                  border: '1px solid var(--border)',
                  borderRadius: 999,
                  padding: '7px 13px',
                  fontSize: 12.5,
                  cursor: 'pointer',
                  color: 'var(--ink)',
                  fontFamily: 'inherit',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      <div
        ref={scrollRef}
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          marginBottom: 24,
          maxHeight: 'calc(100vh - 360px)',
          overflowY: 'auto',
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
              fontSize: 15,
              lineHeight: 1.55,
              whiteSpace: 'pre-wrap',
              border: m.role === 'assistant' ? '1px solid var(--border)' : 'none',
              boxShadow: m.role === 'assistant' ? 'var(--shadow-sm)' : 'none',
            }}
          >
            {isImageDataUrl(m.content) ? (
              <ImageBubble src={m.content} />
            ) : (
              m.content
            )}
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
            }}
          >
            <span style={{ animation: 'dots 1.4s infinite' }}>● ● ●</span>
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes dots {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// Outer component — Suspense wrapper exigido pelo Next.js 14 quando se usa useSearchParams

function isImageDataUrl(s: string): boolean {
  return typeof s === 'string' && s.startsWith('data:image/');
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="page" style={{ maxWidth: 820 }}>
          <div className="section-label">Chat · a carregar...</div>
        </div>
      }
    >
      <ChatInner />
    </Suspense>
  );
}

function ImageBubble({ src }: { src: string }) {
  const filename = `planta-${Date.now()}.png`;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <img
        src={src}
        alt="imagem anexada"
        style={{
          maxWidth: '100%',
          maxHeight: 360,
          borderRadius: 12,
          display: 'block',
        }}
      />
      <a
        href={src}
        download={filename}
        style={{
          fontSize: 11,
          color: 'rgba(255,255,255,0.85)',
          textDecoration: 'underline',
          textAlign: 'right',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.04em',
        }}
      >
        ⬇ guardar
      </a>
    </div>
  );
}
