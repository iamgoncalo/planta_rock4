"""
DB-agnostic seeds — funciona em SQLite OU PostgreSQL.
Insere o mínimo necessário para /api/v1/sensors devolver 200.
"""
from __future__ import annotations
import logging
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

CLUSTERS = ["WC-01", "WC-02", "WC-03", "WC-04", "WC-05", "WC-06", "WC-07", "WC-08"]

CLUSTER_GPS = {
    "WC-01": (38.7870, -9.0950),
    "WC-02": (38.7860, -9.0900),
    "WC-03": (38.7780, -9.0930),
    "WC-04": (38.7820, -9.0880),
    "WC-05": (38.7820, -9.0980),
    "WC-06": (38.7780, -9.0890),
    "WC-07": (38.7870, -9.0990),
    "WC-08": (38.7830, -9.0930),
}


def _sensor_seed_rows() -> list[dict]:
    """Gera 66 sensor rows: 8 hubs + 32 IR + 16 WiFi + 2 LoRa + 8 cameras."""
    rows: list[dict] = []
    for cluster_id in CLUSTERS:
        lat, lon = CLUSTER_GPS[cluster_id]
        rows.append({
            "id": f"{cluster_id}-HUB",
            "cluster_id": cluster_id,
            "type": "lilygo",
            "model": "LilyGo T-SIM7080G",
            "protocol": "LoRaWAN+4G",
            "gps_lat": lat, "gps_lon": lon,
        })
        for i in (1, 2):
            rows.append({
                "id": f"{cluster_id}-IR-IN-{i}",
                "cluster_id": cluster_id,
                "type": "ir_entry", "model": "E18-D80NK",
                "protocol": "GPIO",
                "gps_lat": lat, "gps_lon": lon,
            })
            rows.append({
                "id": f"{cluster_id}-IR-OUT-{i}",
                "cluster_id": cluster_id,
                "type": "ir_exit", "model": "E18-D80NK",
                "protocol": "GPIO",
                "gps_lat": lat, "gps_lon": lon,
            })
        for i in (1, 2):
            rows.append({
                "id": f"{cluster_id}-WIFI-{i}",
                "cluster_id": cluster_id,
                "type": "wifi_aggregate", "model": "TP-Link EAP670",
                "protocol": "WiFi", "gps_lat": lat, "gps_lon": lon,
            })
        rows.append({
            "id": f"{cluster_id}-CAM",
            "cluster_id": cluster_id,
            "type": "camera_ml", "model": "Prosegur Dome",
            "protocol": "RTSP", "gps_lat": lat, "gps_lon": lon,
        })
    for i, loc in enumerate(["North", "South"], start=1):
        rows.append({
            "id": f"LORA-GW-{loc[0]}",
            "cluster_id": "WC-01" if loc == "North" else "WC-06",
            "type": "lorawan_gateway", "model": "Dragino DLOS8",
            "protocol": "LoRaWAN", "gps_lat": CLUSTER_GPS["WC-01"][0], "gps_lon": CLUSTER_GPS["WC-01"][1],
        })
    return rows


async def seed_sensors_if_empty(session_factory) -> None:
    """Se a tabela sensors estiver vazia, insere as 66 linhas + sensor_health a unknown."""
    from app.models.db.sensors import Sensor, SensorHealth

    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(Sensor))
        existing = result.scalar() or 0
        if existing > 0:
            logger.info(f"Seed skip: {existing} sensors já existem")
            return

        rows = _sensor_seed_rows()
        valid_cols = {c.name for c in Sensor.__table__.columns}

        for r in rows:
            kwargs = {k: v for k, v in r.items() if k in valid_cols}
            session.add(Sensor(**kwargs))

        await session.flush()

        health_cols = {c.name for c in SensorHealth.__table__.columns}
        for r in rows:
            h = {"sensor_id": r["id"]}
            if "status" in health_cols:
                h["status"] = "unknown"
            if "events_today" in health_cols:
                h["events_today"] = 0
            session.add(SensorHealth(**h))

        await session.commit()
        logger.info(f"Seed complete: {len(rows)} sensors + {len(rows)} health rows")
