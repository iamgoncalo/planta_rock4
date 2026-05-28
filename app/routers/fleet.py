"""
PlantaOS — Frota de sensores + fusao, com MODO sim/real e PROVENIENCIA.
  GET /api/v1/fleet?mode=sim|real        — sensores (sim da vida; real e carimbado)
  GET /api/v1/fleet/summary              — contagens
  GET /api/v1/fleet/mode                 — modo atual
  POST /api/v1/fleet/mode?mode=sim|real  — trocar modo (interruptor global)
  GET /api/v1/fusion/{cluster}?mode=...  — fusao (sim ou real carimbado)

Principio: simulado e SEMPRE rotulado; real so conta se um sensor enviou < ttl.
"""
from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException, Query

from app import sensors_registry as reg
from app.services import fusion as fus
from app.services import fleet_sim as sim

router = APIRouter(prefix="/api/v1", tags=["fleet"])

_BAT_USABLE_MAH = 17000.0
_MODE = {"mode": "sim"}  # default: simulacao (da vida a consola)


def _ttl() -> float:
    try:
        from app.config import get_settings
        return float(get_settings().real_data_ttl_s)
    except Exception:
        return 90.0


def _safe_cache():
    try:
        from app.services.mqtt_bridge import device_cache
        return device_cache
    except Exception:
        return {}


def _ingest():
    try:
        from app.services import ingest_store
        return ingest_store
    except Exception:
        return None


def _real_device_status(cluster_id, device_cache):
    if not cluster_id:
        return None, None
    cu = cluster_id.upper()
    cached = device_cache.get(cu, {})
    last_seen = cached.get("last_seen")
    if not last_seen:
        return None, None
    age = time.time() - last_seen
    st = "online" if age < 15 else "degraded" if age < 60 else "offline"
    return st, cached


def _battery_real(sensor, cached):
    prof = sensor.get("power_profile", {})
    if prof.get("battery") != "powerbank":
        return None
    if cached:
        status = cached.get("status", {}) or {}
        for k in ("battery_pct", "bateria", "batt"):
            if k in status:
                return {"pct": int(status[k]), "fonte": "real"}
        ma = prof.get("ma", 0) or 1
        uptime_h = float(status.get("uptime_s", 0)) / 3600.0
        pct = max(0, min(100, int(round((1 - uptime_h/(_BAT_USABLE_MAH/ma))*100))))
        return {"pct": pct, "fonte": "estimada"}
    return None


@router.get("/fleet")
async def get_fleet(mode: str = Query(default=None)):
    m = mode or _MODE["mode"]
    fleet = reg.build_fleet()
    out = []
    if m == "sim":
        t = time.time()
        for s in fleet:
            st, bat = sim.simulate_sensor_status(s, t)
            item = dict(s)
            item["status"] = st
            item["origem"] = "simulado"
            if bat is not None:
                item["battery"] = {"pct": bat, "fonte": "simulado"}
            out.append(item)
    else:  # real
        device_cache = _safe_cache()
        for s in fleet:
            st, cached = _real_device_status(s.get("cluster"), device_cache)
            item = dict(s)
            item["status"] = st or "planned"
            item["origem"] = "real" if st else "sem-dados"
            bat = _battery_real(s, cached)
            if bat:
                item["battery"] = bat
            out.append(item)
    return {"total": len(out), "ts": time.time(), "mode": m, "sensors": out}


@router.get("/fleet/summary")
async def get_fleet_summary():
    return reg.fleet_summary(reg.build_fleet())


@router.get("/fleet/mode")
async def get_mode():
    return {"mode": _MODE["mode"]}


@router.post("/fleet/mode")
async def set_mode(mode: str = Query(...)):
    if mode not in ("sim", "real"):
        raise HTTPException(400, "mode deve ser 'sim' ou 'real'")
    _MODE["mode"] = mode
    return {"mode": mode}


@router.get("/fusion/{cluster_id}")
async def get_fusion(cluster_id: str, mode: str = Query(default=None)):
    cid = cluster_id.lower()
    if cid not in reg.CLUSTER_CAP:
        raise HTTPException(404, f"cluster desconhecido: {cluster_id}")
    m = mode or _MODE["mode"]
    cap = reg.CLUSTER_CAP[cid]
    fleet = reg.build_fleet()
    sources = reg.fusion_sources(cid, fleet)

    cam = ir_in = ir_out = wifi = None
    data_source = "sem-dados"

    if m == "sim":
        p = sim.simulate_cluster_params(cid)
        cam = p["pessoas_estimadas"]
        wifi = p["telemoveis_detectados"]
        ir_in, ir_out = p["entradas_ir"], p["saidas_ir"]
        data_source = "simulado"
    else:  # real
        ist = _ingest()
        if ist:
            rec = ist.get(cid)
            fresh = ist.freshness(cid, _ttl())
            if rec and fresh == "real":
                p = rec.get("params", {})
                wifi = p.get("telemoveis_detectados")
                ir_in = p.get("entradas_ir")
                ir_out = p.get("saidas_ir")
                cam = p.get("pessoas_estimadas")
                data_source = "real"
            else:
                data_source = fresh  # stale | none

    result = fus.fuse_cluster(
        cap_inside=cap["m"] + cap["f"] if "m" in cap else cap["masc"] + cap["fem"],
        espera_max=cap.get("espera", cap.get("esp", 100)),
        sources_present=sources,
        camera_people=cam, ir_in=ir_in, ir_out=ir_out,
        wifi_devices=wifi,
        wifi_factor=1.8 if cap.get("unisex", cap.get("uni", False)) else 2.5,
    )
    result["cluster_id"] = cid
    result["mode"] = m
    result["data_source"] = data_source
    result["fontes_disponiveis"] = sources
    result["capacidade_dentro"] = cap["m"] + cap["f"] if "m" in cap else cap["masc"] + cap["fem"]
    return result
