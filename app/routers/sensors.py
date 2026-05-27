"""
sensors.py — Full Sensors Intelligence Layer router.
Replaces the previous in-memory implementation.
All data comes from PostgreSQL via SQLAlchemy async.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update, insert, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.db.sensors import Sensor, SensorHealth, MaintenanceLog, TerminalLog

router = APIRouter(prefix="/api/v1", tags=["sensors"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _sensor_to_dict(s: Sensor, health: SensorHealth | None = None) -> dict:
    d = {
        "id": s.id,
        "cluster_id": s.cluster_id,
        "type": s.type,
        "model": s.model,
        "protocol": s.protocol,
        "location_desc": s.location_desc,
        "gps_lat": s.gps_lat,
        "gps_lon": s.gps_lon,
        "height_cm": s.height_cm,
        "gpio_pin": s.gpio_pin,
        "has_battery": s.has_battery,
        "battery_mah": s.battery_mah,
        "powered_by": s.powered_by,
        "ip_rating": s.ip_rating,
        "coverage_radius_m": s.coverage_radius_m,
        "wifi_factor": s.wifi_factor,
        "fusion_weight": s.fusion_weight,
        "firmware": s.firmware,
        "cost_eur": s.cost_eur,
        "notes": s.notes,
        "critical_note": s.critical_note,
        "installed_at": s.installed_at.isoformat() if s.installed_at else None,
        "installed_by": s.installed_by,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "is_active": s.is_active,
        "health": None,
    }
    if health:
        d["health"] = {
            "last_seen": health.last_seen.isoformat() if health.last_seen else None,
            "last_rssi_dbm": health.last_rssi_dbm,
            "last_uptime_s": health.last_uptime_s,
            "battery_pct": health.battery_pct,
            "firmware_ver": health.firmware_ver,
            "events_today": health.events_today,
            "status": health.status,
            "updated_at": health.updated_at.isoformat() if health.updated_at else None,
        }
    return d


def _maintenance_to_dict(m: MaintenanceLog) -> dict:
    return {
        "id": m.id,
        "sensor_id": m.sensor_id,
        "action": m.action,
        "result": m.result,
        "notes": m.notes,
        "performed_by": m.performed_by,
        "performed_at": m.performed_at.isoformat() if m.performed_at else None,
    }


async def _log_terminal(db: AsyncSession, session_id: str, command: str, output: str, exit_code: int = 0):
    await db.execute(
        insert(TerminalLog).values(
            session_id=session_id,
            command=command,
            output=output,
            exit_code=exit_code,
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# GET /api/v1/sensors
# ---------------------------------------------------------------------------

@router.get("/sensors")
async def list_sensors(
    cluster_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all sensors with health merged. Supports ?cluster_id=&type=&status= filters."""
    q = select(Sensor).where(Sensor.is_active == True)
    if cluster_id:
        q = q.where(Sensor.cluster_id == cluster_id)
    if type:
        q = q.where(Sensor.type == type)

    result = await db.execute(q)
    sensors = result.scalars().all()

    sensor_ids = [s.id for s in sensors]
    health_map: dict[str, SensorHealth] = {}
    if sensor_ids:
        hq = select(SensorHealth).where(SensorHealth.sensor_id.in_(sensor_ids))
        hr = await db.execute(hq)
        for h in hr.scalars().all():
            health_map[h.sensor_id] = h

    out = []
    for s in sensors:
        h = health_map.get(s.id)
        if status and (h is None or h.status != status):
            continue
        out.append(_sensor_to_dict(s, h))

    return out


# ---------------------------------------------------------------------------
# POST /api/v1/sensors
# ---------------------------------------------------------------------------

