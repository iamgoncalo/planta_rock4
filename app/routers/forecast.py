"""
PlantaOS · Forecast router
===========================
GET /api/v1/forecast/cluster/{cluster_id}?horizon_min=30
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services import forecast as fc_service
from app.services.state import get_current_state
from app.services.simulation import simulate_tick  # noqa — usado indirectamente

router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])


class ForecastPointOut(BaseModel):
    minutes_ahead: int
    ocupacao_pct: float
    confidence: float
    surge_active: bool


class ForecastResponse(BaseModel):
    cluster_id: str
    horizon_min: int
    current_ocupacao_pct: float
    points: list[ForecastPointOut]
    peak_ocupacao_pct: float
    peak_at_min: int
    notes: list[str]
    generated_at: datetime


def _minutes_to_next_show_end() -> Optional[int]:
    """Stub minimal — sem acesso ao show schedule retorna None.
    O auto_tick do surge_predictor (Caminho B parte 2) fará esta lógica
    em background com acesso ao shows router."""
    return None


@router.get("/cluster/{cluster_id}", response_model=ForecastResponse)
async def cluster_forecast(
    cluster_id: str,
    horizon_min: int = Query(30, ge=5, le=60),
):
    """Projecta a ocupação do cluster para os próximos minutos."""
    try:
        state = await get_current_state()
    except Exception as e:
        raise HTTPException(500, detail=f"Não consegui ler estado actual: {e}")

    # Encontra ocupação actual agregada por cluster
    sections = getattr(state, "sections", None) or []
    cluster_pcts: list[float] = []
    for s in sections:
        sid = getattr(s, "section_id", "")
        if sid.startswith(cluster_id):
            pct = getattr(s, "ocupacao_pct", 0.0)
            cluster_pcts.append(float(pct))

    if not cluster_pcts:
        raise HTTPException(404, detail=f"Cluster {cluster_id} não encontrado")

    current_pct = sum(cluster_pcts) / len(cluster_pcts)

    # Slope conservador — 0 por defeito (sem histórico em memória ainda)
    slope = 0.0

    forecast = fc_service.project(
        cluster_id=cluster_id,
        current_pct=current_pct,
        trend_slope_per_min=slope,
        minutes_to_show_end=_minutes_to_next_show_end(),
        horizon_min=horizon_min,
    )

    return ForecastResponse(
        cluster_id=forecast.cluster_id,
        horizon_min=forecast.horizon_min,
        current_ocupacao_pct=forecast.current_ocupacao_pct,
        points=[
            ForecastPointOut(
                minutes_ahead=p.minutes_ahead,
                ocupacao_pct=p.ocupacao_pct,
                confidence=p.confidence,
                surge_active=p.surge_active,
            )
            for p in forecast.points
        ],
        peak_ocupacao_pct=forecast.peak_ocupacao_pct,
        peak_at_min=forecast.peak_at_min,
        notes=forecast.notes,
        generated_at=datetime.now(timezone.utc),
    )
