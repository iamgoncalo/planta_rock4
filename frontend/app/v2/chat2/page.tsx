'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLive, type LiveSnapshot } from '@/components/v2/LiveContext';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const CONV_KEY = 'planta-chat-conversations-v1';

/* ════════════════════════════════════════════════════════════════════
   TIPOS
   ════════════════════════════════════════════════════════════════════ */

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  ts: number;
}

interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Msg[];
}

/* ════════════════════════════════════════════════════════════════════
   ROUTING LOCAL · filas (determinístico, nunca "sem dados")
   ════════════════════════════════════════════════════════════════════ */

const VENUE_CENTROID = { lat: 38.7636, lng: -9.0956 };
const MPDLAT = 111320;
const MPDLNG = 111320 * Math.cos((VENUE_CENTROID.lat * Math.PI) / 180);

const CLUSTERS: Record<string, { x_m: number; y_m: number; zone: string }> = {
  'wc-01': { x_m: -380, y_m: 120, zone: 'Portal Norte' },
  'wc-02': { x_m: 80, y_m: -30, zone: 'Central' },
  'wc-03': { x_m: -100, y_m: 80, zone: 'Portão' },
  'wc-04': { x_m: -200, y_m: 200, zone: 'Cumeada' },
  'wc-05': { x_m: 250, y_m: 180, zone: 'Portão · unissex' },
  'wc-06': { x_m: -50, y_m: 250, zone: 'Central · unissex' },
  'wc-07': { x_m: -300, y_m: -80, zone: 'Lockers' },
  'wc-08': { x_m: 350, y_m: 300, zone: 'Exterior' },
};

const COORDS_REGEX = /(-?\d{1,3}\.\d{2,8})\s*,\s*(-?\d{1,3}\.\d{2,8})/;

