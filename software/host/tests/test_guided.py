"""Guided operator, the LED command and the skip-higher-angles rule, against the simulator.

Author: Jessica
"""
import io
import json
from collections import deque

import pytest

from rig import protocol as p
from rig.device import Device
from rig.guided import GuidedOperator
from rig.matrix import Config, load_config, plan
from rig.session import Session
from rig.simulator import SimOperator, SimTransport


def make(cfg, **kw):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    buf = io.StringIO()
    op = GuidedOperator(dev, cfg, out=buf, color=False, angle_wait=None, sleep=lambda s: None, **kw)
    return t, dev, op, buf


def cfg_at(distance, **kw):
    c = Config(name="g", distances_m=(distance,), theta_per_side_deg=(0, 10), rois=(16,), repeats=2,
               run_ms=1000, warmup_s=1, seed=3, **kw)
    c.validate()
    return c


def test_waits_for_the_target_then_returns_and_lights_the_leds():
    cfg = cfg_at(0.8)
    t, dev, op, buf = make(cfg)
    phys = t.device.physics
    phys.d_m = 0.85                     # target 50 mm too far when the check starts

    def fix(n):
        if n == 2:
            phys.d_m = 0.80             # the person moves it
    op.on_poll = fix
    assert op.setup(0.8, 0, True) is None
    text = buf.getvalue()
    assert "too far" in text and "move it closer" in text
    assert "READY" in text and "OK (3/3)" in text
    assert t.device.led == "ok"          # green at the end


def test_needs_three_good_readings_in_a_row():
    cfg = cfg_at(0.3)
    t, dev, op, buf = make(cfg)
    phys = t.device.physics
    phys.d_m = 0.30
    calls = []

    def bump(n):
        calls.append(n)
        if n == 2:                       # a bad reading in the middle resets the count
            phys.d_m = 0.36
        if n == 3:
            phys.d_m = 0.30
    op.on_poll = bump
    op.setup(0.3, 0, True)
    assert len(calls) >= 6               # 1 good, 1 good, 1 bad, then three good
    assert buf.getvalue().count("OK (3/3)") == 1


@pytest.mark.parametrize("a,b,ok,words", [
    (800, 806, True, []),
    (800, 830, False, ["tilt +56.3 deg", "closer"]),
    (830, 800, False, ["tilt -56.3 deg", "farther away"]),
    (860, 862, False, ["too far"]),
    (740, 742, False, ["too close", "move it back"]),
])
def test_judge(a, b, ok, words):
    op = GuidedOperator(None, cfg_at(0.8), out=io.StringIO(), color=False)
    good, todo = op.judge(a, b, 800.0)
    assert good is ok
    for w in words:
        assert any(w in line for line in todo)


def test_expected_range_comes_from_the_config_else_the_distance():
    cfg = cfg_at(0.3, expected_range_mm={0.3: 288.0, 0.8: 803.0})
    op = GuidedOperator(None, cfg, out=io.StringIO(), color=False)
    assert op.expected(0.3) == 288.0 and op.expected(0.8) == 803.0
    assert GuidedOperator(None, cfg_at(0.5), out=io.StringIO(), color=False).expected(0.5) == 500.0


def test_failed_selftest_holds_the_run_until_it_passes():
    cfg = cfg_at(0.3)
    t, dev, op, buf = make(cfg)
    real = dev.selftest
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            return 1, [p.Test("int_idle_B", "FAIL", "GPIO6 level=0 expected=1")]
        return real()
    dev.selftest = flaky
    op.setup(0.3, 0, True)
    text = buf.getvalue()
    assert "self-test failed 1 check" in text and "int_idle_B" in text and "READY" in text
    assert state["n"] == 2


def test_gives_up_after_max_polls():
    cfg = cfg_at(0.8)
    t, dev, op, buf = make(cfg, max_polls=3)
    t.device.physics.d_m = 0.5           # never fixed
    with pytest.raises(TimeoutError):
        op.setup(0.8, 0, True)
    assert t.device.led == "off"


