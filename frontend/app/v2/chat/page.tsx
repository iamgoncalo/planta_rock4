'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLive, type LiveSnapshot } from '@/components/v2/LiveContext';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const STORAGE_KEY = 'planta-chat-history-v1';
const ATTACH_KEY = 'planta-pending-image';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  ts: number;
}

/* ──────────────────────────────────────────────────────────────────
   LOCAL ROUTING — determinístico, nunca dependente do LLM
   ────────────────────────────────────────────────────────────────── */

// Centroid aproximado do Parque Tejo (Lisboa)
const VENUE_CENTROID = { lat: 38.7636, lng: -9.0956 };

// Conversão metros ↔ graus, baseada em Palco Mundo como origem
const METER_PER_DEG_LAT = 111320;
const METER_PER_DEG_LNG = 111320 * Math.cos((VENUE_CENTROID.lat * Math.PI) / 180);

// Posições dos 8 clusters relativas ao Palco Mundo (em metros)
const CLUSTERS: Record<string, { x_m: number; y_m: number; zone: string }> = {
  'wc-01': { x_m: -380, y_m: 120,  zone: 'Entrada NW' },
  'wc-02': { x_m: 80,   y_m: -30,  zone: 'Junto ao palco' },
  'wc-03': { x_m: -100, y_m: 80,   zone: 'Central' },
  'wc-04': { x_m: -200, y_m: 200,  zone: 'Elevado mid' },
  'wc-05': { x_m: 250,  y_m: 180,  zone: 'Elevado leste (unissex)' },
  'wc-06': { x_m: -50,  y_m: 250,  zone: 'Central norte (unissex grande)' },
  'wc-07': { x_m: -300, y_m: -80,  zone: 'NW · lockers' },
  'wc-08': { x_m: 350,  y_m: 300,  zone: 'Outer leste' },
};

const COORDS_REGEX = /(-?\d{1,3}\.\d{2,8})\s*,\s*(-?\d{1,3}\.\d{2,8})/;

function detectCoords(text: string): { lat: number; lng: number } | null {
  const m = text.match(COORDS_REGEX);
  if (!m) return null;
  const lat = parseFloat(m[1]);
  const lng = parseFloat(m[2]);
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
  return { lat, lng };
}

function clusterPos(cid: string): { lat: number; lng: number } {
  const c = CLUSTERS[cid];
  if (!c) return VENUE_CENTROID;
  return {
    lat: VENUE_CENTROID.lat + c.y_m / METER_PER_DEG_LAT,
    lng: VENUE_CENTROID.lng + c.x_m / METER_PER_DEG_LNG,
  };
}

