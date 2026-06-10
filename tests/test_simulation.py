"""Tests 31-36: Simulation service invariants."""
from __future__ import annotations

import pytest
from app.models.sections import SECTION_IDS, UNISEX_SECTIONS, SectionState
from app.services.simulation import simulate_tick, ScenarioName

# All 15 valid scenario names
ALL_SCENARIOS = [
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


# ---------------------------------------------------------------------------
# Test 31 — All 15 scenarios run without exception
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenario_runs_without_exception(scenario: str):
    """simulate_tick must not raise for any valid scenario at any tick."""
    try:
        states = simulate_tick(scenario, tick=0)
        assert states is not None
    except Exception as exc:
        pytest.fail(f"simulate_tick('{scenario}', 0) raised {exc!r}")


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenario_runs_at_multiple_ticks(scenario: str):
    """simulate_tick must be stable across multiple ticks."""
    for tick in (0, 1, 10, 50, 100):
        try:
            states = simulate_tick(scenario, tick=tick)
            assert states is not None
        except Exception as exc:
            pytest.fail(f"simulate_tick('{scenario}', {tick}) raised {exc!r}")


def test_exactly_15_scenarios_defined():
    """There must be exactly 15 scenario names (as per the spec)."""
    assert len(ALL_SCENARIOS) == 15


# ---------------------------------------------------------------------------
# Test 32 — Each scenario returns exactly 14 SectionState objects
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenario_returns_14_sections(scenario: str):
    states = simulate_tick(scenario, tick=1)
    assert len(states) == 14, (
        f"Scenario '{scenario}' returned {len(states)} sections, expected 14"
    )


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenario_returns_section_state_objects(scenario: str):
    states = simulate_tick(scenario, tick=1)
    for s in states:
        assert isinstance(s, SectionState), (
            f"Scenario '{scenario}' returned non-SectionState: {type(s)}"
        )


# ---------------------------------------------------------------------------
# Test 33 — No scenario produces a state with section_id outside SECTION_IDS
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenario_section_ids_all_valid(scenario: str):
    states = simulate_tick(scenario, tick=5)
    valid_ids = set(SECTION_IDS)
    for s in states:
        assert s.section_id in valid_ids, (
            f"Scenario '{scenario}' produced invalid section_id '{s.section_id}'"
        )


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenario_no_gendered_unisex_ids(scenario: str):
    """Gendered variants of the unisex sections must never appear."""
    forbidden = {f"{cid}_{g}" for cid in ("WC-05", "WC-06") for g in ("M", "F")}
    states = simulate_tick(scenario, tick=5)
    for s in states:
        assert s.section_id not in forbidden, (
            f"Scenario '{scenario}' produced forbidden section_id '{s.section_id}'"
        )


# ---------------------------------------------------------------------------
# Test 34 — any_simulated=True in all simulation outputs
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_all_sections_simulated_true(scenario: str):
    """Every SectionState produced by simulate_tick must have simulated=True."""
    states = simulate_tick(scenario, tick=3)
    for s in states:
        assert s.simulated is True, (
            f"Scenario '{scenario}': section {s.section_id} has simulated=False"
        )


# ---------------------------------------------------------------------------
# Test 35 — all_wcs_critical → all sections have status="critical"
# ---------------------------------------------------------------------------
def test_all_wcs_critical_scenario_all_critical():
    states = simulate_tick("all_wcs_critical", tick=0)
    non_critical = [s for s in states if s.status != "critical"]
    assert non_critical == [], (
        f"all_wcs_critical produced non-critical sections: "
        f"{[s.section_id + ':' + s.status for s in non_critical]}"
    )


def test_all_wcs_critical_occupancy_above_threshold():
    """In all_wcs_critical, all sections must have ocupacao_pct >= 90."""
    states = simulate_tick("all_wcs_critical", tick=2)
    for s in states:
        assert s.ocupacao_pct >= 90.0, (
            f"all_wcs_critical: {s.section_id} has ocupacao_pct={s.ocupacao_pct} < 90"
        )


def test_all_wcs_critical_at_multiple_ticks():
    """The all_wcs_critical scenario must remain critical across ticks."""
    for tick in (0, 5, 10, 50):
        states = simulate_tick("all_wcs_critical", tick=tick)
        non_critical = [s for s in states if s.status != "critical"]
        assert non_critical == [], (
            f"all_wcs_critical tick={tick}: non-critical sections found"
        )


# ---------------------------------------------------------------------------
# Test 36 — zero_people → all ocupacao_pct=0
# ---------------------------------------------------------------------------
def test_zero_people_scenario_all_zero_occupancy():
    states = simulate_tick("zero_people", tick=0)
    for s in states:
        assert s.ocupacao_pct == 0.0, (
            f"zero_people: {s.section_id} has ocupacao_pct={s.ocupacao_pct}, expected 0"
        )


def test_zero_people_scenario_zero_queues():
    states = simulate_tick("zero_people", tick=0)
    for s in states:
        assert s.fila_atual == 0, (
            f"zero_people: {s.section_id} has fila_atual={s.fila_atual}, expected 0"
        )


def test_zero_people_scenario_zero_wait_time():
    states = simulate_tick("zero_people", tick=0)
    for s in states:
        assert s.tempo_espera_min == 0.0, (
            f"zero_people: {s.section_id} has tempo_espera_min={s.tempo_espera_min}, expected 0"
        )


def test_zero_people_scenario_at_multiple_ticks():
    """zero_people must stay at zero across ticks (deterministic)."""
    for tick in (0, 1, 10, 42):
        states = simulate_tick("zero_people", tick=tick)
        for s in states:
            assert s.ocupacao_pct == 0.0, (
                f"zero_people tick={tick}: {s.section_id} has ocupacao_pct={s.ocupacao_pct}"
            )


# ---------------------------------------------------------------------------
# Additional: unisex sections never have gender in simulation output
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_simulation_unisex_sections_have_no_gender(scenario: str):
    states = simulate_tick(scenario, tick=0)
    for s in states:
        if s.section_id in UNISEX_SECTIONS:
            assert s.gender is None, (
                f"Scenario '{scenario}': unisex section {s.section_id} has gender={s.gender}"
            )


# ---------------------------------------------------------------------------
# Additional: ocupacao_pct in [0, 100] for all scenarios
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_simulation_ocupacao_pct_in_range(scenario: str):
    states = simulate_tick(scenario, tick=7)
    for s in states:
        assert 0.0 <= s.ocupacao_pct <= 100.0, (
            f"Scenario '{scenario}': {s.section_id} ocupacao_pct={s.ocupacao_pct} out of [0,100]"
        )
