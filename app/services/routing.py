from __future__ import annotations
import math
import time
from typing import Optional

from app.models.sections import SectionState, UNISEX_SECTIONS
from app.models.routing import RouteOption, BathroomRouteDecision, AvoidanceReason
from app.models.shows import Show, ShowImpact
from app.clusters_geo import CLUSTER_GPS as _WC_GPS, ANCHOR_GPS as _ANCHOR_GPS

# Show impact configuration: which clusters are affected by a show
_SHOW_IMPACTS: dict[str, ShowImpact] = {
    "palco_mundo": ShowImpact(
        show_id="palco_mundo",
        affected_sections=["WC-01_M", "WC-01_F", "WC-02_M", "WC-02_F", "WC-05"],
        surge_penalty_min=3.0,
    ),
    "super_bock": ShowImpact(
        show_id="super_bock",
        affected_sections=["WC-03_M", "WC-03_F", "WC-04_M", "WC-04_F", "WC-06"],
        surge_penalty_min=2.0,
    ),
}

# Walking speed assumption: 80 m/min
_WALK_SPEED_M_PER_MIN = 80.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two GPS points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _cluster_id(section_id: str) -> str:
    """Extract cluster prefix, e.g. 'WC-01_M' -> 'WC-01'."""
    return section_id.split("_")[0] if "_" in section_id else section_id


def _walk_time(user_lat: float, user_lon: float, cluster: str) -> float:
    """Walk time in minutes from user position to cluster centroid."""
    if cluster not in _WC_GPS:
        return 5.0  # fallback
    lat, lon = _WC_GPS[cluster]
    dist_m = _haversine_m(user_lat, user_lon, lat, lon)
    return round(dist_m / _WALK_SPEED_M_PER_MIN, 2)


def _surge_penalty(section_id: str, active_show: Optional[Show]) -> float:
    if active_show is None:
        return 0.0
    stage_key = active_show.stage.lower().replace(" ", "_")
    impact = _SHOW_IMPACTS.get(stage_key)
    if impact and section_id in impact.affected_sections:
        return impact.surge_penalty_min * (active_show.expected_surge_pct / 100.0)
    return 0.0


def _build_option(
    section: SectionState,
    user_lat: float,
    user_lon: float,
    active_show: Optional[Show],
) -> RouteOption:
    cluster = _cluster_id(section.section_id)
    walk_min = _walk_time(user_lat, user_lon, cluster)

    # WC-05 is entry_only: people enter but traffic can back up — add +2.0 walk penalty
    if section.section_id == "WC-05":
        walk_min = walk_min + 2.0

    queue_min = section.tempo_espera_min

    avoidance: list[AvoidanceReason] = []
    safety_penalty = 0.0

    if section.status == "critical":
        avoidance.append("critical")
        safety_penalty = 10.0
    if section.status == "offline":
        avoidance.append("offline")
        safety_penalty = 5.0
    if section.ocupacao_pct >= 90.0:
        avoidance.append("full")

    congestion_penalty = min(3.0, section.ocupacao_pct / 100.0 * 3.0)
    surge_pen = _surge_penalty(section.section_id, active_show)
    if surge_pen > 0:
        avoidance.append("surge")

    confidence_penalty = (1.0 - section.simulated) * 0.0  # placeholder; use confidence field
    # sections don't carry confidence directly; infer from status
    section_confidence = 0.4 if section.status == "offline" else (
        0.6 if section.status == "critical" else 0.9
    )
    confidence_penalty = (1.0 - section_confidence) * 2.0

    if section_confidence < 0.6:
        avoidance.append("low_confidence")

    total_cost = (
        walk_min
        + queue_min
        + congestion_penalty
        + surge_pen
        + confidence_penalty
        + safety_penalty
    )

    return RouteOption(
        section_id=section.section_id,
        walk_time_min=round(walk_min, 2),
        queue_wait_min=round(queue_min, 2),
        total_cost_min=round(total_cost, 2),
        confidence=round(section_confidence, 3),
        avoidance_reasons=avoidance,
        simulated=section.simulated,
    )


def compute_route(
    sections: list[SectionState],
    user_lat: float,
    user_lon: float,
    active_show: Optional[Show] = None,
) -> BathroomRouteDecision:
    """Cost-based bathroom routing.

    total_cost = walk_time_min + queue_wait_min + congestion_penalty
                 + surge_penalty + confidence_penalty + safety_penalty

    Never recommends critical WC when non-critical alternatives exist.
    Never recommends offline WC when online alternatives exist.
    The farther-but-faster scenario works: if nearby WC is full, next cheapest wins.
    """
    options = [_build_option(s, user_lat, user_lon, active_show) for s in sections]

    # Sort by total cost ascending
    options.sort(key=lambda o: o.total_cost_min)

    all_critical = all(
        s.status in ("critical", "offline") for s in sections
    )

    # Filter: prefer non-critical and non-offline unless no choice
    safe_options = [o for o in options if "critical" not in o.avoidance_reasons and "offline" not in o.avoidance_reasons]
    if safe_options:
        ranked = safe_options
    else:
        ranked = options  # all_critical case

    recommended = ranked[0]
    alternatives = ranked[1:4]  # up to 3 alternatives

    any_simulated = any(o.simulated for o in [recommended] + alternatives)

    return BathroomRouteDecision(
        recommended=recommended,
        alternatives=alternatives,
        all_critical=all_critical,
        any_simulated=any_simulated,
        ts=time.time(),
    )
