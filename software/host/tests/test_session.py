"""Session runner end to end against the simulator.

Author: Jessica
"""
import csv
import json

import pytest

from rig.device import Device, DeviceError
from rig.matrix import plan
from rig.session import READING_FIELDS, RUN_FIELDS, Session
from rig.simulator import SimOperator, SimTransport

from conftest import cfg_with


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make(tmp_path, cfg, **kw):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    op = SimOperator(t.device)
    return t, Session(dev, cfg, tmp_path / "s", op, **kw), op


def test_full_small_session(tmp_path, small_cfg):
    t, sess, op = make(tmp_path, small_cfg)
    summary = sess.run()
    assert summary == {"accepted": 4, "gave_up": 0, "runs": 12, "rejected_runs": 0}
    out = tmp_path / "s"
    runs = rows(out / "runs.csv")
    blocks = rows(out / "blocks.csv")
    readings = rows(out / "readings.csv")
    assert list(runs[0].keys()) == RUN_FIELDS and list(readings[0].keys()) == READING_FIELDS
    assert len(runs) == 12 and all(r["accepted"] == "True" for r in runs)
    assert len(blocks) == 4 and all(b["accepted"] == "True" for b in blocks)
    # 25 readings per ranging sensor per 1 s run: A and B solo give 25, A+B gives 50
    assert len(readings) == 4 * (25 + 25 + 50)
    # the pucks moved only when the angle changed, warm-up once per distance
    assert op.setups == [(0.3, 0, True), (0.3, 10, False)]
    assert len(rows(out / "warmup.csv")) > 0
    meta = json.loads((out / "session.json").read_text(encoding="utf-8"))
    assert meta["author"] == "Jessica" and meta["starts"][0]["selftest"]["failed"] == 0
    # run order is the planned, seeded order and is logged
    planned = [c for b in plan(small_cfg) for c in b.conditions]
    assert [r["condition"] for r in runs] == planned
    assert "order" in (out / "events.log").read_text(encoding="utf-8")


def test_plan_is_reproducible_and_shuffled(small_cfg):
    a, b = plan(small_cfg), plan(small_cfg)
    assert a == b
    many = plan(cfg_with(small_cfg, repeats=10, rois=(16, 4)))
    assert len({blk.conditions for blk in many}) > 1          # conditions shuffled
    assert len({tuple(x.roi for x in many[i:i + 2]) for i in range(0, 40, 2)}) > 1   # ROI order shuffled
    thetas = [blk.theta_deg for blk in many]
    assert thetas == sorted(thetas)                             # pucks move once per angle


def test_rejected_run_redoes_the_block(tmp_path, small_cfg):
    t, sess, _ = make(tmp_path, small_cfg)
    t.device.inject("stray", {"r00002"})
    summary = sess.run()
    assert summary["accepted"] == 4 and summary["rejected_runs"] == 1
    blocks = rows(tmp_path / "s" / "blocks.csv")
    first = [b for b in blocks if b["block_id"] == blocks[0]["block_id"]]
    assert [b["accepted"] for b in first] == ["False", "True"]
    assert "stopped sensor" in first[0]["reason"]


def test_ambient_jump_redoes_the_block(tmp_path, small_cfg):
    t, sess, _ = make(tmp_path, small_cfg)
    blocks = plan(small_cfg)
    # first solo run of the second block at the same angle (runs are numbered in plan order)
    second_block_runs = [f"r{i:05d}" for i in range(4, 7)]
    solo = [rid for rid, c in zip(second_block_runs, blocks[1].conditions) if c != "AB"][0]
    t.device.inject("ambient_jump", {solo})
    sess.run()
    b2 = [b for b in rows(tmp_path / "s" / "blocks.csv") if b["block_id"] == blocks[1].block_id]
    assert b2[0]["accepted"] == "False" and "solo ambient" in b2[0]["reason"]
    assert b2[-1]["accepted"] == "True"


def test_device_reset_is_recovered(tmp_path, small_cfg):
    t, sess, _ = make(tmp_path, small_cfg)
    t.device.inject("reset", {"r00003"})
    summary = sess.run()
    assert summary["accepted"] == 4
    runs = rows(tmp_path / "s" / "runs.csv")
    assert "device reset" in runs[2]["reject_reason"]
    assert "DEVICE RESET" in (tmp_path / "s" / "events.log").read_text(encoding="utf-8")


