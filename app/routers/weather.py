"""
PlantaOS · Weather router
==========================
GET /api/v1/weather/now — tempo actual em Lisboa (cache 10min).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.operations import WeatherNow
from app.services import weather as service

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])


@router.get("/now", response_model=WeatherNow)
async def now():
    try:
        return await service.get_now()
    except Exception as e:
        raise HTTPException(503, detail=f"Weather source unavailable: {e}")
