'use client';

import { useEffect, useRef, useState } from 'react';
import MuralPanel from '@/components/MuralPanel';
import WcNav from '@/components/WcNav';
import type { ClusterId, PanelData, ScreenCopyMap } from '@/lib/mural-types';
import { fetchMuralData, fetchScreenCopy, pickClusterCopy } from '@/lib/mural-data';

const ID: ClusterId = '07';
const POLL_MS = 2000;

export default function Wc07Page() {
  const [panelData, setPanelData] = useState<PanelData | null>(null);
  const [copyMap, setCopyMap] = useState<ScreenCopyMap>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    try {
      const [all, copy] = await Promise.all([fetchMuralData(), fetchScreenCopy()]);
      setPanelData(all.find((p) => p.id === ID) ?? null);
      setCopyMap(copy);
    } catch { /* mantem ultimo estado */ }
  };

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, POLL_MS);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  return (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden' }}>
      <WcNav id={ID} />
      <MuralPanel id={ID} data={panelData} mode="solo" staggerDelayMs={0} copy={pickClusterCopy(ID, panelData, copyMap)} />
    </div>
  );
}
