/**
 * PlantaOS v2 — Cliente API tipado
 * Consome o backend em api.plantarockinrio.com
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

// ============================================================================
// Tipos
// ============================================================================

export interface Section {
  section_id: string;
  cluster_id?: string;
  gender?: 'M' | 'F' | 'U';
  ocupacao_pct?: number;
  fila_atual?: number;
  tempo_espera_min?: number;
  fluxo_entrada_pmin?: number;
  status?: 'ok' | 'warning' | 'critical' | 'offline';
  simulated?: boolean;
  confidence?: number;
}

export interface KPIs {
  avg_ocupacao_pct?: number;
  total_fila?: number;
  critical_sections?: number;
  redirected_count?: number;
  any_simulated?: boolean;
  flow_index?: number;
}

export interface StateResponse {
  ts?: string;
  kpis?: KPIs;
  sections?: Section[];
}

export interface SensorNode {
  sensor_id: string;
  cluster_id: string;
  model: string;
  vendor?: string;
  network?: string;
  online?: boolean;
  battery_pct?: number;
  rssi?: number;
  last_seen?: string;
  gps_lat?: number;
  gps_lon?: number;
  health?: {
    status?: string;
    note?: string;
  };
}

export interface Alert {
  id: string;
  cluster_id?: string;
  severity: 'info' | 'warning' | 'critical';
  message: string;
  ts: string;
  acknowledged?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  reply: string;
  model?: string;
  ts?: string;
}

// ============================================================================
// Cluster catalog (ground truth — Parque Tejo)
// ============================================================================

export interface ClusterMeta {
  id: string;
  code: string;
  zone: string;
  total: number;
  male: number;
  female: number;
  pmr: number;
  urinois: number;
  sinks: number;
  type: 'MISTO' | 'FEM-DOM' | 'UNISEX' | 'CALHA-M';
  isUnisex: boolean;
  x: number;
  y: number;
  gpsLat: number;
  gpsLon: number;
  distStageM: number;
}

export const CLUSTERS: ClusterMeta[] = [
  {
    id: 'wc-01', code: 'V34', zone: 'Palco Mundo',
    total: 135, male: 72, female: 63, pmr: 2, urinois: 3, sinks: 2,
    type: 'MISTO', isUnisex: false,
    x: 468, y: 379,
    gpsLat: 38.78230, gpsLon: -9.09371, distStageM: 30,
  },
  {
    id: 'wc-02', code: 'V35', zone: 'Central Norte',
    total: 126, male: 54, female: 72, pmr: 2, urinois: 2, sinks: 2,
    type: 'FEM-DOM', isUnisex: false,
    x: 982, y: 467,
    gpsLat: 38.78193, gpsLon: -9.09323, distStageM: 180,
  },
  {
    id: 'wc-03', code: 'S36', zone: 'Entrada Norte',
    total: 102, male: 54, female: 48, pmr: 2, urinois: 3, sinks: 3,
    type: 'MISTO', isUnisex: false,
    x: 1326, y: 588,
    gpsLat: 38.78111, gpsLon: -9.09310, distStageM: 320,
  },
  {
    id: 'wc-04', code: 'S37', zone: 'Music Valley',
    total: 150, male: 84, female: 66, pmr: 2, urinois: 3, sinks: 1,
    type: 'MISTO', isUnisex: false,
    x: 202, y: 765,
    gpsLat: 38.78195, gpsLon: -9.09275, distStageM: 40,
  },
  {
    id: 'wc-05', code: 'M38', zone: 'Central (entrada)',
    total: 133, male: 0, female: 0, pmr: 2, urinois: 0, sinks: 1,
    type: 'UNISEX', isUnisex: true,
    x: 992, y: 913,
    gpsLat: 38.78150, gpsLon: -9.09303, distStageM: 20,
  },
  {
    id: 'wc-06', code: 'W39', zone: 'Sul (maior)',
    total: 208, male: 0, female: 0, pmr: 6, urinois: 6, sinks: 6,
    type: 'UNISEX', isUnisex: true,
    x: 247, y: 1004,
    gpsLat: 38.78010, gpsLon: -9.09549, distStageM: 200,
  },
  {
    id: 'wc-07', code: 'M40', zone: 'Sul Central',
    total: 138, male: 84, female: 54, pmr: 3, urinois: 8, sinks: 2,
    type: 'CALHA-M', isUnisex: false,
    x: 827, y: 1118,
    gpsLat: 38.78069, gpsLon: -9.09356, distStageM: 280,
  },
  {
    id: 'wc-08', code: 'V41', zone: 'Sul Produção',
    total: 145, male: 84, female: 61, pmr: 2, urinois: 4, sinks: 2,
    type: 'MISTO', isUnisex: false,
    x: 249, y: 1384,
    gpsLat: 38.77936, gpsLon: -9.09619, distStageM: 350,
  },
];

export const TOTAL_LUGARES = CLUSTERS.reduce((a, c) => a + c.total, 0); // 1137

// ============================================================================
// Shows (4 days)
// ============================================================================

export interface ShowLineupItem {
  time: string;
  artist: string;
  stage: string;
  genre: string;
  headliner?: boolean;
}

export interface Show {
  id: string;
  date: string;
  dayLabel: string;
  theme: string;
  headliner: string;
  crowd: number;
  peakHour: number;
  surgeFactor: number;
  visitsPerHead: number;
  lineup: ShowLineupItem[];
  crowdCurve: Record<number, number>;
}

export const SHOWS: Show[] = [
  {
    id: 'd1',
    date: '20 Junho 2026',
    dayLabel: 'Sábado · POP DAY',
    theme: 'pop',
    headliner: 'Katy Perry',
    crowd: 118000,
    peakHour: 21,
    surgeFactor: 3.8,
    visitsPerHead: 3.2,
    lineup: [
      { time: '14:30', artist: 'NAPA', stage: 'Palco Mundo', genre: 'Pop PT' },
      { time: '16:00', artist: 'Calema', stage: 'Palco Mundo', genre: 'Kizomba' },
      { time: '18:00', artist: 'Pedro Sampaio', stage: 'Palco Mundo', genre: 'Funk Carioca' },
      { time: '19:30', artist: 'Charlie Puth', stage: 'Palco Mundo', genre: 'Pop' },
      { time: '21:00', artist: 'Katy Perry', stage: 'Palco Mundo', genre: 'Pop', headliner: true },
      { time: '14:30', artist: 'Maninho', stage: 'Music Valley', genre: 'Afrobeats' },
      { time: '16:00', artist: 'Nena', stage: 'Music Valley', genre: 'Pop PT' },
      { time: '18:00', artist: 'Audrey Nuna', stage: 'Music Valley', genre: 'Alt R&B' },
      { time: '21:00', artist: 'Alok', stage: 'Music Valley', genre: 'Electronic', headliner: true },
    ],
    crowdCurve: { 14: 8000, 15: 22000, 16: 40000, 17: 62000, 18: 82000, 19: 96000, 20: 108000, 21: 118000, 22: 116000, 23: 110000, 0: 80000, 1: 45000, 2: 10000 },
  },
  {
    id: 'd2',
    date: '21 Junho 2026',
    dayLabel: 'Domingo · LEGENDS ROCK',
    theme: 'rock',
    headliner: 'Linkin Park',
    crowd: 115000,
    peakHour: 23,
    surgeFactor: 4.2,
    visitsPerHead: 3.8,
    lineup: [
      { time: '14:00', artist: 'P.O.D.', stage: 'Palco Mundo', genre: 'Nu Metal' },
      { time: '15:00', artist: 'Hoobastank', stage: 'Palco Mundo', genre: 'Alt Rock' },
      { time: '16:00', artist: 'Blasted Mechanism', stage: 'Palco Mundo', genre: 'Alt PT' },
      { time: '17:15', artist: 'Sepultura', stage: 'Palco Mundo', genre: 'Thrash Metal' },
      { time: '18:30', artist: 'Grandson', stage: 'Palco Mundo', genre: 'Alt Rock' },
      { time: '19:30', artist: 'Kaiser Chiefs', stage: 'Palco Mundo', genre: 'Indie Rock' },
      { time: '20:30', artist: 'The Pretty Reckless', stage: 'Palco Mundo', genre: 'Hard Rock' },
      { time: '21:30', artist: 'Cypress Hill', stage: 'Palco Mundo', genre: 'Hip-Hop' },
      { time: '23:00', artist: 'Linkin Park', stage: 'Palco Mundo', genre: 'Nu Metal', headliner: true },
      { time: '21:00', artist: 'Tara Perdida', stage: 'Super Bock', genre: 'Metal PT', headliner: true },
    ],
    crowdCurve: { 14: 6000, 15: 18000, 16: 34000, 17: 55000, 18: 74000, 19: 90000, 20: 102000, 21: 110000, 22: 114000, 23: 115000, 0: 95000, 1: 55000, 2: 12000 },
  },
  {
    id: 'd3',
    date: '27 Junho 2026',
    dayLabel: 'Sábado · LEGENDS CLASSIC',
    theme: 'classic',
    headliner: 'Rod Stewart',
    crowd: 110000,
    peakHour: 22,
    surgeFactor: 3.2,
    visitsPerHead: 3.5,
    lineup: [
      { time: '15:00', artist: 'UHF', stage: 'Palco Mundo', genre: 'Rock PT' },
      { time: '16:30', artist: 'Xutos & Pontapés', stage: 'Palco Mundo', genre: 'Rock PT' },
      { time: '18:30', artist: 'Shaggy', stage: 'Palco Mundo', genre: 'Reggae' },
      { time: '19:30', artist: '4 Non Blondes', stage: 'Palco Mundo', genre: 'Rock' },
      { time: '20:30', artist: 'Cyndi Lauper', stage: 'Palco Mundo', genre: 'New Wave' },
      { time: '22:00', artist: 'Rod Stewart', stage: 'Palco Mundo', genre: 'Rock/Pop', headliner: true },
      { time: '17:00', artist: 'Belo', stage: 'Super Bock', genre: 'MPB' },
      { time: '19:30', artist: 'Syro', stage: 'Super Bock', genre: 'Pop PT' },
      { time: '21:00', artist: 'The Wailers', stage: 'Super Bock', genre: 'Reggae 50 anos', headliner: true },
    ],
    crowdCurve: { 14: 5000, 15: 16000, 16: 30000, 17: 50000, 18: 70000, 19: 86000, 20: 98000, 21: 106000, 22: 110000, 23: 108000, 0: 85000, 1: 52000, 2: 9000 },
  },
  {
    id: 'd4',
    date: '28 Junho 2026',
    dayLabel: 'Domingo · URBAN / HIP-HOP',
    theme: 'urban',
    headliner: '21 Savage',
    crowd: 120000,
    peakHour: 22,
    surgeFactor: 3.6,
    visitsPerHead: 3.0,
    lineup: [
      { time: '15:00', artist: 'Irina Barros', stage: 'Palco Mundo', genre: 'Pop PT' },
      { time: '16:30', artist: 'Carlão', stage: 'Palco Mundo', genre: 'Hip-Hop PT' },
      { time: '18:00', artist: 'Dennis', stage: 'Palco Mundo', genre: 'Funk' },
      { time: '19:00', artist: 'Filipe Ret', stage: 'Palco Mundo', genre: 'Trap BR' },
      { time: '19:30', artist: 'Matuê', stage: 'Palco Mundo', genre: 'Trap BR' },
      { time: '20:00', artist: 'Rema', stage: 'Palco Mundo', genre: 'Afrobeats' },
      { time: '20:30', artist: 'Central Cee', stage: 'Palco Mundo', genre: 'UK Drill' },
      { time: '22:00', artist: '21 Savage', stage: 'Palco Mundo', genre: 'Trap', headliner: true },
      { time: '21:00', artist: 'Lola Índigo', stage: 'Super Bock', genre: 'Pop/Urban', headliner: true },
    ],
    crowdCurve: { 14: 7000, 15: 20000, 16: 38000, 17: 60000, 18: 80000, 19: 98000, 20: 110000, 21: 116000, 22: 120000, 23: 118000, 0: 90000, 1: 50000, 2: 11000 },
  },
];

// ============================================================================
// Sensor catalog
// ============================================================================

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
    range: '45m efectivos a 80k pessoas',
    uptime: '99%',
    note: '6 GHz menos congestionado · PoE plug-and-play · Omada mesh.',
    accent: '#2E7D4F',
  },
  {
    name: '2G GSM M2M',
    role: 'Cellular',
    tech: 'LILYGO SIM800L · SIM NOS M2M',
    units: 8,
    costEur: 88,
    range: '700m efectivos a 80k pessoas',
    uptime: '99%',
    note: 'APN m2m.nos.pt · buffer SPIFFS 273 horas offline.',
    accent: '#2563EB',
  },
  {
    name: 'LoRaWAN 868 MHz',
    role: 'Longa distância',
    tech: 'Dragino DLOS8',
    units: 2,
    costEur: 420,
    range: '3 000m em campo aberto',
    uptime: '99.5%',
    note: 'Margem de 40 dB com 80k pessoas · fallback total se WiFi e 2G caírem.',
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
    note: '273 horas de dados retidos em flash local · zero perda de dados se a rede falhar.',
    accent: '#A85D00',
  },
];

export interface SensorSpec {
  id: string;
  name: string;
  category: string;
  vendor: string;
  unitPrice: number;
  unitsProject: number;
  totalCost: number;
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

export const SENSORS: SensorSpec[] = [
  {
    id: 'ir',
    name: 'E18-D80NK · barreira IR difusa',
    category: 'Contagem de entradas/saídas',
    vendor: 'Genérico (Mouser/Amazon)',
    unitPrice: 4,
    unitsProject: 32,
    totalCost: 128,
    protocol: 'GPIO 5V → ESP32',
    range: '3–80 cm ajustável',
    power: '100 mA · 5V',
    ipRating: 'IP54 em caixa',
    installMin: 10,
    privacy: 'Anónimo · só pulsos',
    pros: ['EUR 4 / unidade', 'Sem imagem · zero PII', 'Direccional (entrada vs saída)'],
    cons: ['Requer alinhamento físico', 'Sensível a chuva directa sem caixa'],
    recommended: true,
  },
  {
    id: 'hub2g',
    name: 'LILYGO T-Call SIM800L · hub de cluster',
    category: 'Edge hub',
    vendor: 'LilyGo · AliExpress / Amazon.es',
    unitPrice: 9,
    unitsProject: 8,
    totalCost: 72,
    protocol: '2G GSM → MQTT TLS',
    range: '700m com multidão',
    power: '22 mA médio · bateria 10Ah = 16 dias',
    ipRating: 'IP65 em caixa',
    installMin: 30,
    privacy: 'Só dados agregados',
    pros: ['EUR 9', 'Agrega 4 IR + WiFi sniff', 'Buffer SPIFFS 273 h'],
    cons: ['2G (não 4G)', 'Cobertura 2G futura limitada após 2030'],
    recommended: true,
  },
  {
    id: 'people',
    name: 'Milesight VS121-P · contador WiFi PoE',
    category: 'Contador certificado',
    vendor: 'Milesight · Worten / Amazon.es',
    unitPrice: 149,
    unitsProject: 8,
    totalCost: 1192,
    protocol: 'WiFi PoE',
    range: 'Até 3 m de altura',
    power: 'PoE 802.3af',
    ipRating: 'IP40',
    installMin: 20,
    privacy: 'Edge AI · não guarda imagem',
    pros: ['99.5 % de precisão', 'Edge AI nativo RGPD', 'PoE plug-and-play'],
    cons: ['EUR 149/un', 'Requer switch PoE'],
    recommended: true,
  },
  {
    id: 'wifi_ap',
    name: 'TP-Link EAP670 · WiFi 6E AP',
    category: 'Backbone WiFi',
    vendor: 'TP-Link · Worten / Fnac',
    unitPrice: 129,
    unitsProject: 16,
    totalCost: 2064,
    protocol: 'WiFi 6E 802.11ax · PoE',
    range: '45m efectivos',
    power: 'PoE 802.3at',
    ipRating: 'IP30 (em caixa)',
    installMin: 20,
    privacy: 'Aggregate-only (não guarda MACs)',
    pros: ['6 GHz menos congestionado', 'Omada mesh auto-healing'],
    cons: ['EUR 129', 'Requer switch PoE'],
    recommended: true,
  },
  {
    id: 'lora_gw',
    name: 'Dragino DLOS8 · LoRaWAN gateway',
    category: 'Gateway LoRaWAN',
    vendor: 'Dragino.com',
    unitPrice: 210,
    unitsProject: 2,
    totalCost: 420,
    protocol: 'LoRaWAN 868 MHz → MQTT',
    range: '3 000m outdoor',
    power: 'PoE',
    ipRating: 'IP67',
    installMin: 60,
    privacy: 'Só metadados',
    pros: ['3 km cobertura', 'IP67', 'Backup total se WiFi falha'],
    cons: ['EUR 210 / un', 'Requer PoE no ponto elevado'],
    recommended: true,
  },
  {
    id: 'cam',
    name: 'Câmara Prosegur com pessoa-counting',
    category: 'Validação cruzada',
    vendor: 'Prosegur (parceria Rock World)',
    unitPrice: 0,
    unitsProject: 8,
    totalCost: 0,
    protocol: 'HTTP push (Prosegur API)',
    range: '15 m × 15 m por câmara',
    power: 'PoE',
    ipRating: 'IP66',
    installMin: 0,
    privacy: 'Counting agregado · sem imagem partilhada',
    pros: ['Já instaladas pela Prosegur', 'Custo zero para o projecto'],
    cons: ['Latência ~10 s', 'Depende de Prosegur on-line'],
    recommended: true,
  },
  {
    id: 'matter',
    name: 'Matter 1.2',
    category: 'Protocolo (não usado)',
    vendor: 'Apple / Google / Amazon',
    unitPrice: 0,
    unitsProject: 0,
    totalCost: 0,
    protocol: 'Matter over Thread/WiFi',
    range: '10–30 m',
    power: 'depende do device',
    ipRating: 'varia',
    installMin: 0,
    privacy: 'depende da cloud',
    pros: ['Standard universal', 'Boa interoperabilidade indoor'],
    cons: ['Desenhado para domótica', 'Inadequado outdoor 80k pessoas', 'Sem MQTT/LoRaWAN nativo'],
    recommended: false,
    note: 'Matter é inadequado para festival outdoor. Recomendação Planta: LoRaWAN + MQTT TLS.',
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
  sensors: () => getJson<{ sensors: SensorNode[] } | SensorNode[]>('/api/v1/sensors'),
  alerts: () => getJson<{ alerts: Alert[] } | Alert[]>('/api/v1/alerts'),
  chat: (messages: ChatMessage[]) =>
    getJson<ChatResponse>('/api/v1/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ messages }),
    }),
};

// ============================================================================
// Aggregator: backend sections → 8 clusters
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

export function toWcId(sectionId: string): string {
  return sectionId.split('_')[0].toLowerCase();
}

export function aggregate(sections: Section[]): ClusterLive[] {
  return CLUSTERS.map((meta) => {
    const subset = sections.filter((s) => toWcId(s.section_id) === meta.id);
    let homens = 0;
    let mulheres = 0;
    let occList: number[] = [];
    let waitList: number[] = [];
    let fila = 0;
    let flux = 0;
    let sim = false;
    let crit = false;

    for (const s of subset) {
      const occ = Number(s.ocupacao_pct ?? 0);
      const f = Number(s.fila_atual ?? 0);
      const w = Number(s.tempo_espera_min ?? 0);
      const fx = Number(s.fluxo_entrada_pmin ?? 0);
      const estim = Math.round(fx * 5);
      const g = s.section_id.endsWith('_F')
        ? 'F'
        : s.section_id.endsWith('_M')
        ? 'M'
        : 'U';
      if (g === 'M') homens += estim;
      else if (g === 'F') mulheres += estim;
      occList.push(occ);
      waitList.push(w);
      fila += f;
      flux += fx;
      if (s.simulated) sim = true;
      if (s.status === 'critical') crit = true;
    }

    const occAvg = occList.length
      ? Math.round(occList.reduce((a, b) => a + b, 0) / occList.length)
      : 0;
    const waitAvg = waitList.length
      ? Math.round(waitList.reduce((a, b) => a + b, 0) / waitList.length)
      : 0;
    const pessoas = meta.isUnisex ? homens + mulheres : homens + mulheres;
    const entradas = Math.round(flux * 10);
    const saidas = Math.round(flux * 9);
    let status: 'ok' | 'warning' | 'critical' = 'ok';
    if (crit || occAvg >= 80) status = 'critical';
    else if (occAvg >= 60) status = 'warning';

    return {
      meta,
      ocupacao: occAvg,
      pessoas,
      homens: meta.isUnisex ? null : homens,
      mulheres: meta.isUnisex ? null : mulheres,
      filaTotal: fila,
      esperaMin: waitAvg,
      entradas,
      saidas,
      confianca: sim ? 0.5 : 0.92,
      simulated: sim,
      status,
    };
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
  if (s === 'critical') return 'var(--critical)';
  if (s === 'warning') return 'var(--amber)';
  return 'var(--green)';
}

export function occupancyColor(p: number): string {
  if (p >= 80) return 'var(--critical)';
  if (p >= 60) return 'var(--amber)';
  return 'var(--green-light)';
}
