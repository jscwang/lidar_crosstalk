"""Three further checks on the crossover and its comparison with the geometric model.

1. Reference level. The threshold is a fraction of a reference response. For a monotone cell the observed peak is
   the value at dtheta = 0, so "10% of the peak" and "10% of the value at dtheta = 0" coincide. For the 4x4 cells
   at 0.6 and 0.9 m the peak is at dtheta = 4, and they differ. This script measures by how much (PCHIP, with a
   block-bootstrap interval for the difference).
2. Threshold. Summarises how the PCHIP crossover moves with the threshold fraction (5, 10, 20%), from
   analysis/crossover_estimates.csv.
3. Implied emitter cone. The model  s + 2 d tan(dtheta/2) = d [tan(E/2) + tan(F/2)]  can be inverted for E given a
   measured end-of-overlap angle and an in-plane receive field F. The datasheet gives F only as a diagonal value and
   gives no E. The implied E is a model-dependent number, shown to test whether ONE emitter cone can reproduce BOTH
   zones, not as a measurement of the cone. The measured angle is the dtheta at which the response reaches 1% (and,
   separately, 5%) of its peak, by PCHIP; a soft-edged beam makes such an angle sit before a top-hat model's edge.

Run:   python manuscript_ieee/scripts/crossover_extras.py     (after crossover_analysis.py)
Out:   manuscript_ieee/analysis/crossover_reference_sensitivity.csv
       manuscript_ieee/analysis/crossover_threshold_summary.csv
       manuscript_ieee/analysis/implied_emitter_cone.csv

Author: Jessica
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crossover_analysis as ca  # noqa: E402
from geometry_sensitivity import axis_fov  # noqa: E402

OUT = ca.OUT
N_BOOT = 1000
S = 0.020


def pchip_cross(levels, means, ref, phi, after):
    """First dtheta beyond level `after` where the PCHIP curve falls to phi*ref."""
    f = PchipInterpolator(levels, means)
    grid = np.linspace(after, levels[-1], 4801)
    v = f(grid) - phi * ref
    k = np.flatnonzero(v <= 0)
    if not len(k) or k[0] == 0:
        return float("nan")
    lo, hi = grid[k[0] - 1], grid[k[0]]
    return float(optimize.brentq(lambda z: f(z) - phi * ref, lo, hi))


def pchip_cross_means(levels, means, mode, phi=0.10):
    ipk = int(np.argmax(means))
    ref = means[ipk] if mode == "peak" else means[0]
    return pchip_cross(levels, means, ref, phi, levels[ipk])


def implied_e(end_deg, f_deg, d):
    k = math.tan(math.radians(end_deg) / 2) + S / (2 * d)
    return 2 * math.degrees(math.atan(2 * k - math.tan(math.radians(f_deg) / 2)))


def main():
    rng = np.random.default_rng(ca.SEED + 7)
    ref_rows, cone_rows = [], []
    for d, name in ca.DISTANCES.items():
        pairs = ca.block_table(name)
        for roi in ca.ZONES:
            levels, vals = ca.cell_arrays(pairs, roi)
            means = np.array([v.mean() for v in vals])
            ipk = int(np.argmax(means))
            a = pchip_cross_means(levels, means, "peak")
            b = pchip_cross_means(levels, means, "zero")
            draws = []
            for _ in range(N_BOOT):
                rs = [v[rng.integers(0, len(v), len(v))] for v in vals]
                m = np.array([v.mean() for v in rs])
                draws.append(pchip_cross_means(levels, m, "peak") - pchip_cross_means(levels, m, "zero"))
            draws = np.array([x for x in draws if np.isfinite(x)])
            ref_rows.append({"distance_m": d, "zone": f"{roi}x{roi}", "peak_level_deg": levels[ipk],
                             "ref_peak_kcps": means[ipk], "ref_zero_kcps": means[0],
                             "crossover_ref_peak_deg": a, "crossover_ref_zero_deg": b, "difference_deg": a - b,
                             "diff_ci_lo": np.percentile(draws, 2.5), "diff_ci_hi": np.percentile(draws, 97.5)})

            # extinction angle at 1% and 5% of peak, and the emitter cone it implies
            f_diag = ca.geometry.RECEIVE_FIELD_DEG[roi]
            for phi in (0.01, 0.05):
                ext = pchip_cross(levels, means, means[ipk], phi, levels[ipk])
                row = {"distance_m": d, "zone": f"{roi}x{roi}", "extinction_fraction": phi, "angle_deg": ext,
                       "F_diag_deg": f_diag, "F_inplane_deg": axis_fov(f_diag)}
                for label, f in (("F_as_diagonal", f_diag), ("F_inplane", axis_fov(f_diag))):
                    row[f"E_implied_{label}_deg"] = implied_e(ext, f, d) if np.isfinite(ext) else float("nan")
                cone_rows.append(row)

    ref = pd.DataFrame(ref_rows)
    ref.to_csv(OUT / "crossover_reference_sensitivity.csv", index=False)
    cone = pd.DataFrame(cone_rows)
    cone.to_csv(OUT / "implied_emitter_cone.csv", index=False)

    est = pd.read_csv(OUT / "crossover_estimates.csv")
    m4 = est[est.method == "M4"].pivot_table(index=["distance_m", "zone"], columns="phi", values="crossover_deg")
    m4.columns = [f"M4_at_{int(round(c * 100))}pct" for c in m4.columns]
    m4.reset_index().to_csv(OUT / "crossover_threshold_summary.csv", index=False)

    pd.set_option("display.width", 220)
    print("Reference level (PCHIP, 10%):")
    print(ref.round(3).to_string(index=False))
    print("\nThreshold sensitivity, M4:")
    print(m4.round(2).to_string())
    print("\nImplied emitter cone E (degrees), from the angle at 1% and 5% of peak:")
    print(cone.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
