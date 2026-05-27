from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.routing import BathroomRouteDecision
from app.services.state import get_live_payload, get_active_show
from app.services.routing import compute_route

router = APIRouter(prefix="/api/v1", tags=["routing"])


class RouteRequest(BaseModel):
    user_lat: float
    user_lon: float


@router.post("/route", response_model=BathroomRouteDecision)
async def get_route(body: RouteRequest):
    """Compute the optimal bathroom route from a user GPS position."""
    payload = get_live_payload()
    active_show = get_active_show()

    if not payload.sections:
        raise HTTPException(503, "No section data available")

    return compute_route(payload.sections, body.user_lat, body.user_lon, active_show)
