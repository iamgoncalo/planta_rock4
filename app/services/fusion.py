from __future__ import annotations
from typing import Optional

# Nominal sensor fusion weights
_W_IR = 0.50
_W_WIFI = 0.30
_W_CAMERA = 0.20

# Disagreement threshold (30%)
_DISAGREE_THRESHOLD = 0.30


def fuse(
    ir_entry: Optional[float],
    ir_exit: Optional[float],
    wifi_people: Optional[float],
    camera_count: Optional[float],
) -> tuple[float, float, list[str]]:
    """Fuse sensor readings into (occupancy_delta_per_min, confidence, issues).

    Weights: IR=0.50, WiFi=0.30, Camera=0.20.
    Missing sources have their weight redistributed proportionally.
    Never divides by zero. Never returns negative occupancy delta.
    """
    issues: list[str] = []

    # Derive IR net flow: entries minus exits
    ir_value: Optional[float] = None
    if ir_entry is not None and ir_exit is not None:
        ir_value = float(ir_entry) - float(ir_exit)
    elif ir_entry is not None:
        ir_value = float(ir_entry)
    elif ir_exit is not None:
        ir_value = -float(ir_exit)

    # Build available sources with base weights
    sources: dict[str, tuple[float, float]] = {}  # name -> (value, weight)
    if ir_value is not None:
        sources["ir"] = (ir_value, _W_IR)
    if wifi_people is not None:
        sources["wifi"] = (float(wifi_people), _W_WIFI)
    if camera_count is not None:
        sources["camera"] = (float(camera_count), _W_CAMERA)

    if not sources:
        return (0.0, 0.0, ["all_sensors_missing"])

    # Redistribute weights so they sum to 1.0
    total_weight = sum(w for _, w in sources.values())
    if total_weight == 0.0:
        return (0.0, 0.0, ["all_sensors_missing"])

    scaled: dict[str, tuple[float, float]] = {
        name: (val, w / total_weight)
        for name, (val, w) in sources.items()
    }

    # Weighted average
    fused_value = sum(val * w for val, w in scaled.values())

    # Confidence: base from number of active sources
    active_count = len(sources)
    base_confidence = {1: 0.5, 2: 0.75, 3: 1.0}.get(active_count, 0.5)

    # Check disagreement among sources with more than one reading
    if active_count >= 2:
        values = [val for val, _ in scaled.values()]
        v_min = min(values)
        v_max = max(values)
        span = abs(v_max - v_min)
        reference = max(abs(v_max), abs(v_min), 1.0)  # avoid division by zero
        if span / reference > _DISAGREE_THRESHOLD:
            issues.append("sensors_disagree")
            base_confidence *= 0.75  # lower confidence when sensors disagree

    # Track missing sensors
    if "ir" not in sources:
        issues.append("ir_missing")
    if "wifi" not in sources:
        issues.append("wifi_missing")
    if "camera" not in sources:
        issues.append("camera_missing")

    confidence = max(0.0, min(1.0, base_confidence))

    # Never return negative occupancy delta
    occupancy_delta = max(0.0, fused_value)

    return (round(occupancy_delta, 3), round(confidence, 3), issues)
