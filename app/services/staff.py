"""
PlantaOS · Staff roster service
================================
Gestão de alocação de pessoal aos clusters por turno.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.operations import StaffRoster
from app.models.operations import (
    StaffEntry, StaffRosterResponse, StaffCreateRequest,
)


def _entry_to_pydantic(row: StaffRoster) -> StaffEntry:
    return StaffEntry(
        id=row.id,
        day=row.day,
        cluster_id=row.cluster_id,
        shift_start=row.shift_start,
        shift_end=row.shift_end,
        role=row.role,
        name=row.name,
        contact=row.contact,
        confirmed=row.confirmed,
        notes=row.notes,
    )


async def get_roster(db: AsyncSession, day: str) -> StaffRosterResponse:
    """Devolve roster completo de um dia, agrupado por cluster + role."""
    q = (
        select(StaffRoster)
        .where(StaffRoster.day == day)
        .order_by(StaffRoster.cluster_id, StaffRoster.shift_start)
    )
    res = await db.execute(q)
    rows = res.scalars().all()

    by_cluster: dict[str, list[StaffEntry]] = defaultdict(list)
    by_role: dict[str, int] = defaultdict(int)

    for r in rows:
        entry = _entry_to_pydantic(r)
        by_cluster[r.cluster_id].append(entry)
        by_role[r.role] += 1

    return StaffRosterResponse(
        day=day,
        total=len(rows),
        by_cluster=dict(by_cluster),
        by_role=dict(by_role),
    )


async def add_entry(db: AsyncSession, req: StaffCreateRequest) -> StaffEntry:
    """Adiciona alocação de pessoal."""
    entry = StaffRoster(
        day=req.day,
        cluster_id=req.cluster_id,
        shift_start=req.shift_start,
        shift_end=req.shift_end,
        role=req.role,
        name=req.name,
        contact=req.contact,
        notes=req.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _entry_to_pydantic(entry)


async def confirm(db: AsyncSession, entry_id: int) -> Optional[StaffEntry]:
    """Marca alocação como confirmada."""
    q = select(StaffRoster).where(StaffRoster.id == entry_id)
    res = await db.execute(q)
    row = res.scalar_one_or_none()
    if row is None:
        return None
    row.confirmed = True
    await db.commit()
    await db.refresh(row)
    return _entry_to_pydantic(row)


async def remove(db: AsyncSession, entry_id: int) -> bool:
    """Remove alocação."""
    q = select(StaffRoster).where(StaffRoster.id == entry_id)
    res = await db.execute(q)
    row = res.scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True
