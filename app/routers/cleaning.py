"""
PlantaOS · Cleaning router (unificado — U2)
============================================
Endpoints base:
  GET  /api/v1/cleaning/schedule          → estado dos 8 clusters
  POST /api/v1/cleaning/done              → marcar cluster limpo  [auth]
  POST /api/v1/cleaning/schedule          → agendar limpeza       [auth]
  GET  /api/v1/cleaning/history           → histórico recente

Endpoints v9 (14 unidades operacionais):
  GET  /api/v1/cleaning/units             → catálogo das 14 unidades
  GET  /api/v1/cleaning/units/status      → estado actual por unidade
  POST /api/v1/cleaning/units/{unit_id}/done
  GET  /api/v1/cleaning/units/{unit_id}/history

Endpoints preditivos (calendário + equipa):
  GET  /api/v1/cleaning/staff             → equipa + contactos
  GET  /api/v1/cleaning/calendar          → calendário futuro com atribuições
  GET  /api/v1/cleaning/next-by-unit      → próximos slots por unidade
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_ops_key
from app.db import get_db
from app.models.operations import (
    CleaningScheduleResponse, CleaningEntry,
    CleaningDoneRequest, CleaningScheduleRequest,
)
from app.models.cleaning_v9 import (
    CleaningScheduleV9Response, WCUnitsCatalog, WCUnitDefinition,
)
from app.services import cleaning as service
from app.services import cleaning_v9 as service_v9
from app.services.wc_units import (
    WC_UNITS, unit_by_id, TOTAL_MASC, TOTAL_FEM, TOTAL_ESPERA, TOTAL_CAPACITY,
)
from app.services.cleaning_predictive import (
    build_24h_schedule, next_slots_by_unit,
)
from app.services.cleaning_staff import STAFF, active_team_at_hour

router = APIRouter(prefix="/api/v1/cleaning", tags=["cleaning"])


# ── Endpoints base ─────────────────────────────────────────────────────────────

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


# ── Endpoints v9 — 14 unidades operacionais ────────────────────────────────────

@router.get("/units", response_model=WCUnitsCatalog)
async def get_units_catalog():
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
    return await service_v9.get_units_status(db)


@router.post("/units/{unit_id}/done", response_model=CleaningEntry)
async def mark_unit_done(
    unit_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _auth: str = Depends(require_ops_key),
):
    u = unit_by_id(unit_id)
    if u is None:
        raise HTTPException(404, detail=f"Unit {unit_id} desconhecida")
    req = CleaningDoneRequest(
        cluster_id=unit_id,
        team=body.get("team"),
        operator=body.get("operator"),
        notes=body.get("notes"),
    )
    return await service_v9.mark_unit_done(db, req)


@router.get("/units/{unit_id}/history", response_model=list[CleaningEntry])
async def unit_history(
    unit_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    if unit_by_id(unit_id) is None:
        raise HTTPException(404, detail=f"Unit {unit_id} desconhecida")
    return await service_v9.list_history(db, target_id=unit_id, limit=limit)


# ── Endpoints preditivos ────────────────────────────────────────────────────────

class StaffMember(BaseModel):
    person_id: str
    name: str
    phone: str
    team: str
    role: str
    shift: str
    languages: list[str]


class StaffResponse(BaseModel):
    staff: list[StaffMember]
    total: int
    teams: dict[str, int]
    active_team_now: str


@router.get("/staff", response_model=StaffResponse)
async def get_staff() -> StaffResponse:
    members = [
        StaffMember(
            person_id=p.person_id, name=p.name, phone=p.phone,
            team=p.team, role=p.role, shift=p.shift, languages=list(p.languages),
        ) for p in STAFF
    ]
    team_counts: dict[str, int] = {}
    for p in STAFF:
        team_counts[p.team] = team_counts.get(p.team, 0) + 1
    now_hour = datetime.now(timezone.utc).hour
    return StaffResponse(
        staff=members, total=len(members),
        teams=team_counts,
        active_team_now=active_team_at_hour(now_hour),
    )


@router.get("/calendar")
async def get_calendar(hours: int = Query(24, ge=1, le=72)) -> dict[str, Any]:
    schedule = build_24h_schedule()
    if hours < 24:
        cutoff_iso = (
            datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            .__class__.fromisoformat(
                datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat()
            )
        )
        from datetime import timedelta
        cutoff_str = (datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                      + timedelta(hours=hours)).isoformat()
        schedule = [s for s in schedule if s.scheduled_for_iso <= cutoff_str]
    return {
        "schedule": [asdict(s) for s in schedule],
        "total_slots": len(schedule),
        "hours_ahead": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/next-by-unit")
async def get_next_by_unit(n: int = Query(3, ge=1, le=10)) -> dict[str, Any]:
    schedule = build_24h_schedule()
    grouped = next_slots_by_unit(schedule, n_per_unit=n)
    return {
        "by_unit": grouped,
        "unit_count": len(grouped),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
