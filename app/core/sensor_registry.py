"""
sensor_registry.py — 66-node sensor topology for Rock in Rio Lisboa 2026.

Nodes:
  8  LilyGo TTGO ESP32 hubs (one per cluster)
  32 IR E18-D80NK sensors  (2 entry + 2 exit per cluster × 8)
  16 TP-Link EAP670 APs    (2 per cluster)
   2 Dragino DLOS8 gateways (sector North + South)
   8 Prosegur cameras       (one per cluster)
  ──
  66 total
"""
from __future__ import annotations

FUSION_WEIGHTS = {"ir": 0.50, "wifi": 0.30, "camera": 0.20}
assert abs(sum(FUSION_WEIGHTS.values()) - 1.0) < 1e-9, "fusion weights must sum to 1.0"

# Battery model: LilyGo 10 Ah / 22 mA avg draw → ~454 h → ~18.9 days theoretical
# Real-world derating 0.85 → ~16 days
LILYGO_BATTERY_MAH = 10_000
LILYGO_DRAW_MA = 22
LILYGO_REAL_DAYS = round(LILYGO_BATTERY_MAH / LILYGO_DRAW_MA / 24 * 0.85, 1)

# Health thresholds (seconds since last heartbeat)
ONLINE_THRESHOLD_S = 70
DEGRADED_THRESHOLD_S = 300

# Cluster GPS centroids (static metadata — never in recurring telemetry)
_CLUSTER_GPS = {
    "WC-01": (38.7870, -9.0950),  # Norte — entrada principal
    "WC-02": (38.7860, -9.0900),  # Nordeste — Palco Mundo
    "WC-03": (38.7780, -9.0930),  # Sul — Super Bock Stage
    "WC-04": (38.7820, -9.0880),  # Este — Zona VIP
    "WC-05": (38.7820, -9.0980),  # Oeste — Praça da Alimentação
    "WC-06": (38.7780, -9.0890),  # Sudeste — Campismo
    "WC-07": (38.7870, -9.0990),  # Noroeste — Estacionamento
    "WC-08": (38.7830, -9.0930),  # Centro — Praça Central
}

# Coverage radius per sensor type (metres, for GeoJSON circles)
COVERAGE_RADIUS_M = {
    "lilygo": 0,       # hub, no area
    "ir": 1,           # gate sensor
    "wifi": 40,        # TP-Link EAP670 indoor range
    "camera": 25,      # Prosegur dome camera FOV footprint
    "lorawan": 2000,   # Dragino DLOS8 outdoor range
}


def _ir_nodes(cluster: str, lat: float, lon: float) -> list[dict]:
    """4 IR nodes per cluster: 2 entry + 2 exit."""
    nodes = []
    for gender in ("M", "F"):
        section = f"{cluster}_{gender}"
        for direction in ("entry", "exit"):
            node_id = f"ir_{cluster.lower().replace('-', '')}_{gender.lower()}_{direction}"
            nodes.append({
                "id": node_id,
                "type": "ir",
                "model": "E18-D80NK",
                "cluster_id": cluster,
                "section_id": section,
                "direction": direction,
                "lat": lat + (0.00003 if direction == "entry" else -0.00003),
                "lon": lon + (0.00002 if gender == "M" else -0.00002),
                "hub_id": f"lilygo_{cluster.lower().replace('-', '')}",
                "gateway_id": "gw_north" if lat > 38.782 else "gw_south",
            })
    return nodes


def _ir_nodes_unisex(cluster: str, lat: float, lon: float) -> list[dict]:
    """4 IR nodes for unisex clusters (WC-05, WC-06) — no gender split."""
    nodes = []
    for idx, direction in enumerate(("entry", "exit")):
        for lane in ("A", "B"):
            node_id = f"ir_{cluster.lower().replace('-', '')}_u{lane.lower()}_{direction}"
            nodes.append({
                "id": node_id,
                "type": "ir",
                "model": "E18-D80NK",
                "cluster_id": cluster,
                "section_id": cluster,
                "direction": direction,
                "lat": lat + (0.00003 if direction == "entry" else -0.00003),
                "lon": lon + (0.00002 if lane == "A" else -0.00002),
                "hub_id": f"lilygo_{cluster.lower().replace('-', '')}",
                "gateway_id": "gw_north" if lat > 38.782 else "gw_south",
            })
    return nodes


