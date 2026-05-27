"""
PlantaOS — Onboarding Agent
Guided step-by-step setup for a new LilyGo device.
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


async def onboard_device(cluster_id: str, ws_send: Callable[[Any], None]) -> dict:
    """
    Step-by-step onboarding.
    ws_send receives progress dicts that can be forwarded to a WebSocket client.
    """
    steps = [
        ({"cmd": "ping"},                            "A verificar resposta do device…"),
        ({"cmd": "diagnostics"},                     "A obter info do device…"),
        ({"cmd": "get_status"},                      "A ler sensores…"),
        ({"cmd": "stream_serial", "enable": True},   "A activar serial stream…"),
    ]

    for cmd_payload, desc in steps:
        ws_send({"type": "agent_step", "step": desc})
        await send_command(cluster_id, cmd_payload)
        resp = await _wait_response(cluster_id, 5.0)
        if not resp:
            ws_send({"type": "agent_error", "msg": f"Sem resposta em: {desc}"})
            return {"success": False, "step": desc}
        ws_send({"type": "agent_step_ok", "step": desc, "data": resp})
        await asyncio.sleep(0.2)

    ws_send({"type": "agent_done", "msg": f"{cluster_id} onboarded com sucesso"})
    return {"success": True, "cluster_id": cluster_id}
