import type { PanelData, ClusterId, ClusterState, TelemetryResponse } from './mural-types';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://api.plantarockinrio.com';

export async function fetchMuralData(): Promise<PanelData[]> {
  const res = await fetch(`${API_BASE}/api/v1/telemetry/clusters/now`, {
    cache: 'no-store',
    next: { revalidate: 0 },
  });
  if (!res.ok) throw new Error(`mural fetch failed: ${res.status}`);
  const data: TelemetryResponse = await res.json();

  return data.clusters.map((c) => {
    const id = c.cluster_id.replace('wc-', '') as ClusterId;
    const p = c.params;
    const isUnissex = p.is_unissex;

    let M_pct = 0;
    let F_pct = 0;
    let U_pct = 0;
    let worst = 0;

    if (isUnissex) {
      U_pct = Math.min(100, Math.max(0, Math.round(p.ocupacao_instantanea)));
      worst = U_pct;
    } else {
      const cap = p.capacidade_total || 1;
      M_pct = Math.min(100, Math.max(0, Math.round(((p.homens ?? 0) / cap) * 100)));
      F_pct = Math.min(100, Math.max(0, Math.round(((p.mulheres ?? 0) / cap) * 100)));
      worst = Math.max(M_pct, F_pct);
    }

    const state: ClusterState =
      worst >= 80 ? 'intenso' : worst >= 50 ? 'activo' : 'calmo';

    return {
      id,
      isUnissex,
      M_pct,
      F_pct,
      U_pct,
      wait_min: Math.max(0, Math.round(p.tempo_espera_min ?? 0)),
      confidence: p.confianca_cruzada ?? 0,
      ts: c.ts,
      state,
      worst,
      live: (p.estado_sensor ?? '') !== 'offline' && (p.confianca_cruzada ?? 0) > 0,
    };
  });
}
