"""
Seed script for sensor nodes — Rock in Rio Lisboa 2026.

66 nodes:
  8  LilyGo TTGO T-SIM7080G hubs    (one per cluster, LoRaWAN + 10Ah battery)
  32 E18-D80NK IR sensors            (4 per cluster: 2 entry + 2 exit)
  16 TP-Link EAP670 WiFi APs         (2 per cluster)
   2 Dragino DLOS8 LoRa gateways     (North + South)
   8 Prosegur Dome cameras           (1 per cluster)
  ──
  66 total
"""
from __future__ import annotations

# Cluster GPS centroids
_CLUSTER_GPS = {
    "WC-01": (38.7870, -9.0950),
    "WC-02": (38.7860, -9.0900),
    "WC-03": (38.7780, -9.0930),
    "WC-04": (38.7820, -9.0880),
    "WC-05": (38.7820, -9.0980),
    "WC-06": (38.7780, -9.0890),
    "WC-07": (38.7870, -9.0990),
    "WC-08": (38.7830, -9.0930),
}

_UNISEX = {"WC-05", "WC-06"}

LILYGO_BATTERY_MAH = 10_000
LILYGO_DRAW_MA = 22
LILYGO_REAL_DAYS = round(LILYGO_BATTERY_MAH / LILYGO_DRAW_MA / 24 * 0.85, 1)

FUSION_WEIGHTS = {"lilygo": 0.0, "ir": 0.50, "wifi": 0.30, "camera": 0.20, "lorawan": 0.0}
COVERAGE_RADIUS = {"lilygo": 0, "ir": 1, "wifi": 40, "camera": 25, "lorawan": 2000}


def _hub(cluster: str, lat: float, lon: float) -> dict:
    return {
        "id": f"lilygo_{cluster.lower().replace('-', '')}",
        "cluster_id": cluster,
        "type": "lilygo",
        "model": "LilyGo TTGO T-SIM7080G",
        "protocol": "lorawan",
        "location_desc": f"{cluster} — Hub principal, montado no tecto da instalação",
        "gps_lat": lat,
        "gps_lon": lon,
        "height_cm": 280,
        "gpio_pin": None,
        "has_battery": True,
        "battery_mah": LILYGO_BATTERY_MAH,
        "powered_by": "LiPo 10Ah",
        "ip_rating": "IP54",
        "coverage_radius_m": COVERAGE_RADIUS["lilygo"],
        "wifi_factor": None,
        "fusion_weight": FUSION_WEIGHTS["lilygo"],
        "firmware": "plantaos-hub-v2.1.0",
        "cost_eur": 45.0,
        "notes": f"Hub LilyGo para cluster {cluster}. Gateway: {'gw_north' if lat > 38.782 else 'gw_south'}.",
        "critical_note": None,
        "installed_by": None,
    }


def _ir_nodes_standard(cluster: str, lat: float, lon: float) -> list[dict]:
    """4 IR nodes per standard cluster: 2 entry + 2 exit (M + F)."""
    nodes = []
    for gender in ("M", "F"):
        for direction in ("entry", "exit"):
            node_id = f"ir_{cluster.lower().replace('-', '')}_{gender.lower()}_{direction}"
            nodes.append({
                "id": node_id,
                "cluster_id": cluster,
                "type": "ir",
                "model": "E18-D80NK",
                "protocol": "gpio",
                "location_desc": f"{cluster} — Porta {gender} {direction}, altura 120cm",
                "gps_lat": lat + (0.00003 if direction == "entry" else -0.00003),
                "gps_lon": lon + (0.00002 if gender == "M" else -0.00002),
                "height_cm": 120,
                "gpio_pin": (4 if gender == "M" else 16) + (0 if direction == "entry" else 1),
                "has_battery": False,
                "battery_mah": None,
                "powered_by": "5V via LilyGo",
                "ip_rating": "IP67",
                "coverage_radius_m": COVERAGE_RADIUS["ir"],
                "wifi_factor": None,
                "fusion_weight": FUSION_WEIGHTS["ir"],
                "firmware": "e18-d80nk-v1.0",
                "cost_eur": 8.5,
                "notes": f"Sensor IR porta {gender} {direction}.",
                "critical_note": None,
                "installed_by": None,
            })
    return nodes


