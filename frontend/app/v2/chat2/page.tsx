'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLive, type LiveSnapshot } from '@/components/v2/LiveContext';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const CONV_KEY = 'planta-chat-conversations-v1';
const MAX_IMAGE_BYTES = 2_000_000;

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
   ROUTING LOCAL · filas (determinístico, resposta instantânea)
   ════════════════════════════════════════════════════════════════════ */

// Âncora única do recinto (igual a app/clusters_geo.py — fonte de verdade).
const VENUE_CENTROID = { lat: 38.78145, lng: -9.0943 };

// Posições por cluster vindas de /api/v1/clusters/geo (GPS).
// Arranca com FALLBACK (mesmas coordenadas da fonte); é substituído pela
// fetch da geo ao carregar — alinhado com /twin e o backend.
interface ClusterGeo { lat: number; lng: number; zone: string }
const CLUSTERS: Record<string, ClusterGeo> = {
  'wc-01': { lat: 38.78439, lng: -9.09182, zone: 'Portal Norte' },
  'wc-02': { lat: 38.78402, lng: -9.09134, zone: 'Central' },
  'wc-03': { lat: 38.7832, lng: -9.091209, zone: 'Portão' },
  'wc-04': { lat: 38.78404, lng: -9.09086, zone: 'Cumeada' },
  'wc-05': { lat: 38.78359, lng: -9.09114, zone: 'Portão · unissex' },
  'wc-06': { lat: 38.78219, lng: -9.093601, zone: 'Central · unissex' },
  'wc-07': { lat: 38.78278, lng: -9.09167, zone: 'Lockers' },
  'wc-08': { lat: 38.78145, lng: -9.0943, zone: 'Exterior' },
};

// Preenche CLUSTERS a partir da fonte de verdade (chamado uma vez ao iniciar).
function applyGeo(payload: any) {
  if (!payload?.clusters?.length) return;
  const zoneFor = (id: string, desc: string, unisex: boolean) => {
    if (CLUSTERS[id]?.zone) return CLUSTERS[id].zone;
    return unisex ? `${desc} · unissexo` : desc;
  };
  for (const c of payload.clusters) {
    const id = String(c.id).toLowerCase();
    if (typeof c.gps_lat === 'number' && typeof c.gps_lon === 'number') {
      CLUSTERS[id] = { lat: c.gps_lat, lng: c.gps_lon, zone: zoneFor(id, c.desc ?? '', !!c.unisex) };
    }
  }
}

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
  return { lat: c.lat, lng: c.lng };
}
function haversine(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const R = 6371000;
  const r = (d: number) => (d * Math.PI) / 180;
  const dLat = r(b.lat - a.lat);
  const dLng = r(b.lng - a.lng);
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

interface Rank {
  cid: string; distMeters: number; walkSeconds: number; occ: number; fila: number; waitSec: number; totalCost: number;
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
  if (m > 90) return `${m} min — os nossos WC são inteligentes, mas não tão aventureiros`;
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
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}
function saveConversations(list: Conversation[]) {
  if (typeof window === 'undefined') return;
  try { localStorage.setItem(CONV_KEY, JSON.stringify(list.slice(0, 100))); } catch {}
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
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (ts >= startToday) return 'Hoje';
  if (ts >= startToday - 86400000) return 'Ontem';
  if (ts >= startToday - 6 * 86400000) return 'Esta semana';
  return 'Mais antigo';
}
function fmtTime(ts: number): string {
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/* ════════════════════════════════════════════════════════════════════
   SUGESTÕES
   ════════════════════════════════════════════════════════════════════ */

const SUGGESTIONS = [
  'Qual a fila menor agora?',
  'WC acessível mais perto',
  'Casa-de-banho unissex (WC-05 e WC-06)',
  'Bebedouro mais perto',
  'Saí do Palco Mundo, para onde vou?',
  'Onde há menos espera para senhoras?',
  'Reportar um problema numa casa-de-banho',
  'Qual a casa-de-banho mais limpa agora?',
];

const PLACEHOLDERS = [
  'Pergunta à Planta…',
  'Onde é a WC mais perto?',
  'Qual a fila menor agora?',
  'Bebedouro mais perto',
  'Saí do Palco Mundo, para onde vou?',
];

/* ════════════════════════════════════════════════════════════════════
   ÍCONES (idênticos à PlantaSearchBar, a traço, sem emojis)
   ════════════════════════════════════════════════════════════════════ */

function MicIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}
function ClipIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}
function LocationIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}
function ArrowUp() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  );
}
function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}
function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}
function MenuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

