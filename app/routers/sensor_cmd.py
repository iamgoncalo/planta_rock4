"""
PlantaOS — Router de comandos por sensor (/sensorctl) v2.
v2: reconhece TAMBEM sensores custom (de ambientes criados pelo staff). Se o id
nao esta no registry dos 78, infere o tipo pelo nome (lilygo/cam/ir/gateway/ap)
e responde a mesma — para que QUALQUER sensor adicionado responda a ping/diag.
"""
from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import sensor_commands
try:
    from app.sensors_registry import build_fleet
except Exception:
    build_fleet = None
try:
    from app.services import mqtt_bridge
except Exception:
    mqtt_bridge = None
try:
    from app.routers.fleet import _MODE
except Exception:
    _MODE = "sim"

router = APIRouter(prefix="/api/v1/sensorctl", tags=["sensorctl"])


class CmdIn(BaseModel):
    cmd: str
    value: float | None = None


def _infere_tipo(sid: str) -> str:
    s = sid.lower()
    if "lilygo" in s: return "lilygo"
    if "cam" in s: return "camera"
    if "ir" in s: return "ir"
    if "lora" in s or "gateway" in s: return "gateway_lora"
    if "wifi" in s or "ap-" in s or "-ap" in s: return "ap_wifi"
    return "lilygo"  # default razoavel


def _infere_cluster(sid: str) -> str | None:
    s = sid.lower()
    # wc-0X-... -> wc-0X
    import re
    m = re.match(r"(wc-\d{2})", s)
    return m.group(1) if m else None


def _find_sensor(sid: str) -> dict:
    """Procura no registry; se nao achar, cria um descritor inferido (custom)."""
    if build_fleet:
        for s in build_fleet():
            if s.get("id") == sid:
                return s
    # custom: inferir
    return {
        "id": sid, "tipo": _infere_tipo(sid),
        "cluster": _infere_cluster(sid), "role": "custom",
        "custom": True,
    }


def _current_mode() -> str:
    try:
        from app.routers.fleet import _MODE as m
        return m
    except Exception:
        return "sim"


@router.get("/{sensor_id}")
async def sensor_detail(sensor_id: str):
    s = _find_sensor(sensor_id)
    mode = _current_mode()
    t = time.time()
    from app.services.fleet_sim import sim_sensor_state
    st = sim_sensor_state(sensor_id, s.get("tipo",""), t) if mode == "sim" else {"status":"sem-dados","battery":None,"uptime_s":0,"rssi_dbm":0}
    out = dict(s)
    out["status"] = st["status"]
    out["uptime_s"] = st["uptime_s"]
    out["rssi_dbm"] = st["rssi_dbm"]
    if st.get("battery") is not None:
        out["battery"] = {"pct": st["battery"], "fonte": "simulado"}
    out["origem"] = "simulado" if mode == "sim" else "real"
    out["mode"] = mode
    return out


@router.post("/{sensor_id}/cmd")
async def sensor_cmd(sensor_id: str, body: CmdIn):
    s = _find_sensor(sensor_id)
    mode = _current_mode()
    if mode == "sim":
        return sensor_commands.simulate_command(
            sensor_id, s.get("tipo",""), s.get("cluster") or "wc-01",
            body.cmd, value=body.value)
    # real: enviar ao MQTT (cluster pai)
    if mqtt_bridge and s.get("cluster"):
        try:
            mqtt_bridge.send_command(s["cluster"], {"sensor": sensor_id, "cmd": body.cmd, "value": body.value})
            return {"sensor_id": sensor_id, "cmd": body.cmd, "mode": "real", "ok": True,
                    "resposta": f"comando '{body.cmd}' enviado ao gateway de {s['cluster']}"}
        except Exception as ex:
            return {"sensor_id": sensor_id, "cmd": body.cmd, "mode": "real", "ok": False,
                    "resposta": f"erro a enviar: {ex}"}
    return {"sensor_id": sensor_id, "cmd": body.cmd, "mode": "real", "ok": False,
            "resposta": "sem gateway associado para envio real"}


@router.get("/{sensor_id}/diagnostics")
async def sensor_diagnostics(sensor_id: str):
    s = _find_sensor(sensor_id)
    mode = _current_mode()
    if mode == "sim":
        return sensor_commands.simulate_command(
            sensor_id, s.get("tipo",""), s.get("cluster") or "wc-01",
            "diagnostics")
    return {"sensor_id": sensor_id, "mode": "real", "ok": False,
            "resposta": "diagnostico real disponivel apos ligacao do hardware"}
