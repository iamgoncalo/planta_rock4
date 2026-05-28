"""
PlantaOS — Frota de sensores + fusao. Endpoints de leitura.
  GET /api/v1/fleet            — todos os sensores com estado + bateria estimada
  GET /api/v1/fleet/summary    — contagens por tipo e por cluster
  GET /api/v1/fusion/{cluster} — calculo de fusao ao vivo para um cluster
Estado: deriva do device_cache (MQTT) quando ha; senao 'planned'.
Bateria: estimada pela curva da powerbank (Anker 20Ah) + uptime, ate o device reportar.
"""
from __future__ import annotations
import time
from fastapi import APIRouter, HTTPException

from app import sensors_registry as reg
from app.services import fusion as fus

router = APIRouter(prefix="/api/v1", tags=["fleet"])

# Anker Zolo 20Ah: ~17000 mAh uteis @5V
_BAT_USABLE_MAH = 17000.0


def _device_status(cluster_id, device_cache):
    """Estado real do LilyGo do cluster a partir do device_cache (MQTT)."""
    if not cluster_id:
        return None, None
    cu = cluster_id.upper()
    cached = device_cache.get(cu, {})
    last_seen = cached.get("last_seen")
    if not last_seen:
        return None, None
    age = time.time() - last_seen
    if age < 15:
        st = "online"
    elif age < 60:
        st = "degraded"
    else:
        st = "offline"
    return st, cached


def _battery_pct(sensor, cached):
    """Bateria: real se o device reportar; senao estimada pela curva + uptime."""
    prof = sensor.get("power_profile", {})
    if prof.get("battery") not in ("powerbank",):
        return None  # eletrico/poe/mains nao tem bateria
    # 1) real do device?
    if cached:
        status = cached.get("status", {}) or {}
        for k in ("battery_pct", "bateria", "batt"):
            if k in status:
                return {"pct": int(status[k]), "fonte": "real"}
    # 2) estimada: uptime vs autonomia do perfil
    ma = prof.get("ma", 0) or 1
    autonomia_h = _BAT_USABLE_MAH / ma
    uptime_h = 0.0
    if cached:
        status = cached.get("status", {}) or {}
        uptime_h = float(status.get("uptime_s", 0)) / 3600.0
    pct = max(0, min(100, int(round((1 - uptime_h / autonomia_h) * 100))))
    return {"pct": pct, "fonte": "estimada", "autonomia_h": round(autonomia_h)}


def _safe_cache():
    try:
        from app.services.mqtt_bridge import device_cache
        return device_cache
    except Exception:
        return {}


@router.get("/fleet")
async def get_fleet():
    fleet = reg.build_fleet()
    device_cache = _safe_cache()
    out = []
    for s in fleet:
        st, cached = _device_status(s.get("cluster"), device_cache)
        # IR herda do LilyGo pai
        if s["tipo"] == "ir" and s.get("parent"):
            pst, pc = _device_status(s.get("cluster"), device_cache)
            st = pst
            cached = pc
        item = dict(s)
        item["status"] = st or s.get("status", "planned")
        bat = _battery_pct(s, cached)
        if bat:
            item["battery"] = bat
        out.append(item)
    return {"total": len(out), "ts": time.time(), "sensors": out}


@router.get("/fleet/summary")
async def get_fleet_summary():
    fleet = reg.build_fleet()
    return reg.fleet_summary(fleet)


@router.get("/fusion/{cluster_id}")
async def get_fusion(cluster_id: str):
    cid = cluster_id.lower()
    if cid not in reg.CLUSTER_CAP:
        raise HTTPException(404, f"cluster desconhecido: {cluster_id}")
    cap = reg.CLUSTER_CAP[cid]
    fleet = reg.build_fleet()
    sources = reg.fusion_sources(cid, fleet)

    # Tentar dados reais do ingest_store; senao None (fusao devolve sem-dados)
    cam = ir_in = ir_out = wifi = None
    try:
        from app.services import ingest_store
        rec = ingest_store.get(cid)
        if rec:
            p = rec.get("params", {})
            wifi = p.get("telemoveis_detectados")
            ir_in = p.get("entradas_ir")
            ir_out = p.get("saidas_ir")
            cam = p.get("pessoas_estimadas")  # placeholder ate camara dedicada
    except Exception:
        pass

    result = fus.fuse_cluster(
        cap_inside=cap["masc"] + cap["fem"],
        espera_max=cap["espera"],
        sources_present=sources,
        camera_people=cam,
        ir_in=ir_in, ir_out=ir_out,
        wifi_devices=wifi,
        wifi_factor=1.8 if cap["unisex"] else 2.5,
    )
    result["cluster_id"] = cid
    result["fontes_disponiveis"] = sources
    result["capacidade_dentro"] = cap["masc"] + cap["fem"]
    return result
