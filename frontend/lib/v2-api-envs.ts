/**
 * PlantaOS v2 — Cliente API para AMBIENTES de sensores
 * Modulo separado para nao conflitar com os tipos do v2-api.ts principal.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const r = await fetch(url, init);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export interface Env {
  id: string;
  nome: string;
  modo: 'sim' | 'real';
  refresh_ms: number;
  fixo?: boolean;
  fonte?: string;
  n_sensores?: number;
}

export interface EnvSensor {
  id: string;
  tipo: string;
  cluster?: string | null;
  status?: string;
  label?: string;
  battery?: { pct: number; fonte: string };
  rssi_dbm?: number;
  uptime_s?: number;
  origem?: string;
  age_s?: number;
}

export interface EnvFleet {
  env: string;
  modo: string;
  refresh_ms: number;
  total: number;
  ts: number;
  sensors: EnvSensor[];
}

export const envApi = {
  list: () => getJson<{ envs: Env[] }>('/api/v1/envs'),
  get: (id: string) => getJson<Env & { sensores: EnvSensor[] }>(`/api/v1/envs/${id}`),
  create: (body: { nome: string; modo?: string; refresh_ms?: number }) =>
    getJson<Env>('/api/v1/envs', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),
  remove: (id: string) =>
    getJson<{ deleted: string }>(`/api/v1/envs/${id}`, { method: 'DELETE' }),
  fleet: (id: string) => getJson<EnvFleet>(`/api/v1/envs/${id}/fleet`),
  addSensor: (
    envId: string,
    body: { id: string; tipo: string; label?: string; cluster?: string }
  ) =>
    getJson<EnvSensor>(`/api/v1/envs/${envId}/sensors`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),
  removeSensor: (envId: string, sid: string) =>
    getJson<{ removed: boolean }>(`/api/v1/envs/${envId}/sensors/${sid}`, {
      method: 'DELETE',
    }),
  lobby: () => getJson<{ lobby: any[] }>('/api/v1/lobby'),
  bulkGen: (envId: string, body: { prefixo: string; tipo: string; quantidade: number; inicio?: number }) =>
    getJson<{ adicionados: any[]; ignorados: string[] }>(`/api/v1/envs/${envId}/sensors/bulk_gen`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
    }),
  bulkList: (envId: string, sensores: { id: string; tipo: string; label?: string }[]) =>
    getJson<{ adicionados: any[]; ignorados: string[] }>(`/api/v1/envs/${envId}/sensors/bulk_list`, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ sensores }),
    }),
  caps: (id: string, tipo: string, cluster?: string, rssi?: number) =>
    getJson<any>(`/api/v1/sensorcaps/${id}?tipo=${tipo}${cluster ? '&cluster=' + cluster : ''}${rssi != null ? '&rssi=' + rssi : ''}`),
  networkCoverage: () => getJson<any>('/api/v1/network/coverage'),
  setDemoHour: (h: number) => getJson<any>(`/api/v1/demo/hour?h=${h}`, { method: 'POST' }),
  getDemoHour: () => getJson<any>('/api/v1/demo/hour'),
};
