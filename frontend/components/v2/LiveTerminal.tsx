'use client';

import { useEffect, useState } from 'react';
import { api, aggregate } from '@/lib/v2-api';

interface LogLine {
  ts: string;
  text: string;
  kind: 'tick' | 'info' | 'ok' | 'warn';
}

const MAX_LINES = 6;

export default function LiveTerminal() {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [tickCount, setTickCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let counter = 0;

    const push = (text: string, kind: LogLine['kind'] = 'info') => {
      if (cancelled) return;
      const d = new Date();
      const ts = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`;
      setLines((prev) => {
        const next = [...prev, { ts, text, kind }];
        return next.slice(-MAX_LINES);
      });
    };

    const tick = async () => {
      counter += 1;
      setTickCount(counter);
      try {
        const state = await api.state();
        const clusters = aggregate(state.sections ?? []);
        const total = clusters.reduce((a, c) => a + c.pessoas, 0);
        const occ = state.kpis?.avg_ocupacao_pct ?? 0;
        const crit = clusters.filter((c) => c.status === 'critical').length;
        const fila = state.kpis?.total_fila ?? 0;
        push(
          `tick #${counter} · pessoas=${total} · ocup_média=${occ.toFixed(0)}% · fila_total=${fila} · críticos=${crit}`,
          crit > 0 ? 'warn' : 'ok',
        );
      } catch (err) {
        push(`tick #${counter} · backend offline (a tentar novamente)`, 'warn');
      }
    };

    push('PlantaOS edge online · publisher SCOR activo · intervalo 10 s', 'ok');
    tick();
    const iv = setInterval(tick, 10_000);

    return () => {
      cancelled = true;
      clearInterval(iv);
    };
  }, []);

  return (
    <footer
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: 36,
        background: '#0D1A0F',
        borderTop: '1px solid var(--border-strong)',
        zIndex: 90,
        display: 'flex',
        alignItems: 'center',
        padding: '0 18px',
        gap: 14,
        fontFamily: 'var(--font-mono), monospace',
        fontSize: 10.5,
        overflow: 'hidden',
      }}
    >
      <span
        style={{
          color: '#6FAF82',
          fontWeight: 600,
          letterSpacing: '0.08em',
          flexShrink: 0,
        }}
      >
        ● TERMINAL
      </span>

      <div
        style={{
          flex: 1,
          display: 'flex',
          gap: 18,
          overflow: 'hidden',
          whiteSpace: 'nowrap',
        }}
      >
        {lines.length === 0 ? (
          <span style={{ color: '#7A9E7E' }}>... a aguardar dados ...</span>
        ) : (
          lines.slice(-3).map((l, i) => (
            <span
              key={`${l.ts}-${i}`}
              style={{
                color:
                  l.kind === 'warn'
                    ? '#C25A1A'
                    : l.kind === 'ok'
                    ? '#6FAF82'
                    : '#B5C9B9',
                flexShrink: 0,
              }}
            >
              <span style={{ color: '#7A9E7E', marginRight: 6 }}>{l.ts}</span>
              {l.text}
            </span>
          ))
        )}
      </div>

      <span
        style={{
          color: '#7A9E7E',
          flexShrink: 0,
          fontSize: 10,
        }}
      >
        tick #{tickCount}
      </span>
    </footer>
  );
}
