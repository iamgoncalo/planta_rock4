"""Tests 15-19: Routing service contracts."""
from __future__ import annotations

import pytest
from app.models.sections import SectionState, SECTION_IDS
from app.models.routing import BathroomRouteDecision
from app.services.routing import compute_route, _build_option

# Fixed user position at venue centre
_USER_LAT = 38.782
_USER_LON = -9.093


def _make_section(
    section_id: str,
    ocupacao_pct: float = 40.0,
    fila_atual: int = 5,
    tempo_espera_min: float = 2.0,
    status: str = "normal",
    simulated: bool = True,
) -> SectionState:
    gender = None
    if "_" in section_id:
        suffix = section_id.rsplit("_", 1)[-1]
        if suffix in ("M", "F"):
            gender = suffix  # type: ignore[assignment]
    return SectionState(
        section_id=section_id,
        ocupacao_pct=ocupacao_pct,
        fila_atual=fila_atual,
        tempo_espera_min=tempo_espera_min,
        status=status,  # type: ignore[arg-type]
        simulated=simulated,
        gender=gender,
    )


# ---------------------------------------------------------------------------
# Test 15 — Nearest WC is 100% full, farther WC is 20% → farther WC recommended
# ---------------------------------------------------------------------------
def test_routing_prefers_less_full_over_nearest():
    """
    WC-01 (nearest cluster at 38.782,-9.093) is critical/full.
    WC-07 is farther but nearly empty.
    Routing must prefer WC-07_M despite the walk penalty.
    """
    sections = [
        # WC-01 full/critical
        _make_section("WC-01_M", ocupacao_pct=100.0, fila_atual=30, tempo_espera_min=15.0, status="critical"),
        _make_section("WC-01_F", ocupacao_pct=100.0, fila_atual=25, tempo_espera_min=12.0, status="critical"),
        # WC-07 farther but very light
        _make_section("WC-07_M", ocupacao_pct=20.0, fila_atual=1, tempo_espera_min=0.5, status="normal"),
        _make_section("WC-07_F", ocupacao_pct=15.0, fila_atual=1, tempo_espera_min=0.3, status="normal"),
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, active_show=None)
    assert decision.recommended.section_id in ("WC-07_M", "WC-07_F"), (
        f"Expected farther but emptier WC-07, got {decision.recommended.section_id}"
    )


def test_routing_does_not_recommend_full_when_empty_available():
    """When a non-critical alternative exists, critical WCs must not be recommended."""
    sections = [
        _make_section("WC-02_M", ocupacao_pct=100.0, fila_atual=20, tempo_espera_min=10.0, status="critical"),
        _make_section("WC-08_M", ocupacao_pct=20.0, fila_atual=1, tempo_espera_min=0.5, status="normal"),
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, active_show=None)
    assert decision.recommended.section_id == "WC-08_M"
    assert "critical" not in decision.recommended.avoidance_reasons


# ---------------------------------------------------------------------------
# Test 16 — Critical WC → safety_penalty=10 applied
# ---------------------------------------------------------------------------
def test_routing_critical_section_has_safety_penalty():
    """A critical section must have a total_cost significantly higher than a normal one."""
    critical_section = _make_section("WC-03_M", ocupacao_pct=95.0, tempo_espera_min=0.0, status="critical")
    normal_section = _make_section("WC-03_F", ocupacao_pct=95.0, tempo_espera_min=0.0, status="normal")

    opt_critical = _build_option(critical_section, _USER_LAT, _USER_LON, active_show=None)
    opt_normal = _build_option(normal_section, _USER_LAT, _USER_LON, active_show=None)

    # Safety penalty for critical is 10.0 min — total must be notably higher
    assert opt_critical.total_cost_min > opt_normal.total_cost_min + 5.0, (
        f"Critical penalty not applied: critical_cost={opt_critical.total_cost_min}, "
        f"normal_cost={opt_normal.total_cost_min}"
    )
    assert "critical" in opt_critical.avoidance_reasons


def test_routing_critical_safety_penalty_is_10():
    """The difference in total cost between critical and otherwise-identical normal section
    must be at least 10 minutes (the safety_penalty constant)."""
    critical = _make_section("WC-04_M", ocupacao_pct=50.0, fila_atual=0, tempo_espera_min=0.0, status="critical")
    normal = _make_section("WC-04_F", ocupacao_pct=50.0, fila_atual=0, tempo_espera_min=0.0, status="normal")

    opt_c = _build_option(critical, _USER_LAT, _USER_LON, None)
    opt_n = _build_option(normal, _USER_LAT, _USER_LON, None)

    assert opt_c.total_cost_min >= opt_n.total_cost_min + 10.0, (
        f"Expected ≥10 min safety penalty; diff={opt_c.total_cost_min - opt_n.total_cost_min}"
    )


# ---------------------------------------------------------------------------
# Test 17 — Offline WC → not recommended when alternatives exist
# ---------------------------------------------------------------------------
def test_routing_offline_section_not_recommended():
    """An offline section must never be recommended when an online alternative exists."""
    sections = [
        _make_section("WC-05", ocupacao_pct=10.0, fila_atual=0, tempo_espera_min=0.0, status="offline"),
        _make_section("WC-06", ocupacao_pct=30.0, fila_atual=2, tempo_espera_min=1.0, status="normal"),
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, active_show=None)
    assert decision.recommended.section_id != "WC-05", (
        "Offline WC-05 must not be recommended when WC-06 is available"
    )
    assert "offline" not in decision.recommended.avoidance_reasons


