/**
 * PlantaOS v2 — Cliente API tipado · 100% backend-driven
 *
 * Tudo o que aqui está vem de api.plantarockinrio.com:
 *   - GET  /api/v1/state            → KPIs + sections
 *   - GET  /api/v1/clusters         → 8 clusters agrupados por género
 *   - GET  /api/v1/sensors          → 66 sensores no terreno
 *   - GET  /api/v1/sensors/summary  → contagens por tipo
 *   - GET  /api/v1/shows            → programação real do festival
 *   - GET  /api/v1/alerts           → alertas activos
 *   - POST /api/v1/chat             → Gemini 2.5 Flash com contexto live
 *   - POST /api/v1/route            → recomendação de WC mais rápida
 *
 * Catálogo local de fallback (GPS, lugares, tipologia) apenas para o que
 * o backend não devolve ainda — coordenadas físicas no recinto.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

// ============================================================================
// Tipos — espelham EXACTAMENTE o que o backend devolve
// ============================================================================

export interface Section {
  section_id: string;
  ocupacao_pct: number;
  fila_atual: number;
  tempo_espera_min: number;
  fluxo_entrada_pmin: number;
  status: 'normal' | 'warning' | 'critical' | 'offline' | 'ok';
  simulated: boolean;
  gender: 'M' | 'F' | 'U';
}

export interface KPIs {
  avg_ocupacao_pct: number;
  total_fila: number;
  critical_sections: number;
  redirected_count: number;
  any_simulated: boolean;
}

export interface ClusterSummary {
  avg_ocupacao_pct: number;
  total_fila: number;
  status: string;
  simulated: boolean;
}

export interface BackendCluster {
  cluster_id: string;
  unisex: boolean;
  sections: Section[];
  summary: ClusterSummary;
}

export interface StateResponse {
  kpis: KPIs;
  sections: Section[];
}

export interface ClustersResponse {
  clusters: BackendCluster[];
}

export interface SensorHealth {
  last_seen: string | null;
  last_rssi_dbm: number | null;
  last_uptime_s: number | null;
  battery_pct: number | null;
  firmware_ver: string | null;
  events_today: number;
  status: 'unknown' | 'online' | 'offline' | 'degraded';
  updated_at: string;
}

export interface BackendSensor {
  id: string;
  cluster_id: string;
  type: 'ir_entry' | 'ir_exit' | 'lilygo' | 'wifi_aggregate' | 'camera_ml' | 'lorawan_gateway';
  model: string;
  protocol: string;
  location_desc: string | null;
  gps_lat: number | null;
  gps_lon: number | null;
  height_cm: number | null;
  gpio_pin: number | null;
  has_battery: boolean;
  battery_mah: number | null;
  powered_by: string | null;
  ip_rating: string | null;
  coverage_radius_m: number | null;
  wifi_factor: number | null;
  fusion_weight: number | null;
  firmware: string | null;
  cost_eur: number | null;
  notes: string | null;
  critical_note: string | null;
  installed_at: string | null;
  installed_by: string | null;
  created_at: string;
  is_active: boolean;
  health: SensorHealth;
}

export interface SensorsSummary {
  total: number;
  by_type: Record<string, number>;
  health: Record<string, number>;
  fusion_weights: Record<string, number>;
  clusters: string[];
  unisex_clusters: string[];
}

export interface BackendShow {
  show_id: string;
  name: string;
  stage: string;
  start_iso: string;
  end_iso: string;
  headliner: boolean;
  expected_surge_pct: number;
}

export interface ShowsResponse {
  shows: BackendShow[];
}

export interface Alert {
  id: string;
  cluster_id?: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  ts: string;
  acknowledged?: boolean;
}

export interface ChatResponse {
  reply: string;
  grounded: boolean;
  live_data_available: boolean;
  ts: number;
}

export interface RouteRequest {
  from_section?: string;
  prefer_gender?: 'M' | 'F' | 'U';
}

export interface RouteResponse {
  recommended: string;
  walk_min: number;
  queue_min: number;
  total_cost_min: number;
  alternatives: string[];
}

// ============================================================================
// Catálogo físico local — APENAS coordenadas e tipologia do recinto
// (o backend não devolve isto — vem do planeamento físico Rock World)
// ============================================================================

export interface ClusterMeta {
  id: string;             // wc-01
  backendId: string;      // WC-01
  code: string;           // V34, V35, S36, ...
  zone: string;
  total: number;
  male: number;
  female: number;
  pmr: number;
  urinois: number;
  sinks: number;
  type: 'MISTO' | 'FEM-DOM' | 'UNISEX' | 'CALHA-M';
  isUnisex: boolean;
  // posição relativa no SVG do mapa
  x: number;
  y: number;
  // GPS real Parque Tejo
  gpsLat: number;
  gpsLon: number;
  distStageM: number;
}

export const CLUSTER_META: Record<string, ClusterMeta> = {
  'wc-01': {
    id: 'wc-01', backendId: 'WC-01', code: 'V34', zone: 'Palco Mundo',
    total: 135, male: 72, female: 63, pmr: 2, urinois: 3, sinks: 2,
    type: 'MISTO', isUnisex: false,
    x: 468, y: 379, gpsLat: 38.78230, gpsLon: -9.09371, distStageM: 30,
  },
  'wc-02': {
    id: 'wc-02', backendId: 'WC-02', code: 'V35', zone: 'Central Norte',
    total: 126, male: 54, female: 72, pmr: 2, urinois: 2, sinks: 2,
    type: 'FEM-DOM', isUnisex: false,
    x: 982, y: 467, gpsLat: 38.78193, gpsLon: -9.09323, distStageM: 180,
  },
  'wc-03': {
    id: 'wc-03', backendId: 'WC-03', code: 'S36', zone: 'Entrada Norte',
    total: 102, male: 54, female: 48, pmr: 2, urinois: 3, sinks: 3,
    type: 'MISTO', isUnisex: false,
    x: 1326, y: 588, gpsLat: 38.78111, gpsLon: -9.09310, distStageM: 320,
  },
  'wc-04': {
    id: 'wc-04', backendId: 'WC-04', code: 'S37', zone: 'Music Valley',
    total: 150, male: 84, female: 66, pmr: 2, urinois: 3, sinks: 1,
    type: 'MISTO', isUnisex: false,
    x: 202, y: 765, gpsLat: 38.78195, gpsLon: -9.09275, distStageM: 40,
  },
  'wc-05': {
    id: 'wc-05', backendId: 'WC-05', code: 'M38', zone: 'Central (entrada)',
    total: 133, male: 0, female: 0, pmr: 2, urinois: 0, sinks: 1,
    type: 'UNISEX', isUnisex: true,
    x: 992, y: 913, gpsLat: 38.78150, gpsLon: -9.09303, distStageM: 20,
  },
  'wc-06': {
    id: 'wc-06', backendId: 'WC-06', code: 'W39', zone: 'Sul (maior)',
    total: 208, male: 0, female: 0, pmr: 6, urinois: 6, sinks: 6,
    type: 'UNISEX', isUnisex: true,
    x: 247, y: 1004, gpsLat: 38.78010, gpsLon: -9.09549, distStageM: 200,
  },
  'wc-07': {
    id: 'wc-07', backendId: 'WC-07', code: 'M40', zone: 'Sul Central',
    total: 138, male: 84, female: 54, pmr: 3, urinois: 8, sinks: 2,
    type: 'CALHA-M', isUnisex: false,
    x: 827, y: 1118, gpsLat: 38.78069, gpsLon: -9.09356, distStageM: 280,
  },
  'wc-08': {
    id: 'wc-08', backendId: 'WC-08', code: 'V41', zone: 'Sul Produção',
    total: 145, male: 84, female: 61, pmr: 2, urinois: 4, sinks: 2,
    type: 'MISTO', isUnisex: false,
    x: 249, y: 1384, gpsLat: 38.77936, gpsLon: -9.09619, distStageM: 350,
  },
};

export const CLUSTERS: ClusterMeta[] = Object.values(CLUSTER_META);
export const TOTAL_LUGARES = CLUSTERS.reduce((a, c) => a + c.total, 0);

// ============================================================================
// Catálogo local de sensores (descrição comercial)
// Real-time stock por modelo vem de /api/v1/sensors/summary
// ============================================================================

export interface SensorSpec {
  type: string;
  name: string;
  category: string;
  vendor: string;
  unitPrice: number;
  protocol: string;
  range: string;
  power: string;
  ipRating: string;
  installMin: number;
  privacy: string;
  pros: string[];
  cons: string[];
  recommended: boolean;
  note?: string;
}

export const SENSOR_CATALOG: SensorSpec[] = [
  {
    type: 'ir_entry',
    name: 'E18-D80NK · barreira IR (entrada)',
    category: 'Contagem de entradas',
    vendor: 'Genérico · Mouser / Amazon',
    unitPrice: 4,
    protocol: 'GPIO 5V → ESP32',
    range: '3–80 cm ajustável',
    power: '100 mA · 5V',
    ipRating: 'IP54 em caixa',
    installMin: 10,
    privacy: 'Anónimo · só pulsos',
    pros: ['EUR 4 / unidade', 'Sem imagem · zero PII', 'Direccional (entrada)'],
    cons: ['Requer alinhamento físico', 'Sensível a chuva sem caixa'],
    recommended: true,
  },
  {
    type: 'ir_exit',
    name: 'E18-D80NK · barreira IR (saída)',
    category: 'Contagem de saídas',
    vendor: 'Genérico · Mouser / Amazon',
    unitPrice: 4,
    protocol: 'GPIO 5V → ESP32',
    range: '3–80 cm ajustável',
    power: '100 mA · 5V',
    ipRating: 'IP54 em caixa',
    installMin: 10,
    privacy: 'Anónimo · só pulsos',
    pros: ['EUR 4 / unidade', 'Sem imagem · zero PII', 'Direccional (saída)'],
    cons: ['Requer alinhamento físico', 'Sensível a chuva sem caixa'],
    recommended: true,
  },
  {
    type: 'lilygo',
    name: 'LilyGo T-SIM7080G · hub de cluster',
    category: 'Edge hub LoRaWAN + 4G',
    vendor: 'LilyGo · AliExpress / Amazon.es',
    unitPrice: 28,
    protocol: 'LoRaWAN + 4G LTE → MQTT TLS',
    range: 'Cluster local + uplink',
    power: 'PoE · backup bateria 10 Ah',
    ipRating: 'IP65 em caixa',
    installMin: 30,
    privacy: 'Só dados agregados',
    pros: ['LoRaWAN + 4G dual radio', 'Failover automático', 'Buffer SPIFFS 273 h'],
    cons: ['EUR 28 / un', 'Bateria 3 dias sem PoE'],
    recommended: true,
  },
  {
    type: 'wifi_aggregate',
    name: 'WiFi aggregate · TP-Link EAP670',
    category: 'Contagem por WiFi sniffing',
    vendor: 'TP-Link · Worten / Fnac',
    unitPrice: 129,
    protocol: 'WiFi 6E 802.11ax · PoE',
    range: '45 m efectivos',
    power: 'PoE 802.3at',
    ipRating: 'IP30 (em caixa)',
    installMin: 20,
    privacy: 'Aggregate-only · sem MAC guardado',
    pros: ['6 GHz menos congestionado', 'Omada mesh', 'RGPD nativo'],
    cons: ['EUR 129', 'Requer switch PoE'],
    recommended: true,
  },
  {
    type: 'camera_ml',
    name: 'Câmara Prosegur com pessoa-counting',
    category: 'Validação cruzada por visão',
    vendor: 'Prosegur · parceria Rock World',
    unitPrice: 0,
    protocol: 'HTTP push (Prosegur API)',
    range: '15 × 15 m por câmara',
    power: 'PoE',
    ipRating: 'IP66',
    installMin: 0,
    privacy: 'Counting agregado · sem imagem partilhada',
    pros: ['Já instaladas pela Prosegur', 'Custo zero'],
    cons: ['Latência ~10 s', 'Depende de Prosegur online'],
    recommended: true,
  },
  {
    type: 'lorawan_gateway',
    name: 'Dragino DLOS8 · LoRaWAN gateway',
    category: 'Gateway 868 MHz',
    vendor: 'Dragino.com',
    unitPrice: 210,
    protocol: 'LoRaWAN 868 MHz → MQTT',
    range: '3 000 m outdoor',
    power: 'PoE',
    ipRating: 'IP67',
    installMin: 60,
    privacy: 'Só metadados',
    pros: ['3 km cobertura', 'IP67', 'Backup total'],
    cons: ['EUR 210 / un', 'Requer PoE elevado'],
    recommended: true,
  },
];

export interface NetworkLayer {
  name: string;
  role: string;
  tech: string;
  units: number;
  costEur: number;
  range: string;
  uptime: string;
  note: string;
  accent: string;
}

export const NETWORK_LAYERS: NetworkLayer[] = [
  {
    name: 'WiFi 6E 802.11ax',
    role: 'Primário',
    tech: 'TP-Link EAP670',
    units: 16,
    costEur: 2064,
    range: '45 m efectivos a 80k pessoas',
    uptime: '99%',
    note: '6 GHz menos congestionado · PoE plug-and-play · Omada mesh.',
    accent: '#2E7D4F',
  },
  {
    name: 'LoRaWAN 868 MHz',
    role: 'Longa distância',
    tech: 'Dragino DLOS8 · 2 gateways',
    units: 2,
    costEur: 420,
    range: '3 000 m em campo aberto',
    uptime: '99.5%',
    note: 'Margem de 40 dB com 80k pessoas · fallback total.',
    accent: '#2563EB',
  },
  {
    name: '4G LTE M2M',
    role: 'Cellular',
    tech: 'LilyGo T-SIM7080G · 8 hubs',
    units: 8,
    costEur: 224,
    range: 'Cobertura nacional NOS',
    uptime: '99%',
    note: 'APN m2m.nos.pt · uplink redundante a partir de cada cluster.',
    accent: '#8B5CF6',
  },
  {
    name: 'Buffer SPIFFS local',
    role: 'Resiliência offline',
    tech: 'ESP32 SPIFFS 4MB',
    units: 8,
    costEur: 0,
    range: 'Local — cada hub',
    uptime: '99.98%',
    note: '273 horas de dados retidos · zero perda se a rede falhar.',
    accent: '#A85D00',
  },
];

// ============================================================================
// Fetch helpers
// ============================================================================

async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    cache: 'no-store',
    ...init,
  });
  if (!r.ok) {
    throw new Error(`API ${path} → HTTP ${r.status}`);
  }
  return (await r.json()) as T;
}

export const api = {
  state: () => getJson<StateResponse>('/api/v1/state'),
  clusters: () => getJson<ClustersResponse>('/api/v1/clusters'),
  kpis: () => getJson<KPIs>('/api/v1/kpis'),
  sensors: () => getJson<BackendSensor[]>('/api/v1/sensors'),
  sensorsSummary: () => getJson<SensorsSummary>('/api/v1/sensors/summary'),
  shows: () => getJson<ShowsResponse>('/api/v1/shows'),
  alerts: () => getJson<Alert[]>('/api/v1/alerts'),
  health: () => getJson<{ status: string }>('/api/v1/health'),

  /** Schema correcto do backend: { message: string } */
  chat: (message: string) =>
    getJson<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message }),
    }),

  route: (req: RouteRequest = {}) =>
    getJson<RouteResponse>('/api/v1/route', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(req),
    }),
};

