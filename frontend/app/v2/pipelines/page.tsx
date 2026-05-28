'use client';

import { useEffect, useState } from 'react';
import { Lock } from 'lucide-react';
import PipelinesContent from './_content';

const ADMIN_KEY = 'planta-ops';
const STORE_KEY = 'planta-admin-key';

export default function PipelinesPage() {
  const [authed, setAuthed] = useState(false);
  const [ready, setReady] = useState(false);
  const [val, setVal] = useState('');

  useEffect(() => {
    try {
      const url = new URLSearchParams(window.location.search);
      const fromUrl = url.get('key');
      const stored = localStorage.getItem(STORE_KEY);
      if (fromUrl === ADMIN_KEY || stored === ADMIN_KEY) {
        if (fromUrl === ADMIN_KEY) localStorage.setItem(STORE_KEY, ADMIN_KEY);
        setAuthed(true);
      }
    } catch {}
    setReady(true);
  }, []);

  const tryKey = () => {
    if (val.trim() === ADMIN_KEY) {
      try { localStorage.setItem(STORE_KEY, ADMIN_KEY); } catch {}
      setAuthed(true);
    } else {
      alert('Chave incorrecta.');
    }
  };

  if (!ready) return null;
  if (authed) return <PipelinesContent />;

  return (
    <div style={{
      position: 'fixed', top: 'var(--topbar-h, 72px)', left: 0, right: 0, bottom: 0,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 18, background: 'var(--paper, #FAFAF7)', color: 'var(--ink, #0D1A0F)', padding: 24,
    }}>
      <Lock size={28} strokeWidth={1.4} style={{ color: 'var(--green-soft, #4A7C59)' }} />
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ fontSize: 'clamp(20px,2.6vw,30px)', fontWeight: 300, letterSpacing: '-0.03em', margin: 0 }}>Acesso restrito</h1>
        <p style={{ fontSize: 14, color: 'var(--ink-soft, rgba(13,26,15,0.55))', marginTop: 6, fontStyle: 'italic' }}>Operations only</p>
      </div>
      <div style={{ display: 'flex', gap: 8, width: 'min(360px, 90vw)' }}>
        <input
          type="password"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') tryKey(); }}
          placeholder="Chave de acesso"
          style={{ flex: 1, padding: '12px 16px', borderRadius: 999, border: '1px solid var(--green, #1B3A21)', fontSize: 15, outline: 'none', fontFamily: 'inherit', background: '#fff', color: 'var(--ink, #0D1A0F)' }}
        />
        <button onClick={tryKey} style={{ background: 'var(--green, #1B3A21)', color: '#fff', border: 'none', borderRadius: 999, padding: '12px 22px', fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>Entrar</button>
      </div>
      <a href="/v2" style={{ fontSize: 13, color: 'var(--green-soft, #4A7C59)', textDecoration: 'none' }}>← Voltar ao início</a>
    </div>
  );
}
