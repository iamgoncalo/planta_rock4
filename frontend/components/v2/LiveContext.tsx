'use client';

/**
 * LiveContext — SINGLE SOURCE OF TRUTH para dados ao vivo do PlantaOS.
 *
 * UMA conexão SSE para todo o /v2. Todas as páginas/componentes consomem
 * via useLive(). Mesmos números em todo o lado, sempre.
 *
 * Endpoint: GET /api/v1/telemetry/clusters/stream
 * Payload (a cada segundo):
 *   { clusters: [...], kpis: {kpi_01..kpi_04}, cluster_count, expected_clusters }
 *
 * Fallback: se o EventSource cair, faz polling a cada 2s.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

const STREAM_URL = `${API_BASE}/api/v1/telemetry/clusters/stream`;
const SNAPSHOT_URL = `${API_BASE}/api/v1/telemetry/clusters/now`;
const POLL_INTERVAL_MS = 2000;
const RECONNECT_BACKOFF_MS = [1000, 2000, 4000, 8000];

export interface ClusterParams {
  telemoveis_detectados: number;
  pessoas_estimadas: number;
  homens?: number | null;       // AUSENTE em wc-05/wc-06 (unissexo)
  mulheres?: number | null;     // AUSENTE em wc-05/wc-06
  entradas_ir: number;
  saidas_ir: number;
  ocupacao_instantanea: number; // % == round(100×Σabs/capacidade)
  ocupacao_pct?: number;        // % a 1dp (mesmos abs)
  contagem_prosegur: number;
  confianca_cruzada: number;
  estado_sensor: string;
  fila_atual: number;
  tempo_espera_min: number;
  is_unissex: boolean;
  capacidade_total: number;
}

export interface ClusterPayload {
  cluster_id: string;
  ts: number;
  params: ClusterParams;
}

export interface Kpis {
  kpi_01: number;
  kpi_02: number;
  kpi_03: number;
  kpi_04: number;
}

export interface LiveSnapshot {
  clusters: ClusterPayload[];
  kpis: Kpis;
  cluster_count: number;
  expected_clusters: string[];
}

type Connection = 'connecting' | 'sse' | 'polling' | 'offline';

export interface LiveState {
  snapshot: LiveSnapshot | null;
  connection: Connection;
  tick: number;            // incrementa por cada update recebido
  lastUpdateMs: number;    // timestamp local da última actualização
  // Derived helpers — calculados na hora a partir do snapshot
  totalPessoas: number;
  avgOcc: number;
  criticos: number;
}

const DEFAULT: LiveState = {
  snapshot: null,
  connection: 'connecting',
  tick: 0,
  lastUpdateMs: 0,
  totalPessoas: 0,
  avgOcc: 0,
  criticos: 0,
};

const LiveCtx = createContext<LiveState>(DEFAULT);

function deriveTotals(snap: LiveSnapshot | null) {
  if (!snap || !snap.clusters?.length) {
    return { totalPessoas: 0, avgOcc: 0, criticos: 0 };
  }
  const totalPessoas = snap.clusters.reduce(
    (a, c) => a + (c.params?.pessoas_estimadas || 0),
    0,
  );
  const avgOcc = snap.kpis?.kpi_02 ?? 0;
  const criticos = snap.kpis?.kpi_03 ?? 0;
  return { totalPessoas, avgOcc, criticos };
}

export function LiveProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<LiveState>(DEFAULT);

  // Refs para conexão (não causam re-render)
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempt = useRef(0);
  const cancelledRef = useRef(false);

  const ingest = useCallback((snap: LiveSnapshot, conn: Connection) => {
    const derived = deriveTotals(snap);
    setState((prev) => ({
      snapshot: snap,
      connection: conn,
      tick: prev.tick + 1,
      lastUpdateMs: Date.now(),
      ...derived,
    }));
  }, []);

  // Polling — fallback se SSE indisponível
  const startPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    const fetchOnce = async () => {
      if (cancelledRef.current) return;
      try {
        const r = await fetch(SNAPSHOT_URL, { cache: 'no-store' });
        if (!r.ok) throw new Error(`status ${r.status}`);
        const j: LiveSnapshot = await r.json();
        if (cancelledRef.current) return;
        ingest(j, 'polling');
      } catch {
        if (cancelledRef.current) return;
        setState((prev) => ({ ...prev, connection: 'offline' }));
      }
    };
    fetchOnce();
    pollRef.current = setInterval(fetchOnce, POLL_INTERVAL_MS);
  }, [ingest]);

  // SSE — preferido
  const startSSE = useCallback(() => {
    if (typeof window === 'undefined') return;
    if (esRef.current) {
      try { esRef.current.close(); } catch {}
      esRef.current = null;
    }

    let es: EventSource;
    try {
      es = new EventSource(STREAM_URL);
    } catch {
      // Browser sem suporte → polling
      startPolling();
      return;
    }
    esRef.current = es;

    es.onopen = () => {
      reconnectAttempt.current = 0;
      // Se estava em polling, fecha-o
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      setState((prev) => ({ ...prev, connection: 'sse' }));
    };

    es.onmessage = (ev) => {
      if (cancelledRef.current) return;
      try {
        const j: LiveSnapshot = JSON.parse(ev.data);
        ingest(j, 'sse');
      } catch {
        // ignora mensagem mal-formada
      }
    };

    es.onerror = () => {
      if (cancelledRef.current) return;
      try { es.close(); } catch {}
      esRef.current = null;

      // Backoff exponencial; após 4 tentativas falhadas, cai para polling
      const attempt = reconnectAttempt.current;
      if (attempt < RECONNECT_BACKOFF_MS.length) {
        const delay = RECONNECT_BACKOFF_MS[attempt];
        reconnectAttempt.current += 1;
        setState((prev) => ({ ...prev, connection: 'connecting' }));
        reconnectRef.current = setTimeout(() => {
          if (!cancelledRef.current) startSSE();
        }, delay);
      } else {
        startPolling();
      }
    };
  }, [ingest, startPolling]);

  useEffect(() => {
    cancelledRef.current = false;
    startSSE();
    return () => {
      cancelledRef.current = true;
      if (esRef.current) {
        try { esRef.current.close(); } catch {}
        esRef.current = null;
      }
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
    };
  }, [startSSE]);

  return <LiveCtx.Provider value={state}>{children}</LiveCtx.Provider>;
}

export function useLive(): LiveState {
  return useContext(LiveCtx);
}

// Helper para obter cluster específico
export function useCluster(clusterId: string): ClusterPayload | null {
  const { snapshot } = useLive();
  if (!snapshot) return null;
  return snapshot.clusters.find((c) => c.cluster_id === clusterId) || null;
}