def test_enter_wait_is_asked_only_when_the_angle_changes():
    cfg = cfg_at(0.3)
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    asked = []
    op = GuidedOperator(dev, cfg, out=io.StringIO(), color=False, angle_wait="enter",
                        sleep=lambda s: None, input_fn=lambda msg: asked.append(msg) or "")
    op.setup(0.3, 0, True)
    op.setup(0.3, 0, True)               # same angle, only a distance change: no question
    op.setup(0.3, 10, False)
    assert len(asked) == 2


def test_led_command_and_old_firmware_fallback():
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    assert dev.led("bad") and t.device.led == "bad"
    assert dev.led("off") and t.device.led == "off"
    with pytest.raises(ValueError):
        dev.led("purple")

    class OldFirmware:
        def __init__(self):
            self.queue = deque()
            self.sent = []

        def write_line(self, line):
            self.sent.append(line)
            self.queue.extend(["ERR ? code=unknown_cmd msg=unknown command"])

        def read_line(self, timeout):
            return self.queue.popleft() if self.queue else None

        def close(self):
            pass
    assert Device(OldFirmware()).led("ok") is False


# ------------------------------------------------------------------ adaptive stop
def adaptive_cfg(**kw):
    c = Config(name="a", distances_m=(0.3,), theta_per_side_deg=(20, 0, 15, 10, 5), rois=(16,), repeats=2,
               run_ms=1000, warmup_s=1, seed=5, adaptive_stop_ratio=1.10, **kw)
    c.validate()
    return c


def test_adaptive_plan_runs_angles_in_ascending_order():
    order = []
    for b in plan(adaptive_cfg()):
        if b.theta_deg not in order:
            order.append(b.theta_deg)
    assert order == [0, 5, 10, 15, 20]


def test_higher_angles_are_skipped_once_the_crosstalk_is_gone(tmp_path):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    cfg = adaptive_cfg()
    op = SimOperator(t.device)
    summary = Session(dev, cfg, tmp_path / "s", op).run()
    # the simulated crosstalk is gone by dtheta 30 (15 per side): 20 per side is never run
    assert summary["skipped"] == 2 and summary["accepted"] == 8
    assert [s[1] for s in op.setups] == [0, 5, 10, 15]
    log = (tmp_path / "s" / "events.log").read_text(encoding="utf-8")
    assert "adaptive stop at d=0.3 m after theta=15" in log and "crosstalk check" in log
    assert any("skipping the higher angles" in m for m in op.messages)


def test_a_continuing_session_still_stops(tmp_path):
    """Resume keeps working: the blocks already done are skipped and the rule still applies."""
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    cfg = adaptive_cfg()
    Session(dev, cfg, tmp_path / "s", SimOperator(t.device)).run()
    again = Session(dev, cfg, tmp_path / "s", SimOperator(t.device)).run()
    assert again["accepted"] == 0 and again["gave_up"] == 0


def test_config_fields_validate_and_load(tmp_path):
    bad = [dict(adaptive_stop_ratio=0.9), dict(adaptive_stop_ratio=1.1, adaptive_confirm=0),
           dict(range_tol_mm=0), dict(square_tol_mm=-1)]
    for kw in bad:
        with pytest.raises(ValueError):
            Config(name="x", distances_m=(0.3,), theta_per_side_deg=(0, 5), rois=(16,), repeats=1,
                   run_ms=1000, **kw).validate()
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"name": "c", "distances_m": [0.3, 0.8], "theta_per_side_deg": [0, 5],
                                "rois": [16], "repeats": 1, "run_ms": 1000,
                                "expected_range_mm": {"0.3": 288, "0.8": 803}, "adaptive_stop_ratio": 1.1}),
                    encoding="utf-8")
    cfg = load_config(path)
    assert cfg.expected_range_mm == {0.3: 288.0, 0.8: 803.0} and cfg.adaptive_stop_ratio == 1.1
    assert json.loads(json.dumps(cfg.to_json(), default=str))["adaptive_confirm"] == 1


def test_led_command_line(capsys):
    from rig.cli import main
    assert main(["led", "ok", "--sim"]) == 0
    assert "LED ok" in capsys.readouterr().out


def test_led_hold_turns_the_lights_off_afterwards(capsys, monkeypatch):
    import time
    from rig.cli import main
    monkeypatch.setattr(time, "sleep", lambda s: None)
    assert main(["led", "bad", "--sim", "--hold", "5"]) == 0
    out = capsys.readouterr().out
    assert "LED bad" in out and "holding it for 5 s" in out and out.rstrip().endswith("LED off")


