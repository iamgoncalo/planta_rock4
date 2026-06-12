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
  live: boolean;
}

export interface RawClusterParams {
  homens?: number | null;       // AUSENTE em wc-05/wc-06 (unissexo)
  mulheres?: number | null;     // AUSENTE em wc-05/wc-06
  ocupacao_instantanea: number; // % == round(100×Σabs/capacidade)
  ocupacao_pct?: number;        // % a 1dp (mesmos abs)
  capacidade_total: number;
  tempo_espera_min: number;
  confianca_cruzada: number;
  estado_sensor?: string;
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

export interface SectionCopy {
  pt: string;
  en: string;
  tom: string;
}

export type ScreenCopyMap = Record<string, SectionCopy>;
