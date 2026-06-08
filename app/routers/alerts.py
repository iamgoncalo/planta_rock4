# U3 audit: lê de get_alerts() (derivado de get_live_payload via state) — fonte única ✅
from __future__ import annotations
from fastapi import APIRouter
from app.models.alerts import Alert
from app.services.state import get_alerts

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/alerts", response_model=list[Alert])
async def list_alerts():
    """Return all current alerts (auto-generated from critical sections + manual)."""
    return get_alerts()
