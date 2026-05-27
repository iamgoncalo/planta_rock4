"""
PlantaOS · Cleaning service
============================
Lógica de negócio para limpeza de WCs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.operations import CleaningLog
from app.models.operations import (
    CleaningClusterStatus, CleaningEntry, CleaningScheduleResponse,
    CleaningDoneRequest, CleaningScheduleRequest,
)

# 8 clusters físicos do Parque Tejo
CLUSTER_IDS = [
    "WC-01", "WC-02", "WC-03", "WC-04",
    "WC-05", "WC-06", "WC-07", "WC-08",
]

# Limpeza considerada "fresca" durante 90 minutos
FRESH_MINUTES = 90
# Acima de 180 minutos sem limpeza, fica "urgent"
URGENT_MINUTES = 180


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _entry_to_pydantic(row: CleaningLog) -> CleaningEntry:
    return CleaningEntry(
        id=row.id,
        cluster_id=row.cluster_id,
        cleaned_at=row.cleaned_at,
        scheduled_for=row.scheduled_for,
        status=row.status,
        team=row.team,
        operator=row.operator,
        notes=row.notes,
        created_at=row.created_at,
    )


async def get_schedule(db: AsyncSession) -> CleaningScheduleResponse:
    """Devolve estado de limpeza dos 8 clusters."""
    out: list[CleaningClusterStatus] = []
    now = _utcnow()

    for cid in CLUSTER_IDS:
        # Última limpeza concluída
        q_last = (
            select(CleaningLog)
            .where(CleaningLog.cluster_id == cid)
            .where(CleaningLog.cleaned_at.isnot(None))
            .order_by(desc(CleaningLog.cleaned_at))
            .limit(1)
        )
        last_res = await db.execute(q_last)
        last = last_res.scalar_one_or_none()

        # Próximo agendado (no futuro)
        q_next = (
            select(CleaningLog)
            .where(CleaningLog.cluster_id == cid)
            .where(CleaningLog.scheduled_for.isnot(None))
            .where(CleaningLog.cleaned_at.is_(None))
            .where(CleaningLog.scheduled_for > now)
            .order_by(CleaningLog.scheduled_for)
            .limit(1)
        )
        next_res = await db.execute(q_next)
        nxt = next_res.scalar_one_or_none()

        minutes_since = None
        status: str = "clean"
        last_cleaned_at = None
        last_team = None
        if last and last.cleaned_at:
            last_cleaned_at = last.cleaned_at
            last_team = last.team
            cleaned_aware = last.cleaned_at
            if cleaned_aware.tzinfo is None:
                cleaned_aware = cleaned_aware.replace(tzinfo=timezone.utc)
            delta = (now - cleaned_aware).total_seconds() / 60.0
            minutes_since = int(delta)
            if delta >= URGENT_MINUTES:
                status = "urgent"
            elif delta >= FRESH_MINUTES:
                status = "needs_cleaning"
            else:
                status = "clean"
        else:
            # Sem registo — assume needs_cleaning
            status = "needs_cleaning"

        out.append(
            CleaningClusterStatus(
                cluster_id=cid,
                status=status,
                last_cleaned_at=last_cleaned_at,
                next_scheduled_for=nxt.scheduled_for if nxt else None,
                last_team=last_team,
                minutes_since_clean=minutes_since,
            )
        )

    return CleaningScheduleResponse(clusters=out, generated_at=now)


async def mark_done(db: AsyncSession, req: CleaningDoneRequest) -> CleaningEntry:
    """Regista limpeza concluída."""
    entry = CleaningLog(
        cluster_id=req.cluster_id,
        cleaned_at=_utcnow(),
        status="clean",
        team=req.team,
        operator=req.operator,
        notes=req.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_pydantic(entry)


async def schedule_cleaning(
    db: AsyncSession, req: CleaningScheduleRequest
) -> CleaningEntry:
    """Agenda futura limpeza."""
    entry = CleaningLog(
        cluster_id=req.cluster_id,
        scheduled_for=req.scheduled_for,
        status="needs_cleaning",
        team=req.team,
        notes=req.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_pydantic(entry)


async def list_history(
    db: AsyncSession, cluster_id: Optional[str] = None, limit: int = 50
) -> list[CleaningEntry]:
    """Histórico recente."""
    q = select(CleaningLog).order_by(desc(CleaningLog.created_at)).limit(limit)
    if cluster_id:
        q = q.where(CleaningLog.cluster_id == cluster_id)
    res = await db.execute(q)
    rows = res.scalars().all()
    return [_entry_to_pydantic(r) for r in rows]
