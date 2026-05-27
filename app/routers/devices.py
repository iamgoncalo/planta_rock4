"""
PlantaOS RIR 2026 — Device Control API
All command endpoints route through MQTT to physical hardware.
Terminal WebSocket provides real-time bidirectional control.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import get_settings
from app.services.mqtt_bridge import (
    broadcast_command,
    device_cache,
    get_all_device_statuses,
    get_device_status,
    send_command,
    subscribe,
    unsubscribe,
)

log = logging.getLogger("devices")
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

CLUSTERS = ["WC-01", "WC-02", "WC-03", "WC-04",
            "WC-05", "WC-06", "WC-07", "WC-08"]


# ── Pydantic input ─────────────────────────────────────────────────────────

class Command(BaseModel):
    cmd:    str
    value:  Optional[float] = None
    url:    Optional[str]   = None
    enable: Optional[bool]  = None
    factor: Optional[float] = None


# ── Helpers ────────────────────────────────────────────────────────────────

async def wait_for_response(cluster_id: str, timeout_s: float = 5.0) -> Optional[dict]:
    """Wait up to timeout_s for a /response message from the device."""
    # Clear stale cached response before waiting
    if cluster_id in device_cache:
        device_cache[cluster_id].pop("response", None)

    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        resp = device_cache.get(cluster_id, {}).get("response")
        if resp:
            return resp
        await asyncio.sleep(0.1)
    return None


# ── Status endpoints ───────────────────────────────────────────────────────

@router.get("")
async def list_devices():
    return {"devices": get_all_device_statuses(), "ts": time.time()}


@router.get("/firmware/latest")
async def firmware_info():
    settings = get_settings()
    return {
        "latest": "6.0.0",
        "download_url": f"{settings.public_url}/api/v1/devices/firmware/rockinrio_v6.bin",
        "changelog": "Bidirectional MQTT, OTA, serial streaming, NVS config",
    }


@router.get("/firmware/{filename}")
async def serve_firmware(filename: str):
    path = f"firmware/{filename}"
    if not os.path.exists(path):
        raise HTTPException(404, f"Firmware file not found: {filename}")
    return FileResponse(path, media_type="application/octet-stream")


@router.get("/{cluster_id}/cache")
async def get_device_cache(cluster_id: str):
    return device_cache.get(cluster_id.upper(), {})


@router.get("/{cluster_id}")
async def get_device(cluster_id: str):
    return get_device_status(cluster_id.upper())


# ── Command endpoints ──────────────────────────────────────────────────────

@router.post("/{cluster_id}/cmd")
async def send_device_command(cluster_id: str, command: Command):
    payload = command.model_dump(exclude_none=True)
    ok = await send_command(cluster_id.upper(), payload)
    if not ok:
        raise HTTPException(503, "Failed to reach MQTT broker")
    return {"sent": True, "cluster_id": cluster_id.upper(), "cmd": payload}


@router.post("/{cluster_id}/ping")
async def ping_device(cluster_id: str):
    cid = cluster_id.upper()
    ok = await send_command(cid, {"cmd": "ping"})
    return {"sent": ok, "cluster_id": cid}


@router.post("/{cluster_id}/restart")
async def restart_device(cluster_id: str):
    ok = await send_command(cluster_id.upper(), {"cmd": "restart"})
    return {"sent": ok, "cluster_id": cluster_id.upper()}


@router.post("/{cluster_id}/diagnostics")
async def diagnostics(cluster_id: str):
    cid = cluster_id.upper()
    ok = await send_command(cid, {"cmd": "diagnostics"})
    return {"sent": ok, "cluster_id": cid}


@router.post("/{cluster_id}/reset-counters")
async def reset_counters(cluster_id: str):
    ok = await send_command(cluster_id.upper(), {"cmd": "reset_counters"})
    return {"sent": ok}


@router.post("/{cluster_id}/ota")
async def ota_update(cluster_id: str, url: str):
    ok = await send_command(cluster_id.upper(), {"cmd": "ota", "url": url})
    return {"sent": ok, "url": url}


@router.post("/broadcast")
async def broadcast_all(command: Command):
    payload = command.model_dump(exclude_none=True)
    ok = await broadcast_command(payload)
    return {"sent": ok, "cmd": payload, "targets": "all"}


# ── Agent endpoints ────────────────────────────────────────────────────────

@router.post("/agents/onboard/{cluster_id}")
async def agent_onboard(cluster_id: str):
    from app.agents.onboarding_agent import onboard_device
    result = await onboard_device(cluster_id.upper(), lambda m: None)
    return result


@router.post("/agents/calibrate/{cluster_id}")
async def agent_calibrate(cluster_id: str, real_count: int = 20):
    from app.agents.calibration_agent import run_calibration
    result = await run_calibration(cluster_id.upper(), real_count, lambda m: None)
    return result


@router.post("/agents/system-check")
async def agent_system_check():
    from app.agents.diagnostics_agent import run_system_check
    result = await run_system_check(lambda m: None)
    return result


@router.post("/agents/ota-all")
async def agent_ota_all(url: str):
    from app.agents.ota_agent import update_all_firmware
    asyncio.create_task(update_all_firmware(url, lambda m: None))
    return {"started": True, "url": url}


# ── Terminal WebSocket ─────────────────────────────────────────────────────

TERMINAL_HELP = """PlantaOS Device Terminal v2
Commands reach physical hardware via MQTT.

  scan                           List all devices currently online
  status [WC-01|all]             Device health + last seen
  ping <WC-01>                   Ping device, wait for pong
  diagnostics <WC-01>            Full device diagnostics
  serial <WC-01> [on|off]        Start/stop serial stream
  set <WC-01> wifi_factor <n>    Update wifi_factor on device
  set <WC-01> post_interval <n>  Update telemetry interval (ms)
  set <WC-01> dir_window <n>     Update IR direction window (ms)
  calibrate <WC-01> <factor>     Set IR calibration factor
  reset <WC-01>                  Reset IR entry/exit counters
  restart <WC-01>                Restart device (reboots ESP32)
  flash <WC-01> [url]            OTA update to latest firmware
  broadcast <json>               Send command to ALL 8 devices
  events <WC-01>                 Show last cached IR events
  cache <WC-01>                  Raw MQTT cache for device
  clear                          Clear terminal
  help                           Show this help"""


async def _execute(cmd_str: str) -> str:
    parts = cmd_str.strip().split()
    if not parts:
        return ""
    verb = parts[0].lower()

    if verb == "help":
        return TERMINAL_HELP

    elif verb == "clear":
        return "\x1b[2J\x1b[H"

    elif verb == "scan":
        devs  = get_all_device_statuses()
        lines = ["Scanning devices…", ""]
        for d in devs:
            st  = d.get("status", "unknown")
            dot = ("\x1b[32m●\x1b[0m" if st == "online"
                   else "\x1b[33m◐\x1b[0m" if st == "degraded"
                   else "\x1b[90m○\x1b[0m")
            age = f"há {d.get('age_s', 0)}s" if d.get("age_s") is not None else "nunca visto"
            fw  = d.get("firmware_ver", "?")
            ip  = d.get("ip", "?")
            lines.append(f"  {dot} {d['cluster_id']:<8} {st:<10} {age:<14} fw={fw}  ip={ip}")
        online = sum(1 for d in devs if d.get("status") == "online")
        lines.append(f"\n{online}/8 devices online")
        return "\n".join(lines)

    elif verb == "status":
        target = parts[1].upper() if len(parts) > 1 else "ALL"
        if target == "ALL":
            devs  = get_all_device_statuses()
            lines = [f"  {d['cluster_id']}: {d.get('status','?')} · age={d.get('age_s','?')}s"
                     for d in devs]
            return "\n".join(lines)
        return json.dumps(get_device_status(target), indent=2)

    elif verb == "ping":
        if len(parts) < 2:
            return "Usage: ping <WC-01>"
        cid = parts[1].upper()
        await send_command(cid, {"cmd": "ping"})
        resp = await wait_for_response(cid, 5.0)
        if resp:
            return (f"✓ {cid}: pong · uptime={resp.get('uptime_s','?')}s"
                    f" · ip={resp.get('ip','?')} · rssi={resp.get('rssi_dbm','?')}dBm"
                    f" · fw={resp.get('firmware','?')}")
        return f"✗ {cid}: timeout (5s) — device offline or not reachable"

    elif verb == "diagnostics":
        if len(parts) < 2:
            return "Usage: diagnostics <WC-01>"
        cid = parts[1].upper()
        await send_command(cid, {"cmd": "diagnostics"})
        resp = await wait_for_response(cid, 5.0)
        return json.dumps(resp, indent=2) if resp else f"Timeout: {cid} not responding"

    elif verb == "serial":
        if len(parts) < 2:
            return "Usage: serial <WC-01> [on|off]"
        cid    = parts[1].upper()
        enable = len(parts) < 3 or parts[2].lower() != "off"
        await send_command(cid, {"cmd": "stream_serial", "enable": enable})
        state = "iniciado" if enable else "parado"
        return (f"Serial stream {state} para {cid}\n"
                f"Output aparece em tempo real etiquetado [SERIAL:{cid}]")

    elif verb == "set":
        if len(parts) < 4:
            return "Usage: set <WC-01> <param> <value>"
        cid, param, val = parts[1].upper(), parts[2].lower(), parts[3]
        cmd_map = {
            "wifi_factor":   ("set_wifi_factor",     float),
            "post_interval": ("set_post_interval",   int),
            "dir_window":    ("set_direction_window", int),
            "cluster_id":    ("set_cluster_id",       str),
        }
        if param not in cmd_map:
            return f"Param desconhecido '{param}'. Válidos: {', '.join(cmd_map)}"
        cmd_name, typ = cmd_map[param]
        try:
            typed_val = typ(val)
        except ValueError:
            return f"Valor inválido '{val}' para {param} (esperado {typ.__name__})"
        await send_command(cid, {"cmd": cmd_name, "value": typed_val})
        resp = await wait_for_response(cid, 5.0)
        if resp:
            return (f"✓ {cid}: {param} actualizado"
                    f" · prev={resp.get('prev','?')} → now={resp.get('now', typed_val)}")
        return "Comando enviado (sem confirmação — device pode estar offline)"

    elif verb == "calibrate":
        if len(parts) < 3:
            return ("Usage: calibrate <WC-01> <factor>\n"
                    "  factor=1.0  → sem correcção\n"
                    "  factor=0.94 → multiplica todos os IR counts por 0.94\n"
                    "  Dica: contar 20 pessoas manualmente → factor=20/ir_count")
        cid    = parts[1].upper()
        factor = float(parts[2])
        await send_command(cid, {"cmd": "calibrate_ir", "factor": factor})
        resp = await wait_for_response(cid, 5.0)
        if resp:
            return f"✓ {cid}: IR cal set · prev={resp.get('prev','?')} → {resp.get('now', factor)}"
        return "Comando enviado (sem confirmação)"

    elif verb == "reset":
        if len(parts) < 2:
            return "Usage: reset <WC-01>"
        cid = parts[1].upper()
        await send_command(cid, {"cmd": "reset_counters"})
        return f"✓ Contadores reset para {cid}"

    elif verb == "restart":
        if len(parts) < 2:
            return "Usage: restart <WC-01>"
        cid = parts[1].upper()
        await send_command(cid, {"cmd": "restart"})
        return f"Restart enviado a {cid} · device vai reiniciar em ~1s"

    elif verb == "flash":
        if len(parts) < 2:
            return "Usage: flash <WC-01> [url]"
        cid = parts[1].upper()
        settings = get_settings()
        url = (parts[2] if len(parts) > 2
               else f"{settings.public_url}/api/v1/devices/firmware/rockinrio_v6.bin")
        await send_command(cid, {"cmd": "ota", "url": url})
        return (f"OTA update iniciado para {cid}\n"
                f"  URL: {url}\n"
                f"  Device vai descarregar, verificar, e reiniciar (~30s).\n"
                f"  Monitoriza com: status {cid}")

    elif verb == "broadcast":
        if len(parts) < 2:
            return "Usage: broadcast <json>\nExemplo: broadcast {\"cmd\":\"ping\"}"
        try:
            cmd_obj = json.loads(" ".join(parts[1:]))
            await broadcast_command(cmd_obj)
            return f"Broadcast enviado a todos os 8 devices: {cmd_obj}"
        except json.JSONDecodeError:
            return "Erro: JSON inválido. Exemplo: broadcast {\"cmd\":\"ping\"}"

    elif verb == "events":
        if len(parts) < 2:
            return "Usage: events <WC-01>"
        cid    = parts[1].upper()
        cached = device_cache.get(cid, {})
        if not cached:
            return f"Sem dados em cache para {cid} — device online?"
        return json.dumps({
            "event":  cached.get("event"),
            "status": cached.get("status"),
        }, indent=2)

    elif verb == "cache":
        if len(parts) < 2:
            return "Usage: cache <WC-01>"
        cid = parts[1].upper()
        return json.dumps(device_cache.get(cid, {}), indent=2, default=str)

    else:
        return f"Comando desconhecido: '{verb}'. Escreve 'help' para ver comandos."


@router.websocket("/terminal")
async def device_terminal(ws: WebSocket) -> None:
    """
    Real device control terminal.
    Pings go to physical hardware via MQTT.
    Serial stream output from devices appears in real-time.
    """
    await ws.accept()
    session_id = str(uuid.uuid4())[:8]
    mqtt_q     = subscribe()

    await ws.send_text(json.dumps({
        "type":   "welcome",
        "output": (
            "\x1b[32mPlantaOS Device Terminal v2\x1b[0m\n"
            "Os comandos chegam ao hardware físico via MQTT.\n"
            "Escreve \x1b[33mhelp\x1b[0m para ver comandos disponíveis.\n\n"
            f"\x1b[90mSessão: {session_id}\x1b[0m\n$ "
        ),
    }))

    async def serial_forwarder() -> None:
        """Forward device serial stream messages to this terminal in real-time."""
        while True:
            try:
                msg = await asyncio.wait_for(mqtt_q.get(), timeout=30.0)
                if msg.get("channel") == "serial" and msg.get("cluster_id"):
                    cid    = msg["cluster_id"]
                    line   = msg["payload"] if isinstance(msg["payload"], str) else json.dumps(msg["payload"])
                    await ws.send_text(json.dumps({
                        "type":   "serial",
                        "output": f"\n\x1b[90m[SERIAL:{cid}]\x1b[0m {line}\n$ ",
                    }))
            except asyncio.TimeoutError:
                pass
            except Exception:
                return

    forwarder = asyncio.create_task(serial_forwarder())

    try:
        while True:
            raw  = await ws.receive_text()
            data = json.loads(raw)
            cmd  = data.get("command", "").strip()

            if not cmd:
                await ws.send_text(json.dumps({"type": "prompt", "output": "$ "}))
                continue

            output = await _execute(cmd)
            await ws.send_text(json.dumps({
                "type":    "output",
                "command": cmd,
                "output":  output + "\n\n$ ",
            }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("terminal.error session=%s err=%s", session_id, e)
    finally:
        forwarder.cancel()
        unsubscribe(mqtt_q)
