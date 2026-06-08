"""
PlantaOS — Router Flow: calibração e verificação de fluxos por secção.
GET  /api/v1/flow          → snapshot do motor (para a página /v2/flow)
POST /api/v1/flow/tick     → tick do orquestrador (60s), calcula routing
POST /api/v1/flow/reanchor → corrige deriva de IR com âncora da câmara
"""
from __future__ import annotations

import time
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.flow import FlowEngine, SensorReading, CLUSTERS, get_engine

router = APIRouter(prefix="/api/v1/flow", tags=["flow"])


def _feed_engine(engine: FlowEngine) -> None:
    """Alimenta o motor com dados do ingest_store (real) ou fleet_sim (simulado)."""
    try:
        from app.services import ingest_store
        from app.clusters_capacity import is_unisex
        now = time.time()
        for cid in CLUSTERS:
            rec = ingest_store.get(cid)
            if rec and (now - rec.get("ts_server", 0)) < 300:
                p = rec["params"]
                secs = ("U",) if is_unisex(cid) else ("M", "F")
                # IR cumulativo ao nível do cluster — partilhar pelas secções
                ir_in_total  = int(p.get("entradas_ir") or 0)
                ir_out_total = int(p.get("saidas_ir")   or 0)
                cap_data = CLUSTERS[cid].cap
                total_cap = sum(cap_data.values()) or 1
                entradas = {s: int(ir_in_total  * cap_data[s] / total_cap) for s in secs}
                saidas   = {s: int(ir_out_total * cap_data[s] / total_cap) for s in secs}
                # Câmara: homens/mulheres se disponíveis, senão contagem_prosegur dividida
                cam: dict = {}
                if not is_unisex(cid):
                    if p.get("homens")   is not None: cam["M"] = int(p["homens"])
                    if p.get("mulheres") is not None: cam["F"] = int(p["mulheres"])
                if not cam and p.get("contagem_prosegur") is not None:
                    n = len(secs)
                    for s in secs:
                        cam[s] = int(p["contagem_prosegur"]) // n
                engine.ingest(SensorReading(
                    cluster_id=cid,
                    ts=rec.get("ts_device", int(now * 1000)) / 1000,
                    entradas_ir=entradas,
                    saidas_ir=saidas,
                    pessoas_wifi=int(p.get("pessoas_estimadas") or 0) or None,
                    contagem_cam=cam or None,
                    uptime_s=int(p.get("uptime_s") or 3600),
                ))
            else:
                _feed_sim(engine, cid, now)
    except Exception:
        pass  # o motor nunca pode cravar a API


def _feed_sim(engine: FlowEngine, cid: str, now: float) -> None:
    try:
        from app.services import fleet_sim
        p = fleet_sim.simulate_cluster_params(cid, now)
        cap_data = CLUSTERS[cid].cap
        total_cap = sum(cap_data.values()) or 1
        secs = ("U",) if CLUSTERS[cid].unissex else ("M", "F")
        pax  = int(p.get("pessoas_estimadas") or 20)
        ir_in  = int(p.get("entradas_ir") or 50)
        ir_out = int(p.get("saidas_ir")   or 40)
        engine.ingest(SensorReading(
            cluster_id=cid, ts=now,
            entradas_ir={s: int(ir_in  * cap_data[s] / total_cap) for s in secs},
            saidas_ir  ={s: int(ir_out * cap_data[s] / total_cap) for s in secs},
            pessoas_wifi=pax,
            contagem_cam={s: int(pax * cap_data[s] / total_cap) for s in secs},
            uptime_s=3600,
        ))
    except Exception:
        pass


class ReanchorReq(BaseModel):
    cluster_id: str
    secao: str
    ocupacao_camara: float


def _enrich_with_canonical(page: dict) -> dict:
    """Sobrepõe ocupacao_pct / fila_actual / tempo_espera_min com get_live_payload().

    Garante que /v2/flow mostra os mesmos números que /v2/screen, /v2/twin e
    /v2/scor. Os campos de calibração do FlowEngine (residual, deriva,
    confianca, routing) mantêm-se inalterados — são específicos desta página.
    """
    try:
        from app.services.state import get_live_payload
        live = get_live_payload()
        sec_map = {s.section_id: s for s in live.sections}
        for sec in page.get("secoes", []):
            # "wc-01" + "M" → "WC-01_M"  |  "wc-05" + "U" → "WC-05"
            if sec["secao"] == "U":
                key = f"WC-{sec['cluster_id'][3:]}"
            else:
                key = f"WC-{sec['cluster_id'][3:]}_{sec['secao']}"
            canon = sec_map.get(key)
            if canon is not None:
                sec["ocupacao_pct"] = canon.ocupacao_pct
                sec["fila_actual"] = canon.fila_atual
                sec["tempo_espera_min"] = canon.tempo_espera_min
        # Recalcular kpi_02 (ocupação média) com os valores canónicos
        secoes = page.get("secoes", [])
        if secoes:
            page["kpis"]["kpi_02"] = int(round(
                sum(s["ocupacao_pct"] for s in secoes) / len(secoes)
            ))
    except Exception:
        pass  # fallback ao FlowEngine em caso de erro inesperado
    return page


@router.get("")
def get_flow():
    engine = get_engine()
    _feed_engine(engine)
    return _enrich_with_canonical(engine.flow_page())


def get_flow_snapshot() -> dict:
    """Chamado pelo WS para emitir flow_update sem polling extra."""
    try:
        engine = get_engine()
        return _enrich_with_canonical(engine.flow_page())
    except Exception:
        return {}


@router.post("/tick")
def post_tick(surge: float = 1.0):
    engine = get_engine()
    _feed_engine(engine)
    redirects = engine.tick_route(surge=surge)
    return {"redirects": redirects, "kpis": engine.kpis()}


@router.post("/reanchor")
def post_reanchor(req: ReanchorReq):
    engine = get_engine()
    engine.reanchor(req.cluster_id, req.secao, req.ocupacao_camara)
    return {"ok": True, "cluster_id": req.cluster_id, "secao": req.secao}