// ============================================================================
// Aggregator: BackendCluster[] → ClusterLive[] enriquecido com meta físico
// ============================================================================

export interface ClusterLive {
  meta: ClusterMeta;
  ocupacao: number;
  pessoas: number;
  homens: number | null;
  mulheres: number | null;
  filaTotal: number;
  esperaMin: number;
  entradas: number;
  saidas: number;
  confianca: number;
  simulated: boolean;
  status: 'ok' | 'warning' | 'critical';
}

export function toMetaId(backendId: string): string {
  return backendId.toLowerCase();
}

export function fromMetaId(metaId: string): string {
  return metaId.toUpperCase();
}

export function aggregateClusters(backendClusters: BackendCluster[]): ClusterLive[] {
  return CLUSTERS.map((meta) => {
    const bc = backendClusters.find((c) => c.cluster_id === meta.backendId);
    if (!bc) {
      return {
        meta,
        ocupacao: 0,
        pessoas: 0,
        homens: meta.isUnisex ? null : 0,
        mulheres: meta.isUnisex ? null : 0,
        filaTotal: 0,
        esperaMin: 0,
        entradas: 0,
        saidas: 0,
        confianca: 0.5,
        simulated: true,
        status: 'ok' as const,
      };
    }
    const occ = bc.summary.avg_ocupacao_pct;
    const totalFlux = bc.sections.reduce((a, s) => a + s.fluxo_entrada_pmin, 0);
    const avgWait =
      bc.sections.reduce((a, s) => a + s.tempo_espera_min, 0) /
      Math.max(1, bc.sections.length);
    const pessoasOcc = Math.round((occ / 100) * meta.total);

    let homens: number | null = null;
    let mulheres: number | null = null;
    if (!meta.isUnisex) {
      const secM = bc.sections.find((s) => s.gender === 'M');
      const secF = bc.sections.find((s) => s.gender === 'F');
      homens = Math.round(((secM?.ocupacao_pct ?? 0) / 100) * meta.male);
      mulheres = Math.round(((secF?.ocupacao_pct ?? 0) / 100) * meta.female);
    }

    let status: 'ok' | 'warning' | 'critical' = 'ok';
    if (bc.summary.status === 'critical' || occ >= 80) status = 'critical';
    else if (bc.summary.status === 'warning' || occ >= 60) status = 'warning';

    return {
      meta,
      ocupacao: Math.round(occ),
      pessoas: pessoasOcc,
      homens,
      mulheres,
      filaTotal: bc.summary.total_fila,
      esperaMin: Math.round(avgWait * 10) / 10,
      entradas: Math.round(totalFlux * 5),
      saidas: Math.round(totalFlux * 4.5),
      confianca: bc.summary.simulated ? 0.5 : 0.92,
      simulated: bc.summary.simulated,
      status,
    };
  });
}

