"""Figure 2 and the two tables of the Results, generated from the analysis CSVs (no number is typed).

Fig. 2 (double column):
  (a), (b) response of the 16x16 and 4x4 zones against dtheta, three distances, as a percentage of each cell's observed peak;
           markers are block means (error bars, one SD of five blocks, are mostly smaller than the markers), thin lines are
           PCHIP interpolants, filled inverted triangles mark the PCHIP 10% crossing and open triangles on the baseline mark
           the geometric prediction as coded;
  (c)      the angle at which the response reaches 10% (PCHIP, bars span the model-free bracket) and 1% of its peak against
           distance, with the geometric prediction as coded (solid) and with the receive field converted to an in-plane value
           (dashed).
Table I   crossover, bracket, 1% angle and predictions.   Table II  divider against no divider.

Run:   python manuscript_ieee/scripts/make_results_assets.py   (after crossover_analysis.py, crossover_extras.py, divider_analysis.py)
Out:   figures/fig_results.pdf/png, tables/table_crossover.tex, tables/table_divider.tex, analysis/results_summary.csv

Author: Jessica
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crossover_analysis as ca  # noqa: E402
from geometry_sensitivity import axis_fov, end_of_overlap, E_ASSUMED  # noqa: E402

A, FIG, TAB = ca.OUT, ca.FIG, ca.PROJECT / "tables"
TAB.mkdir(exist_ok=True)
DIST = (0.3, 0.6, 0.9)
COL = {0.3: "#0072B2", 0.6: "#009E73", 0.9: "#D55E00"}
MK = {0.3: "o", 0.6: "s", 0.9: "D"}
ZCOL = {16: "#000000", 4: "#CC79A7"}      # zones in panel (c); distinct from the distance colours of (a) and (b)


def load_cells():
    store = {}
    for d, name in ca.DISTANCES.items():
        pairs = ca.block_table(name)
        for roi in ca.ZONES:
            store[(d, roi)] = ca.cell_arrays(pairs, roi)
    return store


def summary() -> pd.DataFrame:
    est = pd.read_csv(A / "crossover_estimates.csv")
    est = est[est.phi == 0.10]
    brk = pd.read_csv(A / "crossover_bracket.csv").set_index(["distance_m", "zone"])
    ext = pd.read_csv(A / "extinction.csv").set_index(["distance_m", "zone"])
    cone = pd.read_csv(A / "implied_emitter_cone.csv")
    cone = cone[cone.extinction_fraction == 0.01].set_index(["distance_m", "zone"])
    rows = []
    for d in DIST:
        for roi in (16, 4):
            z = f"{roi}x{roi}"
            e = est[(est.distance_m == d) & (est.zone == z)].set_index("method")
            m345 = [e.loc[k, "crossover_deg"] for k in ("M3", "M4", "M5")]
            f_diag = ca.geometry.RECEIVE_FIELD_DEG[roi]
            rows.append({
                "zone": z, "distance_m": d,
                "bracket_lo": brk.loc[(d, z), "last_above_deg"], "bracket_hi": brk.loc[(d, z), "first_at_or_below_deg"],
                "peak_level_deg": brk.loc[(d, z), "peak_level_deg"], "peak_mean_kcps": brk.loc[(d, z), "peak_mean_kcps"],
                "m4": e.loc["M4", "crossover_deg"], "m4_ci_lo": e.loc["M4", "ci_lo"], "m4_ci_hi": e.loc["M4", "ci_hi"],
                "m345_min": min(m345), "m345_max": max(m345),
                "m1": e.loc["M1", "crossover_deg"], "angle_1pct": ext.loc[(d, z), "angle_at_1pct_deg"],
                "pred_as_coded": end_of_overlap(E_ASSUMED, f_diag, d),
                "pred_in_plane": end_of_overlap(E_ASSUMED, axis_fov(f_diag), d),
                "E_implied_inplane": cone.loc[(d, z), "E_implied_F_inplane_deg"]})
    df = pd.DataFrame(rows)
    df.to_csv(A / "results_summary.csv", index=False)
    return df


def figure(store, s: pd.DataFrame):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.2), gridspec_kw={"width_ratios": [1, 1, 0.92]})
    grid = np.linspace(0, 24, 481)
    for ax, roi, tag in ((axes[0], 16, "(a) 16×16 zone"), (axes[1], 4, "(b) 4×4 zone")):
        for d in DIST:
            levels, vals = store[(d, roi)]
            means = np.array([v.mean() for v in vals])
            sds = np.array([v.std(ddof=1) for v in vals])
            ref = means.max()
            ax.plot(grid, 100 * PchipInterpolator(levels, means)(grid) / ref, color=COL[d], lw=0.7, alpha=0.85, zorder=2)
            ax.errorbar(levels, 100 * means / ref, yerr=100 * sds / ref, fmt=MK[d], ms=3.2, color=COL[d], elinewidth=0.5,
                        capsize=1, zorder=3, mfc=COL[d] if roi == 16 else "white", mew=0.8, label=f"{d:g} m")
            r = s[(s.zone == f"{roi}x{roi}") & (s.distance_m == d)].iloc[0]
            ax.plot([r.m4], [10], marker="v", ms=5.5, color=COL[d], mec="black", mew=0.5, zorder=5)
            ax.plot([r.pred_as_coded], [0], marker="^", ms=5, mfc="white", mec=COL[d], mew=0.9, clip_on=False, zorder=4)
        ax.axhline(10, color="#777777", lw=0.5, ls="--", zorder=1)
        ax.axhline(1, color="#999999", lw=0.5, ls=":", zorder=1)
        ax.text(26.8, 11.5, "10%", fontsize=6, color="#555555", ha="right", va="bottom")
        ax.text(26.8, 1.5, "1%", fontsize=6, color="#555555", ha="right", va="bottom")
        ax.set_xlim(-0.6, 27)
        ax.set_ylim(-4, 112)
        ax.set_xlabel("Δθ (degrees)")
        ax.set_title(tag, loc="left", fontsize=7.5, fontweight="bold")
        ax.tick_params(labelsize=7)
    axes[0].set_ylabel("Extra ambient (% of peak)")
    h = [Line2D([], [], marker=MK[d], color=COL[d], lw=0.7, ms=3.5, mfc=COL[d], label=f"{d:g} m") for d in DIST]
    h += [Line2D([], [], marker="v", ls="", color="#999999", mec="black", mew=0.5, ms=5, label="10% crossing"),
          Line2D([], [], marker="^", ls="", mfc="white", mec="#555555", mew=0.9, ms=5, label="geometric, as coded")]
    axes[1].legend(handles=h, fontsize=6, frameon=False, loc="upper right", handletextpad=0.3, borderaxespad=0.1, labelspacing=0.25)

    ax = axes[2]
    dd = np.linspace(0.25, 0.95, 50)
    for roi in (16, 4):
        z = f"{roi}x{roi}"
        c = ZCOL[roi]
        g = s[s.zone == z]
        ax.plot(dd, [end_of_overlap(E_ASSUMED, ca.geometry.RECEIVE_FIELD_DEG[roi], x) for x in dd], color=c, lw=0.8, zorder=1)
        ax.plot(dd, [end_of_overlap(E_ASSUMED, axis_fov(ca.geometry.RECEIVE_FIELD_DEG[roi]), x) for x in dd], color=c, lw=0.8,
                ls="--", zorder=1)
        ax.errorbar(g.distance_m, g.m4, yerr=[g.m4 - g.bracket_lo, g.bracket_hi - g.m4], fmt="o", ms=3.8, color=c, capsize=1.8,
                    elinewidth=0.7, zorder=3)
        ax.plot(g.distance_m, g.angle_1pct, "s", ms=3.8, mfc="white", mec=c, mew=1.0, zorder=3)
    ax.set_xlim(0.22, 0.98)
    ax.set_ylim(0, 28)
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel("Δθ (degrees)")
    ax.set_title("(c) Angles against distance", loc="left", fontsize=7.5, fontweight="bold")
    ax.tick_params(labelsize=7)
    ax.set_xticks([0.3, 0.6, 0.9])
    h = [Line2D([], [], marker="o", ls="", color="#444444", ms=3.8, label="10% crossing (bar: bracket)"),
         Line2D([], [], marker="s", ls="", mfc="white", mec="#444444", mew=1.0, ms=3.8, label="1% of peak"),
         Line2D([], [], color="#444444", lw=0.8, label="model, as coded"),
         Line2D([], [], color="#444444", lw=0.8, ls="--", label="model, receive field in-plane")]
    ax.legend(handles=h, fontsize=5.6, frameon=False, loc="lower right", handletextpad=0.3, borderaxespad=0.1, labelspacing=0.2)
    ax.text(0.62, 27.0, "16×16", color=ZCOL[16], fontsize=6.5, ha="center", va="top", fontweight="bold")
    ax.text(0.45, 12.6, "4×4", color=ZCOL[4], fontsize=6.5, ha="center", va="center", fontweight="bold")
    fig.tight_layout(w_pad=0.9)
    fig.savefig(FIG / "fig_results.png", dpi=600)
    fig.savefig(FIG / "fig_results.pdf", metadata={"Creator": "", "Producer": "", "Author": "Jessica"})
    plt.close(fig)


def tex_crossover(s: pd.DataFrame):
    lines = [r"\begin{table*}[!t]", r"\centering", r"\caption{Angle between the sensors (degrees) at which the extra ambient rate falls to \SI{10}{\percent} "
             r"(crossover) and \SI{1}{\percent} of its peak, and the model's end-of-overlap angle}",
             r"\label{tab:cross}", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
             r"\begin{tabular}{@{}llcccccc@{}}", r"\toprule",
             r"Zone & $d$ (m) & Bracket & Crossover (PCHIP) & Range of three estimators & \SI{1}{\percent} angle & Model, as coded & Model, $F$ in-plane \\",
             r"\midrule"]
    for z in ("16x16", "4x4"):
        g = s[s.zone == z]
        for _, r in g.iterrows():
            zone = r"$16\times16$" if z == "16x16" else r"$4\times4$"
            lines.append(f"{zone} & {r.distance_m:g} & {r.bracket_lo:.0f}--{r.bracket_hi:.0f} & {r.m4:.2f} "
                         f"& {r.m345_min:.2f}--{r.m345_max:.2f} & {r.angle_1pct:.1f} & {r.pred_as_coded:.1f} & {r.pred_in_plane:.1f} \\\\")
        if z == "16x16":
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}",
              r"\par\vspace{1pt}\raggedright\footnotesize Bracket and range (linear, PCHIP and tilted logistic) as defined in Section~\ref{sec:method}; "
              r"bootstrap \SI{95}{\percent} half-widths of the PCHIP value are \SIrange{0.01}{0.07}{\degree} (within-session only).", r"\end{table*}"]
    (TAB / "table_crossover.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_divider():
    e = pd.read_csv(A / "divider_effect.csv")
    lines = [r"\begin{table}[!t]", r"\centering", r"\caption{Change in the extra ambient rate with the divider, "
             r"\si{\percent} of the no-divider cell mean (\SI{95}{\percent} bootstrap interval)}", r"\label{tab:divider}",
             r"\footnotesize", r"\setlength{\tabcolsep}{3.5pt}", r"\begin{tabular}{@{}llcc@{}}", r"\toprule",
             r"Zone & $d$ (m) & $\dth=\SI{4}{\degree}$ & $\dth=\SI{10}{\degree}$ \\", r"\midrule"]
    for z in ("16x16", "4x4"):
        for d in DIST:
            cells = []
            for dth in (4, 10):
                r = e[(e.zone == z) & (e.distance_m == d) & (e.dtheta_deg == dth)].iloc[0]
                cells.append(f"${r.change_pct:+.1f}$ (${r.pct_ci_lo:+.1f}$, ${r.pct_ci_hi:+.1f}$)")
            zone = r"$16\times16$" if z == "16x16" else r"$4\times4$"
            lines.append(f"{zone} & {d:g} & {cells[0]} & {cells[1]} \\\\")
        if z == "16x16":
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    (TAB / "table_divider.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    s = summary()
    figure(load_cells(), s)
    tex_crossover(s)
    tex_divider()
    print(s.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
