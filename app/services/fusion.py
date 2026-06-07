"""
PlantaOS — Shim de fusao sensorial (interface de compatibilidade, tests 8-14).
Expoe fuse(), _W_IR, _W_WIFI, _W_CAMERA com pesos canonicos NorthStar §3.2.
A fusao por-seccao completa (§3.1-3.5) vive em app/fusion.py.
"""
from __future__ import annotations

from statistics import mean, pstdev
from typing import Optional

from app.sensors_topology import BASE_WEIGHTS, CONF_FLOOR, LIVENESS_TRUST

# Pesos NorthStar §3.2 — IR=0.50, WiFi=0.30, Camera=0.20
_W_IR     = BASE_WEIGHTS["ir"]    # 0.50
_W_WIFI   = BASE_WEIGHTS["wifi"]  # 0.30
_W_CAMERA = BASE_WEIGHTS["cam"]   # 0.20


def fuse(
    ir_entry: Optional[float],
    ir_exit: Optional[float],
    wifi_devices: Optional[float],
    camera_count: Optional[float],
) -> tuple[float, float, list[str]]:
    """
    Fusao com redistribuicao de pesos (I-4: nunca divide por zero).
    Retorna (delta_pessoas: float, confianca: float, problemas: list[str]).
    delta >= 0 sempre. confianca in [CONF_FLOOR, 1.0] salvo all_sensors_missing.
    """
    issues: list[str] = []
    estimates: dict[str, float] = {}

    if ir_entry is not None and ir_exit is not None:
        estimates["ir"] = max(0.0, float(ir_entry) - float(ir_exit))
    else:
        issues.append("ir_missing")

    if wifi_devices is not None:
        estimates["wifi"] = max(0.0, float(wifi_devices))
    else:
        issues.append("wifi_missing")

    if camera_count is not None:
        estimates["cam"] = max(0.0, float(camera_count))
    else:
        issues.append("camera_missing")

    if not estimates:
        return 0.0, 0.0, ["all_sensors_missing"]

    # Pesos efectivos renormalizados (I-4: total_w > 0 garantido)
    raw_w = {k: BASE_WEIGHTS[k] for k in estimates}
    total_w = sum(raw_w.values())
    w = {k: v / total_w for k, v in raw_w.items()}
    delta = sum(w[k] * estimates[k] for k in w)

    # Confianca §3.4 (sem ancora Prosegur → accord neutro = 0.5)
    vals = list(estimates.values())
    n = len(vals)
    m = mean(vals)
    if n > 1:
        cv = pstdev(vals) / m if m > 0 else 0.0
        agree = 1.0 - min(cv, 1.0)
        if cv > 0.3:
            issues.append("sensors_disagree")
    else:
        agree = 0.45  # fonte solo: concordancia moderada

    liveness = LIVENESS_TRUST.get(n, 0.5)
    accord = 0.5
    confidence = 0.45 * agree + 0.30 * liveness + 0.25 * accord
    confidence = round(max(CONF_FLOOR, min(1.0, confidence)), 3)

    return round(max(0.0, delta), 6), confidence, issues
