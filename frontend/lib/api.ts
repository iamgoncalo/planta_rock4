import type {
  LivePayload,
  GlobalKPIs,
  SensorHealth,
  Alert,
  Show,
  TVScreenState,
  ClusterSummary,
  BathroomRouteDecision,
  ChatResponse,
  SensorNode,
  GatewayStatus,
  BatteryReport,
  CoverageGeoJSON,
  MaintenanceItem,
  SensorSummary,
} from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store',
    });
  } catch (err) {
    const error = new Error('Sem ligação ao servidor') as Error & { isOffline: boolean };
    error.isOffline = true;
    throw error;
  }

  if (!res.ok) {
    const error = new Error(`HTTP ${res.status}`) as Error & { status: number; isOffline: boolean };
    error.status = res.status;
    error.isOffline = res.status >= 500;
    throw error;
  }

  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
  } catch (err) {
    const error = new Error('Sem ligação ao servidor') as Error & { isOffline: boolean };
    error.isOffline = true;
    throw error;
  }

  if (!res.ok) {
    const error = new Error(`HTTP ${res.status}`) as Error & { status: number; isOffline: boolean };
    error.status = res.status;
    error.isOffline = res.status >= 500;
    throw error;
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string; version: string; uptime_s: number }>('/api/v1/health'),
  state: () => get<LivePayload>('/api/v1/state'),
  clusters: () => get<ClusterSummary[]>('/api/v1/clusters'),
  kpis: () => get<GlobalKPIs>('/api/v1/kpis'),
  shows: () => get<{ shows: Show[]; active_show: Show | null }>('/api/v1/shows'),
  sensors: () => get<SensorHealth[]>('/api/v1/sensors'),
  alerts: () => get<Alert[]>('/api/v1/alerts'),
  tv: (screenId: string) => get<TVScreenState>(`/api/v1/tv/${screenId}`),
  route: (lat: number, lon: number) =>
    post<BathroomRouteDecision>('/api/v1/route', { user_lat: lat, user_lon: lon }),
  chat: (message: string) => post<ChatResponse>('/api/v1/chat', { message }),
  simulateTick: (scenario: string) =>
    post<{ ok: boolean; tick: number }>('/api/v1/simulate/tick', { scenario }),
  sensorsSummary: () => get<SensorSummary>('/api/v1/sensors/summary'),
  sensorsCoverage: () => get<CoverageGeoJSON>('/api/v1/sensors/coverage'),
  sensorsBattery: () => get<BatteryReport[]>('/api/v1/sensors/battery'),
  sensorsMaintenance: () => get<MaintenanceItem[]>('/api/v1/sensors/maintenance'),
  gateways: () => get<GatewayStatus[]>('/api/v1/gateways'),
  sensorsByCluster: (clusterId: string) => get<SensorNode[]>(`/api/v1/sensors/cluster/${clusterId}`),
  sensorById: (sensorId: string) => get<SensorNode>(`/api/v1/sensors/${sensorId}`),
  pingSensor: (sensorId: string) => post<{ acknowledged: boolean }>(`/api/v1/sensors/${sensorId}/ping`, {}),
};
