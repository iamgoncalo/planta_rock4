"""
PlantaOS — Encaminhamento "caminho mais leve" (onda 8a) + comando de secções.

GET /api/v1/route?origem=&genero=  — top-3 com custo decomposto, anti-manada,
  histerese e narrativa determinista (PT+EN). Cache 10s por (origem, género).
PUT /api/v1/sections/{cluster_id}/estado — fechar/reabrir cluster (auditado).
GET /api/v1/decisions — decision_log (auditoria).
GET /api/v1/recusas — recusas_estimadas por género.
Erros sempre JSON. O motor decide; a IA só narra.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.clusters_capacity import ALL_CLUSTERS
from app.services import rota_leve, secoes_mf, decision_log

router = APIRouter(prefix="/api/v1", tags=["route-leve"])

_ORIGENS = {"ENTRADA", "PALCO_MUNDO", "MUSIC_VALLEY", "SUPER_BOCK"} | {
    c.upper() for c in ALL_CLUSTERS
}


@router.get("/route")
async def route_get(
    origem: str = Query(default="ENTRADA"),
    genero: str = Query(default="f", pattern="^[mMfF]$"),
):
    """Top-3 secções permitidas (género respeitado), custo decomposto."""
    o = origem.upper()
    if o not in _ORIGENS:
        raise HTTPException(
            status_code=422,
            detail=f"origem desconhecida: {origem!r} — usa cluster (wc-01..08) "
                   f"ou ENTRADA/PALCO_MUNDO/MUSIC_VALLEY/SUPER_BOCK",
        )
    try:
        return rota_leve.compute_route(o, genero)
    except Exception as ex:
        return {"origem": o, "genero": genero.lower(), "opcoes": [],
                "recomendado": None, "razao": str(ex),
                "narrativa": rota_leve._narrativa([], None)}


class EstadoBody(BaseModel):
    fechado: bool
    utilizador: str = Field(min_length=2, max_length=64)
    justificacao: str = Field(default="", max_length=500)


@router.put("/sections/{cluster_id}/estado")
async def set_section_estado(cluster_id: str, body: EstadoBody):
    """Fecha/reabre um cluster (modo de falha). SEMPRE auditado com
    utilizador + timestamp ms UTC + antes/depois no decision_log."""
    cid = cluster_id.lower()
    if cid not in ALL_CLUSTERS:
        raise HTTPException(status_code=422, detail=f"cluster desconhecido: {cluster_id}")
    rec = secoes_mf.set_fechado(cid, body.fechado, body.utilizador,
                                body.justificacao)
    # recomendações e cache devem reflectir o fecho NO MESMO TICK
    rota_leve.reset()
    return {"ok": True, "cluster_id": cid, "estado": rec,
            "recusas_estimadas": secoes_mf.recusas_estimadas()}


@router.get("/sections/estado")
async def get_sections_estado():
    """Estado aberto/fechado de todos os clusters + recusas estimadas."""
    return {
        "fechados": secoes_mf.estado_fechados(),
        "recusas_estimadas": secoes_mf.recusas_estimadas(),
    }


@router.get("/decisions")
async def get_decisions(
    tipo: Optional[str] = Query(default=None),
    seccao: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Auditoria: decisões do motor e comandos do operador (mais recente 1.º)."""
    items = decision_log.query(tipo=tipo, seccao=seccao, limit=limit)
    return {"total": len(items), "decisions": items}
