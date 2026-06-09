from fastapi import APIRouter, HTTPException, Response
from app.models.sections import SECTION_IDS, SectionState, LivePayload, GlobalKPIs
from app.services.state import get_live_payload, get_section_state

router = APIRouter(prefix="/api/v1", tags=["sections"])


@router.get("/sections", response_model=LivePayload)
async def list_sections(response: Response):
    response.headers["Cache-Control"] = "public, max-age=5, s-maxage=5"
    return get_live_payload()


@router.get("/sections/{section_id}", response_model=SectionState)
async def get_section(section_id: str):
    if section_id not in SECTION_IDS:
        raise HTTPException(404, f"Section '{section_id}' not found")
    try:
        return get_section_state(section_id)
    except KeyError:
        raise HTTPException(404, f"Section '{section_id}' not found")


@router.get("/kpis", response_model=GlobalKPIs)
async def get_kpis(response: Response):
    response.headers["Cache-Control"] = "public, max-age=5, s-maxage=5"
    payload = get_live_payload()
    return payload.kpis
