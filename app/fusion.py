"""
PlantaOS — Canonical Edge-Fusion Engine (NorthStar §3).

Implements:
  §3.1  Per-source estimate + self-reliability
  §3.2  Reliability-gated weighted fusion with auto-redistribution
  §3.3  Prosegur complementary filter (IR drift correction)
  §3.4  Confidence (agreement × liveness × anchor accord)
  §3.5  Section output contract

Invariants enforced:
  I-1: no environmental data in this pipeline
  I-3: all fusion lives here — firmware emits raw signals only
  I-4: never divide by zero — guard every denominator
  I-5: always emit `confianca` ∈ [0,1]
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Literal, Optional

from app.sensors_topology import (
    BASE_WEIGHTS, BETA, CLUSTER_ID_RE, CONF_FLOOR, CRITICAL_COLOUR,
    LIVENESS_TRUST, MAX_DRIFT, STALE_THRESHOLD_MS, USAR_IR,
    WIFI_RELIABILITY_CAP,
)
from app.clusters_capacity import CLUSTER_CAPACITY


# ─────────────────────────────────────────────────────────────────────────────
# I-1..I-8 startup assertions (call from tests or lifespan hook)
# ─────────────────────────────────────────────────────────────────────────────
def startup_assert() -> None:
    """Assert all NorthStar invariants. Raises AssertionError on violation."""
    from app.clusters_capacity import ALL_CLUSTERS

    # I-7  cluster IDs
    for cid in ALL_CLUSTERS:
        assert re.match(CLUSTER_ID_RE, cid), (
            f"I-7 violated: '{cid}' does not match {CLUSTER_ID_RE!r}"
        )

    # I-3 / weights  base weights sum to 1
    total_w = sum(BASE_WEIGHTS.values())
    assert abs(total_w - 1.0) < 1e-9, (
        f"BASE_WEIGHTS sum={total_w:.10f}, expected 1.0"
    )

    # I-5  confianca field exists on FusionResult
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(FusionResult)}
    assert "confianca" in field_names, "I-5 violated: FusionResult missing 'confianca'"

    # I-8  critical colour
    assert CRITICAL_COLOUR == "#C25A1A", (
        f"I-8 violated: CRITICAL_COLOUR={CRITICAL_COLOUR!r}, expected '#C25A1A'"
    )

    # I-4  verified structurally: every denominator in fuse_section is guarded


# ─────────────────────────────────────────────────────────────────────────────
# Data contracts
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class FusionInput:
    """Raw signals from the firmware ingest payload (§2.3).
    No weights, no confidence — that is the backend's job (I-3).
    """
    section_id: str                          # e.g. "wc-01_m" (lowercase)
    ts_ms: int                               # epoch milliseconds from device
    entradas_ir: Optional[int] = None        # cumulative IR entries since reset
    saidas_ir: Optional[int] = None          # cumulative IR exits since reset
    pessoas_estimadas: Optional[float] = None  # WiFi-derived (divisor applied on node)
    luxonis_count: Optional[float] = None    # camera ML head count (edge)
    model_conf: float = 1.0                  # camera model confidence [0,1]
    contagem_prosegur: Optional[int] = None  # Prosegur zone head count (anchor)
    estado_sensor: str = "ok"               # ok | ir_fault | wifi_fault | offline
    ts_ir_ms: Optional[int] = None          # timestamp of IR reading
    ts_wifi_ms: Optional[int] = None        # timestamp of WiFi reading
    ts_cam_ms: Optional[int] = None         # timestamp of camera reading
    usar_ir: bool = True                    # False for wc-05, wc-06


@dataclass
class FusionResult:
    """Section output contract (§3.5). Pushed to state / ws / screen / SCOR."""
    cluster_id: str
    seccao: str                              # "m" | "f" | "u"
    ocupacao_pct: float
    fila_actual: int
    tempo_espera_min: float
    fluxo_entrada_pmin: float
    ocupacao_pct_fused: float
    confianca: float                         # I-5: ALWAYS present ∈ [0,1]
    fontes_activas: list[str]
    estado: str                              # livre | moderado | cheio | critico
    stale: bool
    ts: int                                  # epoch milliseconds


# ─────────────────────────────────────────────────────────────────────────────
# Per-section mutable state (in-memory, single-process)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class _SectionState:
    ir_drift_correction: float = 0.0
    last_good: Optional[FusionResult] = None
    last_entradas_ir: Optional[int] = None
    last_ts_ms: Optional[int] = None


_STATE: dict[str, _SectionState] = {}
_RESULTS: dict[str, FusionResult] = {}


def _get_state(section_id: str) -> _SectionState:
    if section_id not in _STATE:
        _STATE[section_id] = _SectionState()
    return _STATE[section_id]


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────
def health_factor(estado_sensor: str) -> float:
    """0.0 if sensor is in a fault/offline state, 1.0 otherwise."""
    return 0.0 if estado_sensor in ("ir_fault", "wifi_fault", "offline") else 1.0


def _freshness(ts_ms: Optional[int], now_ms: int) -> float:
    """Linear decay toward 0 as data ages past STALE_THRESHOLD_MS."""
    if ts_ms is None:
        return 0.0
    age_ms = max(0, now_ms - ts_ms)
    if age_ms >= STALE_THRESHOLD_MS:
        return 0.0
    return max(0.3, 1.0 - 0.7 * (age_ms / STALE_THRESHOLD_MS))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _coeff_of_variation(values: list[float]) -> float:
    """Population coefficient of variation. Returns 0 when mean=0 (guards /0, I-4)."""
    m = mean(values) if values else 0.0
    if m <= 0:
        return 0.0
    return pstdev(values) / m


def _estado_from_pct(pct: float) -> str:
    if pct < 50:
        return "livre"
    if pct < 70:
        return "moderado"
    if pct < 85:
        return "cheio"
    return "critico"


def _section_capacity(section_id: str) -> int:
    """Capacity for a section_id like 'wc-01_m'. Returns ≥1 (I-4 guard)."""
    parts = section_id.split("_")
    cluster = parts[0]
    gender = parts[1] if len(parts) > 1 else None
    cap_data = CLUSTER_CAPACITY.get(cluster, {})
    if gender == "m":
        return max(1, int(cap_data.get("masc", 1)))
    if gender == "f":
        return max(1, int(cap_data.get("fem", 1)))
    # unisex: use masc (full capacity stored there)
    return max(1, int(cap_data.get("masc", 1)))


# ─────────────────────────────────────────────────────────────────────────────
# §3.4  Confidence
# ─────────────────────────────────────────────────────────────────────────────
def _confidence(
    o: dict[str, float],
    prosegur_target: Optional[float],
    fused: float,
    stale: bool,
) -> float:
    if stale:
        return CONF_FLOOR

    live = list(o.values())
    n = len(live)

    # 1) inter-source agreement: low spread → high confidence
    agree = (
        1.0 - _clamp(_coeff_of_variation(live), 0.0, 1.0)
        if n > 1
        else 0.45
    )

    # 2) liveness: more independent senses → more trust
    liveness = LIVENESS_TRUST.get(n, 0.5)

    # 3) anchor accord: Prosegur expected vs fused
    if prosegur_target is not None and prosegur_target > 0:
        accord = 1.0 - _clamp(abs(fused - prosegur_target) / prosegur_target, 0.0, 1.0)
    else:
        accord = 0.5   # no anchor → neutral

    conf = 0.45 * agree + 0.30 * liveness + 0.25 * accord
    return round(_clamp(conf, CONF_FLOOR, 1.0), 3)


# ─────────────────────────────────────────────────────────────────────────────
# §3.3  Prosegur complementary filter (IR drift correction)
# ─────────────────────────────────────────────────────────────────────────────
def update_ir_drift(cluster_id: str, section_ids: list[str], prosegur_zone_count: int) -> None:
    """
    Slow-walk each section's IR baseline toward the Prosegur zone anchor.
    IR = high-frequency truth; Prosegur = low-frequency ground truth.
    Call once per Prosegur update, not per tick.
    """
    if prosegur_zone_count <= 0:
        return

    # Compute each section's current IR-derived occupancy (people)
    ir_people: dict[str, float] = {}
    for sid in section_ids:
        if sid in _RESULTS:
            cap = _section_capacity(sid)
            ir_people[sid] = _RESULTS[sid].ocupacao_pct * cap / 100.0
        else:
            ir_people[sid] = 0.0

    ir_zone_sum = sum(ir_people.values())
    if ir_zone_sum <= 0:
        return  # I-4: guard /0

    for sid in section_ids:
        share = ir_people[sid] / ir_zone_sum   # I-4: ir_zone_sum > 0 above
        target = prosegur_zone_count * share
        error = ir_people[sid] - target
        st = _get_state(sid)
        st.ir_drift_correction = _clamp(
            st.ir_drift_correction + BETA * error,
            -MAX_DRIFT,
            MAX_DRIFT,
        )


# ─────────────────────────────────────────────────────────────────────────────
# §3.1–3.2  Main fusion function
# ─────────────────────────────────────────────────────────────────────────────
def fuse_section(inp: FusionInput) -> FusionResult:
    """
    Reliability-gated weighted fusion (§3.1–3.5).
    I-4: never divides by zero.
    I-5: always returns confianca.
    """
    now_ms = int(time.time() * 1000)
    st = _get_state(inp.section_id)

    parts = inp.section_id.split("_")
    cluster_id = parts[0]
    seccao = parts[1] if len(parts) > 1 else "u"
    cap = _section_capacity(inp.section_id)

    hf = health_factor(inp.estado_sensor)

    # §3.1  Per-source estimates (o) and reliabilities (r)
    o: dict[str, float] = {}
    r: dict[str, float] = {}

    # IR — direction-aware, drift-corrected
    if inp.usar_ir and inp.entradas_ir is not None and inp.saidas_ir is not None:
        o_ir_raw = max(0.0, float(inp.entradas_ir - inp.saidas_ir) - st.ir_drift_correction)
        o["ir"] = o_ir_raw
        r["ir"] = hf * _freshness(inp.ts_ir_ms or inp.ts_ms, now_ms)
    # wc-05/06: usar_ir=False → r_ir stays 0 (excluded from w)

    # WiFi — aggregate only, reliability capped (range bleed)
    if inp.pessoas_estimadas is not None:
        o["wifi"] = max(0.0, float(inp.pessoas_estimadas))
        r["wifi"] = min(
            WIFI_RELIABILITY_CAP,
            hf * _freshness(inp.ts_wifi_ms or inp.ts_ms, now_ms),
        )

    # Camera ML — only where Luxonis node exists
    if inp.luxonis_count is not None:
        o["cam"] = max(0.0, float(inp.luxonis_count))
        r["cam"] = inp.model_conf * _freshness(inp.ts_cam_ms or inp.ts_ms, now_ms)

    # §3.2  Effective weight = base × reliability, then renormalise
    w = {k: BASE_WEIGHTS.get(k, 0.0) * r.get(k, 0.0) for k in o}
    w = {k: v for k, v in w.items() if v > 0}
    total_w = sum(w.values())

    if total_w == 0:
        # I-4: all senses dead → hold last-good, mark stale
        if st.last_good is not None:
            lg = st.last_good
            return FusionResult(
                cluster_id=lg.cluster_id, seccao=lg.seccao,
                ocupacao_pct=lg.ocupacao_pct, fila_actual=lg.fila_actual,
                tempo_espera_min=lg.tempo_espera_min,
                fluxo_entrada_pmin=lg.fluxo_entrada_pmin,
                ocupacao_pct_fused=lg.ocupacao_pct_fused,
                confianca=CONF_FLOOR,
                fontes_activas=[], estado=lg.estado,
                stale=True, ts=now_ms,
            )
        return FusionResult(
            cluster_id=cluster_id, seccao=seccao,
            ocupacao_pct=0.0, fila_actual=0, tempo_espera_min=0.0,
            fluxo_entrada_pmin=0.0, ocupacao_pct_fused=0.0,
            confianca=CONF_FLOOR, fontes_activas=[], estado="livre",
            stale=True, ts=now_ms,
        )

    # I-4: total_w > 0 guaranteed above
    w = {k: v / total_w for k, v in w.items()}    # renormalise → Σ = 1
    fused_people = sum(w[k] * o[k] for k in w)

    ocupacao_pct = round(_clamp(fused_people / cap * 100.0, 0.0, 100.0), 1)

    # Queue estimate (smooth — no hard cutoff)
    over = fused_people - cap * 0.80
    fila = max(0, int(round(over))) if over > 0 else 0
    espera = round(fila * 0.18, 1)

    # Per-minute entry flow (delta IR over elapsed time)
    if (inp.entradas_ir is not None
            and st.last_entradas_ir is not None
            and st.last_ts_ms is not None
            and inp.ts_ms > st.last_ts_ms):
        delta_ir = max(0, inp.entradas_ir - st.last_entradas_ir)
        elapsed_min = max(0.01, (inp.ts_ms - st.last_ts_ms) / 60_000.0)
        fluxo = round(delta_ir / elapsed_min, 1)
    else:
        fluxo = 0.0

    # Update flow tracking state
    if inp.entradas_ir is not None:
        st.last_entradas_ir = inp.entradas_ir
        st.last_ts_ms = inp.ts_ms

    # Prosegur anchor for confidence
    prosegur_target: Optional[float] = (
        float(inp.contagem_prosegur) if inp.contagem_prosegur is not None else None
    )

    confianca = _confidence(
        o={k: v for k, v in o.items() if k in w},
        prosegur_target=prosegur_target,
        fused=fused_people,
        stale=False,
    )

    result = FusionResult(
        cluster_id=cluster_id,
        seccao=seccao,
        ocupacao_pct=ocupacao_pct,
        fila_actual=fila,
        tempo_espera_min=espera,
        fluxo_entrada_pmin=fluxo,
        ocupacao_pct_fused=ocupacao_pct,
        confianca=confianca,
        fontes_activas=list(w.keys()),
        estado=_estado_from_pct(ocupacao_pct),
        stale=False,
        ts=now_ms,
    )
    st.last_good = result
    _RESULTS[inp.section_id] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Result store (read by state.py to enrich live payload)
# ─────────────────────────────────────────────────────────────────────────────
def get_fused(section_id: str) -> Optional[FusionResult]:
    """Return latest fusion result for a section, or None if never fused."""
    return _RESULTS.get(section_id)


def get_all_fused() -> dict[str, FusionResult]:
    return dict(_RESULTS)
