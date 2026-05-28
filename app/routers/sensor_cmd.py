"""
PlantaOS — Comandos e detalhe por SENSOR INDIVIDUAL.
  GET  /api/v1/sensors/{sensor_id}            — detalhe (sim ou real)
  POST /api/v1/sensors/{sensor_id}/cmd        — comando (sim: resposta coerente; real: MQTT)
  GET  /api/v1/sensors/{sensor_id}/diagnostics — atalho de diagnostico

SIM  -> sensor_commands.simulate_command (resposta realista, coerente com estado).
REAL -> traduz para o cluster pai e usa send_command (MQTT) + espera resposta.
"""
from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import sensors_registry as reg
from app.services import sensor_commands as sc

router = APIRouter(prefix="/api/v1/sensorctl", tags=["sensor-commands"])


def _find_sensor(sensor_id: str) -> dict | None:
    for s in reg.build_fleet():
        if s["id"] == sensor_id:
            return s
    return None


def _mode() -> str:
    try:
        from app.routers.fleet import _MODE
        return _MODE.get("mode", "sim")
    except Exception:
        return "sim"


class CmdIn(BaseModel):
    cmd: str
    value: float | None = None
    mode: str | None = None


@router.get("/{sensor_id}")
async def sensor_detail(sensor_id: str):
    s = _find_sensor(sensor_id)
    if not s:
        raise HTTPException(404, f"sensor desconhecido: {sensor_id}")
    mode = _mode()
    out = dict(s)
    if mode == "sim":
        state = sc.sim_sensor_state(sensor_id, s["tipo"])
        out["status"] = state["status"]
        out["uptime_s"] = state["uptime_s"]
        out["rssi_dbm"] = state["rssi_dbm"]
        if state["battery"] is not None:
            out["battery"] = {"pct": state["battery"], "fonte": "simulado"}
        out["origem"] = "simulado"
    else:
        # real: estado do device_cache do cluster pai
        out["origem"] = "real"
        try:
            from app.services.mqtt_bridge import device_cache
            cu = (s.get("cluster") or "").upper()
            cached = device_cache.get(cu, {})
            last_seen = cached.get("last_seen")
            if last_seen:
                age = time.time() - last_seen
                out["status"] = "online" if age < 15 else "degraded" if age < 60 else "offline"
            else:
                out["status"] = "sem-dados"
        except Exception:
            out["status"] = "sem-dados"
    out["mode"] = mode
    return out


@router.post("/{sensor_id}/cmd")
async def sensor_cmd(sensor_id: str, body: CmdIn):
    s = _find_sensor(sensor_id)
    if not s:
        raise HTTPException(404, f"sensor desconhecido: {sensor_id}")
    mode = body.mode or _mode()
    cluster = s.get("cluster") or ""

    if mode == "sim":
        return sc.simulate_command(sensor_id, s["tipo"], cluster, body.cmd, value=body.value)

    # REAL: traduz para o cluster pai (o LilyGo tem o radio)
    try:
        from app.services.mqtt_bridge import send_command
        cu = cluster.upper()
        payload = {"cmd": body.cmd, "sensor": sensor_id}
        if body.value is not None:
            payload["value"] = body.value
        ok = await send_command(cu, payload)
        return {"sensor_id": sensor_id, "cmd": body.cmd, "mode": "real",
                "ok": ok, "resposta": "comando enviado ao MQTT" if ok else "MQTT inacessível",
                "nota": "resposta do hardware chega de forma assíncrona via cache"}
    except Exception as e:
        return {"sensor_id": sensor_id, "cmd": body.cmd, "mode": "real",
                "ok": False, "resposta": f"erro: {e}"}


@router.get("/{sensor_id}/diagnostics")
async def sensor_diag(sensor_id: str):
    s = _find_sensor(sensor_id)
    if not s:
        raise HTTPException(404, f"sensor desconhecido: {sensor_id}")
    mode = _mode()
    if mode == "sim":
        return sc.simulate_command(sensor_id, s["tipo"], s.get("cluster") or "", "diagnostics")
    return {"sensor_id": sensor_id, "mode": "real", "ok": False,
            "resposta": "em modo real, usa o terminal ou aguarda telemetria do hardware"}