def _ir_nodes_unisex(cluster: str, lat: float, lon: float) -> list[dict]:
    """4 IR nodes for unisex clusters (WC-05, WC-06) — no gender split."""
    nodes = []
    for direction in ("entry", "exit"):
        for lane in ("A", "B"):
            node_id = f"ir_{cluster.lower().replace('-', '')}_u{lane.lower()}_{direction}"
            nodes.append({
                "id": node_id,
                "cluster_id": cluster,
                "type": "ir",
                "model": "E18-D80NK",
                "protocol": "gpio",
                "location_desc": f"{cluster} UNISSEX — Porta {lane} {direction}, altura 120cm",
                "gps_lat": lat + (0.00003 if direction == "entry" else -0.00003),
                "gps_lon": lon + (0.00002 if lane == "A" else -0.00002),
                "height_cm": 120,
                "gpio_pin": (4 if lane == "A" else 16) + (0 if direction == "entry" else 1),
                "has_battery": False,
                "battery_mah": None,
                "powered_by": "5V via LilyGo",
                "ip_rating": "IP67",
                "coverage_radius_m": COVERAGE_RADIUS["ir"],
                "wifi_factor": None,
                "fusion_weight": FUSION_WEIGHTS["ir"],
                "firmware": "e18-d80nk-v1.0",
                "cost_eur": 8.5,
                "notes": f"Sensor IR unissex porta {lane} {direction}.",
                "critical_note": "WC-05/06 UNISSEX — sem divisão por género",
                "installed_by": None,
            })
    return nodes


def _wifi_nodes(cluster: str, lat: float, lon: float) -> list[dict]:
    """2 TP-Link EAP670 APs per cluster."""
    nodes = []
    for i in range(1, 3):
        nodes.append({
            "id": f"wifi_{cluster.lower().replace('-', '')}_ap{i}",
            "cluster_id": cluster,
            "type": "wifi",
            "model": "TP-Link EAP670",
            "protocol": "wifi6",
            "location_desc": f"{cluster} — AP {i}, montado no tecto a 3m",
            "gps_lat": lat + (0.00010 if i == 1 else -0.00010),
            "gps_lon": lon + (0.00010 if i == 1 else -0.00010),
            "height_cm": 300,
            "gpio_pin": None,
            "has_battery": False,
            "battery_mah": None,
            "powered_by": "PoE 802.3af",
            "ip_rating": "IP30",
            "coverage_radius_m": COVERAGE_RADIUS["wifi"],
            "wifi_factor": 2.5,
            "fusion_weight": FUSION_WEIGHTS["wifi"],
            "firmware": "eap670-v5.0.6",
            "cost_eur": 149.0,
            "notes": f"AP WiFi 6 para contagem agregada. Sem MAC storage.",
            "critical_note": "RGPD: apenas contagens agregadas, sem tracking individual, sem armazenamento de MACs",
            "installed_by": None,
        })
    return nodes


def _camera_node(cluster: str, lat: float, lon: float) -> dict:
    """1 Prosegur dome camera per cluster."""
    return {
        "id": f"cam_{cluster.lower().replace('-', '')}",
        "cluster_id": cluster,
        "type": "camera",
        "model": "Prosegur Dome",
        "protocol": "rtsp",
        "location_desc": f"{cluster} — Câmara Prosegur, visão geral da zona de espera",
        "gps_lat": lat + 0.00005,
        "gps_lon": lon,
        "height_cm": 400,
        "gpio_pin": None,
        "has_battery": False,
        "battery_mah": None,
        "powered_by": "PoE 802.3at",
        "ip_rating": "IP66",
        "coverage_radius_m": COVERAGE_RADIUS["camera"],
        "wifi_factor": None,
        "fusion_weight": FUSION_WEIGHTS["camera"],
        "firmware": "prosegur-ml-v3.2",
        "cost_eur": 320.0,
        "notes": f"Câmara ML Prosegur para contagem de multidão.",
        "critical_note": "RGPD: apenas contagem agregada por zonas, sem identificação facial",
        "installed_by": None,
    }


