from __future__ import annotations
from typing import Optional
from fastapi import APIRouter
from app.models.shows import Show
from app.services.state import get_shows, get_active_show

router = APIRouter(prefix="/api/v1", tags=["shows"])


@router.get("/shows")
async def list_shows():
    """Return all scheduled shows and the currently active show."""
    shows = get_shows()
    active = get_active_show()
    return {
        "shows": shows,
        "active_show": active,
        "total_shows": len(shows),
    }
