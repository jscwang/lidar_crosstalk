"""Does the extra ambient light matter for the range readings themselves?

At dtheta = 0 and at the peak level, for each distance and zone, compare a sensor's range statistics with both sensors running
against the same sensor alone, per block, pooled over A and B, then summarised over the five blocks:
    bias    = mean range with both - mean range alone  (mm, valid readings only)
    SD ratio = SD of range with both / SD alone        (geometric mean over blocks, 95% t interval on the log)
    valid   = share of readings with range_status 0 when the sensor ranges alone
and the extra ambient as a multiple of the solo ambient rate.

Run:   python manuscript_ieee/scripts/range_effects.py
Out:   manuscript_ieee/analysis/range_effects.csv

Author: Jessica
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crossover_analysis as ca  # noqa: E402
from rig import analysis as an  # noqa: E402


def t_ci(x: np.ndarray):
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan"), float("nan"), float("nan")
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))
    return m, m - h, m + h


def main():
    rows = []
    for d, name in ca.DISTANCES.items():
        data = an.load(ca.DATA / name)
        data.runs["tag"] = ""
        data.blocks["tag"] = ""
        rs = an.run_stats(data)
        pairs = an.pair_effects(rs)
        solo = rs[rs.condition.isin(["A", "B"]) & (rs.condition == rs.sensor)]
        for roi in ca.ZONES:
            g = pairs[pairs.roi == roi]
            peak_level = g.groupby("dtheta_deg").extra_ambient.mean().idxmax()
            for lvl in sorted({0.0, float(peak_level), 24.0}):
                h = g[g.dtheta_deg == lvl]
                blk = h.groupby("block_id")[["bias_mm", "log_sd_ratio", "extra_ambient", "solo_ambient"]].mean()
                sub = solo[(solo.roi == roi) & (solo.dtheta_deg == lvl)]
                valid = (sub.n_valid.sum() / sub.n.sum()) if len(sub) else float("nan")
                b = t_ci(blk.bias_mm.to_numpy(float))
                s = t_ci(blk.log_sd_ratio.to_numpy(float))
                rows.append({"distance_m": d, "zone": f"{roi}x{roi}", "dtheta_deg": lvl, "n_blocks": len(blk),
                             "valid_share_solo": valid,
                             "bias_mm": b[0], "bias_lo": b[1], "bias_hi": b[2],
                             "sd_ratio": math.exp(s[0]) if np.isfinite(s[0]) else float("nan"),
                             "sd_ratio_lo": math.exp(s[1]) if np.isfinite(s[1]) else float("nan"),
                             "sd_ratio_hi": math.exp(s[2]) if np.isfinite(s[2]) else float("nan")})
    out = pd.DataFrame(rows)
    out.to_csv(ca.OUT / "range_effects.csv", index=False)

    # Extra ambient as a multiple of the solo rate, FULL ARRAY ONLY. For the 4x4 window sensor B's solo ambient is 0.1-2.2 kcps
    # (sensor A's is 5-9 kcps), so a per-sensor ratio is dominated by noise in B's denominator, and a pooled ratio is dominated
    # by A; neither is a stable number, so none is reported for that zone. (An earlier version of this block averaged
    # per-sensor ratios and gave 4x4 values of 81x, 157x and 20x against 51x, 16x and 5x for the pooled form: the instability.)
    from scipy.interpolate import PchipInterpolator
    ext = pd.read_csv(ca.OUT / "extinction.csv").set_index(["distance_m", "zone"])
    rr = []
    for d, name in ca.DISTANCES.items():
        data = an.load(ca.DATA / name)
        data.runs["tag"] = ""
        data.blocks["tag"] = ""
        pairs = an.pair_effects(an.run_stats(data))
        g = pairs[pairs.roi == 16]
        lv = g.groupby("dtheta_deg")[["extra_ambient", "solo_ambient"]].mean()
        ratio = lv.extra_ambient / lv.solo_ambient
        a1 = ext.loc[(d, "16x16"), "angle_at_1pct_deg"]
        rr.append({"distance_m": d, "zone": "16x16", "solo_at_0_kcps": lv.solo_ambient.iloc[0],
                   "solo_at_24_kcps": lv.solo_ambient.iloc[-1], "extra_over_solo_at_0": ratio.iloc[0],
                   "angle_1pct_deg": a1,
                   "extra_over_solo_at_1pct_angle": float(PchipInterpolator(ratio.index.to_numpy(float), ratio.to_numpy(float))(a1))})
    pd.DataFrame(rr).to_csv(ca.OUT / "extra_over_solo_fullarray.csv", index=False)
    print(pd.DataFrame(rr).round(3).to_string(index=False))
    pd.set_option("display.width", 250)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
