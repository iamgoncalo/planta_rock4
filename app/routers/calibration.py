"""
PlantaOS — Calibração por nó WiFi (fusão rolante).

GET  /api/v1/calibration             — todos os nós (k, rssi_1m, threshold_dbm)
PUT  /api/v1/calibration/{node_id}   — actualiza k / rssi_1m / threshold_dbm

Persistência em Postgres (tabela node_calibration) best-effort — a memória é
sempre a fonte ao vivo, com seed k=1.0 para todos os nós da topologia.
Erros sempre em JSON, nunca 500/HTML.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import node_calibration

router = APIRouter(prefix="/api/v1", tags=["calibration"])


class CalibrationUpdate(BaseModel):
    """Campos editáveis de um nó. Todos opcionais — actualiza só o que vier."""
    k: Optional[float] = Field(default=None, gt=0.0, le=20.0)
    rssi_1m: Optional[float] = Field(default=None, ge=-100.0, le=0.0)
    threshold_dbm: Optional[float] = Field(default=None, ge=-70.0, le=0.0)
    # ZONA_B vive entre -70 dBm e o threshold — abaixo de -70 é descartado


@router.get("/calibration")
async def get_calibration():
    """Tabela de calibração completa (seed k=1.0 para todos os nós)."""
    nodes = node_calibration.get_all()
    return {"total": len(nodes), "nodes": nodes}


@router.get("/calibration/{node_id}")
async def get_calibration_node(node_id: str):
    rec = node_calibration.get_node(node_id)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"nó desconhecido: {node_id!r}")
    return rec


@router.put("/calibration/{node_id}")
async def put_calibration(node_id: str, body: CalibrationUpdate):
    """Actualiza a calibração de um nó. Persiste em Postgres (best-effort)."""
    rec = node_calibration.update_node(
        node_id, k=body.k, rssi_1m=body.rssi_1m, threshold_dbm=body.threshold_dbm,
    )
    if rec is None:
        raise HTTPException(status_code=404, detail=f"nó desconhecido: {node_id!r}")

    # Persistência best-effort — nunca derruba o pedido
    try:
        from app.db import AsyncSessionLocal
        if AsyncSessionLocal is not None:
            await node_calibration.persist_node(AsyncSessionLocal, node_id)
    except Exception:
        pass

    return {"ok": True, "node": rec}
