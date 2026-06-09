from __future__ import annotations
from app.routers import rirstaff
import asyncio
import json
import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.health import router as health_router
from app.routers.sections import router as sections_router
from app.routers.clusters import router as clusters_router
from app.routers.clusters_geo import router as clusters_geo_router
from app.routers.state import router as state_router
from app.routers.kpis import router as kpis_router
from app.routers.shows import router as shows_router
from app.routers.firmware import router as firmware_router
from app.routers.sensors import router as sensors_router
from app.routers.alerts import router as alerts_router
from app.routers.tv import router as tv_router
from app.routers.routing import router as routing_router
from app.routers.chat import router as chat_router
from app.routers.simulate import router as simulate_router
from app.routers.scor import router as scor_router
from app.routers.devices import router as devices_router
from app.routers.cleaning import router as cleaning_router  # unificado (U2)
from app.routers.staff import router as staff_router
from app.routers.incidents import router as incidents_router
from app.routers.weather import router as weather_router
from app.routers.scor_observability import router as scor_obs_router
from app.routers.pipelines import router as pipelines_router
from app.routers.telemetry import router as telemetry_router
from app.routers.forecast import router as forecast_router
from app.routers.ingest import router as ingest_router
from app.routers.fleet import router as fleet_router
from app.routers.sensor_cmd import router as sensor_cmd_router
from app.routers.envs import router as envs_router
from app.routers.fusion import router as fusion_router
from app.routers.calibration import router as calibration_router
from app.routers.intelligence import router as intelligence_router
from app.routers.flow import router as flow_router
from app.routers.screen import router as screen_router

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
            from app.models.db.operations import CleaningLog, StaffRoster, IncidentLog, IngestSnapshot, FusaoRolanteSnapshot, NodeCalibration  # noqa
            from app.models.db.flow_history import FlowSnapshot, CrowdProfile  # noqa
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

        # Start auto-tick (avança o simulador para que os valores variem)
        try:
            from app.services.auto_tick import auto_tick_loop
            asyncio.create_task(auto_tick_loop())
            logger.info("Auto-tick loop started")
        except Exception as e:
            logger.warning(f"Auto-tick startup warning: {e}")

        # Start SCOR/Sensaway publisher (publica para o André)
        try:
            from app.services.scor_publisher import publisher_loop
            asyncio.create_task(publisher_loop())
            logger.info("SCOR publisher started")
        except Exception as e:
            logger.warning(f"SCOR publisher startup warning: {e}")

        # Start MQTT bridge (device control — connects when broker is available)
        try:
            from app.services.mqtt_bridge import mqtt_bridge_loop
            asyncio.create_task(mqtt_bridge_loop())
            logger.info("MQTT bridge started")
        except Exception as e:
            logger.warning(f"MQTT bridge startup warning: {e}")

        # Seed crowd profiles e iniciar loop de snapshots de fluxo
        try:
            from app.services.flow_history import seed_crowd_profiles_if_empty, flush_snapshot_loop
            from app.db import AsyncSessionLocal
            await seed_crowd_profiles_if_empty(AsyncSessionLocal)
            asyncio.create_task(flush_snapshot_loop())
            logger.info("Flow history: crowd profiles seeded + snapshot loop started")
        except Exception as e:
            logger.warning(f"Flow history startup warning: {e}")

        # U5: recarregar ingest_store do snapshot + iniciar loop de persistência
        try:
            from app.services.ingest_store import _load_snapshot, snapshot_loop
            from app.db import AsyncSessionLocal
            await _load_snapshot(AsyncSessionLocal)
            asyncio.create_task(snapshot_loop(AsyncSessionLocal))
            logger.info("ingest_store: snapshot recarregado + loop persistência iniciado")
        except Exception as e:
            logger.warning(f"ingest_store snapshot startup warning: {e}")

        # Fusão rolante: recarregar snapshot + calibração e iniciar loop 60s
        try:
            from app.services import fusao_rolante, node_calibration
            from app.db import AsyncSessionLocal
            if AsyncSessionLocal is not None:
                await node_calibration.load_from_db(AsyncSessionLocal)
                await fusao_rolante._load_snapshot(AsyncSessionLocal)
                asyncio.create_task(fusao_rolante.snapshot_loop(AsyncSessionLocal))
            logger.info("fusao_rolante: snapshot recarregado + loop persistência iniciado")
        except Exception as e:
            logger.warning(f"fusao_rolante snapshot startup warning: {e}")

        # Orquestrador de demonstração da fusão rolante (só em fleet mode=sim;
        # cala-se perante dados reais; origem=simulado sempre visível)
        try:
            from app.services.fusao_rolante_demo import demo_loop
            asyncio.create_task(demo_loop())
            logger.info("fusao_rolante_demo: orquestrador agendado")
        except Exception as e:
            logger.warning(f"fusao_rolante_demo startup warning: {e}")

    # CORS — allow frontend dev servers and the API itself
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://planta-rock4-.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Legacy routers (no /api prefix, kept for backwards compat)
    app.include_router(health_router)
    app.include_router(sections_router)

    # All new routers are prefixed under /api
    app.include_router(clusters_router)
    app.include_router(clusters_geo_router)
    app.include_router(state_router)
    app.include_router(kpis_router)
    app.include_router(shows_router)
    app.include_router(firmware_router)
    app.include_router(sensors_router)
    app.include_router(alerts_router)
    app.include_router(tv_router)
    app.include_router(routing_router)
    app.include_router(chat_router)
    app.include_router(simulate_router)
    app.include_router(scor_router)
    app.include_router(devices_router)
    app.include_router(ingest_router)
    app.include_router(fleet_router)
    app.include_router(sensor_cmd_router)
    app.include_router(envs_router)
    app.include_router(fusion_router)
    app.include_router(calibration_router)
    app.include_router(intelligence_router)
    app.include_router(flow_router)
    app.include_router(screen_router)
    app.include_router(cleaning_router)  # unificado (U2)
    app.include_router(staff_router)
    app.include_router(incidents_router)
    app.include_router(weather_router)
    app.include_router(scor_obs_router)
    app.include_router(pipelines_router)
    app.include_router(telemetry_router)
    app.include_router(forecast_router)
    app.include_router(rirstaff.router)

    # WebSocket: broadcasts live payload every 5s to connected clients
    @app.websocket("/api/v1/ws")
    async def ws_state(websocket: WebSocket):
        await websocket.accept()
        from app.services.state import get_live_payload
        try:
            while True:
                payload = get_live_payload()
                await websocket.send_text(payload.model_dump_json())
                try:
                    import json as _json
                    from app.routers.flow import get_flow_snapshot
                    await websocket.send_text(_json.dumps(
                        {"type": "flow_update", "data": get_flow_snapshot()}
                    ))
                except Exception:
                    pass
                await asyncio.sleep(5)
        except WebSocketDisconnect:
            pass
        except Exception:
            try:
                await websocket.close()
            except Exception:
                pass

    # Static files (legacy standalone HTML, still served at /static/*)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ── Next.js dev-server proxy ──────────────────────────────────────────────
    # Forwards every non-API, non-docs request to the Next.js dev server so
    # the full React app (including /sensors, /_next/*, HMR) is reachable at
    # http://localhost:8000 without leaving the backend port.
    NEXT_DEV = "http://localhost:3002"
    # disable httpx auto-decompress so we forward raw bytes; strip Accept-Encoding
    # from upstream requests so Next.js sends plain bytes (no gzip confusion)
    _proxy_client = httpx.AsyncClient(
        base_url=NEXT_DEV,
        timeout=15.0,
        headers={"Accept-Encoding": "identity"},
    )

    # Headers that must NOT be forwarded from the upstream response
    _drop_resp = {"content-encoding", "content-length", "transfer-encoding",
                  "connection", "keep-alive", "te", "trailers", "upgrade"}

    @app.get("/health", include_in_schema=False)
    async def _bare_health():
        return {"status": "ok"}

    @app.get("/{full_path:path}", include_in_schema=False)
    @app.post("/{full_path:path}", include_in_schema=False)
    async def proxy_nextjs(full_path: str, request: Request):
        if full_path.startswith("api/") or full_path.startswith("v1/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Rota API desconhecida: /" + full_path}, status_code=404)
        # Strip hop-by-hop request headers
        skip_req = {"host", "connection", "transfer-encoding", "te",
                    "trailers", "upgrade", "keep-alive", "accept-encoding"}
        fwd_headers = {k: v for k, v in request.headers.items()
                       if k.lower() not in skip_req}
        url = f"/{full_path}"
        if request.url.query:
            url += f"?{request.url.query}"
        try:
            resp = await _proxy_client.request(
                method=request.method,
                url=url,
                headers=fwd_headers,
                content=await request.body(),
            )
            resp_headers = {k: v for k, v in resp.headers.items()
                            if k.lower() not in _drop_resp}
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers,
                media_type=resp.headers.get("content-type"),
            )
        except httpx.ConnectError:
            return HTMLResponse(
                "<h2>PlantaOS</h2>"
                "<p>Frontend dev server não está a correr.<br>"
                "Inicia com: <code>cd planta_rock4/frontend && npm run dev -- -p 3002</code></p>"
                "<p>API: <a href='/docs'>/docs</a></p>",
                status_code=503,
            )

    return app


app = create_app()
