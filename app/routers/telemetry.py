"""
PlantaOS · Telemetry router
============================
Expõe o payload de 8 clusters no formato OFICIAL (cluster_id, ts, params).

Endpoints:
  GET  /api/v1/telemetry/clusters/now       → snapshot único (REST)
  GET  /api/v1/telemetry/clusters/stream    → SSE ao segundo (Server-Sent Events)
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from app.services.cluster_telemetry import CLUSTER_IDS
from app.services.state import get_tick_snapshot

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


def _build_snapshot() -> dict[str, Any]:
    """Serve a vista telemetry do SNAPSHOT ÚNICO do tick (state.py).

    Zero recomputação por request: clusters + kpis são construídos UMA vez
    por tick junto do payload canónico — /flow, /state e este endpoint leem
    o mesmo objecto, por construção."""
    snap = get_tick_snapshot()
    clusters = snap["clusters"]
    return {
        "clusters": clusters,
        "kpis": snap["kpis"],
        "cluster_count": len(clusters),
        "expected_clusters": CLUSTER_IDS,
    }


@router.get("/clusters/now")
async def clusters_now(response: Response) -> dict[str, Any]:
    """Snapshot único — para clients que não suportam SSE. Cache de 5s.

    Cache-Control permite à CDN (Cloudflare) guardar a resposta na borda
    durante 5s — os pedidos nem chegam ao servidor. s-maxage = cache CDN.
    """
    response.headers["Cache-Control"] = "public, max-age=5, s-maxage=5"
    return _build_snapshot()


@router.get("/clusters/stream")
async def clusters_stream(request: Request) -> StreamingResponse:
    """Server-Sent Events com snapshot a cada 1 segundo.

    Cliente: const es = new EventSource('/api/v1/telemetry/clusters/stream');
             es.onmessage = e => console.log(JSON.parse(e.data));
    """
    async def event_stream() -> AsyncIterator[str]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                snap = _build_snapshot()
                yield f"data: {json.dumps(snap, default=str)}\n\n"
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
