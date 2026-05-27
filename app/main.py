from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.routers.health import router as health_router
from app.routers.sections import router as sections_router
from app.routers.clusters import router as clusters_router
from app.routers.state import router as state_router
from app.routers.kpis import router as kpis_router
from app.routers.shows import router as shows_router
from app.routers.sensors import router as sensors_router
from app.routers.alerts import router as alerts_router
from app.routers.tv import router as tv_router
from app.routers.routing import router as routing_router
from app.routers.chat import router as chat_router
from app.routers.simulate import router as simulate_router
from app.routers.scor import router as scor_router

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="PlantaOS",
        version=settings.app_version,
        description="Rock in Rio Lisboa 2026 — WC occupancy management",
    )

    @app.on_event("startup")
    async def startup_db():
        """Ensure DB tables exist, seed initial sensor rows, and start health ticker."""
        try:
            from app.db import engine, Base
            # Import models so they register with Base.metadata
            from app.models.db.sensors import ClusterRef, Sensor, SensorHealth, MaintenanceLog, TerminalLog  # noqa
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("DB startup: tables ensured (SQLAlchemy create_all)")
        except Exception as e:
            logger.warning(f"DB startup warning: {e}")

        # Seed sensor rows if table is empty (SQLAlchemy, DB-agnostic)
        try:
            from app.startup_seeds import seed_sensors_if_empty
            from app.db import AsyncSessionLocal
            await seed_sensors_if_empty(AsyncSessionLocal)
        except Exception as e:
            logger.warning(f"Seed sensors warning: {e}")

        # Start sensor health background ticker
        try:
            from app.services.sensor_health import run_health_ticker
            from app.db import AsyncSessionLocal
            asyncio.create_task(run_health_ticker(AsyncSessionLocal))
            logger.info("Sensor health ticker started")
        except Exception as e:
            logger.warning(f"Health ticker startup warning: {e}")

        # Start SCOR/Sensaway publisher (publica para o André)
        try:
            from app.services.scor_publisher import publisher_loop
            asyncio.create_task(publisher_loop())
            logger.info("SCOR publisher started")
        except Exception as e:
            logger.warning(f"SCOR publisher startup warning: {e}")

    # CORS — allow frontend dev servers and the API itself
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Legacy routers (no /api prefix, kept for backwards compat)
    app.include_router(health_router)
    app.include_router(sections_router)

    # All new routers are prefixed under /api
    app.include_router(clusters_router)
    app.include_router(state_router)
    app.include_router(kpis_router)
    app.include_router(shows_router)
    app.include_router(sensors_router)
    app.include_router(alerts_router)
    app.include_router(tv_router)
    app.include_router(routing_router)
    app.include_router(chat_router)
    app.include_router(simulate_router)
    app.include_router(scor_router)

    # WebSocket: broadcasts live payload every 5s to connected clients
    @app.websocket("/api/v1/ws")
    async def ws_state(websocket: WebSocket):
        await websocket.accept()
        from app.services.state import get_live_payload
        try:
            while True:
                payload = get_live_payload()
                await websocket.send_text(payload.model_dump_json())
                await asyncio.sleep(5)
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass

    # Static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Root: serve dashboard or placeholder
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root():
        dashboard = STATIC_DIR / "index.html"
        if dashboard.exists():
            return dashboard.read_text()
        return "<h1>PlantaOS — Rock in Rio Lisboa 2026</h1><p>Dashboard not yet built. See <a href='/docs'>/docs</a>.</p>"

    return app


app = create_app()
