"""
PlantaOS · SCOR observability router
=====================================
Expõe o histórico in-memory das publicações SCOR.

Endpoints:
  - GET /api/v1/scor/recent?limit=50    → últimas N publicações
  - GET /api/v1/scor/stats              → sucesso/erro/latência
  - GET /api/v1/scor/overview           → stats + latest + config (1 chamada para UI)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from app.models.cleaning_v9 import (
    ScorRecentResponse, ScorRecord, ScorStats, ScorOverview,
)
from app.services.scor_history import scor_history

router = APIRouter(prefix="/api/v1/scor", tags=["scor"])


@router.get("/recent", response_model=ScorRecentResponse)
async def recent(limit: int = Query(50, ge=1, le=500)):
    """Últimas N publicações SCOR (mais recentes primeiro)."""
    records = await scor_history.recent(limit)
    return ScorRecentResponse(
        records=[ScorRecord(**r) for r in records],
        count=len(records),
    )


@router.get("/stats", response_model=ScorStats)
async def stats():
    s = await scor_history.stats()
    return ScorStats(**s)


@router.get("/overview", response_model=ScorOverview)
async def overview():
    """Snapshot agregado — para UI ler 1× em vez de 3 endpoints."""
    s = await scor_history.stats()
    latest_raw = await scor_history.latest()
    config = {
        "url": (
            f"{os.getenv('SCOR_BASE_URL', '')}/api/v1/"
            f"{os.getenv('SCOR_TOKEN_KPI', '')[:6]}.../telemetry"
        ),
        "interval_s": int(os.getenv("SCOR_PUSH_INTERVAL_S", "10")),
        "dry_run": os.getenv("SCOR_DRY_RUN", "false").lower() == "true",
    }
    return ScorOverview(
        stats=ScorStats(**s),
        latest=ScorRecord(**latest_raw) if latest_raw else None,
        config=config,
        generated_at=datetime.now(timezone.utc),
    )
