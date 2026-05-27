from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

AvoidanceReason = Literal["critical", "offline", "low_confidence", "surge", "full"]


class RouteNode(BaseModel):
    node_id: str
    section_id: str
    walk_time_from_user_min: float
    gps_lat: float
    gps_lon: float


class RouteEdge(BaseModel):
    from_node: str
    to_node: str
    walk_time_min: float


class RouteOption(BaseModel):
    section_id: str
    walk_time_min: float
    queue_wait_min: float
    total_cost_min: float
    confidence: float
    avoidance_reasons: list[AvoidanceReason]
    simulated: bool


class BathroomRouteDecision(BaseModel):
    recommended: RouteOption
    alternatives: list[RouteOption]
    all_critical: bool
    any_simulated: bool
    ts: float