/* ════════════════════════════════════════════════════════════════════
   RENDER de mensagens
   ════════════════════════════════════════════════════════════════════ */

function isImageDataUrl(s: string) {
  return typeof s === 'string' && s.startsWith('data:image/');
}
function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0, i = 0;
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
    return <img src={content} alt="anexo" style={{ maxWidth: '100%', maxHeight: 320, borderRadius: 12, display: 'block' }} />;
  }
  const lines = content.split('\n');
  return (
    <>
      {lines.map((line, i) => (
        <span key={i}>{renderInline(line)}{i < lines.length - 1 && <br />}</span>
      ))}
    </>
  );
}

/* ════════════════════════════════════════════════════════════════════
   COMPONENTE
   ════════════════════════════════════════════════════════════════════ */

const iconBtn: React.CSSProperties = {
  background: 'transparent', border: 'none', width: 36, height: 36, borderRadius: '50%',
  display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
  flexShrink: 0, padding: 0, transition: 'background 0.15s, color 0.15s', color: 'var(--ink, #0D1A0F)',
};

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
  const [recording, setRecording] = useState(false);
  const [locBusy, setLocBusy] = useState(false);
  const [focused, setFocused] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [phIdx, setPhIdx] = useState(0);

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const recogRef = useRef<any>(null);
  const handledQuery = useRef<string | null>(null);

  useEffect(() => {
    const list = loadConversations();
    setConversations(list);
    if (list.length) setActiveId(list[0].id);
  }, []);

  // Coordenadas vêm da fonte de verdade (igual ao /twin). Se falhar, fica o fallback.
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/api/v1/clusters/geo`, { cache: 'no-store' });
        if (r.ok) applyGeo(await r.json());
      } catch { /* mantém fallback */ }
    })();
  }, []);

  useEffect(() => {
    const iv = setInterval(() => setPhIdx((i) => (i + 1) % PLACEHOLDERS.length), 4000);
    return () => clearInterval(iv);
  }, []);

  const active = useMemo(() => conversations.find((c) => c.id === activeId) || null, [conversations, activeId]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [active?.messages.length, sending]);

  useEffect(() => {
    const q = params?.get('q');
    if (q && handledQuery.current !== q) {
      handledQuery.current = q;
      send(q, true);
      router.replace('/v2/chat2', { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const persist = (list: Conversation[]) => { setConversations(list); saveConversations(list); };

  const send = async (text?: string, forceNew = false) => {
    const content = (text ?? input).trim();
    if (!content || sending) return;
    setInput('');
    setSending(true);

    let conv: Conversation;
    let list = [...conversations];
    if (forceNew || !active) {
      conv = { id: uid(), title: titleFrom(content), createdAt: Date.now(), updatedAt: Date.now(), messages: [] };
      list = [conv, ...list];
      setActiveId(conv.id);
    } else {
      conv = { ...active, messages: [...active.messages] };
      list = list.map((c) => (c.id === conv.id ? conv : c));
    }
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
        persist([target, ...updated.filter((c) => c.id !== conv.id)]);
      } else {
        conv.messages.push({ role: 'assistant', content: reply, ts: Date.now() });
        persist([conv, ...list.filter((c) => c.id !== conv.id)]);
      }
    };

    const coords = detectCoords(content);
    if (coords) {
      await new Promise((r) => setTimeout(r, 220));
      pushAssistant(formatRecommendation(recommend(coords.lat, coords.lng, snapRef.current)));
      setSending(false);
      return;
    }
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

  // MIC
  const toggleMic = () => {
    const W = window as any;
    const SR = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SR) { alert('Microfone não suportado neste browser. Tenta Chrome ou Safari recente.'); return; }
    if (recording) { try { recogRef.current?.stop(); } catch {} setRecording(false); return; }
    const recog = new SR();
    recog.lang = 'pt-PT'; recog.continuous = false; recog.interimResults = true; recog.maxAlternatives = 1;
    recog.onresult = (e: any) => {
      const transcript = Array.from(e.results as any[]).map((r) => r[0].transcript).join(' ');
      setInput(transcript);
    };
    recog.onerror = () => setRecording(false);
    recog.onend = () => setRecording(false);
    try { recog.start(); recogRef.current = recog; setRecording(true); }
    catch { setRecording(false); alert('Não consegui iniciar o microfone. Verifica permissões.'); }
  };

  // LOCATION
  const captureLocation = () => {
    if (!('geolocation' in navigator)) { alert('Geolocalização não suportada neste browser.'); return; }
    setLocBusy(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocBusy(false);
        send(`Estou em ${pos.coords.latitude.toFixed(6)}, ${pos.coords.longitude.toFixed(6)}. Qual a casa-de-banho mais próxima?`);
      },
      (err) => { setLocBusy(false); alert(`Não consegui obter localização: ${err.message}`); },
      { timeout: 8000, enableHighAccuracy: true },
    );
  };

  // CLIP
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { alert('Por agora só aceito imagens.'); return; }
    if (file.size > MAX_IMAGE_BYTES) { alert('Imagem grande demais (máx 2 MB).'); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      let conv: Conversation;
      let list = [...conversations];
      if (!active) {
        conv = { id: uid(), title: 'Imagem', createdAt: Date.now(), updatedAt: Date.now(), messages: [] };
        list = [conv, ...list]; setActiveId(conv.id);
      } else {
        conv = { ...active, messages: [...active.messages] };
        list = list.map((c) => (c.id === conv.id ? conv : c));
      }
      conv.messages.push({ role: 'user', content: dataUrl, ts: Date.now() });
      conv.messages.push({ role: 'assistant', content: 'Recebi a imagem. Diz-me o que se passa nesta casa-de-banho (sem papel, avaria, sujo) e eu encaminho.', ts: Date.now() });
      conv.updatedAt = Date.now();
      persist(list.map((c) => (c.id === conv.id ? { ...conv, messages: [...conv.messages] } : c)));
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const newConversation = () => { setActiveId(null); setInput(''); setSidebarOpen(false); };
  const selectConversation = (id: string) => { setActiveId(id); setSidebarOpen(false); };
  const deleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Apagar esta conversa?')) return;
    const list = conversations.filter((c) => c.id !== id);
    persist(list);
    if (activeId === id) setActiveId(list[0]?.id ?? null);
  };

  const grouped = useMemo(() => {
    const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt);
    const groups: { label: string; items: Conversation[] }[] = [];
    for (const c of sorted) {
      const g = dateGroup(c.updatedAt);
      let bucket = groups.find((x) => x.label === g);
      if (!bucket) { bucket = { label: g, items: [] }; groups.push(bucket); }
      bucket.items.push(c);
    }
    return groups;
  }, [conversations]);

  const canSend = !!input.trim() && !sending;

  return (
    <div className="c2-root">
      {/* Sidebar histórico */}
      <aside className={`c2-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <button className="c2-new" onClick={newConversation}>
          <PlusIcon /> Nova conversa
        </button>
        <div className="c2-hist">
          {conversations.length === 0 && <div className="c2-hist-empty">As tuas conversas aparecem aqui.</div>}
          {grouped.map((g) => (
            <div key={g.label} className="c2-group">
              <div className="c2-group-label">{g.label}</div>
              {g.items.map((c) => (
                <button key={c.id} className={`c2-conv ${c.id === activeId ? 'is-active' : ''}`} onClick={() => selectConversation(c.id)}>
                  <span className="c2-conv-main">
                    <span className="c2-conv-title">{c.title}</span>
                    <span className="c2-conv-time">{fmtTime(c.updatedAt)}</span>
                  </span>
                  <span className="c2-conv-del" onClick={(e) => deleteConversation(c.id, e)} aria-label="Apagar conversa"><TrashIcon /></span>
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="c2-side-foot">Cada dispositivo tem as suas conversas, guardadas localmente.</div>
      </aside>

      {sidebarOpen && <div className="c2-backdrop" onClick={() => setSidebarOpen(false)} />}

      {/* Painel principal */}
      <main className="c2-main">
        <header className="c2-header">
          <button className="c2-burger" onClick={() => setSidebarOpen(true)} aria-label="Histórico"><MenuIcon /></button>
          <div className="c2-head-text">
            <div className="c2-eyebrow">PlantaOS · Chat</div>
            <h2 className="c2-title">{active ? active.title : 'Pergunta à Planta'}</h2>
          </div>
        </header>

        <div ref={scrollRef} className="c2-scroll">
          {(!active || active.messages.length === 0) && (
            <div className="c2-welcome">
              <p>Pergunta-me sobre filas, ocupação, água ou acessibilidade. Para a recomendação mais rápida agora, partilha a tua localização.</p>
              <div className="c2-chips">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="c2-chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {active?.messages.map((m, i) => (
            <div key={i} className={`c2-row ${m.role === 'user' ? 'is-user' : 'is-ai'}`}>
              <div className={`c2-bubble ${m.role === 'user' ? 'is-user' : 'is-ai'}`}>
                <MessageContent content={m.content} />
              </div>
              <span className="c2-msgtime">{fmtTime(m.ts)}</span>
            </div>
          ))}
          {sending && <div className="c2-row is-ai"><div className="c2-bubble is-ai c2-typing"><span>● ● ●</span></div></div>}
        </div>

        {/* Sugestões rápidas acima da barra (quando já há conversa) */}
        {active && active.messages.length > 0 && (
          <div className="c2-quickchips">
            {SUGGESTIONS.slice(0, 5).map((s) => (
              <button key={s} className="c2-qchip" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}

        {/* A BARRA — idêntica à PlantaSearchBar */}
        <div className="c2-barwrap">
          <div className="c2-bar" style={{
            boxShadow: focused
              ? '0 18px 48px rgba(27,58,33,0.22), 0 2px 6px rgba(27,58,33,0.10)'
              : '0 14px 38px rgba(13,26,15,0.10), 0 2px 6px rgba(13,26,15,0.04)',
          }}>
            <button type="button" onClick={toggleMic} className={recording ? 'mic-recording' : ''}
              title={recording ? 'Parar gravação' : 'Falar com a Planta'} aria-label="Falar"
              style={{ ...iconBtn, background: recording ? 'var(--amber, #C25A1A)' : 'transparent', color: recording ? 'white' : 'var(--ink, #0D1A0F)' }}>
              <MicIcon />
            </button>
            <button type="button" onClick={() => fileRef.current?.click()} title="Anexar imagem" aria-label="Anexar imagem" style={iconBtn}>
              <ClipIcon />
            </button>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
            <button type="button" onClick={captureLocation} disabled={locBusy} title="Partilhar a minha localização" aria-label="Partilhar localização"
              style={{ ...iconBtn, color: locBusy ? 'var(--amber, #C25A1A)' : 'var(--ink, #0D1A0F)', animation: locBusy ? 'loc-pulse 1s ease-in-out infinite' : 'none' }}>
              <LocationIcon />
            </button>
            <input type="text" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
              onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
              placeholder={recording ? 'A ouvir em Português…' : PLACEHOLDERS[phIdx]}
              style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', padding: '10px 8px', fontSize: 15.5, color: 'var(--ink, #0D1A0F)', minWidth: 0, fontFamily: 'inherit', letterSpacing: '-0.005em' }} />
            <button onClick={() => send()} disabled={!canSend} aria-label="Enviar"
              style={{ background: canSend ? 'var(--green-dark, #1B3A21)' : '#EBE9E2', color: canSend ? 'white' : '#A0A39A', border: 'none', borderRadius: '50%', width: 40, height: 40, cursor: canSend ? 'pointer' : 'default', transition: 'background 0.15s, transform 0.15s', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <ArrowUp />
            </button>
          </div>
          <div className="c2-disclaimer">
            {recording ? 'A ouvir em Português · clica no microfone para parar' : 'PlantaOS can make mistakes'}
          </div>
        </div>
      </main>

      <style jsx global>{`
        .mic-recording { animation: mic-pulse 1.2s ease-in-out infinite; }
        @keyframes mic-pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(194,90,26,0.5); } 50% { box-shadow: 0 0 0 10px rgba(194,90,26,0); } }
        @keyframes loc-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }
        @keyframes c2dots { 0%,100% { opacity: 0.3; } 50% { opacity: 1; } }
      `}</style>

      <style jsx>{`
        .c2-root {
          position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0;
          display: grid; grid-template-columns: 288px 1fr; background: #fff; color: var(--ink, #0D1A0F); overflow: hidden;
        }
        .c2-sidebar { display: flex; flex-direction: column; border-right: 1px solid rgba(13,26,15,0.08); padding: 16px 12px; min-height: 0; background: #fcfcf9; }
        .c2-new { display: flex; align-items: center; gap: 8px; width: 100%; background: var(--green-dark, #1B3A21); color: #fff; border: none; border-radius: 999px; padding: 12px 16px; font-size: 14px; font-weight: 600; cursor: pointer; font-family: inherit; margin-bottom: 14px; transition: opacity 0.15s; }
        .c2-new:hover { opacity: 0.92; }
        .c2-hist { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: thin; scrollbar-color: rgba(13,26,15,0.08) transparent; }
        .c2-hist::-webkit-scrollbar { width: 6px; }
        .c2-hist::-webkit-scrollbar-thumb { background: rgba(13,26,15,0.08); border-radius: 4px; }
        .c2-hist-empty { font-size: 13px; color: rgba(13,26,15,0.45); padding: 8px 6px; line-height: 1.5; }
        .c2-group { margin-bottom: 10px; }
        .c2-group-label { font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: rgba(13,26,15,0.4); padding: 6px 8px 4px; }
        .c2-conv { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; background: transparent; border: none; border-radius: 10px; padding: 9px 10px; cursor: pointer; font-family: inherit; color: var(--ink, #0D1A0F); text-align: left; transition: background 0.14s; }
        .c2-conv:hover { background: rgba(13,26,15,0.04); }
        .c2-conv.is-active { background: var(--green-pale, #EDF4EF); }
        .c2-conv-main { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
        .c2-conv-title { font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .c2-conv-time { font-size: 10.5px; color: rgba(13,26,15,0.4); font-family: var(--font-mono, monospace); }
        .c2-conv-del { opacity: 0; color: rgba(13,26,15,0.4); flex-shrink: 0; padding: 4px; border-radius: 6px; display: flex; transition: opacity 0.14s, color 0.14s; }
        .c2-conv:hover .c2-conv-del { opacity: 1; }
        .c2-conv-del:hover { color: var(--amber, #C25A1A); }
        .c2-side-foot { font-size: 10.5px; color: rgba(13,26,15,0.4); padding: 10px 6px 0; border-top: 1px solid rgba(13,26,15,0.08); margin-top: 8px; line-height: 1.4; }

        .c2-backdrop { display: none; }

        .c2-main { display: flex; flex-direction: column; min-height: 0; min-width: 0; }
        .c2-header { flex-shrink: 0; display: flex; align-items: center; gap: 12px; padding: 14px clamp(16px,4vw,40px); border-bottom: 1px solid rgba(13,26,15,0.08); }
        .c2-burger { display: none; background: transparent; border: 1px solid rgba(13,26,15,0.12); border-radius: 10px; width: 40px; height: 40px; align-items: center; justify-content: center; cursor: pointer; color: var(--ink, #0D1A0F); flex-shrink: 0; }
        .c2-head-text { min-width: 0; }
        .c2-eyebrow { font-size: 10px; font-weight: 500; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(13,26,15,0.45); }
        .c2-title { font-size: clamp(18px,2.4vw,28px); font-weight: 500; letter-spacing: -0.03em; line-height: 1; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70vw; font-family: var(--font-display, inherit); }

        .c2-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: clamp(16px,3vw,28px) clamp(16px,4vw,40px) 8px; display: flex; flex-direction: column; gap: 10px; scrollbar-width: thin; scrollbar-color: rgba(13,26,15,0.08) transparent; }
        .c2-scroll::-webkit-scrollbar { width: 8px; }
        .c2-scroll::-webkit-scrollbar-thumb { background: rgba(13,26,15,0.08); border-radius: 4px; }

        .c2-welcome { color: rgba(13,26,15,0.6); max-width: 600px; }
        .c2-welcome p { font-size: 16px; line-height: 1.55; margin: 0 0 18px; }
        .c2-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .c2-chip { background: #fff; border: 1px solid rgba(13,26,15,0.12); border-radius: 999px; padding: 9px 15px; font-size: 13px; cursor: pointer; color: var(--ink, #0D1A0F); font-family: inherit; transition: border-color 0.14s, background 0.14s; }
        .c2-chip:hover { border-color: var(--green-mid, #4A7C59); background: #fafdfb; }

        .c2-row { display: flex; flex-direction: column; gap: 3px; max-width: 80%; }
        .c2-row.is-user { align-self: flex-end; align-items: flex-end; }
        .c2-row.is-ai { align-self: flex-start; align-items: flex-start; }
        .c2-bubble { padding: 11px 15px; border-radius: 16px; font-size: 15px; line-height: 1.55; word-break: break-word; }
        .c2-bubble.is-user { background: var(--ink, #0D1A0F); color: #fff; }
        .c2-bubble.is-ai { background: #fff; color: var(--ink, #0D1A0F); border: 1px solid rgba(13,26,15,0.08); box-shadow: 0 1px 2px rgba(13,26,15,0.04); }
        .c2-msgtime { font-size: 10px; color: rgba(13,26,15,0.35); font-family: var(--font-mono, monospace); padding: 0 4px; }
        .c2-typing span { color: rgba(13,26,15,0.4); animation: c2dots 1.4s infinite; }

        .c2-quickchips { flex-shrink: 0; display: flex; gap: 8px; overflow-x: auto; padding: 8px clamp(16px,4vw,40px); scrollbar-width: none; }
        .c2-quickchips::-webkit-scrollbar { display: none; }
        .c2-qchip { white-space: nowrap; background: #fff; border: 1px solid rgba(13,26,15,0.12); border-radius: 999px; padding: 7px 13px; font-size: 12.5px; cursor: pointer; color: var(--ink, #0D1A0F); font-family: inherit; flex-shrink: 0; transition: border-color 0.14s; }
        .c2-qchip:hover { border-color: var(--green-mid, #4A7C59); }

        .c2-barwrap { flex-shrink: 0; padding: 18px clamp(16px,4vw,40px) max(8px, env(safe-area-inset-bottom)); }
        .c2-bar { display: flex; align-items: center; gap: 2px; max-width: 720px; margin: 0 auto; background: #fff; border: 1px solid var(--green-dark, #1B3A21); border-radius: 999px; padding: 9px 9px 9px 12px; transition: all 0.18s; }
        .c2-disclaimer { text-align: center; margin-top: 9px; font-size: 11px; color: var(--muted, rgba(13,26,15,0.55)); font-family: var(--font-mono, monospace); letter-spacing: 0.04em; }

        @media (max-width: 860px) {
          .c2-root { grid-template-columns: 1fr; }
          .c2-sidebar { position: fixed; top: var(--topbar-h, 72px); left: 0; bottom: 0; width: 288px; z-index: 40; transform: translateX(-100%); transition: transform 0.28s cubic-bezier(0.32,0.72,0,1); box-shadow: 0 0 40px rgba(13,26,15,0.12); }
          .c2-sidebar.is-open { transform: translateX(0); }
          .c2-backdrop { display: block; position: fixed; top: var(--topbar-h, 72px); left: 0; right: 0; bottom: 0; background: rgba(13,26,15,0.3); z-index: 35; }
          .c2-burger { display: flex; }
          .c2-row { max-width: 90%; }
        }
      `}</style>
    </div>
  );
}

export default function Chat2Page() {
  return (
    <Suspense fallback={<div style={{ padding: 40, color: 'rgba(13,26,15,0.45)', fontSize: 13, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Chat · a carregar…</div>}>
      <Chat2Inner />
    </Suspense>
  );
}
