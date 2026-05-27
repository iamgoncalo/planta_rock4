"""
PlantaOS · Cleaning router
===========================
Endpoints:
- GET  /api/v1/cleaning/schedule       → estado dos 8 clusters
- POST /api/v1/cleaning/done           → marcar cluster limpo  [auth]
- POST /api/v1/cleaning/schedule       → agendar limpeza        [auth]
- GET  /api/v1/cleaning/history        → histórico recente
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_ops_key
from app.db import get_db
from app.models.operations import (
    CleaningScheduleResponse, CleaningEntry,
    CleaningDoneRequest, CleaningScheduleRequest,
)
from app.services import cleaning as service

router = APIRouter(prefix="/api/v1/cleaning", tags=["cleaning"])


@router.get("/schedule", response_model=CleaningScheduleResponse)
async def get_schedule(db: AsyncSession = Depends(get_db)):
    return await service.get_schedule(db)


@router.post("/done", response_model=CleaningEntry)
async def mark_done(
    req: CleaningDoneRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    return await service.mark_done(db, req)


@router.post("/schedule", response_model=CleaningEntry)
async def schedule_cleaning(
    req: CleaningScheduleRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    return await service.schedule_cleaning(db, req)


@router.get("/history", response_model=list[CleaningEntry])
async def history(
    cluster_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await service.list_history(db, cluster_id=cluster_id, limit=limit)