def _gateway_node(gw_id: str, lat: float, lon: float, sector: str) -> dict:
    return {
        "id": gw_id,
        "cluster_id": None,
        "type": "lorawan",
        "model": "Dragino DLOS8",
        "protocol": "lorawan",
        "location_desc": f"Gateway LoRa sector {sector} — cobertura 2km raio",
        "gps_lat": lat,
        "gps_lon": lon,
        "height_cm": 600,
        "gpio_pin": None,
        "has_battery": False,
        "battery_mah": None,
        "powered_by": "230V AC",
        "ip_rating": "IP65",
        "coverage_radius_m": COVERAGE_RADIUS["lorawan"],
        "wifi_factor": None,
        "fusion_weight": FUSION_WEIGHTS["lorawan"],
        "firmware": "dlos8-v5.4.1617429706",
        "cost_eur": 299.0,
        "notes": f"Gateway LoRaWAN sector {sector}. Cobre todos os hubs LilyGo do sector.",
        "critical_note": None,
        "installed_by": None,
    }


# Build full seed list
SENSOR_SEED: list[dict] = []

for _cluster, (_lat, _lon) in _CLUSTER_GPS.items():
    SENSOR_SEED.append(_hub(_cluster, _lat, _lon))
    if _cluster in _UNISEX:
        SENSOR_SEED.extend(_ir_nodes_unisex(_cluster, _lat, _lon))
    else:
        SENSOR_SEED.extend(_ir_nodes_standard(_cluster, _lat, _lon))
    SENSOR_SEED.extend(_wifi_nodes(_cluster, _lat, _lon))
    SENSOR_SEED.append(_camera_node(_cluster, _lat, _lon))

SENSOR_SEED.append(_gateway_node("gw_north", 38.7875, -9.0940, "Norte"))
SENSOR_SEED.append(_gateway_node("gw_south", 38.7775, -9.0930, "Sul"))

assert len(SENSOR_SEED) == 66, f"Expected 66 sensors, got {len(SENSOR_SEED)}"


if __name__ == "__main__":
    import psycopg2
    import os

    DB_URL = os.environ.get("DATABASE_URL", "")
    # Strip asyncpg prefix if accidentally passed
    DB_URL = DB_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    inserted = 0
    for s in SENSOR_SEED:
        cur.execute(
            """
            INSERT INTO sensors (
                id, cluster_id, type, model, protocol, location_desc,
                gps_lat, gps_lon, height_cm, gpio_pin, has_battery, battery_mah,
                powered_by, ip_rating, coverage_radius_m, wifi_factor, fusion_weight,
                firmware, cost_eur, notes, critical_note, installed_by
            ) VALUES (
                %(id)s, %(cluster_id)s, %(type)s, %(model)s, %(protocol)s, %(location_desc)s,
                %(gps_lat)s, %(gps_lon)s, %(height_cm)s, %(gpio_pin)s, %(has_battery)s, %(battery_mah)s,
                %(powered_by)s, %(ip_rating)s, %(coverage_radius_m)s, %(wifi_factor)s, %(fusion_weight)s,
                %(firmware)s, %(cost_eur)s, %(notes)s, %(critical_note)s, %(installed_by)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            s,
        )
        if cur.rowcount > 0:
            inserted += 1

    # Insert initial sensor_health rows
    cur.execute(
        """
        INSERT INTO sensor_health (sensor_id, status, events_today)
        SELECT id, 'unknown', 0 FROM sensors
        ON CONFLICT (sensor_id) DO NOTHING
        """
    )
    health_inserted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    total = len(SENSOR_SEED)
    print(f"Seed complete: {inserted}/{total} sensors inserted, {health_inserted} health rows created")