def test_routing_offline_option_has_avoidance_reason():
    """An offline section's RouteOption must contain 'offline' in avoidance_reasons."""
    offline = _make_section("WC-01_M", ocupacao_pct=0.0, status="offline")
    opt = _build_option(offline, _USER_LAT, _USER_LON, None)
    assert "offline" in opt.avoidance_reasons


# ---------------------------------------------------------------------------
# Test 18 — total_cost = walk + queue + congestion + surge + confidence_penalty + safety
# ---------------------------------------------------------------------------
def test_routing_total_cost_components_normal_section():
    """For a normal section, total_cost must equal walk + queue + congestion + confidence_penalty
    (surge=0 and safety_penalty=0 for normal status)."""
    section = _make_section("WC-08_F", ocupacao_pct=40.0, fila_atual=4, tempo_espera_min=2.0, status="normal")
    opt = _build_option(section, _USER_LAT, _USER_LON, active_show=None)

    # congestion_penalty = min(3.0, ocupacao/100 * 3.0) = min(3.0, 0.4*3.0) = 1.2
    expected_congestion = min(3.0, section.ocupacao_pct / 100.0 * 3.0)
    # confidence for normal = 0.9 → confidence_penalty = (1-0.9)*2.0 = 0.2
    expected_conf_penalty = (1.0 - 0.9) * 2.0
    # surge = 0 (no show), safety = 0 (normal)
    expected_cost = (
        opt.walk_time_min
        + section.tempo_espera_min
        + expected_congestion
        + expected_conf_penalty
    )
    assert abs(opt.total_cost_min - expected_cost) < 0.1, (
        f"total_cost mismatch: got {opt.total_cost_min}, expected ~{expected_cost:.2f}"
    )


def test_routing_total_cost_critical_includes_safety():
    """For a critical section, total_cost must include the 10-min safety_penalty."""
    section = _make_section("WC-02_F", ocupacao_pct=95.0, fila_atual=10, tempo_espera_min=5.0, status="critical")
    opt = _build_option(section, _USER_LAT, _USER_LON, active_show=None)

    # safety_penalty = 10.0 for critical
    # confidence for critical = 0.6 → confidence_penalty = (1-0.6)*2.0 = 0.8
    congestion = min(3.0, 95.0 / 100.0 * 3.0)
    expected_cost = opt.walk_time_min + 5.0 + congestion + 0.8 + 10.0
    assert abs(opt.total_cost_min - expected_cost) < 0.1, (
        f"total_cost for critical: got {opt.total_cost_min}, expected ~{expected_cost:.2f}"
    )


def test_routing_total_cost_is_non_negative():
    """total_cost_min must always be ≥ 0."""
    for sid in SECTION_IDS:
        s = _make_section(sid, ocupacao_pct=0.0, fila_atual=0, tempo_espera_min=0.0, status="normal")
        opt = _build_option(s, _USER_LAT, _USER_LON, None)
        assert opt.total_cost_min >= 0.0, f"{sid}: total_cost={opt.total_cost_min} < 0"


# ---------------------------------------------------------------------------
# Test 19 — all_critical=True only when ALL sections are critical
# ---------------------------------------------------------------------------
def test_routing_all_critical_false_when_one_normal():
    """If even one section is non-critical, all_critical must be False."""
    sections = [
        _make_section("WC-01_M", ocupacao_pct=95.0, status="critical"),
        _make_section("WC-01_F", ocupacao_pct=95.0, status="critical"),
        _make_section("WC-05", ocupacao_pct=30.0, status="normal"),  # one normal
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, None)
    assert decision.all_critical is False


def test_routing_all_critical_true_when_every_section_is_critical_or_offline():
    """all_critical is True only when every section has status in {critical, offline}."""
    sections = [
        _make_section("WC-01_M", ocupacao_pct=95.0, status="critical"),
        _make_section("WC-01_F", ocupacao_pct=95.0, status="critical"),
        _make_section("WC-05", ocupacao_pct=0.0, status="offline"),
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, None)
    assert decision.all_critical is True


def test_routing_all_critical_true_all_sections_critical():
    """all_critical=True when all 14 sections are critical."""
    sections = [
        _make_section(sid, ocupacao_pct=95.0, fila_atual=20, tempo_espera_min=10.0, status="critical")
        for sid in SECTION_IDS
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, None)
    assert decision.all_critical is True


def test_routing_all_critical_false_mixed_statuses():
    """If sections are a mix of warning and critical, all_critical is False."""
    sections = [
        _make_section("WC-03_M", ocupacao_pct=95.0, status="critical"),
        _make_section("WC-03_F", ocupacao_pct=75.0, status="warning"),
    ]
    decision = compute_route(sections, _USER_LAT, _USER_LON, None)
    assert decision.all_critical is False


def test_routing_result_is_bathroom_route_decision():
    """compute_route must return a BathroomRouteDecision instance."""
    sections = [_make_section(sid) for sid in ("WC-05", "WC-06")]
    decision = compute_route(sections, _USER_LAT, _USER_LON, None)
    assert isinstance(decision, BathroomRouteDecision)
    assert decision.recommended is not None
    assert isinstance(decision.alternatives, list)
