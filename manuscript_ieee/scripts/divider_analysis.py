"""Divider check: extra ambient with the strip against the same cell without it, at each distance and zone.

For theta = 2 and 5 deg per side (dtheta = 4 and 10 deg), both zones, the divider session has five blocks per cell and the
no-divider main sweep has five blocks of the same cell. The effect is the difference of the two pooled cell means,
    change = mean(divider) - mean(no divider),   in kcps and as a percentage of the no-divider mean,
with a percentile bootstrap interval (the five blocks of each group resampled independently, 10,000 draws) and Welch's t test.

What the comparison can and cannot show. The divider and no-divider cells come from different sessions on different
occasions with the rig reset in between, so the divider is confounded with the session. The strip's size and position were
not recorded. A change near zero is therefore compatible with a strip that blocks nothing, and also with one that blocks a
part of a path while session differences offset it; it cannot demonstrate that no direct coupling exists. The solo ambient
rate is compared as well, to see whether the strip itself changes what a sensor sees.

Run:   python manuscript_ieee/scripts/divider_analysis.py
       CROSSOVER_CAMPAIGN=2 python manuscript_ieee/scripts/divider_analysis.py   # unit-swap campaign: swap_* vs div_swap_*
Out:   manuscript_ieee/analysis[_campaignN]/divider_effect.csv, divider_solo.csv, divider_replicate_0p6.csv

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

N_BOOT = 10000
SEED = ca.SEED + 11
SRC = ca.PROJECT.parent / "Jessica-data" / "pair13_sources"
LEVELS = (2, 4, 10)   # dtheta of the divider cells
# campaign 1: 0.6 m was rerun on the re-squared board with the campaign-2-style protocol (theta=1,2,5, so
# dtheta=2,4,10); the 0.3 and 0.9 m sessions still use the original protocol (theta=2,5, dtheta=4,10 only).
LEVELS_BY_DISTANCE = (
    {0.3: (4, 10), 0.6: (2, 4, 10), 0.9: (4, 10)} if ca.CAMPAIGN == "1" else
    {0.3: (2, 4, 10), 0.6: (2, 4, 10), 0.9: (2, 4, 10)}
)
NODIV_TO_DIV = (lambda n: n.replace("nodiv", "div")) if ca.CAMPAIGN == "1" else (lambda n: n.replace("swap", "div_swap"))


def folder_pairs(path: Path) -> pd.DataFrame:
    data = an.load(path)
    data.runs["tag"] = ""
    data.blocks["tag"] = ""
    return an.pair_effects(an.run_stats(data))


def cell_values(pairs: pd.DataFrame, roi: int, dth: float, col: str = "extra_ambient") -> np.ndarray:
    g = pairs[(pairs.roi == roi) & (pairs.dtheta_deg == dth)]
    return g.groupby("block_id")[col].mean().to_numpy(float)


def boot_diff(a: np.ndarray, b: np.ndarray, rng) -> tuple[float, float]:
    d = np.array([rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(N_BOOT)])
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def main():
    rng = np.random.default_rng(SEED)
    rows, solo_rows, rep_rows = [], [], []
    for d, nd_name in ca.DISTANCES.items():
        nd = ca.block_table(nd_name)
        dv = ca.block_table(NODIV_TO_DIV(nd_name))
        for roi in ca.ZONES:
            for dth in LEVELS_BY_DISTANCE[d]:
                a, b = cell_values(dv, roi, dth), cell_values(nd, roi, dth)
                diff = a.mean() - b.mean()
                lo, hi = boot_diff(a, b, rng)
                t = stats.ttest_ind(a, b, equal_var=False)
                m = b.mean()
                rows.append({"distance_m": d, "zone": f"{roi}x{roi}", "dtheta_deg": dth, "n_div": len(a), "n_nodiv": len(b),
                             "mean_nodiv_kcps": m, "mean_div_kcps": a.mean(), "sd_nodiv": b.std(ddof=1), "sd_div": a.std(ddof=1),
                             "change_kcps": diff, "change_ci_lo": lo, "change_ci_hi": hi,
                             "change_pct": 100 * diff / m, "pct_ci_lo": 100 * lo / m, "pct_ci_hi": 100 * hi / m,
                             "welch_p": t.pvalue})
                # solo ambient (the strip should not change what a sensor sees on its own if it stays out of the field of view)
                for s in ("A", "B"):
                    sa = dv[(dv.roi == roi) & (dv.dtheta_deg == dth) & (dv.sensor == s)].solo_ambient.to_numpy(float)
                    sb = nd[(nd.roi == roi) & (nd.dtheta_deg == dth) & (nd.sensor == s)].solo_ambient.to_numpy(float)
                    solo_rows.append({"distance_m": d, "zone": f"{roi}x{roi}", "dtheta_deg": dth, "sensor": s,
                                      "solo_nodiv_kcps": sb.mean(), "solo_div_kcps": sa.mean(),
                                      "change_pct": 100 * (sa.mean() / sb.mean() - 1) if sb.mean() else np.nan})

    # Note: the old 0.6 m "first vs second divider run" replicate comparison (campaign 1) no longer applies:
    # that compared two early strip placements against each other, both since superseded by the single
    # re-squared-board divider session (div_0p6) used throughout. rep_rows is kept empty for output-shape
    # compatibility.

    eff = pd.DataFrame(rows)
    eff.to_csv(ca.OUT / "divider_effect.csv", index=False)
    pd.DataFrame(solo_rows).to_csv(ca.OUT / "divider_solo.csv", index=False)
    pd.DataFrame(rep_rows).to_csv(ca.OUT / "divider_replicate_0p6.csv", index=False)
    pd.set_option("display.width", 250)
    print(eff[["distance_m", "zone", "dtheta_deg", "mean_nodiv_kcps", "mean_div_kcps", "change_pct", "pct_ci_lo", "pct_ci_hi", "welch_p"]].round(3).to_string(index=False))
    print("\nsolo ambient change, %:")
    print(pd.DataFrame(solo_rows).pivot_table(index=["distance_m", "zone", "dtheta_deg"], columns="sensor", values="change_pct").round(1).to_string())
    print("\n0.6 m first against second divider run:")
    print(pd.DataFrame(rep_rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