def test_expected_range_can_follow_the_angle():
    cfg = cfg_at(0.3, expected_range_mm={0.3: {0.0: 288.0, 30.0: 318.0}, 0.8: 803.0})
    op = GuidedOperator(None, cfg, out=io.StringIO(), color=False)
    assert op.expected(0.3, 0.0) == 288.0 and op.expected(0.3, 30.0) == 318.0
    assert op.expected(0.3, 10.0) == pytest.approx(298.0)      # read straight between the two points
    assert op.expected(0.3, 40.0) == 318.0 and op.expected(0.3, -10.0) == pytest.approx(298.0)
    assert op.expected(0.8, 10.0) == 803.0                     # one number still works
    assert op.expected(1.2, 10.0) == 1200.0                    # no entry: the nominal distance


def test_squareness_is_judged_against_the_measured_offset():
    cfg = cfg_at(0.3, expected_range_mm={0.3: 288.0}, square_offset_mm=4.0, square_tol_mm=2.0)
    op = GuidedOperator(None, cfg, out=io.StringIO(), color=False)
    ok, todo = op.judge(288.0, 292.0, 288.0)                   # B-A is the offset: square
    assert ok and not todo
    assert op.tilt_deg(288.0, 292.0) == pytest.approx(0.0)
    ok, todo = op.judge(288.0, 298.0, 288.0)                   # 6 mm beyond the offset
    assert not ok and "turn target, B-side edge closer" in todo[0]
    assert "tilt +16.7 deg" in todo[0]                         # 20 mm apart: atan(6/20)
    assert op.tilt_deg(288.0, 282.0) == pytest.approx(-26.6, abs=0.1)


def test_angle_table_is_read_from_the_config_file(tmp_path):
    from rig.matrix import load_config
    f = tmp_path / "c.json"
    f.write_text(json.dumps({"name": "t", "distances_m": [0.3], "theta_per_side_deg": [0, 30], "rois": [16],
                             "repeats": 1, "run_ms": 1000, "square_offset_mm": 4,
                             "expected_range_mm": {"0.3": {"0": 288, "30": 318}}}), encoding="utf-8")
    cfg = load_config(f)
    assert cfg.expected_range_mm == {0.3: {0.0: 288.0, 30.0: 318.0}} and cfg.square_offset_mm == 4.0
    f.write_text(json.dumps({"name": "t", "distances_m": [0.3], "theta_per_side_deg": [0], "rois": [16],
                             "repeats": 1, "run_ms": 1000, "expected_range_mm": {"0.3": {}}}), encoding="utf-8")
    with pytest.raises(ValueError, match="empty angle table"):
        load_config(f)


def test_the_geometry_check_ranges_each_sensor_alone():
    """With both ranging, the other sensor's light shifts the range, so the check must not use an A+B run."""
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    dev.configure(p.Settings())
    op = GuidedOperator(dev, cfg_at(0.3, expected_range_mm={0.3: 288.0}), out=io.StringIO(), color=False,
                        check_ms=400)
    a, b = op._measure()
    assert a is not None and b is not None
    assert t.device.runs_started[-2:] == ["guideA", "guideB"]


def test_tilt_uses_the_sensitivity_at_the_puck_angle():
    cfg = cfg_at(0.6, square_offset_mm=2.5, square_tol_mm=10.0)
    op = GuidedOperator(None, cfg, out=io.StringIO(), color=False)
    # at 12 degrees per side and 586 mm, -5.5 mm of B minus A (relative to the offset) is about -1.2 degrees of
    # tilt, not the -15 the flat 20 mm spacing formula gives at 0 degrees
    assert op.tilt_deg(588.0, 585.0, 12.0) == pytest.approx(-1.2, abs=0.2)
    assert op.tilt_deg(588.0, 585.0, 0.0) == pytest.approx(-15.4, abs=0.3)
    ok, todo = op.judge(588.0, 585.0, 586.0, 12.0)
    assert ok                                  # the pass/fail check is in millimetres and is unchanged
