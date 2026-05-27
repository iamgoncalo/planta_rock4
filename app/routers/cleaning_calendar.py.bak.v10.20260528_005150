"""
PlantaOS · Cleaning calendar router
====================================
Endpoints PREDITIVOS (não reactivos):
  GET /api/v1/cleaning/calendar?hours=24       → calendário futuro com atribuições
  GET /api/v1/cleaning/staff                    → 8 pessoas + contactos
  GET /api/v1/cleaning/next-by-unit             → próximas 3 limpezas por unidade
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.cleaning_predictive import (
    build_24h_schedule, next_slots_by_unit,
)
from app.services.cleaning_staff import STAFF, active_team_at_hour

router = APIRouter(prefix="/api/v1/cleaning", tags=["cleaning-predictive"])


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
    """Dataset das pessoas — nomes, contactos, equipas."""
    members = [
        StaffMember(
            person_id=p.person_id, name=p.name, phone=p.phone,
            team=p.team, role=p.role, shift=p.shift, languages=list(p.languages),
        ) for p in STAFF
    ]
    team_counts = {"A": 0, "B": 0}
    for p in STAFF:
        team_counts[p.team] = team_counts.get(p.team, 0) + 1

    now_hour = datetime.now(timezone.utc).hour
    return StaffResponse(
        staff=members,
        total=len(members),
        teams=team_counts,
        active_team_now=active_team_at_hour(now_hour),
    )


@router.get("/calendar")
async def get_calendar(hours: int = Query(24, ge=1, le=72)) -> dict[str, Any]:
    """Calendário preditivo com atribuições de pessoas.

    Devolve TODOS os slots agendados nas próximas N horas.
    """
    schedule = build_24h_schedule()
    # Filtrar para apenas N horas
    if hours < 24:
        cutoff = datetime.now(timezone.utc).replace(microsecond=0)
        cutoff_iso = (cutoff.replace(minute=0, second=0) +
                      __import__('datetime').timedelta(hours=hours)).isoformat()
        schedule = [s for s in schedule if s.scheduled_for_iso <= cutoff_iso]

    items = [asdict(s) for s in schedule]
    return {
        "schedule": items,
        "total_slots": len(items),
        "hours_ahead": hours,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/next-by-unit")
async def get_next_by_unit(n: int = Query(3, ge=1, le=10)) -> dict[str, Any]:
    """Próximos N slots por unidade — para vista de cards."""
    schedule = build_24h_schedule()
    grouped = next_slots_by_unit(schedule, n_per_unit=n)
    return {
        "by_unit": grouped,
        "unit_count": len(grouped),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
