'use client';

import { useEffect, useRef, useState } from 'react';
import {
  api,
  aggregateClusters,
  CLUSTERS,
  type ClusterLive,
} from '@/lib/v2-api';

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  ts: number;
  pending?: boolean;
  error?: boolean;
  grounded?: boolean;
  liveData?: boolean;
}

const SUGGESTIONS = [
  'Qual o WC mais livre agora?',
  'Onde está o pico de fila?',
  'Quando vai haver surge depois do headliner?',
  'Resume o estado dos 8 clusters em duas frases.',
];

const WELCOME =
  'Olá! Sou o assistente PlantaOS, ligado em tempo real aos 8 clusters WC do Parque Tejo. ' +
  'Pergunta-me qual a casa de banho mais rápida, onde está a fila a crescer, ou o que esperar a seguir ao próximo show. Respondo em português europeu.';

export default function ChatPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([
    { role: 'assistant', content: WELCOME, ts: Date.now() },
  ]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [clusters, setClusters] = useState<ClusterLive[]>([]);
  const [contextOk, setContextOk] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Contexto live a cada 15s a partir de /api/v1/clusters
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await api.clusters();
        if (cancelled) return;
        setClusters(aggregateClusters(r.clusters ?? []));
        setContextOk(true);
      } catch {
        if (!cancelled) setContextOk(false);
      }
    };
    tick();
    const iv = setInterval(tick, 15_000);
    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const userMsg: DisplayMessage = {
      role: 'user',
      content: trimmed,
      ts: Date.now(),
    };
    const pendingMsg: DisplayMessage = {
      role: 'assistant',
      content: '',
      ts: Date.now() + 1,
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setInput('');
    setSending(true);

    try {
      const reply = await api.chat(trimmed);
      setMessages((prev) =>
        prev.map((m) =>
          m.ts === pendingMsg.ts
            ? {
                role: 'assistant',
                content: reply.reply,
                ts: m.ts,
                grounded: reply.grounded,
                liveData: reply.live_data_available,
              }
            : m,
        ),
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.ts === pendingMsg.ts
            ? {
                role: 'assistant',
                content:
                  'Não consegui obter resposta. O serviço Gemini pode estar offline ou em rate-limit. Tenta novamente em alguns segundos.',
                ts: m.ts,
                error: true,
              }
            : m,
        ),
      );
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const critCount = clusters.filter((c) => c.status === 'critical').length;
  const warnCount = clusters.filter((c) => c.status === 'warning').length;
  const totalPeople = clusters.reduce((a, c) => a + c.pessoas, 0);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 320px',
        height: 'calc(100vh - 56px - 36px)',
        background: 'var(--surface)',
      }}
    >
      {/* CHAT COLUMN */}
      <section
        style={{
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg)',
          borderRight: '1px solid var(--border)',
          minHeight: 0,
        }}
      >
        <div
          style={{
            padding: '18px 28px 14px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--card)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            gap: 16,
          }}
        >
          <div>
            <div className="section-label" style={{ marginBottom: 4 }}>
              Assistente PlantaOS
            </div>
            <h1
              className="serif"
              style={{
                fontSize: 24,
                fontWeight: 500,
                color: 'var(--ink)',
                lineHeight: 1.1,
                letterSpacing: '-0.01em',
              }}
            >
              Pergunta-me sobre os 8 clusters.
            </h1>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
              Gemini 2.5 Flash · contexto ao vivo injectado · PT-PT
            </p>
          </div>
          <span
            className="pill"
            style={{
              background: contextOk ? 'var(--ok-bg)' : 'var(--amber-bg)',
              color: contextOk ? 'var(--green)' : 'var(--amber)',
              border: contextOk
                ? '1px solid rgba(46,125,79,0.20)'
                : '1px solid rgba(168,93,0,0.20)',
              flexShrink: 0,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: contextOk ? 'var(--green)' : 'var(--amber)',
                animation: 'pulse 1.6s ease-in-out infinite',
              }}
            />
            {contextOk ? 'CONTEXTO LIVE' : 'BACKEND OFFLINE'}
          </span>
        </div>

        <div
          ref={scrollRef}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px 28px',
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            minHeight: 0,
          }}
        >
          {messages.map((m, i) => (
            <Message key={`${m.ts}-${i}`} m={m} />
          ))}
        </div>

        {messages.length <= 1 && (
          <div
            style={{
              padding: '0 28px 14px',
              display: 'flex',
              gap: 8,
              flexWrap: 'wrap',
            }}
          >
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                disabled={sending}
                className="btn btn-outline btn-sm"
                style={{ fontWeight: 500, background: 'var(--card)' }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div
          style={{
            padding: '14px 28px 20px',
            borderTop: '1px solid var(--border)',
            background: 'var(--card)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'flex-end',
              gap: 10,
              background: 'var(--surface)',
              border: '1.5px solid var(--border)',
              borderRadius: 12,
              padding: '10px 12px',
            }}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Pergunta sobre fluxos, filas, ou onde está o pico..."
              rows={1}
              disabled={sending}
              style={{
                flex: 1,
                border: 'none',
                outline: 'none',
                background: 'transparent',
                resize: 'none',
                fontFamily: 'inherit',
                fontSize: 14,
                color: 'var(--ink)',
                minHeight: 24,
                maxHeight: 160,
                lineHeight: 1.5,
              }}
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || sending}
              className="btn btn-primary"
              style={{
                opacity: !input.trim() || sending ? 0.5 : 1,
                pointerEvents: !input.trim() || sending ? 'none' : 'auto',
              }}
            >
              {sending ? '...' : 'Enviar →'}
            </button>
          </div>
          <div
            style={{
              fontSize: 10,
              color: 'var(--faint)',
              marginTop: 8,
              fontFamily: 'var(--font-mono), monospace',
              letterSpacing: '0.06em',
            }}
          >
            Enter envia · Shift+Enter nova linha · respostas não guardadas
          </div>
        </div>
      </section>

      {/* CONTEXT COLUMN */}
      <aside
        style={{
          padding: '22px 22px 32px',
          overflowY: 'auto',
          background: 'var(--surface)',
        }}
      >
        <div className="section-label" style={{ marginBottom: 10 }}>
          Contexto injectado
        </div>
        <p
          style={{
            fontSize: 11,
            color: 'var(--muted)',
            marginBottom: 18,
            lineHeight: 1.6,
          }}
        >
          O modelo recebe o estado destes 8 clusters em cada pergunta. Refresh a
          cada 15 s. Quando a resposta tem o badge ✓ grounded, foi construída a
          partir destes dados.
        </p>

        <div
          style={{
            background: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: '14px 16px',
            marginBottom: 14,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 10,
          }}
        >
          <Stat label="Pessoas" value={totalPeople.toLocaleString('pt-PT')} />
          <Stat
            label="Críticos"
            value={String(critCount)}
            col={critCount > 0 ? 'var(--critical)' : 'var(--green)'}
          />
          <Stat
            label="Avisos"
            value={String(warnCount)}
            col={warnCount > 0 ? 'var(--amber)' : 'var(--green)'}
          />
          <Stat label="Clusters" value="8" />
        </div>

        <div
          style={{
            fontSize: 10,
            color: 'var(--faint)',
            fontWeight: 700,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            marginBottom: 8,
          }}
        >
          Estado por cluster
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {(clusters.length
            ? clusters
            : CLUSTERS.map((m) => ({
                meta: m,
                ocupacao: 0,
                status: 'ok' as const,
                pessoas: 0,
                filaTotal: 0,
                esperaMin: 0,
                entradas: 0,
                saidas: 0,
                confianca: 0.5,
                simulated: true,
                homens: null,
                mulheres: null,
              }))
          ).map((c) => {
            const col =
              c.status === 'critical'
                ? 'var(--critical)'
                : c.status === 'warning'
                ? 'var(--amber)'
                : 'var(--green-light)';
            return (
              <div
                key={c.meta.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '7px 10px',
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 11,
                }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      background: col,
                    }}
                  />
                  <span className="mono" style={{ fontWeight: 600, color: 'var(--text)' }}>
                    {c.meta.id.toUpperCase()}
                  </span>
                  <span style={{ color: 'var(--faint)', fontSize: 10 }}>{c.meta.zone}</span>
                </span>
                <span className="mono" style={{ color: 'var(--text)', fontWeight: 600 }}>
                  {c.ocupacao}%
                </span>
              </div>
            );
          })}
        </div>

        <div
          style={{
            marginTop: 20,
            padding: '12px 14px',
            background: 'var(--green-pale)',
            borderRadius: 8,
            fontSize: 11,
            color: 'var(--muted)',
            lineHeight: 1.6,
          }}
        >
          O modelo nunca inventa dados. Se a métrica não estiver no contexto,
          responde "sem dados disponíveis".
        </div>
      </aside>
    </div>
  );
}

