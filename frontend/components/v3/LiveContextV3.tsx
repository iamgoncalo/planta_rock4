'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';
const STREAM_URL = `${API_BASE}/api/v1/telemetry/clusters/stream`;
const SNAPSHOT_URL = `${API_BASE}/api/v1/telemetry/clusters/now`;
const POLL_MS = 2500;

export interface ClusterLive {
  cluster_id: string;
  ts: number;
  params: {
    pessoas_estimadas: number;
    ocupacao_instantanea: number; // % == round(100×Σabs/capacidade)
    ocupacao_pct?: number;        // % a 1dp (mesmos abs)
    fila_atual: number;
    tempo_espera_min: number;
    capacidade_total: number;
    is_unissex: boolean;
    estado_sensor: string;
    confianca_cruzada: number;
  };
}

interface LiveCtx {
  clusters: ClusterLive[];
  totalPessoas: number;
  avgOcc: number;
  connected: boolean;
}

const Ctx = createContext<LiveCtx>({ clusters: [], totalPessoas: 0, avgOcc: 0, connected: false });

export function LiveProviderV3({ children }: { children: ReactNode }) {
  const [clusters, setClusters] = useState<ClusterLive[]>([]);
  const [connected, setConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const applyPayload = useCallback((data: unknown) => {
    if (!data || typeof data !== 'object') return;
    const d = data as Record<string, unknown>;
    const list = (d.clusters ?? []) as ClusterLive[];
    if (Array.isArray(list) && list.length > 0) {
      setClusters(list);
      setConnected(true);
    }
  }, []);

  const fetchSnapshot = useCallback(async () => {
    try {
      const res = await fetch(SNAPSHOT_URL, { cache: 'no-store' });
      if (res.ok) applyPayload(await res.json());
    } catch {}
  }, [applyPayload]);

  useEffect(() => {
    fetchSnapshot();
    let es: EventSource | null = null;

    const connect = () => {
      try {
        es = new EventSource(STREAM_URL);
        es.onmessage = (e) => { try { applyPayload(JSON.parse(e.data)); } catch {} };
        es.onerror = () => {
          setConnected(false);
          es?.close();
          startPolling();
        };
      } catch {
        startPolling();
      }
    };

    const startPolling = () => {
      if (pollRef.current) return;
      fetchSnapshot();
      pollRef.current = setInterval(fetchSnapshot, POLL_MS);
    };

    connect();

    return () => {
      es?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [applyPayload, fetchSnapshot]);

  const totalPessoas = clusters.reduce((s, c) => s + (c.params?.pessoas_estimadas ?? 0), 0);
  const avgOcc =
    clusters.length > 0
      ? Math.round(clusters.reduce((s, c) => s + (c.params?.ocupacao_instantanea ?? 0), 0) / clusters.length)
      : 0;

  return (
    <Ctx.Provider value={{ clusters, totalPessoas, avgOcc, connected }}>
      {children}
    </Ctx.Provider>
  );
}

export function useLiveV3() { return useContext(Ctx); }
