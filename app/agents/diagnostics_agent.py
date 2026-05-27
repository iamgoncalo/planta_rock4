"""
PlantaOS — Diagnostics Agent
Runs a full system check across all 8 devices and reports issues.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Any

from app.services.mqtt_bridge import send_command, device_cache

CLUSTERS = ["WC-01", "WC-02", "WC-03", "WC-04",
            "WC-05", "WC-06", "WC-07", "WC-08"]


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


async def run_system_check(ws_send: Callable[[Any], None]) -> dict:
    """Run diagnostics on all 8 devices and aggregate issues."""
    results: dict[str, dict] = {}

    for cid in CLUSTERS:
        await send_command(cid, {"cmd": "diagnostics"})
        resp = await _wait_response(cid, 5.0)

        if resp:
            issues = []
            if (resp.get("rssi_dbm") or 0) < -80:
                issues.append("sinal fraco (rssi < -80dBm)")
            if (resp.get("heap_free") or 999_999) < 50_000:
                issues.append("memória baixa (heap < 50kB)")
            fw = resp.get("firmware_ver", "?")
            if fw != "6.0.0":
                issues.append(f"firmware desactualizado ({fw})")
            results[cid] = {"status": "ok", "issues": issues, "data": resp}
        else:
            results[cid] = {"status": "offline", "issues": ["sem resposta"]}

        ws_send({"type": "agent_check", "cluster_id": cid, "result": results[cid]})
        await asyncio.sleep(0.3)

    offline  = [c for c, r in results.items() if r["status"] == "offline"]
    degraded = [c for c, r in results.items() if r.get("issues")]
    ws_send({
        "type":     "agent_done",
        "offline":  offline,
        "degraded": degraded,
        "summary":  f"{len(CLUSTERS) - len(offline)}/8 online · {len(degraded)} com problemas",
    })
    return results
