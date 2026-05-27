export type SectionStatus = 'ok' | 'warning' | 'critical' | 'offline';

export interface SectionState {
  section_id: string;
  cluster_id: string;
  gender: 'M' | 'F' | 'U';
  ocupacao_pct: number;
  fila_atual: number;
  tempo_espera_min: number;
  fluxo_entrada: number;
  fluxo_saida: number;
  status: SectionStatus;
  simulated: boolean;
  confidence: number;
  last_updated: string;
}

export interface GlobalKPIs {
  total_visitors_estimated: number;
  avg_wait_min: number;
  critical_sections: number;
  active_redirections: number;
  sensor_health_pct: number;
  sections_ok: number;
  sections_warning: number;
  sections_critical: number;
  sections_offline: number;
  peak_cluster: string | null;
  lightest_cluster: string | null;
  timestamp: string;
}

export interface LivePayload {
  timestamp: string;
  sections: SectionState[];
  kpis: GlobalKPIs;
  any_simulated: boolean;
  any_critical: boolean;
  active_show: Show | null;
  backend_version: string;
  tick_count: number;
  last_tick_age_s: number;
}

export interface SensorHealth {
  cluster_id: string;
  lilygo_online: boolean;
  lilygo_last_seen: number | null;
  ir_entry_online: boolean;
  ir_exit_online: boolean;
  wifi_online: boolean;
  camera_online: boolean;
  lorawan_available: boolean;
  active_sources: string[];
  confidence: number;
  issues: string[];
  last_update_ts: number;
  simulated: boolean;
}

export interface Alert {
  alert_id: string;
  severity: 'critical' | 'warning' | 'info';
  cluster_id: string | null;
  section_id: string | null;
  message: string;
  created_at: string;
  resolved: boolean;
  resolved_at: string | null;
}

export interface Show {
  show_id: string;
  artist: string;
  stage: string;
  start_time: string;
  end_time: string;
  expected_attendance: number;
  surge_clusters: string[];
  is_active: boolean;
  surge_factor: number;
}

export interface TVScreenState {
  screen_id: string;
  cluster_id: string;
  best_section: SectionState | null;
  alternatives: SectionState[];
  avoid_clusters: string[];
  walking_time_min: number;
  direction_arrow: string;
  critical_override: boolean;
  simulated: boolean;
  last_updated: string;
}

export interface ClusterSummary {
  cluster_id: string;
  name: string;
  location_hint: string;
  sections: SectionState[];
  avg_ocupacao_pct: number;
  total_fila: number;
  min_wait_min: number;
  status: SectionStatus;
  simulated: boolean;
}

export interface RouteOption {
  cluster_id: string;
  section_id: string;
  cluster_name: string;
  walking_time_min: number;
  wait_time_min: number;
  total_time_min: number;
  direction_arrow: string;
  ocupacao_pct: number;
  confidence: number;
}

export interface BathroomRouteDecision {
  best: RouteOption | null;
  alternatives: RouteOption[];
  avoid: string[];
  reasoning: string;
  simulated: boolean;
  grounded: boolean;
  last_tick_age_s: number;
}

export interface ChatResponse {
  reply: string;
  grounded: boolean;
  last_tick_age_s: number;
  sources: string[];
  simulated: boolean;
}

export interface APIError extends Error {
  status?: number;
  isOffline?: boolean;
}

export interface SensorNode {
  id: string;
  type: 'lilygo' | 'ir' | 'wifi' | 'camera' | 'lorawan';
  model: string;
  cluster_id: string | null;
  section_id: string | null;
  direction: string | null;
  lat: number | null;
  lon: number | null;
  hub_id: string | null;
  gateway_id: string | null;
  status: 'online' | 'degraded' | 'offline';
  last_seen_ts: number | null;
}

export interface GatewayStatus {
  gateway_id: string;
  model: string;
  lat: number;
  lon: number;
  status: 'online' | 'degraded' | 'offline';
  last_seen_ts: number;
  connected_hubs: string[];
  packet_loss_pct: number;
}

export interface BatteryReport {
  hub_id: string;
  cluster_id: string;
  battery_mah: number;
  draw_ma: number;
  estimated_days_remaining: number;
  last_seen_ts: number;
  status: 'ok' | 'low' | 'critical';
}

export interface CoverageFeature {
  sensor_id: string;
  sensor_type: string;
  cluster_id: string | null;
  lat: number;
  lon: number;
  radius_m: number;
  status: string;
}

export interface CoverageGeoJSON {
  type: string;
  features: CoverageFeature[];
}

export interface MaintenanceItem {
  cluster_id: string;
  hub_installed: boolean;
  ir_count_expected: number;
  ir_count_installed: number;
  wifi_ap_count_expected: number;
  wifi_ap_count_installed: number;
  camera_count_expected: number;
  camera_count_installed: number;
  last_inspection_ts: number | null;
  notes: string;
}

export interface SensorSummary {
  total: number;
  lilygo: number;
  ir: number;
  wifi: number;
  camera: number;
  lorawan: number;
  clusters: string[];
  unisex_clusters: string[];
  fusion_weights: { ir: number; wifi: number; camera: number };
}