export function aggregateSections(sections: Section[]): ClusterLive[] {
  const byCluster = new Map<string, Section[]>();
  for (const s of sections) {
    const cid = s.section_id.split('_')[0];
    if (!byCluster.has(cid)) byCluster.set(cid, []);
    byCluster.get(cid)!.push(s);
  }
  const fakeBackend: BackendCluster[] = Array.from(byCluster.entries()).map(
    ([cid, secs]) => ({
      cluster_id: cid,
      unisex: cid === 'WC-05' || cid === 'WC-06',
      sections: secs,
      summary: {
        avg_ocupacao_pct:
          secs.reduce((a, s) => a + s.ocupacao_pct, 0) / Math.max(1, secs.length),
        total_fila: secs.reduce((a, s) => a + s.fila_atual, 0),
        status: secs.some((s) => s.status === 'critical')
          ? 'critical'
          : secs.some((s) => s.status === 'warning')
          ? 'warning'
          : 'normal',
        simulated: secs.some((s) => s.simulated),
      },
    }),
  );
  return aggregateClusters(fakeBackend);
}

// ============================================================================
// Sensors helpers
// ============================================================================

export interface SensorEnriched extends BackendSensor {
  spec: SensorSpec | null;
}

export function enrichSensors(sensors: BackendSensor[]): SensorEnriched[] {
  const byType = new Map(SENSOR_CATALOG.map((s) => [s.type, s]));
  return sensors.map((s) => ({
    ...s,
    spec: byType.get(s.type) ?? null,
  }));
}

