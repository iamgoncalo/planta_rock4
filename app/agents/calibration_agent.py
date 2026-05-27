"""
PlantaOS — Calibration Agent
Guided IR calibration: count real people → compute factor → apply to device.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Any

from app.services.mqtt_bridge import send_command, device_cache


async def _wait_response(cluster_id: str, timeout_s: float = 5.0) -> dict | None:
    deadline = asyncio.get_running_loop().time() + timeout_s
    if cluster_id in device_cache:
        device_cache[cluster_id].pop("response", None)
    while asyncio.get_running_loop().time() < deadline:
        resp = device_cache.get(cluster_id, {}).get("response")
        if resp:
            return resp
        await asyncio.sleep(0.1)
    return None


async def run_calibration(
    cluster_id: str,
    real_count: int,
    ws_send: Callable[[Any], None],
) -> dict:
    """
    1. Reset counters on device.
    2. User walks real_count people through the sensors.
    3. Get diagnostics to read IR count.
    4. Compute factor = real_count / ir_count.
    5. Apply to device.
    """
    ws_send({"type": "agent_msg", "msg": "A fazer reset dos contadores…"})
    await send_command(cluster_id, {"cmd": "reset_counters"})
    await asyncio.sleep(0.5)

    ws_send({
        "type": "agent_msg",
        "msg": (f"Contadores reset. Passa {real_count} pessoas pelos sensores IR "
                f"e depois chama POST /agents/calibrate/{cluster_id}?confirm=true"),
    })

    # Get current IR count via diagnostics
    await send_command(cluster_id, {"cmd": "diagnostics"})
    resp = await _wait_response(cluster_id, 5.0)
    ir_count = resp.get("entradas", 0) if resp else 0

    if ir_count == 0:
        msg = "Nenhum evento IR detectado — verificar ligação dos sensores"
        ws_send({"type": "agent_error", "msg": msg})
        return {"error": msg}

    factor = round(real_count / ir_count, 3)
    ws_send({
        "type": "agent_msg",
        "msg": f"Real: {real_count} · IR: {ir_count} · Factor: {factor}",
    })

    await send_command(cluster_id, {"cmd": "calibrate_ir", "factor": factor})
    resp2 = await _wait_response(cluster_id, 5.0)

    ws_send({
        "type": "agent_done",
        "msg": f"Calibração aplicada: ir_cal={factor}",
        "factor": factor,
    })
    return {"success": True, "factor": factor, "real": real_count, "ir_count": ir_count}
