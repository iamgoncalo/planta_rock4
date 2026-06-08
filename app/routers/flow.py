"""
PlantaOS — Router Flow: calibração e verificação de fluxos por secção.
GET  /api/v1/flow                     → snapshot do motor (para a página /v2/flow)
GET  /api/v1/flow/history?day=&hour=  → snapshots históricos por secção
GET  /api/v1/flow/forecast?cluster=&hour= → previsão via crowd_profiles
POST /api/v1/flow/tick                → tick do orquestrador (60s)
POST /api/v1/flow/reanchor            → corrige deriva de IR com câmara
"""
from __future__ import annotations

import time
from datetime import date
from typing import Optional
from fastapi import APIRouter, Query, Response
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


@router.get("/history")
async def get_history(
    response: Response,
    day: Optional[str] = Query(None, description="Dia de festival: YYYY-MM-DD"),
    hour: Optional[int] = Query(None, description="Hora UTC 0-23"),
):
    """Snapshots históricos por secção para um dia+hora do festival.
    Devolve a média de ocupacao_pct, fluxo_entrada, fluxo_saida, fila
    agrupada por cluster_id+secao. Cache 30s (os snapshots gravam a cada 60s).
    """
    response.headers["Cache-Control"] = "public, max-age=30, s-maxage=30"
    try:
        from app.db import AsyncSessionLocal
        from app.models.db.flow_history import FlowSnapshot
        from sqlalchemy import select, func as sqlfunc
        if AsyncSessionLocal is None:
            return {"day": day, "hour": hour, "sections": [], "count": 0}

        fday: Optional[date] = None
        if day:
            try:
                fday = date.fromisoformat(day)
            except ValueError:
                return {"error": "day inválido — usar YYYY-MM-DD"}

        async with AsyncSessionLocal() as session:
            q = select(
                FlowSnapshot.cluster_id,
                FlowSnapshot.secao,
                sqlfunc.avg(FlowSnapshot.ocupacao_pct).label("ocupacao_pct_avg"),
                sqlfunc.avg(FlowSnapshot.fluxo_entrada).label("fluxo_entrada_avg"),
                sqlfunc.avg(FlowSnapshot.fluxo_saida).label("fluxo_saida_avg"),
                sqlfunc.avg(FlowSnapshot.fila).label("fila_avg"),
                sqlfunc.avg(FlowSnapshot.confianca_pct).label("confianca_avg"),
                sqlfunc.count(FlowSnapshot.id).label("n_samples"),
            ).group_by(FlowSnapshot.cluster_id, FlowSnapshot.secao)
            if fday is not None:
                q = q.where(FlowSnapshot.festival_day == fday)
            if hour is not None:
                q = q.where(FlowSnapshot.hour == hour)
            rows = (await session.execute(q)).all()

        sections = [
            {
                "cluster_id": r.cluster_id, "secao": r.secao,
                "ocupacao_pct_avg": round(r.ocupacao_pct_avg or 0, 1),
                "fluxo_entrada_avg": round(r.fluxo_entrada_avg or 0, 2),
                "fluxo_saida_avg": round(r.fluxo_saida_avg or 0, 2),
                "fila_avg": round(r.fila_avg or 0, 1),
                "confianca_avg": round(r.confianca_avg or 0, 1),
                "n_samples": r.n_samples,
            }
            for r in rows
        ]
        return {"day": day, "hour": hour, "sections": sections, "count": len(sections)}
    except Exception as exc:
        return {"error": str(exc), "sections": []}


