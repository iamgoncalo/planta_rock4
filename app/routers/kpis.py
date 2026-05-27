from __future__ import annotations
from fastapi import APIRouter
from app.models.sections import GlobalKPIs
from app.services.state import get_live_payload

router = APIRouter(prefix="/api/v1", tags=["kpis"])


@router.get("/kpis", response_model=GlobalKPIs)
async def get_kpis():
    """Return global KPIs."""
    payload = get_live_payload()
    return payload.kpis