def test_lost_settings_are_resent(tmp_path, small_cfg):
    t, sess, _ = make(tmp_path, small_cfg)
    t.device.inject("settings_lost", {"r00002"})
    summary = sess.run()
    assert summary["accepted"] == 4 and summary["rejected_runs"] == 1
    runs = rows(tmp_path / "s" / "runs.csv")
    assert "settings changed" in runs[1]["reject_reason"]
    # CFG was sent again before the next run
    after = t.sent[t.sent.index("RUN id=r00002 cond=%s dur=1000" % runs[1]["condition"]) + 1:]
    assert after[0].startswith("CFG ")


def test_missed_results_are_counted(tmp_path, small_cfg):
    cfg = cfg_with(small_cfg, run_ms=10000)
    t, sess, _ = make(tmp_path, cfg)
    t.device.inject("missed", {"r00001"})
    sess.run()
    runs = rows(tmp_path / "s" / "runs.csv")
    # one missing reading in about 250 leaves an 80 ms gap: counted, and under the 1% limit
    assert int(runs[0]["missed_A"]) + int(runs[0]["missed_B"]) == 1
    assert runs[0]["accepted"] == "True"


def test_block_given_up_after_max_attempts(tmp_path, small_cfg):
    cfg = cfg_with(small_cfg, max_block_attempts=2)
    t, sess, op = make(tmp_path, cfg)
    t.device.inject("i2c", {"r00001", "r00004"})   # first run of both attempts of block 1
    summary = sess.run()
    assert summary["gave_up"] == 1 and summary["accepted"] == 3
    assert any("failed 2 times" in m for m in op.messages)


class StopAfter(SimOperator):
    def __init__(self, device, n):
        super().__init__(device)
        self.n = n

    def setup(self, *a):
        if len(self.setups) == self.n:
            raise KeyboardInterrupt
        return super().setup(*a)


def test_interrupt_and_resume(tmp_path, small_cfg):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    with pytest.raises(KeyboardInterrupt):
        Session(dev, small_cfg, tmp_path / "s", StopAfter(t.device, 1)).run()
    assert len(rows(tmp_path / "s" / "blocks.csv")) == 2        # the theta=0 blocks
    assert t.sent[-2:] == ["ABORT", "STOPALL"]

    summary = Session(dev, small_cfg, tmp_path / "s", SimOperator(t.device)).run()
    assert summary["accepted"] == 2                              # only the remaining two
    runs = rows(tmp_path / "s" / "runs.csv")
    assert [r["run_id"] for r in runs] == [f"r{i:05d}" for i in range(1, 13)]
    meta = json.loads((tmp_path / "s" / "session.json").read_text(encoding="utf-8"))
    assert len(meta["starts"]) == 2


class FailingSelfTest(SimTransport):
    def write_line(self, line):
        if line == "SELFTEST":
            self.sent.append(line)
            self.queue.extend(["TEST name=run_A_A result=FAIL detail=n=3 problem=too few readings",
                               "SELFTEST failed=1", "OK SELFTEST"])
            return
        super().write_line(line)


def test_selftest_failure_stops_the_session(tmp_path, small_cfg):
    t = FailingSelfTest()
    dev = Device(t)
    dev.connect()
    with pytest.raises(DeviceError, match="self-test failed"):
        Session(dev, small_cfg, tmp_path / "s", SimOperator(t.device)).run()
    meta = json.loads((tmp_path / "s" / "session.json").read_text(encoding="utf-8"))
    assert meta["starts"][0]["selftest"]["failed"] == 1
    assert not any(line.startswith("RUN ") for line in t.sent)


def test_the_ambient_rule_uses_a_floor_in_a_dark_room(small_cfg):
    """In the dark the 4x4 solo ambient is about 1 kcps, where photon noise alone moves it by a fifth, so the
    share-of-reference rule has to be taken on a floor instead."""
    from dataclasses import replace
    from pathlib import Path

    from rig.session import RunResult
    cfg = replace(small_cfg, ambient_tolerance=0.10, ambient_floor_kcps=5.0)
    cfg.validate()
    dev = Device(SimTransport())
    dev.connect()
    sess = Session(dev, cfg, Path("."), SimOperator(SimTransport().device))
    b = plan(cfg)[0]
    for s_ in "AB":
        sess.ambient_ref[(b.distance_m, b.theta_deg, b.roi, s_)] = 1.4          # a dark room

    def results(value):
        return [RunResult(run_id=f"r{i}", condition=c, accepted=True, reason="",
                          solo_ambient=value if c in ("A", "B") else None) for i, c in enumerate(("A", "B", "AB"))]

    ok, why, _, _ = sess._judge_block(b, results(1.7))     # 0.3 kcps on 1.4 is 21%, but under the 0.5 allowance
    assert ok, why
    ok, why, _, _ = sess._judge_block(b, results(2.1))     # 0.7 kcps away: beyond the floor allowance
    assert not ok and "kcps from" in why
