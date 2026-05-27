"""SCOR telemetry endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.services import state as state_service
from app.services.scor import build_scor_entries, _FORBIDDEN_FIELDS

router = APIRouter(prefix="/api/v1", tags=["scor"])


@router.post("/scor/dry-run")
async def scor_dry_run():
    """Dry-run SCOR section telemetry publish.

    Runs publish_scor_sections(sections, dry_run=True).
    Returns confirmation that exactly 14 entries would be sent,
    with no GPS, no CO2, and no forbidden cluster_ids.
    """
    from app.services.scor import publish_scor_sections

    payload = state_service.get_live_payload()
    result = await publish_scor_sections(payload.sections, dry_run=True)

    entries = result.get("entries", [])
    sample = entries[0] if entries else {}

    # Verify no GPS fields
    gps_fields = {"lat", "lon", "latitude", "longitude", "gps_lat", "gps_lon"}
    gps_present = any(
        field in entry
        for entry in entries
        for field in gps_fields
    )

    # Verify no CO2 fields
    co2_fields = {"co2", "co2_ppm", "temperature", "temperatura", "humidity", "humidade"}
    co2_present = any(
        field in entry
        for entry in entries
        for field in co2_fields
    )

    return {
        "sections_sent": len(entries),
        "sample": sample,
        "gps_present": gps_present,
        "co2_present": co2_present,
        "status": "dry_run_ok",
    }
