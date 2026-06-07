'use client';

import { useEffect, useRef, useState } from 'react';
import MuralPanel from '@/components/MuralPanel';
import type { ClusterId, PanelData } from '@/lib/mural-types';
import { fetchMuralData } from '@/lib/mural-data';

const CLUSTER_ORDER: ClusterId[] = ['01', '02', '03', '04', '05', '06', '07', '08'];
const POLL_MS = 5000;

export default function ScreenPage() {
  const [panels, setPanels] = useState<Map<ClusterId, PanelData>>(new Map());
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    try {
      const data = await fetchMuralData();
      setPanels(new Map(data.map((p) => [p.id, p])));
    } catch {
      // keep last known state; offline indicator via null data
    }
  };

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return (
    <>
      {/* Override v2 layout chrome — fullscreen fixed overlay */}
      <style>{`
        .v2-root, .v2-content { overflow: visible !important; }
      `}</style>
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 9999,
          overflow: 'hidden',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gridTemplateRows: 'repeat(2, 1fr)',
          gap: '1px',
          background: '#28351C',
        }}
        aria-label="Mural de casas de banho · Rock in Rio Lisboa"
      >
        {CLUSTER_ORDER.map((id, idx) => (
          <MuralPanel
            key={id}
            id={id}
            data={panels.get(id) ?? null}
            mode="mural"
            staggerDelayMs={idx * 1300}
          />
        ))}
      </div>
    </>
  );
}