function haversine(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const R = 6371000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

interface Ranking {
  cid: string;
  distMeters: number;       // distância real user → cluster (só útil se dentro)
  walkSeconds: number;      // tempo a pé real (só útil se dentro)
  intraVenueDist: number;   // distância cluster → centroid (centralidade)
  occ: number;
  fila: number;
  waitSec: number;
  totalCost: number;
}

function recommendCluster(
  userLat: number,
  userLng: number,
  snapshot: LiveSnapshot | null,
): { best: Ranking; alt: Ranking | null; isOutside: boolean; venueDist: number } | null {
  const user = { lat: userLat, lng: userLng };
  const venueDist = haversine(user, VENUE_CENTROID);
  const isOutside = venueDist > 800; // > 800m do centroid = fora do recinto

  const sourceClusters = Object.keys(CLUSTERS);
  const liveMap = new Map(
    (snapshot?.clusters ?? []).map((c) => [c.cluster_id, c]),
  );

  // Se estás FORA do venue, o tempo a pé é DENTRO do recinto (da entrada/centro
  // ao WC), não desde a tua posição a centenas de km. Se estás DENTRO, é real.
  const refPoint = isOutside ? VENUE_CENTROID : user;

  const ranked: Ranking[] = sourceClusters
    .map((cid) => {
      const pos = clusterPos(cid);
      const distMeters = haversine(refPoint, pos);
      const walkSeconds = distMeters / 1.4; // ~1.4 m/s
      const intraVenueDist = haversine(pos, VENUE_CENTROID);
      const live = liveMap.get(cid);
      const occ = live?.params?.ocupacao_instantanea ?? 0;
      const fila = live?.params?.fila_atual ?? 0;
      const waitSec = (live?.params?.tempo_espera_min ?? 0) * 60;
      const congestionPenalty = occ >= 80 ? 90 : occ >= 60 ? 25 : 0;

      // REGRA CRÍTICA:
      // - DENTRO do recinto: a distância até ti conta (walk_time + queue + congestion).
      // - FORA: a distância de 200+ km é irrelevante. Rankeamos só pelo estado ao
      //   vivo (ocupação, fila, espera) + uma pequena preferência por clusters
      //   centrais (fáceis de encontrar). NUNCA por walkSeconds — senão escolhe-se
      //   o cluster marginalmente mais perto da tua cidade, o que é absurdo.
      const totalCost = isOutside
        ? waitSec + congestionPenalty + occ * 2 + (intraVenueDist / 1.4) * 0.3
        : walkSeconds + waitSec + congestionPenalty;

      return { cid, distMeters, walkSeconds, intraVenueDist, occ, fila, waitSec, totalCost };
    })
    .sort((a, b) => a.totalCost - b.totalCost);

  if (!ranked.length) return null;
  return { best: ranked[0], alt: ranked[1] || null, isOutside, venueDist };
}

function fmtDist(m: number): string {
  if (m < 1000) return `${Math.round(m)} m`;
  if (m < 10000) return `${(m / 1000).toFixed(1)} km`;
  return `${Math.round(m / 1000)} km`;
}

function fmtWalkMin(seconds: number): string {
  const m = Math.max(1, Math.round(seconds / 60));
  if (m > 90) {
    // Salvaguarda: distância absurda → piada, nunca um número ridículo
    return `${m} min 😅 — os nossos WC são inteligentes, mas não tão aventureiros!`;
  }
  return `${m} min`;
}

function formatRecommendation(
  rec: ReturnType<typeof recommendCluster>,
): string {
  if (!rec) {
    return 'Ainda não tenho dados ao vivo. Tenta em poucos segundos.';
  }
  const { best, alt, isOutside, venueDist } = rec;
  const cidUpper = best.cid.toUpperCase();
  const zone = CLUSTERS[best.cid]?.zone ?? '';
  const occLabel = `${Math.round(best.occ)}% ocupação`;
  const filaLabel = best.fila > 0 ? ` · ${best.fila} na fila` : ' · sem fila';
  const waitLabel = best.waitSec > 30 ? ` · ~${Math.round(best.waitSec / 60)} min espera` : '';

  if (isOutside) {
    // FORA do recinto: nada de tempo a pé absurdo. Mostra estado + zona.
    let txt = `Estás a ${fmtDist(venueDist)} do Parque Tejo. Quando chegares, a opção mais desafogada agora é:\n\n`;
    txt += `**${cidUpper}** · ${zone}\n`;
    txt += `${occLabel}${filaLabel}${waitLabel}`;
    if (alt && alt.cid !== best.cid) {
      txt += `\n\nEm segundo: **${alt.cid.toUpperCase()}** — ${Math.round(alt.occ)}% ocupação.`;
    }
    txt += `\n\nQuando entrares no recinto, partilha a localização outra vez e dou-te o caminho a pé exacto.`;
    return txt;
  }

  // DENTRO: caminho real
  let txt = `**${cidUpper}** · ${zone}\n`;
  txt += `${fmtDist(best.distMeters)} · ~${fmtWalkMin(best.walkSeconds)} a pé\n`;
  txt += `${occLabel}${filaLabel}${waitLabel}`;
  if (alt && alt.cid !== best.cid) {
    txt += `\n\nAlternativa: **${alt.cid.toUpperCase()}** — ${fmtWalkMin(alt.walkSeconds)} a pé, ${Math.round(alt.occ)}% ocupação.`;
  }
  return txt;
}

/* ──────────────────────────────────────────────────────────────────
   HISTÓRICO LOCAL
   ────────────────────────────────────────────────────────────────── */

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

function isImageDataUrl(s: string): boolean {
  return typeof s === 'string' && s.startsWith('data:image/');
}

/* Suporte simples a markdown: **bold** + quebras de linha */
function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let idx = 0;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(<strong key={idx++}>{m[1]}</strong>);
    last = regex.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function MessageContent({ content }: { content: string }) {
  if (isImageDataUrl(content)) {
    return <ImageBubble src={content} />;
  }
  const lines = content.split('\n');
  return (
    <>
      {lines.map((line, i) => (
        <span key={i}>
          {renderInline(line)}
          {i < lines.length - 1 && <br />}
        </span>
      ))}
    </>
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
          color: 'rgba(255,255,255,0.9)',
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

/* ──────────────────────────────────────────────────────────────────
   COMPONENT
   ────────────────────────────────────────────────────────────────── */

function ChatInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { snapshot } = useLive();
  const snapshotRef = useRef<LiveSnapshot | null>(null);
  snapshotRef.current = snapshot;

  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const handledQuery = useRef<string | null>(null);

  useEffect(() => {
    setMessages(loadHistory());
    // Aceitar imagem anexada via sessionStorage
    try {
      const raw = sessionStorage.getItem(ATTACH_KEY);
      if (raw) {
        const data = JSON.parse(raw);
        sessionStorage.removeItem(ATTACH_KEY);
        if (data && data.dataUrl) {
          const imgMsg: Msg = {
            role: 'user',
            content: data.dataUrl,
            ts: Date.now(),
          };
          setMessages((prev) => {
            const next = [...prev, imgMsg];
            saveHistory(next);
            return next;
          });
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

    // ╔═════════════════════════════════════════════════════════╗
    // ║ INTERCEPT: coordenadas → routing local determinístico   ║
    // ║ NUNCA "sem dados" quando há coords.                     ║
    // ╚═════════════════════════════════════════════════════════╝
    const coords = detectCoords(content);
    if (coords) {
      // Espera 250ms para parecer "a pensar" + esperar pelo primeiro tick do useLive
      await new Promise((r) => setTimeout(r, 250));
      const rec = recommendCluster(coords.lat, coords.lng, snapshotRef.current);
      const reply = formatRecommendation(rec);
      const aiMsg: Msg = { role: 'assistant', content: reply, ts: Date.now() };
      setMessages((m) => {
        const next = [...m, aiMsg];
        saveHistory(next);
        return next;
      });
      setSending(false);
      return;
    }

    // Fluxo normal — chamar /api/v1/chat
    try {
      const r = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      let reply = 'Desculpa, não consegui processar.';
      if (r.ok) {
        const j = await r.json();
        reply =
          j.reply ||
          j.message ||
          j.response ||
          j.text ||
          JSON.stringify(j).slice(0, 200);
      } else {
        reply = `Erro do servidor (${r.status}).`;
      }
      const aiMsg: Msg = { role: 'assistant', content: reply, ts: Date.now() };
      setMessages((m) => {
        const next = [...m, aiMsg];
        saveHistory(next);
        return next;
      });
    } catch {
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

  const askLocation = () => {
    if (!('geolocation' in navigator)) {
      alert('Geolocalização não suportada neste browser.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        send(`Estou em ${latitude.toFixed(6)}, ${longitude.toFixed(6)}. Qual a casa-de-banho mais próxima?`);
      },
      (err) => alert(`Não consegui obter localização: ${err.message}`),
      { timeout: 8000, enableHighAccuracy: true },
    );
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 'var(--topbar-h, 72px)',
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg, #FBFAF7)',
      }}
    >
      {/* Header fixo */}
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          padding: '14px clamp(16px, 4vw, 40px)',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg, #FBFAF7)',
        }}
      >
        <div>
          <div className="section-label">Chat · Planta Smart Homes</div>
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 'clamp(20px, 3vw, 28px)',
              fontWeight: 500,
              letterSpacing: '-0.03em',
              lineHeight: 1,
              marginTop: 3,
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
              flexShrink: 0,
              fontFamily: 'inherit',
            }}
          >
            Limpar
          </button>
        )}
      </div>

      {/* Área de mensagens — scroll INTERNO (tipo WhatsApp) */}
      <div
        ref={scrollRef}
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: 'clamp(16px, 3vw, 28px) clamp(16px, 4vw, 40px)',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {messages.length === 0 && (
          <div style={{ color: 'var(--muted)', maxWidth: 560 }}>
            <p style={{ fontSize: 16, lineHeight: 1.55, marginBottom: 18 }}>
              Sou o assistente da Planta. Pergunta-me sobre os clusters,
              ocupação, filas — ou partilha a tua localização para a
              recomendação mais rápida.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
              <button
                onClick={askLocation}
                style={{
                  background: 'var(--green-dark, #1B3A21)',
                  color: 'white',
                  border: 'none',
                  borderRadius: 999,
                  padding: '8px 16px',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                📍 Onde está o WC mais perto?
              </button>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {[
                'Qual o cluster mais cheio agora?',
                'Quantas pessoas há agora no festival?',
                'Quando é a próxima limpeza?',
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  style={{
                    background: 'white',
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

        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? 'var(--ink)' : 'white',
              color: m.role === 'user' ? 'white' : 'var(--ink)',
              padding: '11px 15px',
              borderRadius: 16,
              maxWidth: '85%',
              fontSize: 15,
              lineHeight: 1.55,
              border: m.role === 'assistant' ? '1px solid var(--border)' : 'none',
              boxShadow: m.role === 'assistant' ? 'var(--shadow-sm)' : 'none',
              wordBreak: 'break-word',
            }}
          >
            <MessageContent content={m.content} />
          </div>
        ))}
        {sending && (
          <div
            style={{
              alignSelf: 'flex-start',
              background: 'white',
              padding: '11px 15px',
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

      {/* Input próprio fixo no fundo (tipo WhatsApp) */}
      <div
        style={{
          flexShrink: 0,
          padding: 'clamp(10px, 2vw, 16px) clamp(16px, 4vw, 40px)',
          borderTop: '1px solid var(--border)',
          background: 'var(--bg, #FBFAF7)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            maxWidth: 820,
            margin: '0 auto',
            background: 'white',
            border: '1px solid var(--green-dark, #1B3A21)',
            borderRadius: 999,
            padding: '6px 6px 6px 8px',
          }}
        >
          <button
            type="button"
            onClick={askLocation}
            title="Partilhar localização"
            aria-label="Localização"
            style={{
              background: 'transparent',
              border: 'none',
              width: 38,
              height: 38,
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              color: 'var(--ink)',
              fontSize: 18,
            }}
          >
            📍
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
            placeholder="Pergunta à Planta…"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              padding: '10px 6px',
              fontSize: 15.5,
              color: 'var(--ink)',
              minWidth: 0,
              fontFamily: 'inherit',
            }}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || sending}
            aria-label="Enviar"
            style={{
              background: input.trim() && !sending ? 'var(--green-dark, #1B3A21)' : '#EBE9E2',
              color: input.trim() && !sending ? 'white' : '#A0A39A',
              border: 'none',
              borderRadius: '50%',
              width: 40,
              height: 40,
              cursor: input.trim() && !sending ? 'pointer' : 'default',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              transition: 'background 0.15s',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
          </button>
        </div>
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

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="page" style={{ maxWidth: 820 }}>
          <div className="section-label">Chat · a carregar…</div>
        </div>
      }
    >
      <ChatInner />
    </Suspense>
  );
}