export function groupSensorsByCluster(
  sensors: BackendSensor[],
): Map<string, BackendSensor[]> {
  const m = new Map<string, BackendSensor[]>();
  for (const s of sensors) {
    if (!m.has(s.cluster_id)) m.set(s.cluster_id, []);
    m.get(s.cluster_id)!.push(s);
  }
  return m;
}

// ============================================================================
// Shows helpers
// ============================================================================

export interface DisplayShow {
  id: string;
  name: string;
  stage: string;
  date: string;
  dayKey: string;
  time: string;
  endTime: string;
  headliner: boolean;
  surgePct: number;
}

const MONTHS_PT = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];
const WEEKDAYS_PT = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'];

export function adaptShow(s: BackendShow): DisplayShow {
  const d = new Date(s.start_iso);
  const e = new Date(s.end_iso);
  const dayKey = s.start_iso.slice(0, 10);
  const date = `${d.getUTCDate()} ${MONTHS_PT[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  const fmt = (x: Date) =>
    `${String(x.getUTCHours()).padStart(2, '0')}:${String(x.getUTCMinutes()).padStart(2, '0')}`;
  return {
    id: s.show_id,
    name: s.name,
    stage: s.stage,
    date,
    dayKey,
    time: fmt(d),
    endTime: fmt(e),
    headliner: s.headliner,
    surgePct: s.expected_surge_pct,
  };
}

export interface ShowDay {
  dayKey: string;
  date: string;
  dayLabel: string;
  shows: DisplayShow[];
  headliner: DisplayShow | null;
}

export function groupShowsByDay(shows: BackendShow[]): ShowDay[] {
  const adapted = shows.map(adaptShow);
  const byDay = new Map<string, DisplayShow[]>();
  for (const s of adapted) {
    if (!byDay.has(s.dayKey)) byDay.set(s.dayKey, []);
    byDay.get(s.dayKey)!.push(s);
  }
  return Array.from(byDay.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([dayKey, ss]) => {
      const d = new Date(dayKey + 'T12:00:00Z');
      const dayLabel = WEEKDAYS_PT[d.getUTCDay()];
      ss.sort((a, b) => a.time.localeCompare(b.time));
      const head = ss.find((s) => s.headliner) ?? null;
      return { dayKey, date: ss[0].date, dayLabel, shows: ss, headliner: head };
    });
}

// ============================================================================
// Utilities
// ============================================================================

export function fmtNumber(n: number, locale = 'pt-PT'): string {
  return n.toLocaleString(locale);
}

export function fmtPct(n: number): string {
  return `${Math.round(n)}%`;
}

export function statusColor(s: 'ok' | 'warning' | 'critical'): string {
  if (s === 'critical') return '#C25A1A';
  if (s === 'warning') return '#A85D00';
  return '#2E7D4F';
}

export function occupancyColor(p: number): string {
  if (p >= 80) return '#C25A1A';
  if (p >= 60) return '#A85D00';
  if (p >= 40) return '#6FAF82';
  return '#2E7D4F';
}

export function sensorTypeLabel(type: string): string {
  return ({
    ir_entry: 'IR entrada',
    ir_exit: 'IR saída',
    lilygo: 'LilyGo hub',
    wifi_aggregate: 'WiFi counter',
    camera_ml: 'Câmara ML',
    lorawan_gateway: 'LoRa gateway',
  } as Record<string, string>)[type] ?? type;
}

export function sensorHealthColor(status: string): string {
  return ({
    online: '#2E7D4F',
    unknown: '#A85D00',
    degraded: '#C25A1A',
    offline: '#7A9E7E',
  } as Record<string, string>)[status] ?? '#7A9E7E';
}

// Compatibility alias para páginas existentes
export const aggregate = aggregateSections;