def _wifi_nodes(cluster: str, lat: float, lon: float) -> list[dict]:
    """2 TP-Link EAP670 APs per cluster."""
    return [
        {
            "id": f"wifi_{cluster.lower().replace('-', '')}_ap{i}",
            "type": "wifi",
            "model": "TP-Link EAP670",
            "cluster_id": cluster,
            "section_id": None,
            "lat": lat + (0.00010 * (1 if i == 1 else -1)),
            "lon": lon + (0.00010 * (1 if i == 1 else -1)),
            "hub_id": None,
            "gateway_id": "gw_north" if lat > 38.782 else "gw_south",
        }
        for i in range(1, 3)
    ]


def _camera_node(cluster: str, lat: float, lon: float) -> dict:
    """1 Prosegur dome camera per cluster."""
    return {
        "id": f"cam_{cluster.lower().replace('-', '')}",
        "type": "camera",
        "model": "Prosegur Dome",
        "cluster_id": cluster,
        "section_id": None,
        "lat": lat + 0.00005,
        "lon": lon,
        "hub_id": None,
        "gateway_id": None,
    }


def _lilygo_node(cluster: str, lat: float, lon: float) -> dict:
    """1 LilyGo TTGO ESP32 hub per cluster."""
    return {
        "id": f"lilygo_{cluster.lower().replace('-', '')}",
        "type": "lilygo",
        "model": "LilyGo TTGO T-SIM7080G",
        "cluster_id": cluster,
        "section_id": None,
        "lat": lat,
        "lon": lon,
        "hub_id": None,
        "gateway_id": "gw_north" if lat > 38.782 else "gw_south",
        "battery_mah": LILYGO_BATTERY_MAH,
        "draw_ma": LILYGO_DRAW_MA,
        "estimated_days": LILYGO_REAL_DAYS,
    }


# Build the full 66-node registry
_REGISTRY: list[dict] = []
_UNISEX = {"WC-05", "WC-06"}

for _cluster, (_lat, _lon) in _CLUSTER_GPS.items():
    _REGISTRY.append(_lilygo_node(_cluster, _lat, _lon))
    if _cluster in _UNISEX:
        _REGISTRY.extend(_ir_nodes_unisex(_cluster, _lat, _lon))
    else:
        _REGISTRY.extend(_ir_nodes(_cluster, _lat, _lon))
    _REGISTRY.extend(_wifi_nodes(_cluster, _lat, _lon))
    _REGISTRY.append(_camera_node(_cluster, _lat, _lon))

# LoRa gateways (2)
_REGISTRY.append({
    "id": "gw_north",
    "type": "lorawan",
    "model": "Dragino DLOS8",
    "cluster_id": None,
    "section_id": None,
    "lat": 38.7875,
    "lon": -9.0940,
    "hub_id": None,
    "gateway_id": None,
})
_REGISTRY.append({
    "id": "gw_south",
    "type": "lorawan",
    "model": "Dragino DLOS8",
    "cluster_id": None,
    "section_id": None,
    "lat": 38.7775,
    "lon": -9.0930,
    "hub_id": None,
    "gateway_id": None,
})

assert len(_REGISTRY) == 66, f"Expected 66 nodes, got {len(_REGISTRY)}"

# Public exports
SENSOR_REGISTRY: list[dict] = _REGISTRY

SENSOR_SUMMARY = {
    "total": len(_REGISTRY),
    "lilygo": sum(1 for n in _REGISTRY if n["type"] == "lilygo"),
    "ir": sum(1 for n in _REGISTRY if n["type"] == "ir"),
    "wifi": sum(1 for n in _REGISTRY if n["type"] == "wifi"),
    "camera": sum(1 for n in _REGISTRY if n["type"] == "camera"),
    "lorawan": sum(1 for n in _REGISTRY if n["type"] == "lorawan"),
    "clusters": list(_CLUSTER_GPS.keys()),
    "unisex_clusters": list(_UNISEX),
    "fusion_weights": FUSION_WEIGHTS,
}


def get_nodes_by_cluster(cluster_id: str) -> list[dict]:
    return [n for n in SENSOR_REGISTRY if n.get("cluster_id") == cluster_id]


def get_node_by_id(sensor_id: str) -> dict | None:
    for node in SENSOR_REGISTRY:
        if node["id"] == sensor_id:
            return node
    return None


def get_gateway_nodes() -> list[dict]:
    return [n for n in SENSOR_REGISTRY if n["type"] == "lorawan"]


def get_battery_nodes() -> list[dict]:
    return [n for n in SENSOR_REGISTRY if n["type"] == "lilygo"]
