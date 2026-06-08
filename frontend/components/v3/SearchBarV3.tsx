'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function SearchBarV3() {
  const router = useRouter();
  const [input, setInput] = useState('');

  const submit = () => {
    const q = input.trim();
    if (!q) return;
    router.push(`/v2/chat2?q=${encodeURIComponent(q)}`);
    setInput('');
  };

  return (
    <div className="v3-searchbar">
      <div className="v3-searchbar-input">
        <input
          type="text"
          className="v3-searchbar-text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
          placeholder="Pergunta à Planta…"
          aria-label="Pergunta à Planta"
        />
        <button
          className="v3-searchbar-send"
          onClick={submit}
          disabled={!input.trim()}
          aria-label="Enviar"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
