"""Recompute every number quoted in the manuscript text from the analysis files and compare at the precision printed.

Each check is (where, what the text says, the value recomputed from analysis/*.csv, how to round it). A mismatch prints FAIL and the
script exits 1. If a number in the text changes, change it here too; that is the point.

Run:   python manuscript_ieee/scripts/check_text_numbers.py
Out:   manuscript_ieee/analysis/text_number_checks.csv

Author: Jessica
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

A = Path(__file__).resolve().parent.parent / "analysis"
s = pd.read_csv(A / "results_summary.csv")
est = pd.read_csv(A / "crossover_estimates.csv")
e10 = est[est.phi == 0.10]
bump = pd.read_csv(A / "crossover_bump_tests.csv").set_index(["distance_m", "zone"])
aic = pd.read_csv(A / "crossover_aic.csv")
diffs = pd.read_csv(A / "crossover_method_differences.csv")
ps = pd.read_csv(A / "crossover_per_sensor.csv")
ps = ps[ps.method == "M4"]
rng = pd.read_csv(A / "range_effects.csv")
ratio = pd.read_csv(A / "extra_over_solo_fullarray.csv")
div = pd.read_csv(A / "divider_effect.csv")
dsolo = pd.read_csv(A / "divider_solo.csv")
drep = pd.read_csv(A / "divider_replicate_0p6.csv")
thr = pd.read_csv(A / "crossover_threshold_summary.csv")
prov = pd.read_csv(A / "crossover_provenance_sensitivity.csv")
cone = pd.read_csv(A / "implied_emitter_cone.csv")
cone1 = cone[cone.extinction_fraction == 0.01]

F = s[s.zone == "16x16"].sort_values("distance_m")
W = s[s.zone == "4x4"].sort_values("distance_m")
rows = []


def chk(where, text, value, nd=None, lo=None, hi=None):
    """nd: compare round(value, nd) with text; lo/hi: check value lies in [lo, hi] (text is then a range label)."""
    if nd is not None:
        ok = abs(round(float(value), nd) - float(text)) < 1e-9
        shown = f"{value:.{max(nd, 0)}f}" if nd >= 0 else f"{value:.0f}"
    else:
        ok = lo <= float(value) <= hi
        shown = f"{value:.3f}"
    rows.append({"where": where, "text": text, "recomputed": shown, "ok": ok})


# ---- Results: angular response
for z, name, df in (("16x16", "full-array peak", F), ("4x4", "window peak", W)):
    for d, txt in zip((0.3, 0.6, 0.9), {"16x16": (1006, 665, 302), "4x4": (273, 65, 24)}[z]):
        chk(f"Results/angular: {name} {d} m (kcps)", txt, df[df.distance_m == d].peak_mean_kcps.iloc[0], nd=0)
for d, txt, nd in zip((0.3, 0.6, 0.9), (23, 8, 3.5), (0, 0, 1)):
    chk(f"Results/angular: extra over solo, full array {d} m", txt, ratio[ratio.distance_m == d].extra_over_solo_at_0.iloc[0], nd=nd)
chk("Results/angular: window 0.6 m, 4 deg above 0 deg (%)", 4.5, bump.loc[(0.6, "4x4"), "diff_pct_of_0"], nd=1)
chk("Results/angular: window 0.9 m, 4 deg above 0 deg (%)", 23, bump.loc[(0.9, "4x4"), "diff_pct_of_0"], nd=0)
chk("Results/angular: window 0.3 m, lower by (%)", -25, bump.loc[(0.3, "4x4"), "diff_pct_of_0"], nd=0)
chk("Results/angular: Welch p 0.6 m", 0.0024, bump.loc[(0.6, "4x4"), "welch_p"], nd=4)
chk("Results/angular: Welch p 0.9 m below 0.0001", 0.0001, 0.0001 - bump.loc[(0.9, "4x4"), "welch_p"], lo=0, hi=1)

# ---- Results: crossover
for z, df, txt in (("16x16", F, [(16, 18)] * 3), ("4x4", W, [(8, 10), (8, 10), (10, 12)])):
    for (lo, hi), (_, r) in zip(txt, df.iterrows()):
        chk(f"Results/crossover: bracket lower edge {z} {r.distance_m} m", lo, r.bracket_lo, nd=0)
        chk(f"Results/crossover: bracket upper edge {z} {r.distance_m} m", hi, r.bracket_hi, nd=0)
for z, df, txt in (("16x16", F, (16.15, 16.97, 17.90)), ("4x4", W, (8.22, 9.47, 10.80))):
    for t, (_, r) in zip(txt, df.iterrows()):
        chk(f"Results/crossover: PCHIP {z} {r.distance_m} m", t, r.m4, nd=2)
e = e10.assign(hw=(e10.ci_hi - e10.ci_lo) / 2)
m4 = e[e.method == "M4"]
chk("Results/crossover: smallest M4 bootstrap half-width", 0.01, m4.hw.min(), nd=2)
chk("Results/crossover: largest M4 bootstrap half-width", 0.07, m4.hw.max(), nd=2)
sp = m4.method_spread_deg
chk("Results/crossover: smallest estimator spread", 0.13, sp.min(), nd=2)
chk("Results/crossover: largest estimator spread", 1.02, sp.max(), nd=2)
r_ = (sp.to_numpy() / m4.hw.to_numpy())
chk("Results/crossover: smallest spread/half-width ratio", 10, r_.min(), nd=0)
chk("Results/crossover: largest spread/half-width ratio", 44, r_.max(), nd=0)
for z, nm in (("16x16", "full array"),):
    d1 = diffs[(diffs.pair == "M1-M4") & (diffs.zone == z)].diff_deg
    chk("Results/crossover: logistic minus PCHIP, full array, min", 0.9, d1.min(), nd=1)
    chk("Results/crossover: logistic minus PCHIP, full array, max", 1.0, d1.max(), nd=1)
chk("Results/crossover: logistic at 0.9 m full array", 18.84, e10[(e10.method == "M1") & (e10.distance_m == 0.9) & (e10.zone == "16x16")].crossover_deg.iloc[0], nd=2)
chk("Results/crossover: min dAIC over the five cells", 140, aic[aic.delta_aic_M1_minus_M5 > 10].delta_aic_M1_minus_M5.min(), lo=140, hi=1e9)
chk("Results/crossover: number of cells with dAIC above 140", 5, (aic.delta_aic_M1_minus_M5 > 140).sum(), nd=0)
m45 = diffs[diffs.pair == "M4-M5"].diff_deg.abs()
chk("Results/crossover: PCHIP vs tilted logistic, max |difference|", 0.14, m45.max(), lo=0, hi=0.14)
chk("Results/crossover: threshold shift, smallest", 0.7, np.abs(np.r_[thr["M4_at_5pct"] - thr["M4_at_10pct"], thr["M4_at_20pct"] - thr["M4_at_10pct"]]).min(), nd=1)
chk("Results/crossover: threshold shift, largest", 1.7, np.abs(np.r_[thr["M4_at_5pct"] - thr["M4_at_10pct"], thr["M4_at_20pct"] - thr["M4_at_10pct"]]).max(), nd=1)
af = ps[ps.zone == "16x16"].A_minus_B_deg
aw = ps[ps.zone == "4x4"].A_minus_B_deg
chk("Results/crossover: A earlier than B, full array, min", 1.0, (-af).min(), nd=1)
chk("Results/crossover: A earlier than B, full array, max", 1.1, (-af).max(), nd=1)
chk("Results/crossover: A later than B, window, min", 0.6, aw.min(), nd=1)
chk("Results/crossover: A later than B, window, max", 1.0, aw.max(), nd=1)
chk("Results/crossover: A-B same sign at every distance (full array negative, window positive)", 1, int((af < 0).all() and (aw > 0).all()), nd=0)

# ---- Results: reaching negligible interference
for z, df, txt in (("16x16", F, (19.9, 20.9, 21.6)), ("4x4", W, (11.4, 12.5, 13.1))):
    for t, (_, r) in zip(txt, df.iterrows()):
        chk(f"Results/1% angle {z} {r.distance_m} m", t, r.angle_1pct, nd=1)
for d, t in zip((0.3, 0.6, 0.9), (0.19, 0.09, 0.04)):
    chk(f"Results/extra over solo at the 1% angle, full array {d} m", t, ratio[ratio.distance_m == d].extra_over_solo_at_1pct_angle.iloc[0], nd=2)
r0 = rng[(rng.dtheta_deg == 0)]
chk("Results/range: largest |bias| at 0 deg (mm)", 0.3, r0.bias_mm.abs().max(), nd=1)
f0 = r0[r0.zone == "16x16"]
chk("Results/range: SD ratio full array, smallest (% above 1)", 7, 100 * (f0.sd_ratio.min() - 1), nd=0)
chk("Results/range: SD ratio full array, largest (% above 1)", 10, 100 * (f0.sd_ratio.max() - 1), nd=0)
chk("Results/range: SD ratio window 0.3 m (% above 1)", 13, 100 * (r0[(r0.zone == "4x4") & (r0.distance_m == 0.3)].sd_ratio.iloc[0] - 1), nd=0)
r24 = rng[(rng.dtheta_deg == 24) & rng.sd_ratio.notna()]
chk("Results/range: at 24 deg every SD-ratio interval contains 1", 1, int(((r24.sd_ratio_lo <= 1) & (r24.sd_ratio_hi >= 1)).all()), nd=0)
chk("Results/range: at 24 deg every bias interval contains 0", 1, int(((r24.bias_lo <= 0) & (r24.bias_hi >= 0)).all()), nd=0)
chk("Results/range: window valid share at 0.6 m, 0 deg (about half)", 0.5, r0[(r0.zone == "4x4") & (r0.distance_m == 0.6)].valid_share_solo.iloc[0], nd=1)
chk("Results/range: window valid share at 0.9 m, 0 deg (none)", 0, r0[(r0.zone == "4x4") & (r0.distance_m == 0.9)].valid_share_solo.iloc[0], nd=0)

# ---- Results: geometric model
chk("Results/model: as coded, full array min", 23.4, F.pred_as_coded.min(), nd=1)
chk("Results/model: as coded, full array max", 25.8, F.pred_as_coded.max(), nd=1)
chk("Results/model: as coded, window min", 17.3, W.pred_as_coded.min(), nd=1)
chk("Results/model: as coded, window max", 19.8, W.pred_as_coded.max(), nd=1)
o16 = F.pred_as_coded.to_numpy() - F.angle_1pct.to_numpy()
o4 = W.pred_as_coded.to_numpy() - W.angle_1pct.to_numpy()
chk("Results/model: as coded beyond the 1% angle, full array min", 3.4, o16.min(), nd=1)
chk("Results/model: as coded beyond the 1% angle, full array max", 4.3, o16.max(), nd=1)
chk("Results/model: as coded beyond the 1% angle, window min", 5.9, o4.min(), nd=1)
chk("Results/model: as coded beyond the 1% angle, window max", 6.8, o4.max(), nd=1)
chk("Results/model: in-plane full array min", 19.5, F.pred_in_plane.min(), nd=1)
chk("Results/model: in-plane full array max", 21.9, F.pred_in_plane.max(), nd=1)
chk("Results/model: in-plane full array within 0.5 deg of the 1% angle", 0.5, np.abs(F.pred_in_plane.to_numpy() - F.angle_1pct.to_numpy()).max(), lo=0, hi=0.5)
w_in = W.pred_in_plane.to_numpy() - W.angle_1pct.to_numpy()
chk("Results/model: in-plane window too late, min", 3.8, w_in.min(), nd=1)
chk("Results/model: in-plane window too late, max", 4.6, w_in.max(), nd=1)
c16 = cone1[cone1.zone == "16x16"].E_implied_F_inplane_deg
c4 = cone1[cone1.zone == "4x4"].E_implied_F_inplane_deg
chk("Results/model: implied cone full array, min (26-28)", 26, c16.min(), nd=0)
chk("Results/model: implied cone full array, max (26-28)", 28, c16.max(), nd=0)
chk("Results/model: implied cone window, min (18-20)", 18, c4.min(), nd=0)
chk("Results/model: implied cone window, max (18-20)", 20, c4.max(), nd=0)
chk("Results/model: within-zone spread of implied cone at most 1.8", 1.8, max(c16.max() - c16.min(), c4.max() - c4.min()), nd=1)

# ---- Results: divider
chg = div.change_pct
chk("Results/divider: smallest change (%)", -7.7, chg.min(), nd=1)
chk("Results/divider: largest change (%)", 17.2, chg.max(), nd=1)
chk("Results/divider: cells within +-4.2%", 10, (chg.abs() <= 4.25).sum(), nd=0)
x = div[div.change_pct.abs() > 4.25]
chk("Results/divider: exceptions are window cells at 10 deg", 1, int((x.zone == "4x4").all() and (x.dtheta_deg == 10).all()), nd=0)
chk("Results/divider: exception absolute change, smaller (kcps)", -0.5, x.change_kcps.min(), nd=1)
chk("Results/divider: exception absolute change, larger (kcps)", 0.8, x.change_kcps.max(), nd=1)
d3, d6, d9 = (div[div.distance_m == d].change_pct for d in (0.3, 0.6, 0.9))
chk("Results/divider: 0.3 m all fell", 1, int((d3 < 0).all()), nd=0)
chk("Results/divider: 0.3 m least fall (%)", -0.7, d3.max(), nd=1)
chk("Results/divider: 0.3 m largest fall (%)", -7.7, d3.min(), nd=1)
chk("Results/divider: 0.6 m all rose", 1, int((d6 > 0).all()), nd=0)
chk("Results/divider: 0.6 m smallest rise (%)", 3.9, d6.min(), nd=1)
chk("Results/divider: 0.6 m largest rise (%)", 17.2, d6.max(), nd=1)
chk("Results/divider: 0.9 m smallest (%)", -0.1, d9.min(), nd=1)
chk("Results/divider: 0.9 m largest (%)", 2.5, d9.max(), nd=1)
excl = ((div.pct_ci_lo > 0) | (div.pct_ci_hi < 0))
chk("Results/divider: intervals excluding zero", 10, excl.sum(), nd=0)
chk("Results/divider: intervals including zero are the 0.9 m window", 1, int(((~excl) == ((div.distance_m == 0.9) & (div.zone == "4x4"))).all()), nd=0)
chk("Results/divider: solo ambient change, smallest (%)", -20, dsolo.change_pct.min(), nd=0)
chk("Results/divider: solo ambient change, largest (%)", 18, dsolo.change_pct.max(), nd=0)
chk("Results/divider: two 0.6 m placements agree within (%)", 1.6, drep.pct_of_second.abs().max(), lo=0, hi=1.65)

# ---- Methods / Discussion
_m = [f"M{i}" for i in range(1, 6)]
chk("Methods: excluding refill blocks, max change in any crossover (deg)", 0.01, np.abs(prov[[f"{c}_main_only" for c in _m]].to_numpy() - prov[[f"{c}_all" for c in _m]].to_numpy()).max(), nd=2)
chk("Discussion: 1% angle per sensor, full array at 0.9 m (deg)", 11, F[F.distance_m == 0.9].angle_1pct.iloc[0] / 2, nd=0)
chk("Discussion: 1% angle per sensor, window at 0.9 m (deg)", 6.5, W[W.distance_m == 0.9].angle_1pct.iloc[0] / 2, nd=1)
chk("Discussion: 10% angle per sensor, full array at 0.9 m (deg)", 9, F[F.distance_m == 0.9].m4.iloc[0] / 2, nd=0)
chk("Discussion: 10% angle per sensor, window at 0.9 m (deg)", 5.4, W[W.distance_m == 0.9].m4.iloc[0] / 2, nd=1)
chk("Discussion: window peak at 0.3 m (kcps)", 273, W[W.distance_m == 0.3].peak_mean_kcps.iloc[0], nd=0)
chk("Abstract: union of 10% brackets for the window, lower", 8, W.bracket_lo.min(), nd=0)
chk("Abstract: union of 10% brackets for the window, upper", 12, W.bracket_hi.max(), nd=0)
chk("Abstract: 1% angles, full array, rounded lower", 20, F.angle_1pct.min(), nd=0)
chk("Abstract: 1% angles, full array, rounded upper", 22, F.angle_1pct.max(), nd=0)
chk("Abstract: 1% angles, window, rounded lower", 11, W.angle_1pct.min(), nd=0)
chk("Abstract: 1% angles, window, rounded upper", 13, W.angle_1pct.max(), nd=0)
chk("Abstract/Conclusion: model overshoot from 3 to 7 (min over both zones)", 3, min(o16.min(), o4.min()), nd=0)
chk("Abstract/Conclusion: model overshoot from 3 to 7 (max over both zones)", 7, max(o16.max(), o4.max()), nd=0)

out = pd.DataFrame(rows)
out.to_csv(A / "text_number_checks.csv", index=False)
bad = out[~out.ok]
print(f"{len(out)} numeric claims checked, {len(bad)} failed")
if len(bad):
    print(bad.to_string(index=False))
sys.exit(1 if len(bad) else 0)
