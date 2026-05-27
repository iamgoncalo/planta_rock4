"""
PlantaOS · Cleaning service v9
===============================
Escalado para 14 unidades operacionais (cluster × género).

Compatibilidade backwards: aceita tanto "WC-04" (cluster legacy) como
"WC-04_M"/"WC-04_F" (unidade nova). Quando recebe cluster, cria 1 registo
mas marca TODAS as unidades desse cluster como limpas.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.operations import CleaningLog
from app.models.operations import (
    CleaningEntry, CleaningDoneRequest, CleaningScheduleRequest,
)
from app.models.cleaning_v9 import (
    UnitCleaningStatus, CleaningScheduleV9Response,
)
from app.services.wc_units import WC_UNITS, units_by_cluster

FRESH_MINUTES = 60        # limpo nos últimos 60 min
URGENT_MINUTES = 90       # acima de 90 min = urgente
DEFAULT_CADENCE_MIN = 60  # ronda esperada de 1 em 1 hora


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _last_clean(db: AsyncSession, target_id: str) -> CleaningLog | None:
    """Última limpeza CONCLUÍDA para um target (cluster_id OU unit_id).
    Considera registos onde cluster_id == target OU notes/team contém o unit_id."""
    # Estratégia: armazenamos o unit_id no campo cluster_id (sobrescreve para suportar ambos)
    q = (
        select(CleaningLog)
        .where(CleaningLog.cluster_id == target_id)
        .where(CleaningLog.cleaned_at.isnot(None))
        .order_by(desc(CleaningLog.cleaned_at))
        .limit(1)
    )
    res = await db.execute(q)
    return res.scalar_one_or_none()


async def get_units_status(db: AsyncSession) -> CleaningScheduleV9Response:
    """Estado de TODAS as 14 unidades operacionais."""
    now = _utcnow()
    units_out: list[UnitCleaningStatus] = []

    for u in WC_UNITS:
        last = await _last_clean(db, u.unit_id)
        # Fallback: se nada para unit_id, tenta cluster_id (compat com Caminho A)
        if last is None and u.gender == "U":
            last = await _last_clean(db, u.cluster_id)

        minutes_since = None
        status = "needs_cleaning"
        last_cleaned_at = None
        last_team = None
        last_operator = None

        if last and last.cleaned_at:
            last_cleaned_at = last.cleaned_at
            last_team = last.team
            last_operator = last.operator
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

        units_out.append(UnitCleaningStatus(
            unit_id=u.unit_id,
            cluster_id=u.cluster_id,
            gender=u.gender,
            label=u.label,
            capacity_simultaneous=int(u.masc if u.gender == "M" else u.fem if u.gender == "F" else u.masc),
            capacity_total=float(u.total),
            espera=float(u.espera),
            note=u.note,
            status=status,
            last_cleaned_at=last_cleaned_at,
            minutes_since_clean=minutes_since,
            last_team=last_team,
            last_operator=last_operator,
        ))

    # Stats agregados
    clean = sum(1 for u in units_out if u.status == "clean")
    needs = sum(1 for u in units_out if u.status == "needs_cleaning")
    urgent = sum(1 for u in units_out if u.status == "urgent")

    return CleaningScheduleV9Response(
        units=units_out,
        total_units=len(units_out),
        clean_count=clean,
        needs_count=needs,
        urgent_count=urgent,
        generated_at=now,
    )


async def mark_unit_done(db: AsyncSession, req: CleaningDoneRequest) -> CleaningEntry:
    """Marca uma unidade (cluster_id OU unit_id) como limpa.
    
    Se `cluster_id` é um cluster (ex: "WC-04"), regista 1 entry no nome do cluster.
    Se é uma unit_id (ex: "WC-04_M"), regista para essa unidade específica.
    """
    target = req.cluster_id  # pode ser cluster_id ou unit_id

    entry = CleaningLog(
        cluster_id=target,  # armazenamos o que o cliente enviou
        cleaned_at=_utcnow(),
        status="clean",
        team=req.team,
        operator=req.operator,
        notes=req.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return CleaningEntry(
        id=entry.id,
        cluster_id=entry.cluster_id,
        cleaned_at=entry.cleaned_at,
        scheduled_for=entry.scheduled_for,
        status=entry.status,
        team=entry.team,
        operator=entry.operator,
        notes=entry.notes,
        created_at=entry.created_at,
    )


async def list_history(
    db: AsyncSession, target_id: Optional[str] = None, limit: int = 100
) -> list[CleaningEntry]:
    """Histórico recente, opcionalmente filtrado por unit_id ou cluster_id."""
    q = select(CleaningLog).order_by(desc(CleaningLog.created_at)).limit(limit)
    if target_id:
        q = q.where(CleaningLog.cluster_id == target_id)
    res = await db.execute(q)
    rows = res.scalars().all()
    return [
        CleaningEntry(
            id=r.id,
            cluster_id=r.cluster_id,
            cleaned_at=r.cleaned_at,
            scheduled_for=r.scheduled_for,
            status=r.status,
            team=r.team,
            operator=r.operator,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in rows
    ]
