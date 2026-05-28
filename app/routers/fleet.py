"""
PlantaOS — Router da frota v4.
Em SIM: TUDO enriquecido pelo simulador (ignora status 'planned' do registry —
em simulacao todos os sensores estao "presentes"). Em REAL: respeita planned
(sensores fisicamente nao instalados ficam 'planned'). Bateria sempre presente
em lilygos e cameras em sim. Inclui /fleet, /fleet/summary, /fleet/mode.
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


def _enriquece_sim(s: dict, t: float) -> dict:
    st = fleet_sim.sim_sensor_state(s["id"], s.get("tipo",""), t)
    s["status"] = st["status"]
    s["uptime_s"] = st["uptime_s"]
    s["rssi_dbm"] = st["rssi_dbm"]
    if st["battery"] is not None:
        s["battery"] = {"pct": st["battery"], "fonte": "simulado"}
    s["origem"] = "simulado"
    return s


def _enriquece_real(s: dict, t: float) -> dict:
    s["origem"] = "real"
    # planned -> mantem (real nao tem dados)
    if s.get("status") == "planned":
        return s
    if not ingest_store:
        s["status"] = "sem-dados"; return s
    rec = ingest_store.get(s["id"])
    if not rec:
        s["status"] = "sem-dados"
        return s
    age = t - rec.get("ts_server", 0)
    if age < 15: s["status"] = "online"
    elif age < 60: s["status"] = "degraded"
    else: s["status"] = "offline"
    s["age_s"] = round(age, 1)
    return s


@router.get("/fleet")
async def get_fleet(mode: str = Query(default=None)):
    m = mode if mode in ("sim","real") else _MODE
    t = time.time()
    raw = build_fleet()
    out = []
    for s in raw:
        item = dict(s)
        item["mode"] = m
        if m == "sim":
            # SIM: ignora "planned", tudo passa pelo simulador
            _enriquece_sim(item, t)
        else:
            _enriquece_real(item, t)
        out.append(item)
    return {"sensors": out, "mode": m, "ts": t, "total": len(out)}


@router.get("/fleet/summary")
async def fleet_summary(mode: str = Query(default=None)):
    data = await get_fleet(mode=mode)
    s = data["sensors"]
    statuses = Counter(x.get("status","desconhecido") for x in s)
    bats = [x["battery"]["pct"] for x in s if x.get("battery")]
    by_cluster = {}
    for x in s:
        c = x.get("cluster") or "—"
        by_cluster.setdefault(c, {"total":0,"online":0})
        by_cluster[c]["total"] += 1
        if x.get("status") == "online":
            by_cluster[c]["online"] += 1
    return {
        "total": len(s),
        "status": dict(statuses),
        "battery_avg_pct": round(sum(bats)/len(bats), 1) if bats else None,
        "battery_n": len(bats),
        "by_cluster": by_cluster,
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
