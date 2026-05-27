"""
PlantaOS — OTA Agent
Mass firmware update — flashes devices one by one and tracks progress.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Any

from app.services.mqtt_bridge import send_command, get_device_status

CLUSTERS = ["WC-01", "WC-02", "WC-03", "WC-04",
            "WC-05", "WC-06", "WC-07", "WC-08"]

OTA_REBOOT_WAIT_S = 35  # device downloads + flashes + reboots


async def update_all_firmware(url: str, ws_send: Callable[[Any], None]) -> dict:
    """
    Flash all devices sequentially.
    After sending OTA command the device reboots automatically (~30s).
    We wait OTA_REBOOT_WAIT_S then check if it's back online.
    """
    results: dict[str, dict] = {}

    for cid in CLUSTERS:
        ws_send({"type": "ota_start", "cluster_id": cid, "url": url})
        await send_command(cid, {"cmd": "ota", "url": url})

        # Device reboots during this window
        await asyncio.sleep(OTA_REBOOT_WAIT_S)

        status = get_device_status(cid)
        result = {
            "status": status.get("status"),
            "firmware_ver": status.get("firmware_ver", "?"),
            "age_s": status.get("age_s"),
        }
        results[cid] = result
        ws_send({"type": "ota_result", "cluster_id": cid, **result})

    ok_count = sum(1 for r in results.values() if r.get("status") == "online")
    ws_send({
        "type":    "ota_complete",
        "updated": ok_count,
        "total":   len(CLUSTERS),
    })
    return results
