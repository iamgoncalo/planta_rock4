"""
PlantaOS — Ambiente operacional (chuva/calor/vento) + lama por aresta + evacuação.

GET  /api/v1/ambiente                       — estado completo das flags
PUT  /api/v1/ambiente/{flag}                — liga/desliga chuva|calor|vento
GET  /api/v1/ambiente/eventos               — EVENT_LOG (inicio/fim por flag)
POST /api/v1/ambiente/evacuacao             — fecha N clusters num só comando (S05)
PUT  /api/v1/flow/aresta/{aresta_id}/estado — lama|cortada|normal numa aresta (S02/S09)
GET  /api/v1/flow/arestas                   — estado de todas as arestas

Erros sempre JSON (422 em flag/aresta/cluster inválidos). Tudo auditado no
decision_log com utilizador + antes/depois. Cache/histerese de rotas caem
NO MESMO TICK (rota_leve.reset()).
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.clusters_capacity import ALL_CLUSTERS
from app.services import ambiente, decision_log, rota_leve, secoes_mf

router = APIRouter(prefix="/api/v1", tags=["ambiente"])


# ── Flags de ambiente ────────────────────────────────────────────────────────
class FlagBody(BaseModel):
    activo: bool
    intensidade: Optional[Literal["fraca", "moderada", "forte"]] = None
    temp_c: Optional[float] = Field(default=None, ge=-20.0, le=60.0)
    kmh: Optional[float] = Field(default=None, ge=0.0, le=300.0)
    utilizador: str = Field(min_length=2, max_length=64)
    justificacao: str = Field(default="", max_length=500)
    fonte: Literal["operador", "forecast"] = "operador"


@router.get("/ambiente")
async def get_ambiente():
    """Estado completo das flags + factores canónicos derivados."""
    return ambiente.estado()


@router.get("/ambiente/eventos")
async def get_ambiente_eventos():
    """EVENT_LOG de ambiente (mais recente primeiro)."""
    items = ambiente.eventos()
    return {"total": len(items), "eventos": items}


@router.put("/ambiente/{flag}")
async def put_ambiente_flag(flag: str, body: FlagBody):
    """Liga/desliga uma flag de ambiente. SEMPRE auditada (decision_log +
    EVENT_LOG). 422 se a flag for desconhecida."""
    try:
        rec = ambiente.set_flag(
            flag.lower(), body.activo, body.utilizador,
            intensidade=body.intensidade, temp_c=body.temp_c, kmh=body.kmh,
            justificacao=body.justificacao, fonte=body.fonte,
        )
    except ValueError as ex:
        raise HTTPException(status_code=422, detail=str(ex))
    # rotas e esperas reflectem o ambiente no mesmo tick
    rota_leve.reset()
    return {"ok": True, "flag": flag.lower(), "estado": rec,
            "ambiente": ambiente.estado_resumo()}


# ── Evacuação em bloco (S05) ────────────────────────────────────────────────
class EvacuacaoBody(BaseModel):
    clusters: list[str] = Field(min_length=1)
    utilizador: str = Field(min_length=2, max_length=64)
    justificacao: str = Field(min_length=2, max_length=500)


@router.post("/ambiente/evacuacao")
async def post_evacuacao(body: EvacuacaoBody):
    """Fecha TODOS os clusters indicados num só comando (S05). Lista vazia ou
    cluster inválido ⇒ 422. Auditado como tipo='evacuacao'."""
    cids = [c.lower() for c in body.clusters]
    invalidos = [c for c in cids if c not in ALL_CLUSTERS]
    if invalidos:
        raise HTTPException(status_code=422,
                            detail=f"clusters desconhecidos: {invalidos}")
    antes = secoes_mf.estado_fechados()
    for cid in cids:
        secoes_mf.set_fechado(cid, True, body.utilizador, body.justificacao)
    rota_leve.reset()   # recomendações excluem os fechados no mesmo tick
    decision_log.log(
        tipo="evacuacao", origem="operador", utilizador=body.utilizador,
        antes={"fechados": sorted(k for k, v in antes.items()
                                  if v.get("fechado"))},
        depois={"clusters": cids},
        justificacao=body.justificacao,
    )
    return {"ok": True, "clusters": cids,
            "fechados": secoes_mf.estado_fechados(),
            "recusas_estimadas": secoes_mf.recusas_estimadas()}


# ── Lama / corte por aresta (S02 · S09) ─────────────────────────────────────
class ArestaBody(BaseModel):
    estado: Literal["lama", "cortada", "normal"]
    utilizador: str = Field(min_length=2, max_length=64)
    justificacao: str = Field(default="", max_length=500)


@router.put("/flow/aresta/{aresta_id}/estado")
async def put_aresta_estado(aresta_id: str, body: ArestaBody):
    """Marca uma aresta do grafo como lama/cortada/normal. Valida contra o
    grafo real de rota_leve (422 se não existir). Auditado; a cache e a
    histerese de rotas caem no mesmo tick."""
    try:
        rec = ambiente.set_aresta_estado(aresta_id, body.estado,
                                         body.utilizador, body.justificacao)
    except ValueError as ex:
        raise HTTPException(status_code=422, detail=str(ex))
    rota_leve.reset()
    return {"ok": True, **rec}


@router.get("/flow/arestas")
async def get_arestas():
    """Estado de todas as arestas (declarado + lama efectiva/generalizada)."""
    return ambiente.estado_arestas()
