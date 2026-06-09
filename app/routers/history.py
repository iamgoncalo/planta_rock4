"""
PlantaOS — Memória extrema exposta (onda 5a/5d).
GET /api/v1/history/replay?dia=YYYY-MM-DD  — blocos de 10 min p/ twin replay
GET /api/v1/history/{secao}?from=&to=&page=&size=  — paginado JSON
Erros sempre em JSON. Nunca 500.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services import section_history

router = APIRouter(prefix="/api/v1", tags=["history"])


# rota literal ANTES da paramétrica
@router.get("/history/replay")
async def history_replay(dia: str = Query(..., description="YYYY-MM-DD (UTC)")):
    """Série do dia em blocos de 10 min — alimenta o twin em modo replay."""
    try:
        return section_history.replay_dia(dia)
    except ValueError as ex:
        raise HTTPException(status_code=422, detail=str(ex))
    except Exception as ex:
        return {"dia": dia, "bloco_min": 10, "seccoes": {}, "razao": str(ex)}


@router.get("/history/{secao}")
async def history_section(
    secao: str,
    ts_from: Optional[int] = Query(default=None, alias="from"),
    ts_to: Optional[int] = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=120, ge=1, le=1000),
):
    """Histórico ao minuto de uma secção (retenção 7 dias), paginado."""
    from app.services import secoes_mf
    if secao.lower() not in secoes_mf.section_ids():
        raise HTTPException(status_code=404, detail=f"secção desconhecida: {secao}")
    return section_history.query(secao, ts_from, ts_to, page, size)
