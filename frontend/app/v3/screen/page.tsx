'use client';

import { useEffect, useState } from 'react';
import { useLiveV3 } from '@/components/v3/LiveContextV3';

const API = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

interface ScreenEntry {
  pt: string;
  en: string;
  tom: string;
}

type ScreenCopy = Record<string, ScreenEntry>;

const TOM_COLOUR: Record<string, string> = {
  urgente:  'var(--v3-amber)',
  cheio:    'var(--v3-amber)',
  disponivel: 'var(--v3-blue)',
  vazio:    '#22C55E',
};

export default function ScreenPage() {
  const { clusters } = useLiveV3();
  const [copy, setCopy] = useState<ScreenCopy>({});

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`${API}/api/v1/screen/copy`, { cache: 'no-store' });
        if (r.ok) setCopy(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 6000);
    return () => clearInterval(id);
  }, []);

  const entries = Object.entries(copy);

  if (entries.length === 0) {
    return (
      <div className="v3-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 13, color: 'var(--v3-muted)' }}>A carregar mensagens…</span>
      </div>
    );
  }

  return (
    <div className="v3-page">
      <div style={{ fontSize: 11, fontFamily: 'var(--v3-font-mono)', color: 'var(--v3-muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 14 }}>
        Mensagens de ecrã · {entries.length} secções
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
        {entries.map(([key, msg]) => {
          const [clRaw, gender] = key.split('_');
          const colour = TOM_COLOUR[msg.tom] ?? 'var(--v3-ink)';
          const cl = clusters.find((c) => c.cluster_id.toLowerCase() === clRaw);
          const occ = cl?.params?.ocupacao_pct ?? cl?.params?.ocupacao_instantanea ?? 0;

          return (
            <div key={key} className="v3-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--v3-font-mono)', fontWeight: 600, fontSize: 12, color: 'var(--v3-ink)' }}>
                  {clRaw.toUpperCase()} · {gender === 'm' ? 'MASC' : gender === 'f' ? 'FEM' : 'UNI'}
                </span>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  {occ > 0 && (
                    <span style={{ fontFamily: 'var(--v3-font-mono)', fontSize: 11, color: 'var(--v3-muted)' }}>{occ}%</span>
                  )}
                  <span className="v3-badge" style={{ background: `color-mix(in srgb, ${colour} 12%, transparent)`, color: colour }}>
                    {msg.tom}
                  </span>
                </div>
              </div>

              <p style={{ margin: '0 0 6px', fontSize: 14, fontWeight: 600, color: colour, lineHeight: 1.4 }}>
                {msg.pt}
              </p>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--v3-muted)', lineHeight: 1.4 }}>
                {msg.en}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
