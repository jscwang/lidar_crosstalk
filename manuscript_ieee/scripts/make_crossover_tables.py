"""Markdown tables for CROSSOVER_ANALYSIS.md, generated from the analysis CSVs so no number is retyped.

Run:   python manuscript_ieee/scripts/make_crossover_tables.py
Out:   manuscript_ieee/analysis/crossover_tables.md

Author: Jessica
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
A = HERE.parent / "analysis"


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def f2(x):
    return "n/a" if pd.isna(x) else f"{x:.2f}"


def main():
    est = pd.read_csv(A / "crossover_estimates.csv")
    br = pd.read_csv(A / "crossover_bracket.csv")
    e10 = est[est.phi == 0.10]
    piv = e10.pivot_table(index=["distance_m", "zone"], columns="method", values="crossover_deg")
    m4 = e10[e10.method == "M4"].set_index(["distance_m", "zone"])
    br = br.set_index(["distance_m", "zone"])
    rows = []
    for (d, z), r in piv.iterrows():
        non_log = [r["M3"], r["M4"], r["M5"]]
        rows.append({"d (m)": d, "zone": z, "peak at": f"{br.loc[(d, z), 'peak_level_deg']:.0f}",
                     "bracket": f"{br.loc[(d, z), 'last_above_deg']:.0f}-{br.loc[(d, z), 'first_at_or_below_deg']:.0f}",
                     "M1": f2(r["M1"]), "M2": f2(r["M2"]), "M3": f2(r["M3"]), "M4": f2(r["M4"]), "M5": f2(r["M5"]),
                     "M4 boot 95% CI": f"{m4.loc[(d, z), 'ci_lo']:.2f}-{m4.loc[(d, z), 'ci_hi']:.2f}",
                     "range M1-M5": f2(max(r[["M1", "M2", "M3", "M4", "M5"]]) - min(r[["M1", "M2", "M3", "M4", "M5"]])),
                     "range M3-M5": f2(max(non_log) - min(non_log))})
    t_main = md(pd.DataFrame(rows))

    # M1 inside the bracket?
    chk = []
    for (d, z), r in piv.iterrows():
        lo, hi = br.loc[(d, z), "last_above_deg"], br.loc[(d, z), "first_at_or_below_deg"]
        chk.append({"d (m)": d, "zone": z, "bracket": f"{lo:.0f}-{hi:.0f}",
                    **{k: ("inside" if lo <= r[k] <= hi + 1e-9 else "OUTSIDE") for k in ("M1", "M2", "M3", "M4", "M5")}})
    t_chk = md(pd.DataFrame(chk))

    aic = pd.read_csv(A / "crossover_aic.csv")
    t_aic = md(pd.DataFrame({"d (m)": aic.distance_m, "zone": aic.zone, "RMSE M1 (kcps)": aic.rmse_M1.round(2),
                             "RMSE M5 (kcps)": aic.rmse_M5.round(2), "dAIC (M1-M5)": aic.delta_aic_M1_minus_M5.round(1),
                             "M5 tilt b (per deg)": aic.M5_b_per_deg.round(3)}))

    bump = pd.read_csv(A / "crossover_bump_tests.csv")
    t_bump = md(pd.DataFrame({"d (m)": bump.distance_m, "zone": bump.zone, "mean at 0": bump.mean_at_0.round(2),
                              "mean at 4": bump.mean_at_4.round(2),
                              "diff (kcps)": bump.diff_4_minus_0.round(2),
                              "95% CI": bump.diff_ci_lo.round(2).astype(str) + " to " + bump.diff_ci_hi.round(2).astype(str),
                              "diff %": bump.diff_pct_of_0.round(1),
                              "Welch p": bump.welch_p.map(lambda p: f"{p:.4f}"),
                              "Mann-Whitney p": bump.mannwhitney_p.map(lambda p: f"{p:.4f}")}))

    th = est[est.method == "M4"].pivot_table(index=["distance_m", "zone"], columns="phi", values="crossover_deg")
    th.columns = [f"{int(round(c * 100))}%" for c in th.columns]
    th = th.reset_index().rename(columns={"distance_m": "d (m)"})
    for c in ("5%", "10%", "20%"):
        th[c] = th[c].map(f2)
    t_th = md(th)

    ref = pd.read_csv(A / "crossover_reference_sensitivity.csv")
    t_ref = md(pd.DataFrame({"d (m)": ref.distance_m, "zone": ref.zone, "peak at": ref.peak_level_deg.astype(int),
                             "ref = peak": ref.crossover_ref_peak_deg.round(2),
                             "ref = value at 0": ref.crossover_ref_zero_deg.round(2),
                             "difference": ref.difference_deg.round(2),
                             "95% CI of difference": ref.diff_ci_lo.round(2).astype(str) + " to " + ref.diff_ci_hi.round(2).astype(str)}))

    ps = pd.read_csv(A / "crossover_per_sensor.csv")
    ps = ps[ps.method == "M4"]
    t_ps = md(pd.DataFrame({"d (m)": ps.distance_m, "zone": ps.zone, "A (deg)": ps.A_deg.round(2), "B (deg)": ps.B_deg.round(2),
                            "A - B": ps.A_minus_B_deg.round(2),
                            "95% CI of A - B": ps.diff_ci_lo.round(2).astype(str) + " to " + ps.diff_ci_hi.round(2).astype(str),
                            "A peak at": ps.A_peak_level.astype(int), "B peak at": ps.B_peak_level.astype(int)}))

    ext = pd.read_csv(A / "extinction.csv")
    gs = pd.read_csv(A / "geometry_sensitivity.csv")
    rows = []
    for _, r in ext.iterrows():
        g = gs[(gs.zone == r.zone) & (gs.distance_m == r.distance_m)].set_index("variant").end_of_overlap_deg
        rows.append({"d (m)": r.distance_m, "zone": r.zone, "angle at 1% of peak": f"{r.angle_at_1pct_deg:.2f}",
                     "V0 as coded": f"{g['V0']:.2f}", "V1 receive field in-plane": f"{g['V1']:.2f}",
                     "V2 both in-plane": f"{g['V2']:.2f}"})
    t_geo = md(pd.DataFrame(rows))

    cone = pd.read_csv(A / "implied_emitter_cone.csv")
    c1 = cone[cone.extinction_fraction == 0.01]
    t_cone = md(pd.DataFrame({"d (m)": c1.distance_m, "zone": c1.zone, "angle at 1% (deg)": c1.angle_deg.round(2),
                              "E implied, F in-plane (deg)": c1.E_implied_F_inplane_deg.round(1),
                              "E implied, F as diagonal (deg)": c1.E_implied_F_as_diagonal_deg.round(1)}))

    parts = {"MAIN": t_main, "BRACKET_CHECK": t_chk, "AIC": t_aic, "BUMP": t_bump, "THRESHOLD": t_th,
             "REFERENCE": t_ref, "PER_SENSOR": t_ps, "GEOMETRY": t_geo, "CONE": t_cone}
    text = "\n\n".join(f"<!-- {k} -->\n{v}" for k, v in parts.items())
    (A / "crossover_tables.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
