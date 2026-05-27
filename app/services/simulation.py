from __future__ import annotations
import random
from typing import Literal

from app.models.sections import (
    SECTION_IDS,
    UNISEX_SECTIONS,
    SectionState,
    SectionStatus,
)

ScenarioName = Literal[
    "normal",
    "pre_show",
    "during_show",
    "post_show_surge",
    "wc05_overcrowded",
    "wc06_relief",
    "ir_offline",
    "wifi_offline",
    "camera_offline",
    "lorawan_fallback",
    "all_sensors_degraded",
    "sensors_disagree",
    "all_wcs_critical",
    "zero_people",
    "recovery_after_redirect",
]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _status(ocupacao: float, offline: bool = False) -> SectionStatus:
    if offline:
        return "offline"
    if ocupacao >= 90:
        return "critical"
    if ocupacao >= 70:
        return "warning"
    return "normal"


def _make_section(
    section_id: str,
    ocupacao_pct: float,
    fila_atual: int,
    tempo_espera_min: float,
    fluxo_entrada_pmin: float,
    offline: bool = False,
) -> SectionState:
    gender = None
    if section_id not in UNISEX_SECTIONS and "_" in section_id:
        suffix = section_id.rsplit("_", 1)[-1]
        if suffix in ("M", "F"):
            gender = suffix  # type: ignore[assignment]

    return SectionState(
        section_id=section_id,
        ocupacao_pct=round(min(100.0, max(0.0, ocupacao_pct)), 1),
        fila_atual=max(0, fila_atual),
        tempo_espera_min=round(max(0.0, tempo_espera_min), 1),
        fluxo_entrada_pmin=round(max(0.0, fluxo_entrada_pmin), 2),
        status=_status(ocupacao_pct, offline),
        gender=gender,
        simulated=True,
    )


def _normal_base(tick: int) -> list[SectionState]:
    """Baseline: mild activity, smooth sinusoidal variation per tick."""
    rng = _rng(tick)
    states = []
    for sid in SECTION_IDS:
        base = 30.0 + rng.uniform(-10, 10)
        occ = base + 10 * (tick % 20) / 20.0
        fila = int(occ / 15)
        espera = fila * 0.5
        fluxo = rng.uniform(1.0, 3.0)
        states.append(_make_section(sid, occ, fila, espera, fluxo))
    return states


def simulate_tick(scenario: str, tick: int) -> list[SectionState]:
    """Return deterministic list[SectionState] for a given scenario and tick.

    All returned states have simulated=True.
    WC-05 and WC-06 never have gender.
    Deterministic per scenario+tick (tick used as seed for smooth animation).
    """
    rng = _rng(tick * 31 + hash(scenario) % 1000)

    if scenario == "normal":
        return _normal_base(tick)

    elif scenario == "pre_show":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 500)
            occ = 50.0 + rng2.uniform(0, 20) + (tick % 10) * 2
            fila = int(occ / 12)
            espera = fila * 0.6
            fluxo = rng2.uniform(3.0, 6.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "during_show":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 700)
            occ = 75.0 + rng2.uniform(-5, 20)
            fila = int(occ / 8)
            espera = fila * 0.8
            fluxo = rng2.uniform(5.0, 10.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "post_show_surge":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 900)
            # Surge decays after 30 ticks
            surge_factor = max(0.0, 1.0 - (tick % 30) / 30.0)
            occ = 85.0 * surge_factor + 30.0 * (1 - surge_factor) + rng2.uniform(-5, 5)
            fila = int(occ / 7)
            espera = fila * 1.0
            fluxo = rng2.uniform(4.0, 12.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "wc05_overcrowded":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 300)
            if sid == "WC-05":
                occ = 95.0 + rng2.uniform(0, 5)
                fila = 20 + rng2.randint(0, 5)
                espera = 8.0 + rng2.uniform(0, 2)
                fluxo = 12.0
            else:
                occ = 40.0 + rng2.uniform(-10, 15)
                fila = int(occ / 15)
                espera = fila * 0.5
                fluxo = rng2.uniform(2.0, 5.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "wc06_relief":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 400)
            if sid == "WC-06":
                # WC-06 is operating well, taking overflow from elsewhere
                occ = 45.0 + rng2.uniform(-5, 10)
                fila = int(occ / 20)
                espera = fila * 0.3
                fluxo = rng2.uniform(4.0, 7.0)
            else:
                occ = 80.0 + rng2.uniform(-10, 15)
                fila = int(occ / 9)
                espera = fila * 0.9
                fluxo = rng2.uniform(5.0, 9.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "ir_offline":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 200)
            # IR offline → lower confidence, WiFi+Camera only
            occ = 50.0 + rng2.uniform(-15, 20)
            fila = int(occ / 13)
            espera = fila * 0.6
            fluxo = rng2.uniform(2.0, 5.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "wifi_offline":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 250)
            occ = 45.0 + rng2.uniform(-10, 20)
            fila = int(occ / 14)
            espera = fila * 0.55
            fluxo = rng2.uniform(1.5, 4.5)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "camera_offline":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 350)
            occ = 55.0 + rng2.uniform(-15, 15)
            fila = int(occ / 12)
            espera = fila * 0.65
            fluxo = rng2.uniform(2.0, 6.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "lorawan_fallback":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 600)
            # LoRaWAN fallback: cached last-known values with drift
            drift = (tick % 10) * 0.5
            occ = 60.0 + drift + rng2.uniform(-5, 5)
            fila = int(occ / 11)
            espera = fila * 0.7
            fluxo = rng2.uniform(1.0, 3.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "all_sensors_degraded":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 800)
            # Noisy readings, wider variance
            occ = 50.0 + rng2.uniform(-25, 35)
            fila = max(0, int(occ / 10))
            espera = fila * 1.2
            fluxo = rng2.uniform(0.5, 8.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "sensors_disagree":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 550)
            # Artificially conflicting readings — wide spread
            occ = rng2.uniform(20, 85)
            fila = int(occ / 10)
            espera = fila * rng2.uniform(0.3, 1.5)
            fluxo = rng2.uniform(1.0, 10.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "all_wcs_critical":
        states = []
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 100)
            occ = 92.0 + rng2.uniform(0, 8)
            fila = 25 + rng2.randint(0, 10)
            espera = 10.0 + rng2.uniform(0, 5)
            fluxo = 14.0 + rng2.uniform(0, 3)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    elif scenario == "zero_people":
        states = []
        for sid in SECTION_IDS:
            states.append(_make_section(sid, 0.0, 0, 0.0, 0.0))
        return states

    elif scenario == "recovery_after_redirect":
        states = []
        recovery_progress = min(1.0, (tick % 40) / 40.0)
        for sid in SECTION_IDS:
            rng2 = _rng(tick + abs(hash(sid)) % 450)
            # Sections recovering from critical: occupancy declines over time
            peak = 90.0 + rng2.uniform(0, 10)
            occ = peak * (1 - recovery_progress) + 30.0 * recovery_progress
            occ += rng2.uniform(-5, 5)
            fila = max(0, int(occ / 12))
            espera = fila * 0.6
            fluxo = rng2.uniform(1.0, 5.0)
            states.append(_make_section(sid, occ, fila, espera, fluxo))
        return states

    else:
        # Unknown scenario → fall back to normal
        return _normal_base(tick)
