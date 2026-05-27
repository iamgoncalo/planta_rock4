"""
PlantaOS · Pipelines observability
===================================
Snapshot dos data flows activos no sistema. Não inventa dados — devolve
factos do estado interno (auto_tick contador, SCOR stats, etc).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.scor_history import scor_history

router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


class PipelineNode(BaseModel):
    id: str
    label: str
    role: str               # "ingestion" | "processing" | "output" | "ai"
    status: str             # "live" | "pre_install" | "idle" | "error"
    rate_per_minute: float  # eventos/min estimados
    last_event_iso: str | None = None
    details: dict


class PipelinesOverview(BaseModel):
    nodes: list[PipelineNode]
    generated_at: datetime
    hardware_install_date: str = "2026-06-11"


# Tracker simples do auto_tick
_TICK_COUNTER = {"count": 0, "last_ts": 0.0}


def _bump_tick():
    """Chamada pelo auto_tick para registar ocorrência."""
    _TICK_COUNTER["count"] += 1
    _TICK_COUNTER["last_ts"] = time.time()


@router.get("/overview", response_model=PipelinesOverview)
async def overview():
    """Snapshot dos 4 fluxos principais."""
    scor_stats = await scor_history.stats()
    scor_latest = await scor_history.latest()

    nodes: list[PipelineNode] = []

    # 1. INGESTION — sensores físicos (pre-install até 11 Junho)
    nodes.append(PipelineNode(
        id="ingestion_sensors",
        label="Ingestão de sensores",
        role="ingestion",
        status="pre_install",
        rate_per_minute=0.0,
        last_event_iso=None,
        details={
            "hardware_install_date": "2026-06-11",
            "expected_sources": ["IR E18-D80NK", "WiFi 6E aggregate", "Câmaras ML"],
            "fusion_weights": {"ir": 0.50, "wifi": 0.30, "camera": 0.20},
            "expected_rate_per_min": 480,  # 8 clusters × 60 events/min
        },
    ))

    # 2. PROCESSING — auto_tick (simulação interna até 11 Jun)
    tick_count = _TICK_COUNTER["count"]
    tick_age_s = (time.time() - _TICK_COUNTER["last_ts"]) if _TICK_COUNTER["last_ts"] else None
    interval_s = int(os.getenv("AUTO_TICK_INTERVAL_S", "10"))
    nodes.append(PipelineNode(
        id="processing_tick",
        label="Auto-tick (simulação)",
        role="processing",
        status="live" if (tick_age_s is not None and tick_age_s < 60) else "idle",
        rate_per_minute=60.0 / interval_s if interval_s else 0,
        last_event_iso=(
            datetime.fromtimestamp(_TICK_COUNTER["last_ts"], tz=timezone.utc).isoformat()
            if _TICK_COUNTER["last_ts"] else None
        ),
        details={
            "interval_s": interval_s,
            "total_ticks_session": tick_count,
            "scenario": os.getenv("AUTO_TICK_SCENARIO", "normal"),
        },
    ))

    # 3. OUTPUT — SCOR publisher para Sensaway
    nodes.append(PipelineNode(
        id="output_scor",
        label="SCOR publisher",
        role="output",
        status=("live" if scor_stats["last_5min_count"] > 0 else "idle"),
        rate_per_minute=scor_stats["last_5min_count"] / 5.0,
        last_event_iso=scor_latest["iso"] if scor_latest else None,
        details={
            "destination": "Sensaway",
            "url": (
                f"{os.getenv('SCOR_BASE_URL', '')}"
                f"/api/v1/{os.getenv('SCOR_TOKEN_KPI', '')[:6]}.../telemetry"
            ),
            "interval_s": int(os.getenv("SCOR_PUSH_INTERVAL_S", "10")),
            "success_rate_pct": scor_stats["success_rate_pct"],
            "avg_latency_ms": scor_stats["avg_latency_ms_5min"],
            "ok_count": scor_stats["ok_count"],
            "error_count": scor_stats["error_count"],
        },
    ))

    # 4. AI — Gemini chat
    nodes.append(PipelineNode(
        id="ai_gemini",
        label="Chat AI · Gemini",
        role="ai",
        status="live",
        rate_per_minute=0.0,  # on-demand
        last_event_iso=None,
        details={
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            "key_set": bool(os.getenv("GEMINI_API_KEY")),
            "trigger": "on user request",
        },
    ))

    return PipelinesOverview(
        nodes=nodes,
        generated_at=datetime.now(timezone.utc),
    )
