from __future__ import annotations
from fastapi import APIRouter
from app.models.sections import LivePayload
from app.services.state import get_live_payload

router = APIRouter(prefix="/api/v1", tags=["state"])


@router.get("/state", response_model=LivePayload)
async def get_state():
    """Return the full live payload (sections + KPIs + alerts)."""
    return get_live_payload()
