"""
sensor_health.py — Background health tick service.
Runs every 60s, marks sensors online/degraded/offline based on last_seen age.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.sensors import Sensor, SensorHealth

logger = logging.getLogger(__name__)

ONLINE_THRESHOLD_S = 70
DEGRADED_THRESHOLD_S = 300


def _compute_status(last_seen: datetime | None) -> str:
    if last_seen is None:
        return "unknown"
    now = datetime.now(timezone.utc)
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_s = (now - last_seen).total_seconds()
    if age_s < ONLINE_THRESHOLD_S:
        return "online"
    if age_s < DEGRADED_THRESHOLD_S:
        return "degraded"
    return "offline"


async def sensor_health_tick(db_factory) -> None:
    """
    Single tick: query all sensor_health rows, compute new status,
    upsert changed rows, and log changed sensors.
    """
    async with db_factory() as db:
        try:
            result = await db.execute(select(SensorHealth))
            healths = result.scalars().all()

            changed = []
            for h in healths:
                new_status = _compute_status(h.last_seen)
                if new_status != h.status:
                    changed.append((h.sensor_id, h.status, new_status))
                    await db.execute(
                        update(SensorHealth)
                        .where(SensorHealth.sensor_id == h.sensor_id)
                        .values(status=new_status, updated_at=datetime.now(timezone.utc))
                    )

            if changed:
                await db.commit()
                for sensor_id, old, new in changed:
                    logger.info(f"sensor_health_tick: {sensor_id} {old} -> {new}")
            else:
                logger.debug(f"sensor_health_tick: no changes ({len(healths)} sensors checked)")

        except Exception as e:
            logger.error(f"sensor_health_tick error: {e}")


async def run_health_ticker(db_factory, interval_s: int = 60) -> None:
    """Background loop running sensor_health_tick every interval_s seconds."""
    while True:
        try:
            await sensor_health_tick(db_factory)
        except Exception as e:
            logger.error(f"Health ticker error: {e}")
        await asyncio.sleep(interval_s)
