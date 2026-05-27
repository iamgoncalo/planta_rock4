"""
PlantaOS · Staff roster router
===============================
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_ops_key
from app.db import get_db
from app.models.operations import (
    StaffRosterResponse, StaffEntry, StaffCreateRequest,
)
from app.services import staff as service

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


@router.get("/roster", response_model=StaffRosterResponse)
async def get_roster(day: str, db: AsyncSession = Depends(get_db)):
    """Roster completo de um dia. day=YYYY-MM-DD."""
    return await service.get_roster(db, day)


@router.post("/", response_model=StaffEntry)
async def create(
    req: StaffCreateRequest,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    return await service.add_entry(db, req)


@router.post("/{entry_id}/confirm", response_model=StaffEntry)
async def confirm(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    out = await service.confirm(db, entry_id)
    if out is None:
        raise HTTPException(404, detail="Entry not found")
    return out


@router.delete("/{entry_id}")
async def remove(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    ok = await service.remove(db, entry_id)
    if not ok:
        raise HTTPException(404, detail="Entry not found")
    return {"deleted": True, "id": entry_id}
