'use client';

import { notFound } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import MuralPanel from '@/components/MuralPanel';
import type { ClusterId, PanelData, ScreenCopyMap } from '@/lib/mural-types';
import { fetchMuralData, fetchScreenCopy, pickClusterCopy } from '@/lib/mural-data';

const VALID_IDS = new Set<ClusterId>(['01', '02', '03', '04', '05', '06', '07', '08']);
const POLL_MS = 5000;

export default function WcIndividualPage({
  params,
}: {
  params: { id: string };
}) {
  const id = params.id as ClusterId;

  if (!VALID_IDS.has(id)) {
    notFound();
  }

  const [panelData, setPanelData] = useState<PanelData | null>(null);
  const [copyMap, setCopyMap] = useState<ScreenCopyMap>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    try {
      const [all, copy] = await Promise.all([fetchMuralData(), fetchScreenCopy()]);
      setPanelData(all.find((p) => p.id === id) ?? null);
      setCopyMap(copy);
    } catch {
      // keep last known state
    }
  };

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        overflow: 'hidden',
      }}
    >
      <MuralPanel
        id={id}
        data={panelData}
        mode="solo"
        staggerDelayMs={0}
        copy={pickClusterCopy(id, panelData, copyMap)}
      />
    </div>
  );
}