@router.get("/history/timeline")
async def get_history_timeline(
    response: Response,
    day: Optional[str] = Query(None, description="Dia de festival: YYYY-MM-DD"),
):
    """Série temporal por hora — média de todas as secções. Usado pelo sparkline.
    Devolve lista de {hour, avg_occ, n_sections} para o dia pedido.
    """
    response.headers["Cache-Control"] = "public, max-age=30, s-maxage=30"
    try:
        from app.db import AsyncSessionLocal
        from app.models.db.flow_history import FlowSnapshot
        from sqlalchemy import select, func as sqlfunc
        if AsyncSessionLocal is None:
            return {"day": day, "timeline": []}

        fday: Optional[date] = None
        if day:
            try:
                fday = date.fromisoformat(day)
            except ValueError:
                return {"error": "day inválido — usar YYYY-MM-DD"}

        async with AsyncSessionLocal() as session:
            q = select(
                FlowSnapshot.hour,
                sqlfunc.avg(FlowSnapshot.ocupacao_pct).label("avg_occ"),
                sqlfunc.avg(FlowSnapshot.fluxo_entrada).label("avg_entrada"),
                sqlfunc.count(FlowSnapshot.id).label("n"),
            ).group_by(FlowSnapshot.hour).order_by(FlowSnapshot.hour)
            if fday is not None:
                q = q.where(FlowSnapshot.festival_day == fday)
            rows = (await session.execute(q)).all()

        timeline = [
            {"hour": r.hour, "avg_occ": round(r.avg_occ or 0, 1),
             "avg_entrada": round(r.avg_entrada or 0, 2), "n": r.n}
            for r in rows
        ]
        return {"day": day, "timeline": timeline}
    except Exception as exc:
        return {"error": str(exc), "timeline": []}


@router.get("/forecast")
async def get_forecast(
    response: Response,
    cluster: Optional[str] = Query(None, description="cluster_id ex: wc-01"),
    hour: Optional[int] = Query(None, description="Hora futura UTC 0-23"),
):
    """Previsão de ocupação via JOIN flow_snapshot × crowd_profiles.
    Calcula a média histórica do mesmo slot horário em todos os dias de festival,
    ponderada pelo surge_factor do show previsto nessa hora.
    Cache 5 min (crowd_profiles são estáticos, histórico cresce lentamente).
    """
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=300"
    try:
        from app.db import AsyncSessionLocal
        from app.models.db.flow_history import FlowSnapshot, CrowdProfile
        from sqlalchemy import select, func as sqlfunc
        if AsyncSessionLocal is None:
            return {"cluster": cluster, "hour": hour, "forecast": [], "profiles": []}

        async with AsyncSessionLocal() as session:
            # Média histórica do slot horário (todos os dias de festival)
            q_hist = select(
                FlowSnapshot.cluster_id,
                FlowSnapshot.secao,
                sqlfunc.avg(FlowSnapshot.ocupacao_pct).label("occ_hist"),
                sqlfunc.avg(FlowSnapshot.fluxo_entrada).label("fl_entrada_hist"),
                sqlfunc.count(FlowSnapshot.id).label("n"),
            ).group_by(FlowSnapshot.cluster_id, FlowSnapshot.secao)
            if cluster:
                q_hist = q_hist.where(FlowSnapshot.cluster_id == cluster.lower())
            if hour is not None:
                q_hist = q_hist.where(FlowSnapshot.hour == hour)
            hist_rows = (await session.execute(q_hist)).all()

            # Perfis de show para esta hora (todos os dias)
            q_prof = select(CrowdProfile)
            if hour is not None:
                q_prof = q_prof.where(CrowdProfile.hour == hour)
            prof_rows = (await session.execute(q_prof)).scalars().all()

        # Surge médio para esta hora (média dos 4 dias)
        surge_avg = (
            sum(p.surge_factor or 1.0 for p in prof_rows) / len(prof_rows)
            if prof_rows else 1.0
        )

        forecast = [
            {
                "cluster_id": r.cluster_id,
                "secao": r.secao,
                "ocupacao_prevista_pct": round(min(100.0, (r.occ_hist or 0) * surge_avg), 1),
                "fluxo_entrada_previsto": round((r.fl_entrada_hist or 0) * surge_avg, 2),
                "base_historica_pct": round(r.occ_hist or 0, 1),
                "surge_factor": round(surge_avg, 2),
                "n_amostras": r.n,
            }
            for r in hist_rows
        ]
        profiles = [
            {
                "festival_day": str(p.festival_day),
                "hour": p.hour,
                "show_name": p.show_name,
                "palco": p.palco,
                "expected_attendance": p.expected_attendance,
                "surge_factor": p.surge_factor,
            }
            for p in prof_rows
        ]
        return {
            "cluster": cluster, "hour": hour,
            "surge_avg": round(surge_avg, 2),
            "forecast": forecast,
            "profiles": profiles,
        }
    except Exception as exc:
        return {"error": str(exc), "forecast": []}
