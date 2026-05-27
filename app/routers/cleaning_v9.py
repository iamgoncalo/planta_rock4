"""
PlantaOS · Cleaning router v9
==============================
Endpoints novos para 14 unidades:
  - GET  /api/v1/cleaning/units              → estrutura das 14 unidades (catalog)
  - GET  /api/v1/cleaning/units/status       → estado actual de cada unidade
  - POST /api/v1/cleaning/units/{unit_id}/done   → marca unidade limpa
  - GET  /api/v1/cleaning/units/{unit_id}/history → histórico

Endpoints legacy v8 mantidos para compatibilidade.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_ops_key
from app.db import get_db
from app.models.operations import CleaningEntry, CleaningDoneRequest
from app.models.cleaning_v9 import (
    CleaningScheduleV9Response, WCUnitsCatalog, WCUnitDefinition,
)
from app.services import cleaning_v9 as service
from app.services.wc_units import (
    WC_UNITS, unit_by_id, TOTAL_MASC, TOTAL_FEM, TOTAL_ESPERA, TOTAL_CAPACITY,
)

router = APIRouter(prefix="/api/v1/cleaning", tags=["cleaning-v9"])


@router.get("/units", response_model=WCUnitsCatalog)
async def get_units_catalog():
    """Devolve o catálogo das 14 unidades operacionais — hard limits do XLSX.
    Sem dados de runtime. Apenas a estrutura física oficial.
    """
    return WCUnitsCatalog(
        units=[
            WCUnitDefinition(
                unit_id=u.unit_id,
                cluster_id=u.cluster_id,
                gender=u.gender,
                label=u.label,
                masc=u.masc,
                fem=u.fem,
                espera=u.espera,
                total=u.total,
                note=u.note,
            ) for u in WC_UNITS
        ],
        total_count=len(WC_UNITS),
        total_masc=TOTAL_MASC,
        total_fem=TOTAL_FEM,
        total_espera=TOTAL_ESPERA,
        total_capacity=TOTAL_CAPACITY,
    )


@router.get("/units/status", response_model=CleaningScheduleV9Response)
async def get_units_status(db: AsyncSession = Depends(get_db)):
    """Estado actual de cada uma das 14 unidades — clean/needs_cleaning/urgent.
    """
    return await service.get_units_status(db)


@router.post("/units/{unit_id}/done", response_model=CleaningEntry)
async def mark_unit_done(
    unit_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    """Marca uma unidade específica como limpa.
    Body: { team?, operator?, notes? }
    """
    u = unit_by_id(unit_id)
    if u is None:
        raise HTTPException(404, detail=f"Unit {unit_id} desconhecida")

    req = CleaningDoneRequest(
        cluster_id=unit_id,  # usamos unit_id no campo cluster_id da DB
        team=body.get("team"),
        operator=body.get("operator"),
        notes=body.get("notes"),
    )
    return await service.mark_unit_done(db, req)


@router.get("/units/{unit_id}/history", response_model=list[CleaningEntry])
async def unit_history(
    unit_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Histórico recente de limpezas para esta unidade."""
    if unit_by_id(unit_id) is None:
        raise HTTPException(404, detail=f"Unit {unit_id} desconhecida")
    return await service.list_history(db, target_id=unit_id, limit=limit)