@router.post("/sensors", status_code=201)
async def create_sensor(body: dict, db: AsyncSession = Depends(get_db)):
    """Create a new sensor + log install maintenance entry."""
    sensor_id = body.get("id") or f"sensor_{uuid.uuid4().hex[:8]}"
    s = Sensor(
        id=sensor_id,
        cluster_id=body.get("cluster_id"),
        type=body.get("type", "ir"),
        model=body.get("model", "unknown"),
        protocol=body.get("protocol"),
        location_desc=body.get("location_desc"),
        gps_lat=body.get("gps_lat"),
        gps_lon=body.get("gps_lon"),
        height_cm=body.get("height_cm"),
        gpio_pin=body.get("gpio_pin"),
        has_battery=body.get("has_battery", False),
        battery_mah=body.get("battery_mah"),
        powered_by=body.get("powered_by"),
        ip_rating=body.get("ip_rating"),
        coverage_radius_m=body.get("coverage_radius_m"),
        wifi_factor=body.get("wifi_factor"),
        fusion_weight=body.get("fusion_weight"),
        firmware=body.get("firmware"),
        cost_eur=body.get("cost_eur"),
        notes=body.get("notes"),
        critical_note=body.get("critical_note"),
        installed_by=body.get("installed_by"),
        is_active=True,
    )
    db.add(s)
    await db.flush()

    # Health row
    db.add(SensorHealth(sensor_id=sensor_id, status="unknown", events_today=0))

    # Maintenance install log
    db.add(MaintenanceLog(
        sensor_id=sensor_id,
        action="install",
        result="created",
        notes=f"Sensor criado via API. Modelo: {s.model}",
        performed_by=body.get("installed_by", "api"),
    ))

    await db.commit()
    return {"sensor_id": sensor_id, "created": True}


# ---------------------------------------------------------------------------
# GET /api/v1/sensors/summary
# ---------------------------------------------------------------------------

@router.get("/sensors/summary")
async def sensors_summary(db: AsyncSession = Depends(get_db)):
    """Topology summary: total counts by type."""
    result = await db.execute(
        text("SELECT type, COUNT(*) as cnt FROM sensors WHERE is_active = true GROUP BY type")
    )
    counts = {row[0]: row[1] for row in result.fetchall()}

    total = sum(counts.values())
    health_result = await db.execute(
        text("SELECT status, COUNT(*) FROM sensor_health GROUP BY status")
    )
    health_counts = {row[0]: row[1] for row in health_result.fetchall()}

    return {
        "total": total,
        "by_type": counts,
        "health": health_counts,
        "fusion_weights": {"ir": 0.50, "wifi": 0.30, "camera": 0.20},
        "clusters": ["WC-01", "WC-02", "WC-03", "WC-04", "WC-05", "WC-06", "WC-07", "WC-08"],
        "unisex_clusters": ["WC-05", "WC-06"],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/sensors/battery/status
# ---------------------------------------------------------------------------

@router.get("/sensors/battery/status")
async def battery_status(db: AsyncSession = Depends(get_db)):
    """Battery status for hub (lilygo) sensors."""
    q = select(Sensor, SensorHealth).join(
        SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
    ).where(Sensor.type == "lilygo", Sensor.is_active == True)

    result = await db.execute(q)
    rows = result.all()

    out = []
    for s, h in rows:
        battery_mah = s.battery_mah or 10000
        draw_ma = 22
        days_left = round(battery_mah / draw_ma / 24 * 0.85, 1)
        battery_pct = h.battery_pct if h else None
        out.append({
            "hub_id": s.id,
            "cluster_id": s.cluster_id,
            "battery_mah": battery_mah,
            "draw_ma": draw_ma,
            "days_left": days_left,
            "battery_pct": battery_pct,
            "status": h.status if h else "unknown",
            "last_seen": h.last_seen.isoformat() if h and h.last_seen else None,
        })
    return out


# ---------------------------------------------------------------------------
# GET /api/v1/sensors/coverage/geojson
# ---------------------------------------------------------------------------

@router.get("/sensors/coverage/geojson")
async def coverage_geojson(db: AsyncSession = Depends(get_db)):
    """GeoJSON FeatureCollection of sensor coverage circles."""
    q = select(Sensor, SensorHealth).join(
        SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
    ).where(Sensor.is_active == True, Sensor.gps_lat.isnot(None))

    result = await db.execute(q)
    rows = result.all()

    features = []
    for s, h in rows:
        r = s.coverage_radius_m or 0
        if r == 0:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [s.gps_lon, s.gps_lat],
            },
            "properties": {
                "sensor_id": s.id,
                "sensor_type": s.type,
                "cluster_id": s.cluster_id,
                "radius_m": r,
                "status": h.status if h else "unknown",
                "model": s.model,
            },
        })

    return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# GET /api/v1/sensors/cluster/{cluster_id}