function detectCoords(text: string): { lat: number; lng: number } | null {
  const m = text.match(COORDS_REGEX);
  if (!m) return null;
  const lat = parseFloat(m[1]);
  const lng = parseFloat(m[2]);
  if (Number.isNaN(lat) || Number.isNaN(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
  return { lat, lng };
}

function clusterPos(cid: string) {
  const c = CLUSTERS[cid];
  return { lat: VENUE_CENTROID.lat + c.y_m / MPDLAT, lng: VENUE_CENTROID.lng + c.x_m / MPDLNG };
}

function haversine(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const R = 6371000;
  const r = (d: number) => (d * Math.PI) / 180;
  const dLat = r(b.lat - a.lat);
  const dLng = r(b.lng - a.lng);
  const x =
    Math.sin(dLat / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

interface Rank {
  cid: string;
  distMeters: number;
  walkSeconds: number;
  occ: number;
  fila: number;
  waitSec: number;
  totalCost: number;
}

function recommend(lat: number, lng: number, snap: LiveSnapshot | null) {
  const user = { lat, lng };
  const venueDist = haversine(user, VENUE_CENTROID);
  const isOutside = venueDist > 800;
  const refPoint = isOutside ? VENUE_CENTROID : user;
  const liveMap = new Map((snap?.clusters ?? []).map((c) => [c.cluster_id, c]));

  const ranked: Rank[] = Object.keys(CLUSTERS)
    .map((cid) => {
      const distMeters = haversine(refPoint, clusterPos(cid));
      const walkSeconds = distMeters / 1.4;
      const live = liveMap.get(cid);
      const occ = live?.params?.ocupacao_instantanea ?? 0;
      const fila = live?.params?.fila_atual ?? 0;
      const waitSec = (live?.params?.tempo_espera_min ?? 0) * 60;
      const congestion = occ >= 80 ? 90 : occ >= 60 ? 25 : 0;
      return { cid, distMeters, walkSeconds, occ, fila, waitSec, totalCost: walkSeconds + waitSec + congestion };
    })
    .sort((a, b) => a.totalCost - b.totalCost);

  return { best: ranked[0], alt: ranked[1] || null, isOutside, venueDist };
}

function fmtDist(m: number) {
  if (m < 1000) return `${Math.round(m)} m`;
  if (m < 10000) return `${(m / 1000).toFixed(1)} km`;
  return `${Math.round(m / 1000)} km`;
}
function fmtWalk(seconds: number) {
  const m = Math.max(1, Math.round(seconds / 60));
  if (m > 90) return `${m} min 😅 — os nossos WC são inteligentes, mas não tão aventureiros!`;
  return `${m} min`;
}

function formatRecommendation(rec: ReturnType<typeof recommend>): string {
  const { best, alt, isOutside, venueDist } = rec;
  const id = best.cid.toUpperCase();
  const zone = CLUSTERS[best.cid]?.zone ?? '';
  const occ = `${Math.round(best.occ)}% ocupação`;
  const fila = best.fila > 0 ? ` · ${best.fila} pessoas na fila` : '';
  let txt = '';
  if (isOutside) txt += `Estás a ${fmtDist(venueDist)} do Parque Tejo. Quando chegares, vai a:\n\n`;
  txt += `**${id}** · ${zone}\n${fmtDist(best.distMeters)} · ~${fmtWalk(best.walkSeconds)} a pé\n${occ}${fila}`;
  if (best.waitSec > 30) txt += ` · ~${Math.round(best.waitSec / 60)} min espera`;
  if (alt && alt.cid !== best.cid) {
    txt += `\n\nAlternativa: **${alt.cid.toUpperCase()}** — ${fmtWalk(alt.walkSeconds)} a pé, ${Math.round(alt.occ)}% ocupação.`;
  }
  return txt;
}

/* ════════════════════════════════════════════════════════════════════
   PERSISTÊNCIA · conversas (local-first)
   ════════════════════════════════════════════════════════════════════ */

function loadConversations(): Conversation[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(CONV_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveConversations(list: Conversation[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(CONV_KEY, JSON.stringify(list.slice(0, 100)));
  } catch {}
}

function titleFrom(text: string): string {
  if (detectCoords(text)) return 'WC mais perto';
  const t = text.trim().replace(/\s+/g, ' ');
  return t.length > 42 ? t.slice(0, 42) + '…' : t;
}

function uid(): string {
  return `c-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function dateGroup(ts: number): string {
  const now = new Date();
  const d = new Date(ts);
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startYesterday = startToday - 86400000;
  const startWeek = startToday - 6 * 86400000;
  if (ts >= startToday) return 'Hoje';
  if (ts >= startYesterday) return 'Ontem';
  if (ts >= startWeek) return 'Esta semana';
  return 'Mais antigo';
}

/* ════════════════════════════════════════════════════════════════════
   RENDER de mensagens (markdown simples + imagem)
   ════════════════════════════════════════════════════════════════════ */

function isImageDataUrl(s: string) {
  return typeof s === 'string' && s.startsWith('data:image/');
}

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    parts.push(<strong key={i++}>{m[1]}</strong>);
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function MessageContent({ content }: { content: string }) {
  if (isImageDataUrl(content)) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <img src={content} alt="anexo" style={{ maxWidth: '100%', maxHeight: 320, borderRadius: 12, display: 'block' }} />
        <a
          href={content}
          download={`planta-${Date.now()}.png`}
          style={{ fontSize: 11, color: 'rgba(255,255,255,0.9)', textDecoration: 'underline', textAlign: 'right', fontFamily: 'var(--font-mono)' }}
        >
          ⬇ guardar
        </a>
      </div>
    );
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

/* ════════════════════════════════════════════════════════════════════
   COMPONENTE
   ════════════════════════════════════════════════════════════════════ */

function Chat2Inner() {
  const router = useRouter();
  const params = useSearchParams();
  const { snapshot } = useLive();
  const snapRef = useRef<LiveSnapshot | null>(null);
  snapRef.current = snapshot;

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const handledQuery = useRef<string | null>(null);

  // boot
  useEffect(() => {
    const list = loadConversations();
    setConversations(list);
    if (list.length) setActiveId(list[0].id);
  }, []);

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) || null,
    [conversations, activeId],
  );

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [active?.messages.length, sending]);

  // ?q= da searchbar/links
  useEffect(() => {
    const q = params?.get('q');
    if (q && handledQuery.current !== q) {
      handledQuery.current = q;
      send(q, true);
      router.replace('/v2/chat2', { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const persist = (list: Conversation[]) => {
    setConversations(list);
    saveConversations(list);
  };

  const ensureConversation = (firstText: string): Conversation => {
    if (active) return active;
    const conv: Conversation = {
      id: uid(),
      title: titleFrom(firstText),
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [],
    };
    return conv;
  };

  const send = async (text?: string, forceNew = false) => {
    const content = (text ?? input).trim();
    if (!content || sending) return;

    setInput('');
    setSending(true);

    // resolve conversa alvo
    let conv: Conversation;
    let list = [...conversations];
    if (forceNew || !active) {
      conv = {
        id: uid(),
        title: titleFrom(content),
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
      };
      list = [conv, ...list];
      setActiveId(conv.id);
    } else {
      conv = { ...active, messages: [...active.messages] };
      list = list.map((c) => (c.id === conv.id ? conv : c));
    }

    // user msg
    conv.messages.push({ role: 'user', content, ts: Date.now() });
    conv.updatedAt = Date.now();
    if (conv.messages.length === 1) conv.title = titleFrom(content);
    list = list.map((c) => (c.id === conv.id ? { ...conv, messages: [...conv.messages] } : c));
    persist(list);

    const pushAssistant = (reply: string) => {
      const updated = loadConversations();
      const target = updated.find((c) => c.id === conv.id);
      if (target) {
        target.messages.push({ role: 'assistant', content: reply, ts: Date.now() });
        target.updatedAt = Date.now();
        const reordered = [target, ...updated.filter((c) => c.id !== conv.id)];
        persist(reordered);
      } else {
        conv.messages.push({ role: 'assistant', content: reply, ts: Date.now() });
        persist([conv, ...list.filter((c) => c.id !== conv.id)]);
      }
    };

    // INTERCEPT coords → routing local
    const coords = detectCoords(content);
    if (coords) {
      await new Promise((r) => setTimeout(r, 220));
      pushAssistant(formatRecommendation(recommend(coords.lat, coords.lng, snapRef.current)));
      setSending(false);
      return;
    }

    // backend
    try {
      const r = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });
      let reply = 'Desculpa, não consegui processar agora.';
      if (r.ok) {
        const j = await r.json();
        reply = j.reply || j.message || j.response || j.text || reply;
      }
      pushAssistant(reply);
    } catch {
      pushAssistant('Problema de ligação. Tenta dentro de momentos.');
    } finally {
      setSending(false);
    }
  };

  const newConversation = () => {
    setActiveId(null);
    setInput('');
    setSidebarOpen(false);
  };

  const selectConversation = (id: string) => {
    setActiveId(id);
    setSidebarOpen(false);
  };

  const deleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Apagar esta conversa?')) return;
    const list = conversations.filter((c) => c.id !== id);
    persist(list);
    if (activeId === id) setActiveId(list[0]?.id ?? null);
  };

  const askLocation = () => {
    if (!('geolocation' in navigator)) {
      alert('Geolocalização não suportada.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        send(`Estou em ${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}. Qual a casa-de-banho mais perto?`),
      (err) => alert(`Não consegui obter localização: ${err.message}`),
      { timeout: 8000, enableHighAccuracy: true },
    );
  };

  // agrupar conversas por data
  const grouped = useMemo(() => {
    const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
    const groups: { label: string; items: Conversation[] }[] = [];
    for (const c of sorted) {
      const g = dateGroup(c.updatedAt);
      let bucket = groups.find((x) => x.label === g);
      if (!bucket) {
        bucket = { label: g, items: [] };
        groups.push(bucket);
      }
      bucket.items.push(c);
    }
    return groups;
  }, [conversations]);

  return (
    <div className="c2-root">
      {/* Sidebar de histórico */}
      <aside className={`c2-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <button className="c2-new" onClick={newConversation}>
          <span className="c2-new-plus">+</span> Nova conversa
        </button>
        <div className="c2-hist">
          {conversations.length === 0 && (
            <div className="c2-hist-empty">As tuas conversas aparecem aqui.</div>
          )}
          {grouped.map((g) => (
            <div key={g.label} className="c2-group">
              <div className="c2-group-label">{g.label}</div>
              {g.items.map((c) => (
                <button
                  key={c.id}
                  className={`c2-conv ${c.id === activeId ? 'is-active' : ''}`}
                  onClick={() => selectConversation(c.id)}
                >
                  <span className="c2-conv-title">{c.title}</span>
                  <span className="c2-conv-del" onClick={(e) => deleteConversation(c.id, e)} aria-label="Apagar">
                    ✕
                  </span>
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="c2-side-foot">Histórico guardado só neste dispositivo.</div>
      </aside>

      {/* Backdrop mobile */}
      {sidebarOpen && <div className="c2-backdrop" onClick={() => setSidebarOpen(false)} />}

      {/* Painel de conversa */}
      <main className="c2-main">
        <header className="c2-header">
          <button className="c2-burger" onClick={() => setSidebarOpen(true)} aria-label="Histórico">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <div>
            <div className="c2-eyebrow">Chat · Planta Smart Homes</div>
            <h2 className="c2-title">{active ? active.title : 'Ask Planta anything'}</h2>
          </div>
        </header>

        <div ref={scrollRef} className="c2-scroll">
          {(!active || active.messages.length === 0) && (
            <div className="c2-welcome">
              <p>
                Pergunta-me sobre as filas, a ocupação, ou partilha a tua localização para a
                recomendação mais rápida agora.
              </p>
              <div className="c2-chips">
                <button className="c2-chip c2-chip-primary" onClick={askLocation}>📍 WC mais perto</button>
                {['Qual a fila menor agora?', 'WC acessível mais perto', 'Bebedouro mais perto', 'Estado unissex (WC-05 e WC-06)'].map((s) => (
                  <button key={s} className="c2-chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {active?.messages.map((m, i) => (
            <div key={i} className={`c2-bubble ${m.role === 'user' ? 'is-user' : 'is-ai'}`}>
              <MessageContent content={m.content} />
            </div>
          ))}
          {sending && (
            <div className="c2-bubble is-ai c2-typing">
              <span>● ● ●</span>
            </div>
          )}
        </div>

        <div className="c2-inputbar">
          <div className="c2-inputwrap">
            <button className="c2-icon" onClick={askLocation} aria-label="Localização" title="Partilhar localização">📍</button>
            <input
              className="c2-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
              placeholder="Pergunta à Planta…"
            />
            <button
              className="c2-send"
              onClick={() => send()}
              disabled={!input.trim() || sending}
              aria-label="Enviar"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" /><polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </div>
        </div>
      </main>

      <style jsx>{`
        .c2-root {
          position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0;
          display: grid; grid-template-columns: 288px 1fr; background: #fff; color: #0d1a0f; overflow: hidden;
        }
        /* Sidebar */
        .c2-sidebar {
          display: flex; flex-direction: column; border-right: 1px solid rgba(13,26,15,0.08);
          padding: 16px 12px; min-height: 0; background: #fcfcf9;
        }
        .c2-new {
          display: flex; align-items: center; gap: 8px; width: 100%;
          background: #1b3a21; color: #fff; border: none; border-radius: 12px;
          padding: 12px 14px; font-size: 14px; font-weight: 600; cursor: pointer;
          font-family: inherit; margin-bottom: 14px; transition: opacity 0.15s;
        }
        .c2-new:hover { opacity: 0.92; }
        .c2-new-plus { font-size: 18px; line-height: 1; }
        .c2-hist { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: thin; scrollbar-color: rgba(13,26,15,0.08) transparent; }
        .c2-hist::-webkit-scrollbar { width: 6px; }
        .c2-hist::-webkit-scrollbar-thumb { background: rgba(13,26,15,0.08); border-radius: 4px; }
        .c2-hist-empty { font-size: 13px; color: rgba(13,26,15,0.45); padding: 8px 6px; line-height: 1.5; }
        .c2-group { margin-bottom: 10px; }
        .c2-group-label { font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(13,26,15,0.4); padding: 6px 8px 4px; }
        .c2-conv {
          display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%;
          background: transparent; border: none; border-radius: 10px; padding: 9px 10px;
          font-size: 13.5px; cursor: pointer; font-family: inherit; color: #0d1a0f; text-align: left;
          transition: background 0.14s;
        }
        .c2-conv:hover { background: rgba(13,26,15,0.04); }
        .c2-conv.is-active { background: #f0f4f0; }
        .c2-conv-title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
        .c2-conv-del { opacity: 0; font-size: 12px; color: rgba(13,26,15,0.45); flex-shrink: 0; padding: 2px 4px; border-radius: 4px; transition: opacity 0.14s; }
        .c2-conv:hover .c2-conv-del { opacity: 1; }
        .c2-conv-del:hover { color: #c25a1a; }
        .c2-side-foot { font-size: 10.5px; color: rgba(13,26,15,0.4); padding: 10px 6px 0; border-top: 1px solid rgba(13,26,15,0.08); margin-top: 8px; line-height: 1.4; }

        .c2-backdrop { display: none; }

        /* Main */
        .c2-main { display: flex; flex-direction: column; min-height: 0; min-width: 0; }
        .c2-header {
          flex-shrink: 0; display: flex; align-items: center; gap: 12px;
          padding: 14px clamp(16px, 4vw, 40px); border-bottom: 1px solid rgba(13,26,15,0.08);
        }
        .c2-burger {
          display: none; background: transparent; border: 1px solid rgba(13,26,15,0.12);
          border-radius: 10px; width: 40px; height: 40px; align-items: center; justify-content: center;
          cursor: pointer; color: #0d1a0f; flex-shrink: 0;
        }
        .c2-eyebrow { font-size: 10px; font-weight: 500; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(13,26,15,0.45); }
        .c2-title { font-size: clamp(18px, 2.4vw, 28px); font-weight: 500; letter-spacing: -0.03em; line-height: 1; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70vw; }

        .c2-scroll {
          flex: 1; min-height: 0; overflow-y: auto;
          padding: clamp(16px, 3vw, 28px) clamp(16px, 4vw, 40px);
          display: flex; flex-direction: column; gap: 12px;
          scrollbar-width: thin; scrollbar-color: rgba(13,26,15,0.08) transparent;
        }
        .c2-scroll::-webkit-scrollbar { width: 8px; }
        .c2-scroll::-webkit-scrollbar-thumb { background: rgba(13,26,15,0.08); border-radius: 4px; }

        .c2-welcome { color: rgba(13,26,15,0.55); max-width: 560px; }
        .c2-welcome p { font-size: 16px; line-height: 1.55; margin: 0 0 18px; }
        .c2-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .c2-chip {
          background: #fff; border: 1px solid rgba(13,26,15,0.12); border-radius: 999px;
          padding: 9px 15px; font-size: 13px; cursor: pointer; color: #0d1a0f; font-family: inherit;
          transition: border-color 0.14s, background 0.14s;
        }
        .c2-chip:hover { border-color: #4a7c59; }
        .c2-chip-primary { background: #1b3a21; color: #fff; border-color: #1b3a21; font-weight: 600; }

        .c2-bubble {
          padding: 11px 15px; border-radius: 16px; max-width: 78%; font-size: 15px;
          line-height: 1.55; word-break: break-word;
        }
        .c2-bubble.is-user { align-self: flex-end; background: #0d1a0f; color: #fff; }
        .c2-bubble.is-ai { align-self: flex-start; background: #fff; color: #0d1a0f; border: 1px solid rgba(13,26,15,0.08); box-shadow: 0 1px 2px rgba(13,26,15,0.04); }
        .c2-typing span { color: rgba(13,26,15,0.4); animation: c2dots 1.4s infinite; }
        @keyframes c2dots { 0%,100% { opacity: 0.3; } 50% { opacity: 1; } }

        /* Input */
        .c2-inputbar { flex-shrink: 0; padding: clamp(10px,2vw,16px) clamp(16px,4vw,40px); border-top: 1px solid rgba(13,26,15,0.08); }
        .c2-inputwrap {
          display: flex; align-items: center; gap: 4px; max-width: 820px; margin: 0 auto;
          background: #fff; border: 1px solid #1b3a21; border-radius: 999px; padding: 6px 6px 6px 8px;
        }
        .c2-icon { background: transparent; border: none; width: 38px; height: 38px; border-radius: 50%; cursor: pointer; font-size: 18px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
        .c2-input { flex: 1; background: transparent; border: none; outline: none; padding: 10px 6px; font-size: 15.5px; color: #0d1a0f; min-width: 0; font-family: inherit; }
        .c2-send {
          background: #1b3a21; color: #fff; border: none; border-radius: 50%; width: 40px; height: 40px;
          cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
          transition: background 0.15s, opacity 0.15s;
        }
        .c2-send:disabled { background: #ebe9e2; color: #a0a39a; cursor: default; }

        @media (max-width: 860px) {
          .c2-root { grid-template-columns: 1fr; }
          .c2-sidebar {
            position: fixed; top: var(--topbar-h, 72px); left: 0; bottom: 0; width: 288px; z-index: 40;
            transform: translateX(-100%); transition: transform 0.28s cubic-bezier(0.32,0.72,0,1);
            box-shadow: 0 0 40px rgba(13,26,15,0.12);
          }
          .c2-sidebar.is-open { transform: translateX(0); }
          .c2-backdrop { display: block; position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0; background: rgba(13,26,15,0.3); z-index: 35; }
          .c2-burger { display: flex; }
        }
      `}</style>
    </div>
  );
}

export default function Chat2Page() {
  return (
    <Suspense
      fallback={
        <div style={{ padding: 40, color: 'rgba(13,26,15,0.45)', fontSize: 13, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Chat · a carregar…
        </div>
      }
    >
      <Chat2Inner />
    </Suspense>
  );
}
