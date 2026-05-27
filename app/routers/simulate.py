from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services import state as state_service
from app.services.simulation import ScenarioName

router = APIRouter(prefix="/api/v1", tags=["simulate"])

_VALID_SCENARIOS = {
    "normal", "pre_show", "during_show", "post_show_surge",
    "wc05_overcrowded", "wc06_relief", "ir_offline", "wifi_offline",
    "camera_offline", "lorawan_fallback", "all_sensors_degraded",
    "sensors_disagree", "all_wcs_critical", "zero_people",
    "recovery_after_redirect",
}


class SimulateTickRequest(BaseModel):
    scenario: str


@router.post("/simulate/tick")
async def simulate_tick(body: SimulateTickRequest):
    """Advance simulation by one tick. Returns new scenario, tick, and section count."""
    if body.scenario not in _VALID_SCENARIOS:
        raise HTTPException(
            400,
            f"Unknown scenario '{body.scenario}'. Valid scenarios: {sorted(_VALID_SCENARIOS)}",
        )
    state_service.advance_tick(body.scenario)
    return {
        "scenario": state_service.CURRENT_SCENARIO,
        "tick": state_service.TICK,
        "sections_count": 14,
    }
