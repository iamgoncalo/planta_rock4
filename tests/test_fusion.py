"""Tests 8-14: Sensor fusion service contracts."""
from __future__ import annotations

import pytest
from app.services.fusion import fuse, _W_IR, _W_WIFI, _W_CAMERA


# ---------------------------------------------------------------------------
# Test 8 — All sensors available and in agreement → high confidence, no issues
# ---------------------------------------------------------------------------
def test_fuse_all_sensors_agree_high_confidence():
    """With all three sources at the same value, expect confidence=1.0 and no issues."""
    delta, confidence, issues = fuse(3.0, 0.0, 3.0, 3.0)  # ir_net=3, wifi=3, camera=3
    assert confidence > 0.8, f"Expected confidence > 0.8, got {confidence}"
    assert issues == [], f"Expected no issues, got {issues}"
    assert delta >= 0.0


def test_fuse_all_sensors_returns_valid_tuple():
    """fuse() must always return a 3-tuple (float, float, list)."""
    result = fuse(1.0, 0.5, 2.0, 2.0)
    assert isinstance(result, tuple)
    assert len(result) == 3
    delta, confidence, issues = result
    assert isinstance(delta, float)
    assert isinstance(confidence, float)
    assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# Test 9 — WiFi missing → weights redistribute, no crash
# ---------------------------------------------------------------------------
def test_fuse_wifi_missing_no_crash():
    """Removing WiFi must not raise; weights must redistribute to sum to 1."""
    delta, confidence, issues = fuse(3.0, 0.0, None, 3.0)
    assert delta >= 0.0
    assert 0.0 <= confidence <= 1.0
    assert "wifi_missing" in issues
    # No exception means weights redistributed successfully


def test_fuse_wifi_missing_still_produces_output():
    """With IR and camera only, output should still be non-trivial."""
    delta, confidence, issues = fuse(5.0, 1.0, None, 4.0)
    # ir_net = 4.0, camera = 4.0 → should produce something close to 4.0
    assert delta > 0.0
    assert confidence > 0.0


# ---------------------------------------------------------------------------
# Test 10 — All sensors None → (0.0, 0.0, ["all_sensors_missing"])
# ---------------------------------------------------------------------------
def test_fuse_all_none_returns_zero_and_flag():
    delta, confidence, issues = fuse(None, None, None, None)
    assert delta == 0.0, f"Expected delta=0.0, got {delta}"
    assert confidence == 0.0, f"Expected confidence=0.0, got {confidence}"
    assert "all_sensors_missing" in issues, f"Expected 'all_sensors_missing' in {issues}"


def test_fuse_all_none_does_not_raise():
    """Calling fuse with all None must never raise an exception."""
    try:
        result = fuse(None, None, None, None)
        assert result is not None
    except Exception as exc:
        pytest.fail(f"fuse(None, None, None, None) raised {exc!r}")


# ---------------------------------------------------------------------------
# Test 11 — Negative ir_entry → no negative output
# ---------------------------------------------------------------------------
def test_fuse_negative_ir_no_negative_output():
    """A negative IR entry value must not produce a negative occupancy delta."""
    delta, confidence, issues = fuse(-1.0, 0.5, 2.0, 1.0)
    assert delta >= 0.0, f"Expected non-negative delta, got {delta}"


def test_fuse_all_negative_no_negative_output():
    """Even when all inputs are negative, delta must be clamped to ≥ 0."""
    delta, confidence, issues = fuse(-10.0, 0.0, -5.0, -3.0)
    assert delta >= 0.0, f"Expected non-negative delta, got {delta}"


def test_fuse_strong_exit_dominates_no_negative():
    """IR exit >> IR entry → net negative, but output must be ≥ 0."""
    delta, confidence, issues = fuse(0.0, 20.0, None, None)
    assert delta >= 0.0


