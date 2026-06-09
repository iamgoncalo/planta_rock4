"""
PlantaOS — Router de FUSAO. Expoe /api/v1/fusion/{cluster_id}?mode=sim|real.
Combina o simulador (fleet_sim) com o motor de fusao (fusion). Em sim, gera
parametros realistas por proximidade ao palco. Em real, le do ingest_store.
Sempre robusto: nunca lanca 500, devolve {estado: "sem-dados"} se faltar tudo.
U3 audit: lê de ingest_store (dados reais) com fallback fleet_sim. Fonte única ✅
"""
from __future__ import annotations
import time
from fastapi import APIRouter, Query, HTTPException

from app.services import fleet_sim
try:
    from app.services import fusion as fusion_engine
except Exception:
    fusion_engine = None
try:
    from app.services import ingest_store
except Exception:
    ingest_store = None
try:
    from app.services import fusao_rolante
except Exception:
    fusao_rolante = None

router = APIRouter(prefix="/api/v1", tags=["fusion"])

# Mapa cluster -> fontes disponíveis (que sensores existem em cada um)
CLUSTER_SOURCES = {
    "wc-01": ["camera","ir","wifi"], "wc-02": ["camera","ir","wifi"],
    "wc-03": ["camera","ir","wifi"], "wc-04": ["camera","ir","wifi"],
    "wc-05": ["camera","wifi"],      "wc-06": ["camera","wifi"],
    "wc-07": ["camera","ir","wifi"], "wc-08": ["camera","ir","wifi"],
}


def _seccoes_rolante(cluster_id: str) -> dict:
    """Fusão rolante por secção: {'m':…,'f':…} em MF, {'u':…} nos unissexo.
    Cada secção: ocupacao, fila_estimada, confianca_cruzada, a_actual,
    idade_ancora_s, nos_online, flag_anomalia. Vazio se ainda sem dados."""
    if fusao_rolante is None:
        return {}
    try:
        return fusao_rolante.get_cluster_payload(cluster_id)
    except Exception:
        return {}


def _empty(cluster_id: str, mode: str, reason: str) -> dict:
    return {
        "cluster_id": cluster_id, "mode": mode,
        "estado": "sem-dados", "data_source": "none",
        "pessoas": 0, "ocupacao_pct": 0.0, "fila_atual": 0, "tempo_espera_min": 0.0,
        "confianca": 0.0, "fontes_usadas": [], "pesos": {}, "estimativas_por_fonte": {},
        "fontes_disponiveis": CLUSTER_SOURCES.get(cluster_id, []),
        "capacidade_dentro": 0,
        "seccoes": _seccoes_rolante(cluster_id),
        "razao": reason,
    }


@router.get("/fusion/{cluster_id}")
async def fusion_cluster(cluster_id: str, mode: str = Query(default="sim")):
    cluster_id = cluster_id.lower()
    if cluster_id not in fleet_sim.CAP:
        raise HTTPException(404, f"cluster desconhecido: {cluster_id}")
    if fusion_engine is None:
        return _empty(cluster_id, mode, "motor de fusao indisponivel")

    cap = fleet_sim.CAP[cluster_id]
    cap_in = cap["m"] + cap["f"]
    esp_max = cap["esp"]
    srcs = CLUSTER_SOURCES.get(cluster_id, ["camera","ir","wifi"])
    t = time.time()

    if mode == "sim":
        try:
            p = fleet_sim.simulate_cluster_params(cluster_id, t)
            r = fusion_engine.fuse_cluster(
                cap_inside=cap_in, espera_max=esp_max, sources_present=srcs,
                camera_people=p.get("pessoas_estimadas"),
                ir_in=p.get("entradas_ir"), ir_out=p.get("saidas_ir"),
                wifi_devices=p.get("telemoveis_detectados"),
                wifi_factor=p.get("_wifi_factor", 2.5),
            )
            r["cluster_id"] = cluster_id
            r["mode"] = "sim"
            r["data_source"] = "simulado"
            r["fontes_disponiveis"] = srcs
            r["capacidade_dentro"] = cap_in
            r["seccoes"] = _seccoes_rolante(cluster_id)
            return r
        except Exception as ex:
            return _empty(cluster_id, mode, f"erro no simulador: {ex}")

    # real
    if not ingest_store:
        return _empty(cluster_id, "real", "ingest_store indisponivel")
    rec = ingest_store.get(cluster_id)
    if not rec:
        return _empty(cluster_id, "real", "sem ingestao recente")
    params = rec.get("params", {})
    age = t - rec.get("ts_server", 0)
    try:
        r = fusion_engine.fuse_cluster(
            cap_inside=cap_in, espera_max=esp_max, sources_present=srcs,
            camera_people=params.get("pessoas_estimadas") or params.get("camera_people"),
            ir_in=params.get("entradas_ir") or params.get("ir_in"),
            ir_out=params.get("saidas_ir") or params.get("ir_out"),
            wifi_devices=params.get("telemoveis_detectados") or params.get("wifi_devices"),
            wifi_factor=params.get("_wifi_factor") or params.get("wifi_factor") or 2.5,
        )
        r["cluster_id"] = cluster_id
        r["mode"] = "real"
        r["data_source"] = "real" if age < 30 else "stale"
        r["fontes_disponiveis"] = srcs
        r["capacidade_dentro"] = cap_in
        r["age_s"] = round(age, 1)
        r["seccoes"] = _seccoes_rolante(cluster_id)
        return r
    except Exception as ex:
        return _empty(cluster_id, mode, f"erro na fusao real: {ex}")


@router.get("/fusion")
async def fusion_all(mode: str = Query(default="sim")):
    """Devolve a fusao de todos os 8 clusters num so pedido. Util para a consola."""
    out = {}
    for cid in fleet_sim.CAP:
        try:
            out[cid] = await fusion_cluster(cid, mode=mode)
        except Exception as ex:
            out[cid] = _empty(cid, mode, str(ex))
    return {"clusters": out, "mode": mode, "ts": time.time()}
