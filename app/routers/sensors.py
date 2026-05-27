from __future__ import annotations
import time
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.models.sensors import IRReading, CameraMLReading, SensorHealth
from app.models.sensors import SensorNode, GatewayStatus, BatteryReport, CoverageFeature, CoverageGeoJSON, MaintenanceItem
from app.services.state import get_sensor_health, ingest_ir, ingest_camera
from app.core.sensor_registry import (
    SENSOR_REGISTRY,
    SENSOR_SUMMARY,
    COVERAGE_RADIUS_M,
    ONLINE_THRESHOLD_S,
    DEGRADED_THRESHOLD_S,
    get_nodes_by_cluster,
    get_node_by_id,
    get_gateway_nodes,
    get_battery_nodes,
)

router = APIRouter(prefix="/api/v1", tags=["sensors"])


def _node_status(last_seen: float, now: float) -> str:
    age = now - last_seen
    if age < ONLINE_THRESHOLD_S:
        return "online"
    if age < DEGRADED_THRESHOLD_S:
        return "degraded"
    return "offline"


def _health_map() -> dict[str, SensorHealth]:
    """Index existing health records by cluster_id."""
    return {h.cluster_id: h for h in get_sensor_health()}


# ---------------------------------------------------------------------------
# Existing endpoints (preserved)
# ---------------------------------------------------------------------------

@router.get("/sensors", response_model=list[SensorHealth])
async def list_sensors():
    """Health status for all 8 clusters."""
    return get_sensor_health()


@router.post("/sensor", response_model=dict)
async def ingest_ir_reading(reading: IRReading):
    """Ingest IR gate reading."""
    ingest_ir(reading)
    return {"status": "accepted", "source_id": reading.source_id, "simulated": reading.simulated}


@router.post("/prosegur", response_model=dict)
async def ingest_camera_reading(reading: CameraMLReading):
    """Ingest Prosegur camera ML crowd-count."""
    ingest_camera(reading)
    return {"status": "accepted", "source_id": reading.source_id, "zone": reading.zone}


# ---------------------------------------------------------------------------
# New endpoints
# ---------------------------------------------------------------------------

@router.get("/sensors/summary")
async def sensors_summary():
    """Return static topology summary (counts, fusion weights)."""
    return SENSOR_SUMMARY


@router.get("/sensors/coverage", response_model=CoverageGeoJSON)
async def sensors_coverage():
    """GeoJSON FeatureCollection of sensor coverage circles."""
    now = time.time()
    features: list[CoverageFeature] = []
    for node in SENSOR_REGISTRY:
        if node["lat"] is None:
            continue
        radius = COVERAGE_RADIUS_M.get(node["type"], 0)
        if radius == 0:
            continue
        features.append(CoverageFeature(
            sensor_id=node["id"],
            sensor_type=node["type"],
            cluster_id=node.get("cluster_id"),
            lat=node["lat"],
            lon=node["lon"],
            radius_m=radius,
            status="online",  # static topology; runtime health in /sensors
        ))
    return CoverageGeoJSON(type="FeatureCollection", features=features)


@router.get("/sensors/battery", response_model=list[BatteryReport])
async def sensors_battery():
    """Battery estimates for all 8 LilyGo hubs."""
    now = time.time()
    reports: list[BatteryReport] = []
    for node in get_battery_nodes():
        reports.append(BatteryReport(
            hub_id=node["id"],
            cluster_id=node["cluster_id"],
            battery_mah=node["battery_mah"],
            draw_ma=node["draw_ma"],
            estimated_days_remaining=node["estimated_days"],
            last_seen_ts=now,
            status="ok" if node["estimated_days"] > 3 else "low",
        ))
    return reports


@router.get("/sensors/maintenance", response_model=list[MaintenanceItem])
async def sensors_maintenance():
    """Installation & maintenance checklist for all clusters."""
    now = time.time()
    items: list[MaintenanceItem] = []
    clusters = ["WC-01", "WC-02", "WC-03", "WC-04", "WC-05", "WC-06", "WC-07", "WC-08"]
    for cluster in clusters:
        nodes = get_nodes_by_cluster(cluster)
        n_ir = sum(1 for n in nodes if n["type"] == "ir")
        n_wifi = sum(1 for n in nodes if n["type"] == "wifi")
        n_cam = sum(1 for n in nodes if n["type"] == "camera")
        n_hub = sum(1 for n in nodes if n["type"] == "lilygo")
        items.append(MaintenanceItem(
            cluster_id=cluster,
            hub_installed=n_hub > 0,
            ir_count_expected=4,
            ir_count_installed=n_ir,
            wifi_ap_count_expected=2,
            wifi_ap_count_installed=n_wifi,
            camera_count_expected=1,
            camera_count_installed=n_cam,
            last_inspection_ts=None,
            notes="",
        ))
    return items


@router.get("/gateways", response_model=list[GatewayStatus])
async def list_gateways():
    """Status for both Dragino DLOS8 LoRa gateways."""
    now = time.time()
    result: list[GatewayStatus] = []
    for gw in get_gateway_nodes():
        result.append(GatewayStatus(
            gateway_id=gw["id"],
            model=gw["model"],
            lat=gw["lat"],
            lon=gw["lon"],
            status="online",
            last_seen_ts=now,
            connected_hubs=[
                n["id"] for n in SENSOR_REGISTRY
                if n.get("gateway_id") == gw["id"] and n["type"] == "lilygo"
            ],
            packet_loss_pct=0.0,
        ))
    return result


@router.get("/sensors/cluster/{cluster_id}", response_model=list[SensorNode])
async def sensors_by_cluster(cluster_id: str):
    """All sensor nodes for a specific cluster."""
    nodes = get_nodes_by_cluster(cluster_id)
    if not nodes:
        raise HTTPException(status_code=404, detail=f"Cluster {cluster_id!r} not found")
    now = time.time()
    return [
        SensorNode(
            id=n["id"],
            type=n["type"],
            model=n["model"],
            cluster_id=n.get("cluster_id"),
            section_id=n.get("section_id"),
            direction=n.get("direction"),
            lat=n.get("lat"),
            lon=n.get("lon"),
            hub_id=n.get("hub_id"),
            gateway_id=n.get("gateway_id"),
            status="online",
            last_seen_ts=now,
        )
        for n in nodes
    ]


@router.get("/sensors/{sensor_id}", response_model=SensorNode)
async def get_sensor(sensor_id: str):
    """Single sensor node detail."""
    node = get_node_by_id(sensor_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")
    now = time.time()
    return SensorNode(
        id=node["id"],
        type=node["type"],
        model=node["model"],
        cluster_id=node.get("cluster_id"),
        section_id=node.get("section_id"),
        direction=node.get("direction"),
        lat=node.get("lat"),
        lon=node.get("lon"),
        hub_id=node.get("hub_id"),
        gateway_id=node.get("gateway_id"),
        status="online",
        last_seen_ts=now,
    )


@router.post("/sensors/{sensor_id}/ping", response_model=dict)
async def ping_sensor(sensor_id: str):
    """Mark sensor as responsive (ops health check)."""
    node = get_node_by_id(sensor_id)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id!r} not found")
    return {"sensor_id": sensor_id, "pinged_at": time.time(), "acknowledged": True}
