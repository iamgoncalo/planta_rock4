"""
PlantaOS — Sensor topology and fusion parameters.
All configurable constants live here; never hardcode in fusion.py or elsewhere.
§1.1 source inventory, §3.2 base weights, §3.3 Prosegur filter params.
"""
from __future__ import annotations

# §3.2  Base weights (IR=0.50, WiFi=0.30, Camera=0.20 — NorthStar spec)
BASE_WEIGHTS: dict[str, float] = {
    "ir":   0.50,
    "wifi": 0.30,
    "cam":  0.20,
}

# §1.2  WiFi reliability cap: range bleed + MAC randomisation make it unreliable
WIFI_RELIABILITY_CAP: float = 0.6

# §1.1  Clusters that skip IR (USAR_IR=false — unisex with no directional beams)
USAR_IR: dict[str, bool] = {
    "wc-01": True,
    "wc-02": True,
    "wc-03": True,
    "wc-04": True,
    "wc-05": False,   # entry-only unisex, no IR directional sensors
    "wc-06": False,   # bidirectional unisex, highest traffic
    "wc-07": True,
    "wc-08": True,
}

# §3.4  Confidence floor when stale or all sources dead
CONF_FLOOR: float = 0.15

# §3.3  Prosegur complementary filter
BETA: float = 0.05       # slow drift-correction rate (per update)
MAX_DRIFT: float = 30.0  # maximum IR drift correction in people

# §3.1  Staleness: data older than this → freshness decays to 0
STALE_THRESHOLD_MS: int = 180_000   # 3 minutes

# §3.4  Liveness trust bonus: more independent senses → more trust
LIVENESS_TRUST: dict[int, float] = {1: 0.50, 2: 0.80, 3: 1.00}

# §1.7  Cluster ID regex (I-7)
CLUSTER_ID_RE: str = r"^wc-0[1-8]$"

# §0 I-8  The one and only critical colour — never red
CRITICAL_COLOUR: str = "#C25A1A"
