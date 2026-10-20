"""Analysis maths, and recovery of a known crossover from a simulated session.

Author: Jessica
"""
import math

import numpy as np
import pandas as pd
import pytest
from scipy import optimize

from rig import analysis as an
from rig.device import Device
from rig.matrix import Config
from rig.session import Session
from rig.simulator import Physics, SimOperator, SimTransport, SimulatedDevice


def test_x10_closed_form_matches_root():
    for top, x0, w in ((100.0, 20.0, 2.0), (5.0, 8.0, 0.7), (1.0, 3.0, 4.0)):
        f = lambda x: an.logistic(x, top, x0, w) - 0.1 * an.logistic(0.0, top, x0, w)   # noqa: E731
        root = optimize.brentq(f, 0.0, 200.0)
        assert an.x10(top, x0, w) == pytest.approx(root, abs=1e-9)
    assert math.isnan(an.x10(-1.0, 10.0, 2.0))


def test_fit_recovers_noiseless_logistic():
    x = np.repeat(np.arange(0, 32, 2.0), 3)
    y = an.logistic(x, 800.0, 22.0, 1.8)
    popt = an.fit_logistic(x, y)
    assert popt == pytest.approx([800.0, 22.0, 1.8], rel=1e-4)
    assert an.fit_logistic(np.array([0.0, 10.0]), np.array([1.0, 0.0])) is None   # too few levels


def _rs(rows):
    base = dict(distance_m=0.3, roi=16, theta_deg=0.0, dtheta_deg=0.0, repeat=1, tag="", n=750, n_valid=750,
                mean_signal=1.0)
    return pd.DataFrame([{**base, **r} for r in rows])


def test_pair_effects_and_summary_numbers():
    rows = []
    for rep, (amb_solo, amb_ab, sd_solo, sd_ab) in enumerate([(400, 900, 1.0, 2.0), (420, 880, 1.2, 2.4)], 1):
        blk = f"b{rep}"
        for sensor in "AB":
            rows += [
                dict(run_id=f"{blk}{sensor}s", block_id=blk, repeat=rep, sensor=sensor, condition=sensor,
                     mean_mm=300.0, sd_mm=sd_solo, dropout=0.0, mean_ambient=amb_solo),
                dict(run_id=f"{blk}AB", block_id=blk, repeat=rep, sensor=sensor, condition="AB",
                     mean_mm=303.0, sd_mm=sd_ab, dropout=0.1, mean_ambient=amb_ab),
            ]
    pairs = an.pair_effects(_rs(rows))
    assert len(pairs) == 4
    assert sorted(pairs["extra_ambient"]) == [460, 460, 500, 500]
    assert np.allclose(pairs["sd_ratio"], 2.0) and np.allclose(pairs["bias_mm"], 3.0)
    assert np.allclose(pairs["extra_dropout"], 0.1)
    summ = an.summarize(pairs)
    row = summ.iloc[0]
    assert row["n_blocks"] == 2 and row["extra_ambient_mean"] == pytest.approx(480.0)
    assert row["sd_ratio_geomean"] == pytest.approx(2.0)
    # 95% t interval of (500, 460): 480 +/- 12.706 * 28.28 / sqrt(2)
    assert row["extra_ambient_ci_hi"] - 480 == pytest.approx(12.706 * 20.0, rel=1e-3)


def test_zero_sd_solo_does_not_crash():
    rows = [dict(run_id="s", block_id="b", sensor="A", condition="A", mean_mm=300.0, sd_mm=0.0, dropout=0.0,
                 mean_ambient=400.0),
            dict(run_id="ab", block_id="b", sensor="A", condition="AB", mean_mm=300.0, sd_mm=1.0, dropout=0.0,
                 mean_ambient=500.0)]
    pairs = an.pair_effects(_rs(rows))
    assert math.isnan(pairs.iloc[0]["sd_ratio"]) and math.isnan(pairs.iloc[0]["log_sd_ratio"])


@pytest.fixture(scope="module")
def fine_session(tmp_path_factory):
    """Simulated session with 1 deg steps around the crossover and a known truth."""
    cfg = Config(name="fine", distances_m=(0.3,), theta_per_side_deg=(0, 5, 8, 9, 10, 11, 12, 13, 14, 15, 17),
                 rois=(16, 4), repeats=4, run_ms=4000, warmup_s=1, seed=3)
    cfg.validate()
    dev_sim = SimulatedDevice(Physics(), seed=11)
    t = SimTransport(dev_sim)
    dev = Device(t)
    dev.connect()
    out = tmp_path_factory.mktemp("fine") / "s"
    Session(dev, cfg, out, SimOperator(dev_sim)).run()
    return out, dev_sim.physics


def test_crossover_recovered_from_simulated_session(fine_session):
    out, physics = fine_session
    res = an.analyze(out, n_boot=300, figures=True)
    xo = res["crossover"].set_index("roi")
    for roi in (16, 4):
        physics.d_m = 0.3
        truth = physics.true_x10(roi)
        row = xo.loc[roi]
        assert row["crossover_deg"] == pytest.approx(truth, abs=1.5), (roi, truth)
        assert row["ci_lo"] - 0.5 <= truth <= row["ci_hi"] + 0.5
        assert row["n_levels"] == 11 and row["note"] == ""
        assert row["predicted_deg"] == pytest.approx({16: 23.4, 4: 17.3}[roi], abs=0.05)
    assert res["counts"]["runs_usable"] == 11 * 2 * 4 * 3
    for name in ("fig1_extra_ambient", "fig2_sd_ratio", "fig3_dropout", "fig4_drift"):
        for ext in ("png", "pdf"):
            f = res["out"] / "figures" / f"{name}.{ext}"
            data = f.read_bytes()
            assert b"Jessica" in data and b"matplotlib" not in data.lower()
    assert "Author: Jessica" in (res["out"] / "summary.md").read_text(encoding="utf-8")


def test_crosstalk_is_significant_at_zero_and_gone_far_out(fine_session):
    out, _ = fine_session
    summ = pd.read_csv(out / "analysis" / "effects_summary.csv", keep_default_na=False)
    near = summ[(summ["dtheta_deg"] == 0)]
    far = summ[(summ["dtheta_deg"] == 34)]
    assert (near["extra_ambient_t_p"].astype(float) < 0.01).all()
    assert (near["extra_ambient_ci_lo"].astype(float) > 0).all()
    assert (far["extra_ambient_mean"].astype(float).abs() < 0.05 * near["extra_ambient_mean"].astype(float).max()).all()


def test_rejected_runs_are_excluded(tmp_path, small_cfg):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    t.device.inject("stray", {"r00002"})
    Session(dev, small_cfg, tmp_path / "s", SimOperator(t.device)).run()
    data = an.load(tmp_path / "s")
    usable = an.usable_runs(data)
    assert "r00002" not in set(usable["run_id"])
    # the whole first attempt of that block is excluded, not only the bad run
    assert not usable["run_id"].isin(["r00001", "r00003"]).any()
    assert len(usable) == 12