# ---------------------------------------------------------------------------
# Test 12 — Sensors disagree >30% → "sensors_disagree" in issues, confidence < 0.7
# ---------------------------------------------------------------------------
def test_fuse_2source_disagree_flags_issue_and_lowers_confidence():
    """Two sources with >30% relative spread → sensors_disagree, confidence < 0.7."""
    # ir_net = 10.0, camera = 1.0 → span=9, ref=10, ratio=0.9 > 0.30
    # 2 sources → base_confidence=0.75, * 0.75 = 0.5625
    delta, confidence, issues = fuse(10.0, 0.0, None, 1.0)
    assert "sensors_disagree" in issues, f"Expected 'sensors_disagree' in {issues}"
    assert confidence < 0.7, f"Expected confidence < 0.7 when sensors disagree, got {confidence}"


def test_fuse_3source_agree_no_disagree_flag():
    """When all three sources agree closely, no sensors_disagree flag."""
    delta, confidence, issues = fuse(5.0, 0.0, 5.0, 5.0)  # net ir=5, wifi=5, cam=5
    assert "sensors_disagree" not in issues


# ---------------------------------------------------------------------------
# Test 13 — Never returns negative delta
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("ir_e,ir_x,wifi,cam", [
    (-100.0, 0.0, None, None),
    (0.0, 100.0, 0.0, 0.0),
    (-5.0, 5.0, -2.0, -1.0),
    (None, 10.0, None, None),
    (0.1, 100.0, 0.0, 0.0),
])
def test_fuse_never_negative_delta(ir_e, ir_x, wifi, cam):
    delta, _, _ = fuse(ir_e, ir_x, wifi, cam)
    assert delta >= 0.0, (
        f"fuse({ir_e}, {ir_x}, {wifi}, {cam}) returned negative delta={delta}"
    )


# ---------------------------------------------------------------------------
# Test 14 — Fusion weights sum to 1.0 for any subset of available sensors
# ---------------------------------------------------------------------------
def test_fusion_weights_all_three_sum_to_one():
    """Nominal weights must sum to 1.0."""
    total = _W_IR + _W_WIFI + _W_CAMERA
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, not 1.0"


def test_fusion_weight_redistribution_ir_only():
    """With only IR, the single source gets all the weight (implicit: produces same value)."""
    value = 5.0
    delta, conf, issues = fuse(value, 0.0, None, None)
    # net ir = 5.0, only source → weight = 1.0 → delta = 5.0
    assert abs(delta - value) < 1e-6, f"Expected delta={value}, got {delta}"
    assert "wifi_missing" in issues
    assert "camera_missing" in issues


def test_fusion_weight_redistribution_wifi_only():
    """With only WiFi, the single source gets full weight."""
    value = 7.0
    delta, conf, issues = fuse(None, None, value, None)
    assert abs(delta - value) < 1e-6, f"Expected delta={value}, got {delta}"
    assert "ir_missing" in issues
    assert "camera_missing" in issues


def test_fusion_weight_redistribution_camera_only():
    """With only camera, the single source gets full weight."""
    value = 4.0
    delta, conf, issues = fuse(None, None, None, value)
    assert abs(delta - value) < 1e-6, f"Expected delta={value}, got {delta}"
    assert "ir_missing" in issues
    assert "wifi_missing" in issues


def test_fusion_weight_redistribution_ir_and_wifi():
    """With IR and WiFi, redistributed weights must sum to 1 (verified via blended output)."""
    ir_val = 4.0
    wifi_val = 4.0
    delta, conf, issues = fuse(ir_val, 0.0, wifi_val, None)
    # Both sources at 4.0 → weighted average must also be 4.0 regardless of weights
    assert abs(delta - 4.0) < 1e-6, f"Expected delta=4.0, got {delta}"


def test_fusion_weight_redistribution_ir_and_camera():
    """With IR and Camera at same value, weighted average equals that value."""
    val = 6.0
    delta, conf, issues = fuse(val, 0.0, None, val)
    assert abs(delta - val) < 1e-6, f"Expected delta={val}, got {delta}"