function Message({ m }: { m: DisplayMessage }) {
  const isUser = m.role === 'user';
  return (
    <div
      className="fade-in"
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      <div
        style={{
          maxWidth: '76%',
          background: isUser ? 'var(--green-dark)' : 'var(--card)',
          color: isUser ? '#FFFFFF' : 'var(--ink)',
          border: isUser ? 'none' : '1px solid var(--border)',
          borderRadius: 14,
          padding: '12px 16px',
          fontSize: 14,
          lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          boxShadow: isUser ? 'none' : 'var(--shadow-sm)',
        }}
      >
        {m.pending ? (
          <span
            style={{
              display: 'inline-flex',
              gap: 4,
              alignItems: 'center',
              color: 'var(--faint)',
            }}
          >
            <Dot delay={0} />
            <Dot delay={0.15} />
            <Dot delay={0.3} />
          </span>
        ) : m.error ? (
          <span style={{ color: 'var(--critical)', fontSize: 13 }}>{m.content}</span>
        ) : (
          m.content
        )}
        {!m.pending && !isUser && (
          <div
            className="mono"
            style={{
              fontSize: 9,
              color: 'var(--faint)',
              marginTop: 8,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              display: 'flex',
              gap: 10,
              alignItems: 'center',
            }}
          >
            <span>Gemini 2.5 Flash</span>
            {m.grounded && (
              <span style={{ color: 'var(--green)', fontWeight: 700 }}>✓ grounded</span>
            )}
            {m.liveData && (
              <span style={{ color: 'var(--green)', fontWeight: 700 }}>● live</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      style={{
        width: 7,
        height: 7,
        borderRadius: '50%',
        background: 'currentColor',
        opacity: 0.6,
        animation: 'pulse 1.2s ease-in-out infinite',
        animationDelay: `${delay}s`,
        display: 'inline-block',
      }}
    />
  );
}

function Stat({
  label,
  value,
  col = 'var(--ink)',
}: {
  label: string;
  value: string;
  col?: string;
}) {
  return (
    <div>
      <div
        className="serif"
        style={{
          fontSize: 22,
          fontWeight: 500,
          color: col,
          lineHeight: 1,
          letterSpacing: '-0.02em',
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: 9,
          color: 'var(--faint)',
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          fontWeight: 600,
          marginTop: 3,
        }}
      >
        {label}
      </div>
    </div>
  );
}
