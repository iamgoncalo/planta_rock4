from __future__ import annotations
from fastapi import APIRouter
from app.models.sensors import IRReading, CameraMLReading, SensorHealth
from app.services.state import get_sensor_health, ingest_ir, ingest_camera

router = APIRouter(prefix="/api/v1", tags=["sensors"])


@router.get("/sensors", response_model=list[SensorHealth])
async def list_sensors():
    """Return health status for all 8 sensor clusters."""
    return get_sensor_health()


@router.post("/sensor", response_model=dict)
async def ingest_ir_reading(reading: IRReading):
    """Ingest an IR gate reading (entry or exit count)."""
    ingest_ir(reading)
    return {"status": "accepted", "source_id": reading.source_id, "simulated": reading.simulated}


@router.post("/prosegur", response_model=dict)
async def ingest_camera_reading(reading: CameraMLReading):
    """Ingest a Prosegur camera ML crowd-count reading."""
    ingest_camera(reading)
    return {"status": "accepted", "source_id": reading.source_id, "zone": reading.zone}
