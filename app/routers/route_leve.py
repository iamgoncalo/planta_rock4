"""
PlantaOS — Encaminhamento "caminho mais leve" (onda 8a) + comando de secções.

GET /api/v1/route?origem=&genero=  — top-3 com custo decomposto, anti-manada,
  histerese e narrativa determinista (PT+EN). Cache 10s por (origem, género).
PUT /api/v1/sections/{id}/estado — fechar/reabrir CLUSTER ({fechado}) OU
  marcar SECÇÃO em limpeza ({em_limpeza, eta_min}) — sempre auditado.
GET /api/v1/decisions — decision_log (auditoria).
GET /api/v1/recusas — recusas_estimadas por género.
POST /api/v1/gateways/{gw_id}/heartbeat · GET /api/v1/gateways — HB dos 2
  gateways LoRaWAN (offline >120 s ⇒ alerta_crit auditado).
Erros sempre JSON. O motor decide; a IA só narra.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.clusters_capacity import ALL_CLUSTERS
from app.services import rota_leve, secoes_mf, decision_log, gateways_hb

router = APIRouter(prefix="/api/v1", tags=["route-leve"])

_ORIGENS = {"ENTRADA", "PALCO_MUNDO", "MUSIC_VALLEY", "SUPER_BOCK"} | {
    c.upper() for c in ALL_CLUSTERS
}


@router.get("/route")
async def route_get(
    origem: str = Query(default="ENTRADA"),
    genero: str = Query(default="f", pattern="^[mMfF]$"),
    pcd: bool = Query(default=False),
):
    """Top-3 secções permitidas (género respeitado), custo decomposto.
    pcd=true: caminhos SEM arestas em lama (acessibilidade)."""
    o = origem.upper()
    if o not in _ORIGENS:
        raise HTTPException(
            status_code=422,
            detail=f"origem desconhecida: {origem!r} — usa cluster (wc-01..08) "
                   f"ou ENTRADA/PALCO_MUNDO/MUSIC_VALLEY/SUPER_BOCK",
        )
    try:
        return rota_leve.compute_route(o, genero, pcd=pcd)
    except Exception as ex:
        return {"origem": o, "genero": genero.lower(), "opcoes": [],
                "recomendado": None, "razao": str(ex),
                "narrativa": rota_leve._narrativa([], None)}


class EstadoBody(BaseModel):
    fechado: Optional[bool] = None          # cluster fechado/reaberto
    em_limpeza: Optional[bool] = None       # SECÇÃO em limpeza (wc-04_f, …)
    eta_min: Optional[int] = Field(default=None, ge=0, le=240)
    utilizador: str = Field(min_length=2, max_length=64)
    justificacao: str = Field(default="", max_length=500)


@router.put("/sections/{section_id}/estado")
async def set_section_estado(section_id: str, body: EstadoBody):
    """Fecha/reabre um CLUSTER ({fechado}) ou marca UMA SECÇÃO em limpeza
    ({em_limpeza, eta_min}). 422 se id desconhecido ou combinação inválida.
    SEMPRE auditado com utilizador + ts ms UTC + antes/depois."""
    sid = section_id.lower()
    if body.fechado is None and body.em_limpeza is None:
        raise HTTPException(
            status_code=422,
            detail="body tem de incluir 'fechado' (cluster) ou "
                   "'em_limpeza' (secção)",
        )
    if body.fechado is not None and body.em_limpeza is not None:
        raise HTTPException(
            status_code=422,
            detail="combinação inválida: 'fechado' aplica-se a cluster e "
                   "'em_limpeza' a secção — um de cada vez",
        )

    if body.em_limpeza is not None:
        # estado POR SECÇÃO: wc-04_f em limpeza NÃO afecta wc-04_m
        if sid not in secoes_mf.section_ids():
            raise HTTPException(
                status_code=422,
                detail=f"secção desconhecida: {section_id} — usa wc-0X_m, "
                       f"wc-0X_f ou wc-05/wc-06",
            )
        rec = secoes_mf.set_limpeza(sid, body.em_limpeza, body.eta_min or 0,
                                    body.utilizador, body.justificacao)
        rota_leve.reset()
        return {"ok": True, "section_id": sid, "limpeza": rec,
                "recusas_estimadas": secoes_mf.recusas_estimadas()}

    # fechado → aplica-se ao CLUSTER inteiro
    if sid not in ALL_CLUSTERS:
        raise HTTPException(
            status_code=422,
            detail=f"cluster desconhecido: {section_id} — 'fechado' "
                   f"aplica-se a clusters (wc-01..08)",
        )
    rec = secoes_mf.set_fechado(sid, body.fechado, body.utilizador,
                                body.justificacao)
    # recomendações e cache devem reflectir o fecho NO MESMO TICK
    rota_leve.reset()
    return {"ok": True, "cluster_id": sid, "estado": rec,
            "recusas_estimadas": secoes_mf.recusas_estimadas()}


@router.get("/sections/estado")
async def get_sections_estado():
    """Estado fechados (cluster) + limpezas (secção, com eta) + recusas."""
    return {
        "fechados": secoes_mf.estado_fechados(),
        "limpezas": secoes_mf.estado_limpezas(),
        "recusas_estimadas": secoes_mf.recusas_estimadas(),
    }


# ── Heartbeat dos 2 gateways LoRaWAN ────────────────────────────────────────
@router.post("/gateways/{gw_id}/heartbeat")
async def gateway_heartbeat(gw_id: str):
    """Sinal de vida de um gateway. 422 se o id não é canónico."""
    try:
        rec = gateways_hb.heartbeat(gw_id)
    except ValueError as ex:
        raise HTTPException(status_code=422, detail=str(ex))
    return {"ok": True, **rec}


@router.get("/gateways")
async def gateways_estado():
    """Estado dos dois gateways (offline se calado >120 s, auditado)."""
    return {"gateways": gateways_hb.estado()}


@router.get("/decisions")
async def get_decisions(
    tipo: Optional[str] = Query(default=None),
    seccao: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Auditoria: decisões do motor e comandos do operador (mais recente 1.º)."""
    items = decision_log.query(tipo=tipo, seccao=seccao, limit=limit)
    return {"total": len(items), "decisions": items}
