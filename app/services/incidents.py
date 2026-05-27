"""
PlantaOS · Incidents service
=============================
Registo e gestão de incidentes durante o festival.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.operations import IncidentLog
from app.models.operations import (
    IncidentEntry, IncidentListResponse,
    IncidentCreateRequest, IncidentResolveRequest,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _entry_to_pydantic(row: IncidentLog) -> IncidentEntry:
    return IncidentEntry(
        id=row.id,
        cluster_id=row.cluster_id,
        severity=row.severity,
        category=row.category,
        note=row.note,
        reported_by=row.reported_by,
        resolved=row.resolved,
        resolved_at=row.resolved_at,
        resolved_by=row.resolved_by,
        resolution_note=row.resolution_note,
        occurred_at=row.occurred_at or row.created_at,
        created_at=row.created_at,
    )


async def create(db: AsyncSession, req: IncidentCreateRequest) -> IncidentEntry:
    """Cria novo incidente."""
    entry = IncidentLog(
        cluster_id=req.cluster_id,
        severity=req.severity,
        category=req.category,
        note=req.note,
        reported_by=req.reported_by,
        occurred_at=_utcnow(),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_pydantic(entry)


async def list_incidents(
    db: AsyncSession,
    day: Optional[str] = None,
    cluster_id: Optional[str] = None,
    severity: Optional[str] = None,
    open_only: bool = False,
    limit: int = 100,
) -> IncidentListResponse:
    """Lista incidentes filtrados."""
    q = select(IncidentLog).order_by(desc(IncidentLog.occurred_at)).limit(limit)
    if cluster_id:
        q = q.where(IncidentLog.cluster_id == cluster_id)
    if severity:
        q = q.where(IncidentLog.severity == severity)
    if open_only:
        q = q.where(IncidentLog.resolved == False)  # noqa: E712
    if day:
        # day formato "2026-06-20"
        q = q.where(func.to_char(IncidentLog.occurred_at, "YYYY-MM-DD") == day)
    res = await db.execute(q)
    rows = res.scalars().all()
    entries = [_entry_to_pydantic(r) for r in rows]

    open_count = sum(1 for e in entries if not e.resolved)
    critical_count = sum(1 for e in entries if e.severity == "critical")

    return IncidentListResponse(
        incidents=entries,
        total=len(entries),
        open_count=open_count,
        critical_count=critical_count,
    )


async def resolve(
    db: AsyncSession, incident_id: int, req: IncidentResolveRequest
) -> Optional[IncidentEntry]:
    """Marca incidente como resolvido."""
    q = select(IncidentLog).where(IncidentLog.id == incident_id)
    res = await db.execute(q)
    row = res.scalar_one_or_none()
    if row is None:
        return None
    row.resolved = True
    row.resolved_at = _utcnow()
    row.resolved_by = req.resolved_by
    row.resolution_note = req.resolution_note
    await db.commit()
    await db.refresh(row)
    return _entry_to_pydantic(row)