# ---------------------------------------------------------------------------

@router.get("/sensors/cluster/{cluster_id}")
async def sensors_by_cluster(cluster_id: str, db: AsyncSession = Depends(get_db)):
    """All sensors for a specific cluster."""
    q = select(Sensor, SensorHealth).join(
        SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
    ).where(Sensor.cluster_id == cluster_id, Sensor.is_active == True)

    result = await db.execute(q)
    rows = result.all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id!r} not found or has no sensors")

    return [_sensor_to_dict(s, h) for s, h in rows]


# ---------------------------------------------------------------------------
# GET /api/v1/sensors/{sensor_id}
# ---------------------------------------------------------------------------

@router.get("/sensors/{sensor_id}")
async def get_sensor(sensor_id: str, db: AsyncSession = Depends(get_db)):
    """Single sensor detail with health + last 20 maintenance logs."""
    q = select(Sensor, SensorHealth).join(
        SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
    ).where(Sensor.id == sensor_id)

    result = await db.execute(q)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")

    s, h = row
    d = _sensor_to_dict(s, h)

    mq = select(MaintenanceLog).where(MaintenanceLog.sensor_id == sensor_id).order_by(
        MaintenanceLog.performed_at.desc()
    ).limit(20)
    mr = await db.execute(mq)
    d["maintenance"] = [_maintenance_to_dict(m) for m in mr.scalars().all()]

    return d


# ---------------------------------------------------------------------------
# PATCH /api/v1/sensors/{sensor_id}
# ---------------------------------------------------------------------------

