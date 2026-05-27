import time
from fastapi import APIRouter
from app.config import get_settings

router = APIRouter(tags=["health"])


async def _health_response() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": s.app_version,
        "simulation": s.simulation_active,
        "ts": time.time(),
    }


@router.get("/health")
async def health():
    return await _health_response()


@router.get("/v1/health")
async def health_v1():
    return await _health_response()


@router.get("/api/v1/health")
async def health_api_v1():
    return await _health_response()
