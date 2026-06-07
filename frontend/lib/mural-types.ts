export type ClusterId = '01' | '02' | '03' | '04' | '05' | '06' | '07' | '08';
export type ClusterState = 'calmo' | 'activo' | 'intenso';

export interface PanelData {
  id: ClusterId;
  isUnissex: boolean;
  M_pct: number;
  F_pct: number;
  U_pct: number;
  wait_min: number;
  confidence: number;
  ts: number;
  state: ClusterState;
  worst: number;
}

export interface RawClusterParams {
  homens: number | null;
  mulheres: number | null;
  ocupacao_instantanea: number;
  capacidade_total: number;
  tempo_espera_min: number;
  confianca_cruzada: number;
  is_unissex: boolean;
}

export interface RawCluster {
  cluster_id: string;
  ts: number;
  params: RawClusterParams;
}

export interface TelemetryResponse {
  clusters: RawCluster[];
}
