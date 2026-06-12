"""
PlantaOS · Cluster telemetry — formato oficial Sensaway
========================================================
Devolve o snapshot dos 8 clusters no MESMO formato que o scor_publisher
envia para a Sensaway, mas exposto via API para o frontend consumir.

Formato (hard limit definido pelo CEO):
{
  "cluster_id": "wc-01",        ← lowercase, sem M/F (cluster, não section)
  "ts": 1634712287000,           ← epoch milliseconds
  "params": {
    "telemoveis_detectados": int,
    "pessoas_estimadas": int,    ← Σ ocupacao_abs das secções (snapshot único)
    "homens": int,               ← AUSENTE em WC-05, WC-06 (unissex, regra dura)
    "mulheres": int,             ← AUSENTE em WC-05, WC-06
    "entradas_ir": int,
    "saidas_ir": int,
    "ocupacao_instantanea": int,  ← % (derivado dos mesmos abs, ponderado por cap)
    "contagem_prosegur": int,
    "confianca_cruzada": float,   ← 0.0–1.0
    "estado_sensor": "okay" | "simulado" | "warn" | "fail"
  }
}

A função aqui constrói o payload a partir do mesmo state que o publisher usa,
agregando sections (WC-01_M + WC-01_F) num cluster_id "wc-01".
"""
from __future__ import annotations

import time
from typing import Any

# Clusters unissex (FEM=0 no XLSX oficial)
UNISEX_CLUSTERS = {"wc-05", "wc-06"}

# Lista oficial dos 8 clusters (lowercase para o payload)
CLUSTER_IDS = ["wc-01", "wc-02", "wc-03", "wc-04", "wc-05", "wc-06", "wc-07", "wc-08"]

# Capacidade oficial (XLSX) — para validação e detecção de overcrowding
CLUSTER_CAPACITY = {
    "wc-01": 135,   # 72 + 63
    "wc-02": 126,   # 54 + 72
    "wc-03": 102,   # 54 + 48
    "wc-04": 150,   # 84 + 66
    "wc-05": 133,   # unissex
    "wc-06": 208,   # unissex (maior)
    "wc-07": 138,   # 84 + 54
    "wc-08": 145,   # 84 + 61
}


def build_cluster_payload(state: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Constrói o array de 8 clusters a partir do state interno.

    state.sections tem section_id "WC-01_M", "WC-01_F", ... ou "WC-05" (unissex).
    Agregamos por cluster_id (wc-01, wc-02, ...) somando M+F quando aplicável.
    """
    ts_ms = int(time.time() * 1000)

    # Agregar sections por cluster
    agg: dict[str, dict[str, Any]] = {
        cid: {
            "pessoas": 0.0,
            "homens": 0.0,
            "mulheres": 0.0,
            "fluxo": 0.0,
            "occ_list": [],
            "fila": 0,
            "tempo_espera": 0.0,
            "critical": False,
            "simulated": True,
            "section_count": 0,
        } for cid in CLUSTER_IDS
    }

    sections = state.get("sections", []) if state else []
    for sec in sections:
        sid: str = sec.get("section_id", "")
        # "WC-01_M" → "wc-01" · "WC-05" → "wc-05"
        cluster_id = sid.split("_")[0].lower()
        if cluster_id not in agg:
            continue

        a = agg[cluster_id]
        a["section_count"] += 1
        occ_pct = float(sec.get("ocupacao_pct", 0))
        # SEM jitter: este payload é construído UMA vez por tick no snapshot
        # único (state.get_tick_snapshot) — ruído por chamada fazia dois curls
        # no mesmo tick devolverem números diferentes.
        a["occ_list"].append(occ_pct)
        # Pessoas: ocupacao_abs canónico do snapshot — o MESMO inteiro que o
        # /flow serve por secção. Fallback: pct × capacidade oficial.
        from app.clusters_capacity import capacity_gender, capacity_inside
        gender = sec.get("gender") or "M"
        abs_ = sec.get("ocupacao_abs")
        if abs_ is None:
            cap_sec = (capacity_inside(cluster_id)
                       if cluster_id in UNISEX_CLUSTERS
                       else capacity_gender(cluster_id, gender))
            abs_ = int(round((occ_pct / 100.0) * cap_sec)) if cap_sec > 0 else 0
        abs_ = int(abs_)
        a["pessoas"] += abs_
        if cluster_id not in UNISEX_CLUSTERS:
            if gender == "M":
                a["homens"] = abs_
            elif gender == "F":
                a["mulheres"] = abs_

        a["fluxo"] += float(sec.get("fluxo_entrada_pmin", 0))
        a["fila"] += int(sec.get("fila_atual", 0))
        a["tempo_espera"] = max(a["tempo_espera"], float(sec.get("tempo_espera_min", 0)))
        if sec.get("status") == "critical":
            a["critical"] = True
        if sec.get("simulated") is False:
            a["simulated"] = False

    # Construir payload final no formato OFICIAL
    payload: list[dict[str, Any]] = []
    for cid in CLUSTER_IDS:
        a = agg[cid]
        is_uni = cid in UNISEX_CLUSTERS
        cap_total = CLUSTER_CAPACITY.get(cid, 0)
        pessoas = int(a["pessoas"])
        # Ocupação % derivada dos MESMOS abs (ponderada pela capacidade) —
        # Σ ocupacao_abs do /flow e este campo ficam coerentes por construção
        occ_pct = (round(min(100.0, 100.0 * pessoas / cap_total), 1)
                   if cap_total > 0 else 0.0)

        # Estado do sensor — derivado do contexto
        if a["simulated"]:
            estado = "simulado"
        elif a["critical"]:
            estado = "warn"
        elif a["section_count"] == 0:
            estado = "fail"
        else:
            estado = "okay"

        params = {
            "telemoveis_detectados": int(round(pessoas * 1.4)),
            "pessoas_estimadas": pessoas,
        }
        # REGRA DURA: clusters unissexo NUNCA levam homens/mulheres —
        # nem como null; o campo não existe no payload.
        if not is_uni:
            params["homens"] = int(a["homens"])
            params["mulheres"] = int(a["mulheres"])
        params.update({
            "entradas_ir": int(round(a["fluxo"] * 10)),
            "saidas_ir": int(round(a["fluxo"] * 9)),
            "ocupacao_instantanea": int(round(occ_pct)),
            "contagem_prosegur": int(round(pessoas * 1.1)),
            "confianca_cruzada": 0.5 if a["simulated"] else 0.92,
            "estado_sensor": estado,
            # Extras úteis (não breakam o hard-limit do CEO)
            "fila_atual": a["fila"],
            "tempo_espera_min": round(a["tempo_espera"], 1),
            "is_unissex": is_uni,
            "capacidade_total": cap_total,
        })
        payload.append({
            "cluster_id": cid,
            "ts": ts_ms,
            "params": params,
        })

    return payload


def build_kpis(state: dict[str, Any] | None) -> dict[str, Any]:
    """KPIs agregados — formato do scor_publisher."""
    if not state:
        return {"kpi_01": 0, "kpi_02": 0.0, "kpi_03": 0, "kpi_04": 0}
    kpis = state.get("kpis", {}) or {}
    avg_occ = float(kpis.get("avg_ocupacao_pct", 0))
    return {
        "kpi_01": int(round(max(0.0, 100.0 - avg_occ))),  # Flow Index
        "kpi_02": round(avg_occ, 1),                       # Avg Occupancy %
        "kpi_03": int(kpis.get("critical_sections", 0)),   # Critical Alerts
        "kpi_04": int(kpis.get("redirected_count", 0)),    # Redirected
    }
