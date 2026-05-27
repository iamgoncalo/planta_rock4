from __future__ import annotations
from fastapi import APIRouter
from app.models.tv import TVScreenState
from app.services.state import get_tv_state

router = APIRouter(prefix="/api/v1", tags=["tv"])


@router.get("/tv/{screen_id}", response_model=TVScreenState)
async def get_tv_screen(screen_id: str):
    """Return the current display state for a TV screen."""
    return get_tv_state(screen_id)
