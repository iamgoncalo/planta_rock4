"""
PlantaOS — Router da frota v5. DISTINCAO HONESTA real vs simulado.
U3 audit: lê de ingest_store (dados reais) com fallback fleet_sim. Fonte única ✅
Cada sensor decide a sua origem SOZINHO:
  - 'real-vivo'  : ha pacote no ingest_store ha <15s (dado verdadeiro)
  - 'real-mudo'  : devia transmitir mas nao ha pacote (>60s ou nunca) — em modo real
  - 'simulado'   : nao ha pacote real E o ambiente esta em modo sim
HIBRIDO: mesmo em modo 'sim', se um sensor real transmitir, aparece como REAL
no meio dos simulados. Nunca finge que um simulado e real.
"""
from __future__ import annotations
import time
from collections import Counter
from fastapi import APIRouter, Query

from app.sensors_registry import build_fleet
from app.services import fleet_sim
try:
    from app.services import ingest_store
except Exception:
    ingest_store = None

router = APIRouter(prefix="/api/v1", tags=["fleet"])
_MODE = "sim"

REAL_VIVO_S = 15    # transmitiu ha menos disto = vivo
REAL_MUDO_S = 60    # entre vivo e isto = instavel; acima = mudo


def _ingest_age(sid: str, t: float):
    """Idade do ultimo pacote real, ou None se nunca houve."""
    if not ingest_store:
        return None
    rec = ingest_store.get(sid)
    if not rec:
        return None
    return t - rec.get("ts_server", 0)


def _decide(s: dict, mode: str, t: float) -> dict:
    """Decide origem e estado de UM sensor, honestamente."""
    sid = s["id"]
    age = _ingest_age(sid, t)

    # 1) Ha dado real recente? -> REAL (independente do modo)
    if age is not None and age <= REAL_MUDO_S:
        s["data_origin"] = "real"
        s["status"] = "online" if age <= REAL_VIVO_S else "degraded"
        s["age_s"] = round(age, 1)
        s["origem"] = "real"
        # nao mexe nos valores — vem do ingest noutro sitio
        return s

    # 2) Sem dado real. Conforme o modo do ambiente:
    if mode == "real":
        # devia ser real mas esta mudo
        s["data_origin"] = "real-mudo"
        s["status"] = "sem-dados"
        s["origem"] = "real"
        if age is not None:
            s["age_s"] = round(age, 1)
        return s

    # 3) modo sim -> simulado honesto
    st = fleet_sim.sim_sensor_state(sid, s.get("tipo",""), t)
    s["data_origin"] = "simulado"
    s["status"] = st["status"]
    s["uptime_s"] = st["uptime_s"]
    s["rssi_dbm"] = st["rssi_dbm"]
    if st["battery"] is not None:
        s["battery"] = {"pct": st["battery"], "fonte": "simulado"}
    s["origem"] = "simulado"
    return s


@router.get("/fleet")
async def get_fleet(mode: str = Query(default=None)):
    m = mode if mode in ("sim","real") else _MODE
    t = time.time()
    raw = build_fleet()
    out = [_decide(dict(s), m, t) for s in raw]
    # contagem honesta
    origem = Counter(x.get("data_origin","?") for x in out)
    return {"sensors": out, "mode": m, "ts": t, "total": len(out),
            "reais": origem.get("real", 0),
            "simulados": origem.get("simulado", 0),
            "reais_mudos": origem.get("real-mudo", 0)}


@router.get("/fleet/summary")
async def fleet_summary(mode: str = Query(default=None)):
    data = await get_fleet(mode=mode)
    s = data["sensors"]
    statuses = Counter(x.get("status","desconhecido") for x in s)
    origens = Counter(x.get("data_origin","?") for x in s)
    bats = [x["battery"]["pct"] for x in s if x.get("battery")]
    return {
        "total": len(s),
        "status": dict(statuses),
        "origem": dict(origens),
        "reais": origens.get("real", 0),
        "simulados": origens.get("simulado", 0),
        "reais_mudos": origens.get("real-mudo", 0),
        "battery_avg_pct": round(sum(bats)/len(bats), 1) if bats else None,
        "mode": data["mode"],
        "ts": data["ts"],
    }


@router.get("/fleet/mode")
async def get_mode():
    return {"mode": _MODE}


@router.post("/fleet/mode")
async def set_mode(mode: str = Query(...)):
    global _MODE
    if mode in ("sim","real"):
        _MODE = mode
    return {"mode": _MODE}