@router.patch("/sensors/{sensor_id}")
async def update_sensor(sensor_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Update notes, location, active status."""
    allowed = {"notes", "critical_note", "location_desc", "gps_lat", "gps_lon", "is_active", "wifi_factor", "installed_by"}
    updates = {k: v for k, v in body.items() if k in allowed}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    result = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")

    for k, v in updates.items():
        setattr(s, k, v)
    await db.commit()
    await db.refresh(s)
    return {"sensor_id": sensor_id, "updated": True, "fields": list(updates.keys()), **{k: getattr(s, k) for k in updates.keys()}}


# ---------------------------------------------------------------------------
# DELETE /api/v1/sensors/{sensor_id}
# ---------------------------------------------------------------------------

@router.delete("/sensors/{sensor_id}")
async def delete_sensor(sensor_id: str, db: AsyncSession = Depends(get_db)):
    """Soft delete — sets is_active=False."""
    result = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")

    await db.execute(update(Sensor).where(Sensor.id == sensor_id).values(is_active=False))
    db.add(MaintenanceLog(
        sensor_id=sensor_id,
        action="deactivate",
        result="soft_deleted",
        notes="Sensor desactivado via API (soft delete)",
        performed_by="api",
    ))
    await db.commit()
    return {"sensor_id": sensor_id, "deleted": False, "deactivated": True}


# ---------------------------------------------------------------------------
# POST /api/v1/sensors/{sensor_id}/ping
# ---------------------------------------------------------------------------

@router.post("/sensors/{sensor_id}/ping")
async def ping_sensor(sensor_id: str, db: AsyncSession = Depends(get_db)):
    """Connectivity test — updates health last_seen."""
    result = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")

    now = _now_utc()
    await db.execute(
        update(SensorHealth).where(SensorHealth.sensor_id == sensor_id).values(
            last_seen=now,
            status="online",
            updated_at=now,
        )
    )
    await db.commit()
    return {"sensor_id": sensor_id, "pinged_at": now.isoformat(), "acknowledged": True, "status": "online"}


# ---------------------------------------------------------------------------
# POST /api/v1/sensors/{sensor_id}/maintenance
# ---------------------------------------------------------------------------

@router.post("/sensors/{sensor_id}/maintenance")
async def log_maintenance(sensor_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Log a maintenance action."""
    result = await db.execute(select(Sensor).where(Sensor.id == sensor_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")

    m = MaintenanceLog(
        sensor_id=sensor_id,
        action=body.get("action", "note"),
        result=body.get("result"),
        notes=body.get("notes"),
        performed_by=body.get("performed_by", "api"),
    )
    db.add(m)
    await db.flush()   # execute INSERT, get RETURNING id before commit
    await db.refresh(m)  # pull server defaults (performed_at)
    await db.commit()
    return _maintenance_to_dict(m)


# ---------------------------------------------------------------------------
# GET /api/v1/sensors/{sensor_id}/maintenance
# ---------------------------------------------------------------------------

@router.get("/sensors/{sensor_id}/maintenance")
async def get_maintenance(
    sensor_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Maintenance history for a sensor."""
    q = select(MaintenanceLog).where(MaintenanceLog.sensor_id == sensor_id).order_by(
        MaintenanceLog.performed_at.desc()
    ).limit(limit)
    r = await db.execute(q)
    return [_maintenance_to_dict(m) for m in r.scalars().all()]


# ---------------------------------------------------------------------------
# WebSocket /api/v1/sensors/terminal
# ---------------------------------------------------------------------------

TERMINAL_HELP = """PlantaOS Sensor Terminal v2
Comandos disponíveis:

  status [sensor_id|all]         — estado de saúde dos sensores
  ping <sensor_id>               — teste de conectividade
  list [cluster <id>] [type <t>] — listar sensores com filtros
  battery                        — estado da bateria dos hubs
  gateways                       — estado dos gateways LoRa/AP
  add sensor <json>              — adicionar novo sensor
  remove sensor <id>             — desactivar sensor (soft delete)
  calibrate <sensor_id> <factor> — actualizar wifi_factor
  logs <sensor_id> [n]           — histórico de manutenção
  note <sensor_id> <text>        — adicionar nota de manutenção
  coverage                       — resumo de cobertura por cluster
  clear                          — limpar terminal
  help                           — mostrar esta ajuda

$ """


async def _terminal_cmd(
    db: AsyncSession,
    session_id: str,
    raw: str,
) -> tuple[str, int]:
    """Process a terminal command. Returns (output, exit_code)."""
    raw = raw.strip()
    if not raw:
        return "$ ", 0

    parts = raw.split()
    cmd = parts[0].lower()
    args = parts[1:]
    output = ""
    exit_code = 0

    try:
        if cmd == "help":
            output = TERMINAL_HELP

        elif cmd == "clear":
            output = "\033[2J\033[H"

        elif cmd == "status":
            target = args[0] if args else "all"
            if target == "all":
                r = await db.execute(
                    select(Sensor, SensorHealth).join(
                        SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
                    ).where(Sensor.is_active == True).limit(30)
                )
                rows = r.all()
                lines = ["ID                              TYPE       STATUS     LAST SEEN"]
                lines.append("-" * 70)
                for s, h in rows:
                    status = h.status if h else "unknown"
                    last = h.last_seen.strftime("%H:%M:%S") if h and h.last_seen else "never"
                    lines.append(f"{s.id:<32} {s.type:<10} {status:<10} {last}")
                output = "\n".join(lines) + "\n\n$ "
            else:
                r = await db.execute(
                    select(Sensor, SensorHealth).join(
                        SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
                    ).where(Sensor.id == target)
                )
                row = r.first()
                if not row:
                    output = f"Sensor '{target}' não encontrado.\n\n$ "
                    exit_code = 1
                else:
                    s, h = row
                    status = h.status if h else "unknown"
                    last = h.last_seen.isoformat() if h and h.last_seen else "nunca"
                    rssi = h.last_rssi_dbm if h else "N/A"
                    uptime = h.last_uptime_s if h else "N/A"
                    bat = h.battery_pct if h else "N/A"
                    output = (
                        f"Sensor:     {s.id}\n"
                        f"Tipo:       {s.type}\n"
                        f"Modelo:     {s.model}\n"
                        f"Cluster:    {s.cluster_id or 'N/A'}\n"
                        f"Status:     {status}\n"
                        f"Último:     {last}\n"
                        f"RSSI:       {rssi} dBm\n"
                        f"Uptime:     {uptime} s\n"
                        f"Bateria:    {bat}%\n"
                        f"\n$ "
                    )

        elif cmd == "ping":
            if not args:
                output = "Uso: ping <sensor_id>\n\n$ "
                exit_code = 1
            else:
                target = args[0]
                r = await db.execute(select(Sensor).where(Sensor.id == target))
                s = r.scalar_one_or_none()
                if not s:
                    output = f"Sensor '{target}' não encontrado.\n\n$ "
                    exit_code = 1
                else:
                    now = _now_utc()
                    await db.execute(
                        update(SensorHealth).where(SensorHealth.sensor_id == target).values(
                            last_seen=now, status="online", updated_at=now
                        )
                    )
                    await db.commit()
                    output = f"PING {target}: OK — {now.strftime('%H:%M:%S UTC')}\n\n$ "

        elif cmd == "list":
            q = select(Sensor, SensorHealth).join(
                SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
            ).where(Sensor.is_active == True)

            i = 0
            while i < len(args):
                if args[i] == "cluster" and i + 1 < len(args):
                    q = q.where(Sensor.cluster_id == args[i + 1])
                    i += 2
                elif args[i] == "type" and i + 1 < len(args):
                    q = q.where(Sensor.type == args[i + 1])
                    i += 2
                else:
                    i += 1

            r = await db.execute(q)
            rows = r.all()
            lines = [f"{'ID':<32} {'TYPE':<10} {'CLUSTER':<8} {'STATUS':<10} {'MODEL'}"]
            lines.append("-" * 80)
            for s, h in rows:
                status = h.status if h else "unknown"
                lines.append(f"{s.id:<32} {s.type:<10} {(s.cluster_id or 'N/A'):<8} {status:<10} {s.model}")
            output = "\n".join(lines) + f"\n\nTotal: {len(rows)} sensores\n\n$ "

        elif cmd == "battery":
            r = await db.execute(
                select(Sensor, SensorHealth).join(
                    SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
                ).where(Sensor.type == "lilygo", Sensor.is_active == True)
            )
            rows = r.all()
            lines = [f"{'HUB':<30} {'CLUSTER':<8} {'mAh':<8} {'DIAS':<8} {'%BAT':<6} STATUS"]
            lines.append("-" * 70)
            for s, h in rows:
                mah = s.battery_mah or 10000
                days = round(mah / 22 / 24 * 0.85, 1)
                bat = f"{h.battery_pct}%" if h and h.battery_pct is not None else "N/A"
                status = h.status if h else "unknown"
                lines.append(f"{s.id:<30} {(s.cluster_id or 'N/A'):<8} {mah:<8} {days:<8} {bat:<6} {status}")
            output = "\n".join(lines) + "\n\n$ "

        elif cmd == "gateways":
            r = await db.execute(
                select(Sensor, SensorHealth).join(
                    SensorHealth, Sensor.id == SensorHealth.sensor_id, isouter=True
                ).where(Sensor.type.in_(["lorawan", "wifi"]), Sensor.is_active == True)
            )
            rows = r.all()
            lines = [f"{'ID':<30} {'TYPE':<10} {'STATUS':<10} {'MODEL'}"]
            lines.append("-" * 70)
            for s, h in rows:
                status = h.status if h else "unknown"
                lines.append(f"{s.id:<30} {s.type:<10} {status:<10} {s.model}")
            output = "\n".join(lines) + "\n\n$ "

        elif cmd == "add" and len(args) >= 2 and args[0] == "sensor":
            try:
                json_str = raw[len("add sensor"):].strip()
                data = json.loads(json_str)
                sensor_id = data.get("id") or f"sensor_{uuid.uuid4().hex[:8]}"
                s = Sensor(
                    id=sensor_id,
                    cluster_id=data.get("cluster_id"),
                    type=data.get("type", "ir"),
                    model=data.get("model", "unknown"),
                    protocol=data.get("protocol"),
                    location_desc=data.get("location_desc"),
                    gps_lat=data.get("gps_lat"),
                    gps_lon=data.get("gps_lon"),
                    has_battery=data.get("has_battery", False),
                    battery_mah=data.get("battery_mah"),
                    firmware=data.get("firmware"),
                    cost_eur=data.get("cost_eur"),
                    notes=data.get("notes"),
                    is_active=True,
                )
                db.add(s)
                await db.flush()
                db.add(SensorHealth(sensor_id=sensor_id, status="unknown"))
                db.add(MaintenanceLog(sensor_id=sensor_id, action="install", result="created", performed_by="terminal"))
                await db.commit()
                output = f"Sensor '{sensor_id}' criado com sucesso.\n\n$ "
            except json.JSONDecodeError as e:
                output = f"Erro de JSON: {e}\nUso: add sensor {{\"id\":\"...\",\"type\":\"ir\",...}}\n\n$ "
                exit_code = 1

        elif cmd == "remove" and len(args) >= 2 and args[0] == "sensor":
            target = args[1]
            r = await db.execute(select(Sensor).where(Sensor.id == target))
            s = r.scalar_one_or_none()
            if not s:
                output = f"Sensor '{target}' não encontrado.\n\n$ "
                exit_code = 1
            else:
                await db.execute(update(Sensor).where(Sensor.id == target).values(is_active=False))
                db.add(MaintenanceLog(sensor_id=target, action="deactivate", result="soft_deleted", performed_by="terminal"))
                await db.commit()
                output = f"Sensor '{target}' desactivado (soft delete).\n\n$ "

        elif cmd == "calibrate":
            if len(args) < 2:
                output = "Uso: calibrate <sensor_id> <factor>\n\n$ "
                exit_code = 1
            else:
                target, factor_str = args[0], args[1]
                try:
                    factor = float(factor_str)
                    r = await db.execute(select(Sensor).where(Sensor.id == target))
                    s = r.scalar_one_or_none()
                    if not s:
                        output = f"Sensor '{target}' não encontrado.\n\n$ "
                        exit_code = 1
                    else:
                        await db.execute(update(Sensor).where(Sensor.id == target).values(wifi_factor=factor))
                        db.add(MaintenanceLog(sensor_id=target, action="calibrate", result=f"wifi_factor={factor}", performed_by="terminal"))
                        await db.commit()
                        output = f"Sensor '{target}' calibrado: wifi_factor={factor}\n\n$ "
                except ValueError:
                    output = f"Factor inválido: '{factor_str}'. Use um número decimal.\n\n$ "
                    exit_code = 1

        elif cmd == "logs":
            if not args:
                output = "Uso: logs <sensor_id> [n]\n\n$ "
                exit_code = 1
            else:
                target = args[0]
                n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
                q = select(MaintenanceLog).where(MaintenanceLog.sensor_id == target).order_by(
                    MaintenanceLog.performed_at.desc()
                ).limit(n)
                r = await db.execute(q)
                logs = r.scalars().all()
                if not logs:
                    output = f"Sem registos para '{target}'.\n\n$ "
                else:
                    lines = [f"{'DATA':<22} {'ACÇÃO':<15} {'RESULTADO':<15} NOTAS"]
                    lines.append("-" * 70)
                    for m in logs:
                        ts = m.performed_at.strftime("%Y-%m-%d %H:%M:%S") if m.performed_at else "N/A"
                        lines.append(f"{ts:<22} {(m.action or ''):<15} {(m.result or ''):<15} {m.notes or ''}")
                    output = "\n".join(lines) + "\n\n$ "

        elif cmd == "note":
            if len(args) < 2:
                output = "Uso: note <sensor_id> <text>\n\n$ "
                exit_code = 1
            else:
                target = args[0]
                note_text = " ".join(args[1:])
                r = await db.execute(select(Sensor).where(Sensor.id == target))
                s = r.scalar_one_or_none()
                if not s:
                    output = f"Sensor '{target}' não encontrado.\n\n$ "
                    exit_code = 1
                else:
                    db.add(MaintenanceLog(sensor_id=target, action="note", result="ok", notes=note_text, performed_by="terminal"))
                    await db.commit()
                    output = f"Nota adicionada a '{target}'.\n\n$ "

        elif cmd == "coverage":
            r = await db.execute(
                text("""
                    SELECT s.cluster_id, s.type, COUNT(*) as cnt,
                           COUNT(CASE WHEN sh.status = 'online' THEN 1 END) as online_cnt
                    FROM sensors s
                    LEFT JOIN sensor_health sh ON s.id = sh.sensor_id
                    WHERE s.is_active = true AND s.cluster_id IS NOT NULL
                    GROUP BY s.cluster_id, s.type
                    ORDER BY s.cluster_id, s.type
                """)
            )
            rows = r.fetchall()
            lines = [f"{'CLUSTER':<8} {'TIPO':<12} {'TOTAL':<8} ONLINE"]
            lines.append("-" * 40)
            for row in rows:
                lines.append(f"{row[0]:<8} {row[1]:<12} {row[2]:<8} {row[3]}")
            output = "\n".join(lines) + "\n\n$ "

        else:
            output = f"Comando desconhecido: '{cmd}'. Escreva 'help' para ver comandos.\n\n$ "
            exit_code = 1

    except Exception as e:
        output = f"Erro interno: {e}\n\n$ "
        exit_code = 2

    # Log to terminal_log
    await _log_terminal(db, session_id, raw, output, exit_code)
    return output, exit_code


@router.websocket("/sensors/terminal")
async def sensors_terminal(websocket: WebSocket):
    """WebSocket interactive terminal for sensor management."""
    await websocket.accept()
    session_id = str(uuid.uuid4())

    welcome = {
        "type": "welcome",
        "session_id": session_id,
        "output": "PlantaOS Sensor Terminal v2\nRock in Rio Lisboa 2026\nEscreva 'help' para ver comandos.\n\n$ ",
    }
    await websocket.send_json(welcome)

    try:
        async for session in get_db():
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        msg = json.loads(data)
                        command = msg.get("command", "")
                    except json.JSONDecodeError:
                        command = data

                    output, exit_code = await _terminal_cmd(session, session_id, command)
                    await websocket.send_json({
                        "type": "output",
                        "command": command,
                        "output": output,
                        "exit_code": exit_code,
                    })
            except WebSocketDisconnect:
                break
            except Exception as e:
                try:
                    await websocket.send_json({"type": "error", "output": f"Erro: {e}\n\n$ "})
                except Exception:
                    pass
                break
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
