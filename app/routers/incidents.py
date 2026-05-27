"""
PlantaOS · Incidents router
============================
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_ops_key
from app.db import get_db
from app.models.operations import (
    IncidentEntry, IncidentListResponse,
    IncidentCreateRequest, IncidentResolveRequest,
)
from app.services import incidents as service

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("/", response_model=IncidentListResponse)
async def list_incidents(
    day: Optional[str] = None,
    cluster_id: Optional[str] = None,
    severity: Optional[str] = None,
    open_only: bool = False,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    return await service.list_incidents(
        db, day=day, cluster_id=cluster_id,
        severity=severity, open_only=open_only, limit=limit,
    )


@router.post("/", response_model=IncidentEntry)
async def create(
    req: IncidentCreateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    return await service.create(db, req)


@router.post("/{incident_id}/resolve", response_model=IncidentEntry)
async def resolve(
    incident_id: int,
    req: IncidentResolveRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    out = await service.resolve(db, incident_id, req)
    if out is None:
        raise HTTPException(404, detail="Incident not found")
    return out
