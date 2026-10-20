"""Before-swap (campaign 1) and after-swap (campaign 2) versions of every data figure in the arXiv paper, in the format
Jessica asked for in chat (16 Oct 2026, reference images fig5_range_vs_background.png and fig6_rejection.png), plus the
unit-swap table.

Fig. 5  time trace, one block, sensor at position A, before and after the swap (2 x 2).
Fig. 6  (a,c) range SD ratio against extra ambient / own signal, with the sqrt(1+k x) curve; (b,d) range shift against the
        same quantity. Row 1 before the swap, row 2 after.
Fig. 7  4x4 window, 0.6 m, unit 3 (sensor A before the swap, sensor B after): (a) signal histogram, neighbor off/on;
        (b) acceptance rule; (c) readings rejected against angle. Row 1 before the swap, row 2 after.
Fig. 8  extra ambient against angle (16x16, 4x4) and angles against distance, before and after the swap.
Fig. 9  estimator comparison, four rows: 16x16 and 4x4, before and after the swap.
Table   unit-swap results: crossing angle and peak extra ambient per unit, both campaigns.

Run:   python manuscript_ieee/scripts/make_arxiv_swap_figures.py
Out:   manuscript_ieee/arxiv/figures/fig_{timetrace,scatter_ratio,signal_threshold,results,crossover_methods}.pdf/png,
       manuscript_ieee/arxiv/tables/table_swap.tex, manuscript_ieee/arxiv/analysis_swap_numbers.txt

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
from scipy.optimize import curve_fit

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parent
sys.path.insert(0, str(ROOT / "software" / "host"))
sys.path.insert(0, str(HERE))
from rig import analysis as an  # noqa: E402
import crossover_analysis as ca  # noqa: E402
from geometry_sensitivity import axis_fov, end_of_overlap, E_ASSUMED  # noqa: E402

DATA = PROJECT / "data_pair13"
OUTF = PROJECT / "arxiv" / "figures"
OUTT = PROJECT / "arxiv" / "tables"
ADIR = {1: PROJECT / "analysis", 2: PROJECT / "analysis_campaign2"}
SESS = {1: {0.3: "nodiv_0p3", 0.6: "nodiv_0p6", 0.9: "nodiv_0p9"},
        2: {0.3: "swap_0p3", 0.6: "swap_0p6", 0.9: "swap_0p9"}}
TITLE = {1: "Before swap (campaign 1)", 2: "After swap (campaign 2)"}
UNIT_AT = {1: {"A": 3, "B": 1}, 2: {"A": 1, "B": 3}}
DIST = (0.3, 0.6, 0.9)

# palette of Jessica's reference figures (Figs. 6 and 7) and of the earlier Figs. 8 and 9
PCOL = {0.3: "#1f5f8b", 0.6: "#3d9a8b", 0.9: "#d4a72c"}
GREY, ORANGE = "#8a9099", "#d2622f"
COL = {0.3: "#0072B2", 0.6: "#009E73", 0.9: "#D55E00"}
MK = {0.3: "o", 0.6: "s", 0.9: "D"}
ZCOL = {16: "#000000", 4: "#CC79A7"}
META = {"Creator": "", "Producer": "", "Author": "Jessica"}
NOTES = []

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    OUTF.mkdir(exist_ok=True, parents=True)
    fig.savefig(OUTF / f"{name}.png", dpi=300)
    fig.savefig(OUTF / f"{name}.pdf", metadata=META)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------- Fig. 5
def fig_timetrace():
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 3.3), sharex=True)
    for j, camp in enumerate((1, 2)):
        data = an.load(DATA / SESS[camp][0.3])
        runs = an.usable_runs(data)
        blk = runs[runs.block_id == "d030_t000_r1_roi16"]
        run_of = dict(zip(blk.condition, blk.run_id))
        rd = data.readings
        solo = rd[(rd.run_id == run_of["A"]) & (rd.sensor == "A")].sort_values("t_int_us")
        both = rd[(rd.run_id == run_of["AB"]) & (rd.sensor == "A")].sort_values("t_int_us")
        t_solo = (solo.t_int_us.to_numpy() - solo.t_int_us.iloc[0]) / 1e6
        gap = t_solo[-1] + (t_solo[1] - t_solo[0])
        t_both = (both.t_int_us.to_numpy() - both.t_int_us.iloc[0]) / 1e6 + gap
        ax1, ax2 = axes[0, j], axes[1, j]
        ax1.plot(t_solo, solo.ambient_rate, color="#0072B2", lw=0.6)
        ax1.plot(t_both, both.ambient_rate, color="#D55E00", lw=0.6)
        ax1.axvline(gap, color="gray", lw=0.6, ls=":")
        ax1.set_ylim(0, 3500)
        ax1.text(gap / 2, 3400, "A alone", ha="center", va="top", fontsize=7)
        ax1.text(gap + (t_both[-1] - gap) / 2, 3400, "A with B", ha="center", va="top", fontsize=7, color="#D55E00")
        ax1.set_title(f"({'ab'[j]}) {TITLE[camp]}: sensor A is unit {UNIT_AT[camp]['A']}", loc="left", fontsize=7.5,
                      fontweight="bold")
        ax2.plot(t_solo, solo.range_mm, color="#0072B2", lw=0.5, marker=".", ms=1.5, ls="none")
        ax2.plot(t_both, both.range_mm, color="#D55E00", lw=0.5, marker=".", ms=1.5, ls="none")
        ax2.axvline(gap, color="gray", lw=0.6, ls=":")
        ax2.set_xlabel("elapsed time (s)")
        if j == 0:
            ax1.set_ylabel("ambient rate (kcps)")
            ax2.set_ylabel("range (mm)")
        NOTES.append(f"fig5 camp{camp}: solo mean ambient {solo.ambient_rate.mean():.1f}, A+B {both.ambient_rate.mean():.1f} kcps "
                     f"({both.ambient_rate.mean() / solo.ambient_rate.mean():.1f}x); range {solo.range_mm.mean():.2f} -> "
                     f"{both.range_mm.mean():.2f} mm")
    fig.tight_layout()
    save(fig, "fig_timetrace")


# ---------------------------------------------------------------------------------------------- Fig. 6
def scatter_points(camp):
    rows = []
    for d, name in SESS[camp].items():
        data = an.load(DATA / name)
        rs = an.run_stats(data)
        pe = an.pair_effects(rs)
        solo = rs[rs.condition == rs.sensor][["block_id", "sensor", "mean_signal", "dropout"]].rename(columns={"dropout": "sdrop"})
        ab = rs[rs.condition == "AB"][["block_id", "sensor", "dropout"]].rename(columns={"dropout": "adrop"})
        m = pe.merge(solo, on=["block_id", "sensor"]).merge(ab, on=["block_id", "sensor"])
        m["x"] = 100 * m.extra_ambient / m.mean_signal
        m["d"] = d
        m["minvalid"] = 1 - np.maximum(m.sdrop, m.adrop)
        rows.append(m)
    df = pd.concat(rows, ignore_index=True)
    n0 = len(df[np.isfinite(df.sd_ratio) & np.isfinite(df.x)])
    df = df[np.isfinite(df.sd_ratio) & np.isfinite(df.x) & (df.minvalid >= 0.20)]
    return df, n0 - len(df)


def fig_scatter():
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.0))
    for i, camp in enumerate((1, 2)):
        df, dropped = scatter_points(camp)
        f = lambda x, k: np.sqrt(np.clip(1 + k * x, 0, None))
        k, _ = curve_fit(f, df.x.values / 100, df.sd_ratio.values, p0=[3.0])
        k = float(k[0])
        r = float(np.corrcoef(df.x, df.sd_ratio)[0, 1])
        r16 = float(np.corrcoef(df[df.roi == 16].x, df[df.roi == 16].sd_ratio)[0, 1])
        mean_shift, sd_shift = float(df.bias_mm.mean()), float(df.bias_mm.std())
        NOTES.append(f"fig6 camp{camp}: n={len(df)} (dropped {dropped} cells <20% valid), k={k:.2f}, r(all points)={r:.2f}, "
                     f"r(16x16 points)={r16:.2f}, range shift mean {mean_shift:+.3f} mm SD {sd_shift:.3f}; "
                     f"by distance {df.groupby('d').bias_mm.mean().round(3).to_dict()}; max x={df.x.max():.1f}%")
        ax, bx = axes[i]
        for d in DIST:
            for roi, mk, filled in ((16, "o", True), (4, "^", False)):
                g = df[(df.d == d) & (df.roi == roi)]
                if not len(g):
                    continue
                for a, y in ((ax, g.sd_ratio), (bx, g.bias_mm)):
                    a.plot(g.x, y, mk, ms=4.6 if roi == 16 else 5.2, mfc=PCOL[d] if filled else "none", mec=PCOL[d],
                           mew=0.9 if not filled else 0.0, ls="none", zorder=3)
        xs = np.linspace(0, 8.6, 100)
        ax.plot(xs, f(xs / 100, k), color="#333333", lw=1.6, zorder=2)
        ax.axhline(1.0, color="#bbbbbb", lw=0.9, zorder=1)
        bx.axhline(0.0, color="#bbbbbb", lw=0.9, zorder=1)
        ax.set_xlim(-0.4, 8.7)
        bx.set_xlim(-0.4, 8.7)
        ax.set_ylim(0.94, 1.27)
        bx.set_ylim(-2, 2)
        ax.set_ylabel("Range SD ratio (neighbor on / alone)")
        bx.set_ylabel("Range shift (mm)")
        ax.set_title(f"({'ac'[i]}) {TITLE[camp]}" + chr(10) + f"Scatter grows with background relative to signal (r = {r:.2f})",
                     loc="left", fontsize=7)
        bx.set_title(f"({'bd'[i]}) {TITLE[camp]}" + chr(10) + f"No systematic shift in the distance (mean {mean_shift:+.2f} mm)",
                     loc="left", fontsize=7)
        for a in (ax, bx):
            a.grid(color="#eeeeee", lw=0.6)
            a.set_axisbelow(True)
            if i == 1:
                a.set_xlabel("Extra ambient ÷ own signal (%)")
        h = [Line2D([], [], marker="o", ls="", color=PCOL[d], ms=4.6, label=f"16×16, {d:g} m") for d in DIST]
        h += [Line2D([], [], marker="^", ls="", mfc="none", mec=PCOL[d], ms=5.2, label=f"4×4, {d:g} m")
              for d in (0.3, 0.6)]
        h += [Line2D([], [], color="#333333", lw=1.6, label=f"√(1 + k·x), k = {k:.1f}")]
        ax.legend(handles=h, fontsize=6.0, ncol=2, frameon=True, framealpha=0.9, edgecolor="none", loc="upper left",
                  handletextpad=0.3, columnspacing=0.9, borderaxespad=0.2)
    fig.tight_layout(h_pad=1.2, w_pad=1.2)
    save(fig, "fig_scatter_ratio")


# ---------------------------------------------------------------------------------------------- Fig. 7
SIGNAL_THRESHOLD = 1028   # dashed line: between the last rejected (1024) and first accepted (1032) quantised values


def fig_threshold():
    cfg = {1: dict(name="nodiv_0p6", sensor="A", theta=6, ann=(0, 4, 6, 8, 10)),
           2: dict(name="swap_0p6", sensor="B", theta=8, ann=(0, 6, 8, 10, 12))}
    fig, axes = plt.subplots(2, 3, figsize=(7.16, 4.9), gridspec_kw={"width_ratios": [1.15, 1, 1]})
    for i, camp in enumerate((1, 2)):
        c = cfg[camp]
        data = an.load(DATA / c["name"])
        runs = an.usable_runs(data)
        rd = data.readings
        sens = c["sensor"]

        def readings(th, cond):
            sel = runs[(runs.roi == 4) & (runs.dtheta_deg == th)]
            return rd[rd.run_id.isin(sel[sel.condition == cond].run_id) & (rd.sensor == sens)]

        th = c["theta"]
        solo, both = readings(th, sens), readings(th, "AB")
        rej_s, rej_b = 100 * (solo.range_status != 0).mean(), 100 * (both.range_status != 0).mean()
        sd_s, sd_b = solo.signal_rate.std(), both.signal_rate.std()
        NOTES.append(f"fig7 camp{camp}: sensor {sens} (unit {UNIT_AT[camp][sens]}), 0.6 m, 4x4, dtheta={th}: rejected "
                     f"{rej_s:.1f}% -> {rej_b:.1f}%, SD {sd_s:.0f} -> {sd_b:.0f} kcps, mean signal {solo.signal_rate.mean():.0f}")
        a, b, cc = axes[i]
        bins = np.arange(780, 1440, 20)
        a.axvspan(bins[0], SIGNAL_THRESHOLD, color="#eeeeee", zorder=0)
        a.hist(solo.signal_rate, bins=bins, weights=np.full(len(solo), 1 / len(solo)), histtype="step", color=GREY, lw=1.6)
        a.hist(both.signal_rate, bins=bins, weights=np.full(len(both), 1 / len(both)), histtype="step", color=ORANGE, lw=1.6)
        a.axvline(SIGNAL_THRESHOLD, color="#333333", lw=0.9, ls="--")
        a.set_yticks([])
        a.set_ylabel("Fraction of readings")
        a.set_xlabel("Own signal, per reading (kcps)")
        a.set_title(f"({'ad'[i]}) {TITLE[camp]}" + chr(10) + f"4×4, 0.6 m, sensor {sens} (unit {UNIT_AT[camp][sens]}), Δθ = {th}°",
                    loc="left", fontsize=6.8)
        a.set_ylim(0, a.get_ylim()[1] * 1.45)
        a.legend(handles=[Line2D([], [], color=GREY, lw=1.6, label=f"neighbor off: {rej_s:.1f}% rejected (SD {sd_s:.0f} kcps)"),
                          Line2D([], [], color=ORANGE, lw=1.6, label=f"neighbor on: {rej_b:.1f}% rejected (SD {sd_b:.0f} kcps)")],
                 fontsize=5.8, frameon=False, loc="upper right", borderaxespad=0.1, handlelength=1.2)

        edges = np.arange(972, 1080, 8)
        mids = edges[:-1] + 4
        for df_, colr, mk, mfc in ((solo, GREY, "o", GREY), (both, ORANGE, "s", "white")):
            pct = []
            for lo, hi in zip(edges[:-1], edges[1:]):
                g = df_[(df_.signal_rate >= lo) & (df_.signal_rate < hi)]
                pct.append(100 * (g.range_status == 0).mean() if len(g) else np.nan)
            b.plot(mids, pct, mk + "-", color=colr, mfc=mfc, mec=colr, ms=4.8, lw=1.4, mew=1.1)
        b.axvline(SIGNAL_THRESHOLD, color="#333333", lw=0.9, ls="--")
        b.set_ylim(-5, 105)
        b.set_xlabel("Own signal, per reading (kcps)")
        b.set_ylabel("Readings accepted (%)")
        b.set_title(f"({'be'[i]}) The acceptance rule is the same", loc="left", fontsize=6.8, pad=14)
        b.legend(handles=[Line2D([], [], color=GREY, marker="o", lw=1.4, ms=4.8, label="neighbor off"),
                          Line2D([], [], color=ORANGE, marker="s", mfc="white", lw=1.4, ms=4.8, label="neighbor on")],
                 fontsize=6.4, frameon=False, loc="lower right", borderaxespad=0.3)

        angles = sorted(runs[(runs.roi == 4)].dtheta_deg.unique())
        rs_, rb_, ms_ = [], [], {}
        for t in angles:
            s_, b_ = readings(t, sens), readings(t, "AB")
            rs_.append(100 * (s_.range_status != 0).mean())
            rb_.append(100 * (b_.range_status != 0).mean())
            ms_[t] = s_.signal_rate.mean()
        cc.plot(angles, rs_, "o-", color=GREY, ms=4.8, lw=1.4)
        cc.plot(angles, rb_, "s-", color=ORANGE, mfc="white", ms=4.8, lw=1.4, mew=1.1)
        cc.set_ylim(-36, 108)
        cc.set_xlim(-0.8, 25)
        for n_, t in enumerate(c["ann"]):
            cc.text(t, -9 - 9 * (n_ % 2), f"{ms_[t]:.0f}", ha="left" if t == 0 else "center", va="top", fontsize=5.8, color="#777777")
        cc.text(0, -29, "mean signal (kcps) at the labelled angles", fontsize=5.6, color="#777777", va="top", ha="left")
        cc.set_xlabel("Angle between sensors Δθ (°)")
        cc.set_ylabel("Readings rejected (%)")
        cc.set_title(f"({'cf'[i]}) Rejected only near" + chr(10) + "the threshold", loc="left", fontsize=6.8)
        cc.legend(handles=[Line2D([], [], color=GREY, marker="o", lw=1.4, ms=4.8, label="neighbor off"),
                           Line2D([], [], color=ORANGE, marker="s", mfc="white", lw=1.4, ms=4.8, label="neighbor on")],
                  fontsize=6.4, frameon=False, loc="center right", borderaxespad=0.1)
    fig.tight_layout(h_pad=1.4, w_pad=1.0)
    save(fig, "fig_signal_threshold")


# ---------------------------------------------------------------------------------------------- Figs. 8 and 9
def cells(camp):
    store = {}
    for d, name in SESS[camp].items():
        pairs = ca.block_table(name)
        for roi in (16, 4):
            store[(d, roi)] = ca.cell_arrays(pairs, roi)
    return store


def summary(camp):
    est = pd.read_csv(ADIR[camp] / "crossover_estimates.csv")
    est = est[est.phi == 0.10]
    brk = pd.read_csv(ADIR[camp] / "crossover_bracket.csv").set_index(["distance_m", "zone"])
    ext = pd.read_csv(ADIR[camp] / "extinction.csv").set_index(["distance_m", "zone"])
    rows = []
    for d in DIST:
        for roi in (16, 4):
            z = f"{roi}x{roi}"
            e = est[(est.distance_m == d) & (est.zone == z)].set_index("method")
            rows.append({"zone": z, "distance_m": d, "m4": e.loc["M4", "crossover_deg"],
                         "lo": brk.loc[(d, z), "last_above_deg"], "hi": brk.loc[(d, z), "first_at_or_below_deg"],
                         "a1": ext.loc[(d, z), "angle_at_1pct_deg"]})
    return pd.DataFrame(rows)


def fig_results():
    fig, axes = plt.subplots(2, 3, figsize=(7.16, 4.5), gridspec_kw={"width_ratios": [1, 1, 0.92]})
    grid = np.linspace(0, 24, 481)
    for i, camp in enumerate((1, 2)):
        store, s = cells(camp), summary(camp)
        for j, (roi, tag) in enumerate(((16, "16×16 zone"), (4, "4×4 zone"))):
            ax = axes[i, j]
            for d in DIST:
                levels, vals = store[(d, roi)]
                means = np.array([v.mean() for v in vals])
                sds = np.array([v.std(ddof=1) for v in vals])
                ref = means.max()
                ax.plot(grid, 100 * PchipInterpolator(levels, means)(grid) / ref, color=COL[d], lw=0.7, alpha=0.85, zorder=2)
                ax.errorbar(levels, 100 * means / ref, yerr=100 * sds / ref, fmt=MK[d], ms=3.2, color=COL[d], elinewidth=0.5,
                            capsize=1, zorder=3, mfc=COL[d] if roi == 16 else "white", mew=0.8)
                r = s[(s.zone == f"{roi}x{roi}") & (s.distance_m == d)].iloc[0]
                ax.plot([r.m4], [10], marker="v", ms=5.5, color=COL[d], mec="black", mew=0.5, zorder=5)
                ax.plot([end_of_overlap(E_ASSUMED, ca.geometry.RECEIVE_FIELD_DEG[roi], d)], [0], marker="^", ms=5, mfc="white",
                        mec=COL[d], mew=0.9, clip_on=False, zorder=4)
            ax.axhline(10, color="#777777", lw=0.5, ls="--", zorder=1)
            ax.axhline(1, color="#999999", lw=0.5, ls=":", zorder=1)
            ax.set_xlim(-0.6, 27)
            ax.set_ylim(-4, 112)
            ax.set_xlabel("Δθ (degrees)")
            ax.set_title(f"({'abcdef'[i * 3 + j]}) {tag}" + chr(10) + TITLE[camp], loc="left", fontsize=6.8, fontweight="bold")
        axes[i, 0].set_ylabel("Extra ambient (% of peak)")
        if i == 0:
            h = [Line2D([], [], marker=MK[d], color=COL[d], lw=0.7, ms=3.5, mfc=COL[d], label=f"{d:g} m") for d in DIST]
            h += [Line2D([], [], marker="v", ls="", color="#999999", mec="black", mew=0.5, ms=5, label="10% crossing"),
                  Line2D([], [], marker="^", ls="", mfc="white", mec="#555555", mew=0.9, ms=5, label="geometric model")]
            axes[0, 1].legend(handles=h, fontsize=6, frameon=False, loc="upper right", handletextpad=0.3, borderaxespad=0.1,
                              labelspacing=0.25)
        ax = axes[i, 2]
        dd = np.linspace(0.25, 0.95, 50)
        for roi in (16, 4):
            z = f"{roi}x{roi}"
            c = ZCOL[roi]
            g = s[s.zone == z]
            ax.plot(dd, [end_of_overlap(E_ASSUMED, ca.geometry.RECEIVE_FIELD_DEG[roi], x) for x in dd], color=c, lw=0.8, zorder=1)
            ax.plot(dd, [end_of_overlap(E_ASSUMED, axis_fov(ca.geometry.RECEIVE_FIELD_DEG[roi]), x) for x in dd], color=c,
                    lw=0.8, ls="--", zorder=1)
            ax.errorbar(g.distance_m, g.m4, yerr=[g.m4 - g.lo, g.hi - g.m4], fmt="o", ms=3.8, color=c, capsize=1.8,
                        elinewidth=0.7, zorder=3)
            ax.plot(g.distance_m, g.a1, "s", ms=3.8, mfc="white", mec=c, mew=1.0, zorder=3)
        ax.set_xlim(0.22, 0.98)
        ax.set_ylim(0, 28)
        ax.set_xlabel("Distance (m)")
        ax.set_ylabel("Δθ (degrees)")
        ax.set_xticks([0.3, 0.6, 0.9])
        ax.set_title(f"({'abcdef'[i * 3 + 2]}) Angles against distance" + chr(10) + TITLE[camp], loc="left", fontsize=6.8,
                     fontweight="bold")
        ax.text(0.62, 27.0, "16×16", color=ZCOL[16], fontsize=6.5, ha="center", va="top", fontweight="bold")
        ax.text(0.45, 12.6, "4×4", color=ZCOL[4], fontsize=6.5, ha="center", va="center", fontweight="bold")
        if i == 0:
            h = [Line2D([], [], marker="o", ls="", color="#444444", ms=3.8, label="10% crossing (bar: bracket)"),
                 Line2D([], [], marker="s", ls="", mfc="white", mec="#444444", mew=1.0, ms=3.8, label="1% of peak"),
                 Line2D([], [], color="#444444", lw=0.8, label="model"),
                 Line2D([], [], color="#444444", lw=0.8, ls="--", label="model, receive field in-plane")]
            ax.legend(handles=h, fontsize=5.4, frameon=False, loc="lower right", handletextpad=0.3, borderaxespad=0.1,
                      labelspacing=0.2)
    fig.tight_layout(w_pad=0.9, h_pad=1.2)
    save(fig, "fig_results")


def fig_methods():
    colour = {"M1": "#0072B2", "M4": "#009E73", "M5": "#D55E00"}
    grid = np.linspace(0, 24, 481)
    fig, axes = plt.subplots(4, 3, figsize=(7.16, 8.2), sharex=True)
    row = 0
    for camp in (1, 2):
        store = cells(camp)
        est_all = pd.read_csv(ADIR[camp] / "crossover_estimates.csv")
        for roi in (16, 4):
            for c, d in enumerate(DIST):
                ax = axes[row, c]
                levels, vals = store[(d, roi)]
                means = np.array([v.mean() for v in vals])
                sds = np.array([v.std(ddof=1) for v in vals])
                ref = means.max()
                ax.errorbar(levels, 100 * means / ref, yerr=100 * sds / ref, fmt="o", ms=3, color="black", capsize=1.5,
                            elinewidth=0.6, zorder=5)
                x, y = ca.flat(levels, vals)
                p1, p5 = ca.fit_logistic(x, y), ca.fit_tilted(x, y)
                if p1 is not None:
                    ax.plot(grid, 100 * ca.logistic(grid, *p1) / ref, color=colour["M1"], lw=0.9)
                if p5 is not None:
                    ax.plot(grid, 100 * ca.tilted(grid, *p5) / ref, color=colour["M5"], lw=0.9, ls="--")
                ax.plot(grid, 100 * PchipInterpolator(levels, means)(grid) / ref, color=colour["M4"], lw=0.7, ls=":")
                e = est_all[(est_all.distance_m == d) & (est_all.zone == f"{roi}x{roi}") & (est_all.phi == 0.10)].set_index("method")
                for k, ms_, z in (("M4", 7.0, 5.5), ("M5", 5.0, 6.0), ("M1", 4.0, 6.5)):
                    v = e.loc[k, "crossover_deg"]
                    if np.isfinite(v):
                        ax.plot([v], [10], marker="v", ms=ms_, color=colour[k], mec="black", mew=0.4, zorder=z)
                ax.axvline(end_of_overlap(E_ASSUMED, ca.geometry.RECEIVE_FIELD_DEG[roi], d), color="#777777", lw=0.7, ls="-.")
                ax.axhline(10, color="#999999", lw=0.5, ls="--")
                ax.set_ylim(-8, 118)
                ax.set_xlim(-0.5, 27)
                ax.set_title(f"{roi}×{roi}, {d:.1f} m, {'before' if camp == 1 else 'after'} swap", fontsize=7, loc="left",
                             fontweight="bold")
                if c == 0:
                    ax.set_ylabel("Extra ambient (% of peak)")
                if row == 3:
                    ax.set_xlabel("Δθ (degrees)")
            row += 1
    h = [Line2D([], [], color=colour["M1"], lw=0.9, label="M1 logistic"),
         Line2D([], [], color=colour["M5"], lw=0.9, ls="--", label="M5 tilted logistic"),
         Line2D([], [], color=colour["M4"], lw=0.7, ls=":", label="M4 PCHIP"),
         Line2D([], [], color="#777777", lw=0.7, ls="-.", label="geometric model"),
         Line2D([], [], marker="v", ls="", color="#999999", mec="black", mew=0.4, ms=4.5, label="10% crossing")]
    fig.legend(h, [x.get_label() for x in h], loc="lower center", ncol=5, fontsize=6.5, frameon=False)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "fig_crossover_methods")


# ---------------------------------------------------------------------------------------------- unit-swap table
def unit_table():
    out = {}
    for camp in (1, 2):
        ps = pd.read_csv(ADIR[camp] / "crossover_per_sensor.csv")
        ps = ps[ps.method == "M4"].set_index(["distance_m", "zone"])
        for d in DIST:
            pairs = ca.block_table(SESS[camp][d])
            for roi in (16, 4):
                z = f"{roi}x{roi}"
                for sensor in "AB":
                    lv, vals = ca.cell_arrays(pairs, roi, sensor=sensor)
                    peak = max(v.mean() for v in vals)
                    cross = ps.loc[(d, z), f"{sensor}_deg"]
                    out[(camp, d, roi, UNIT_AT[camp][sensor])] = (cross, peak)
    lines = [r"\begin{table*}[!t]", r"\centering",
             r"\caption{Unit-swap results: \SI{10}{\percent} crossing angle (M4, degrees) and peak extra ambient rate (kcps) "
             r"of each unit, in campaign~1 (unit~3 at A, unit~1 at B) and campaign~2 (units exchanged), each sensor analysed "
             r"separately}",
             r"\label{tab:swap}", r"\footnotesize", r"\setlength{\tabcolsep}{3pt}",
             r"\begin{tabular}{@{}ll*{4}{c}*{4}{c}*{2}{c}@{}}", r"\toprule",
             r" & & \multicolumn{4}{c}{Crossing angle (deg)} & \multicolumn{4}{c}{Peak extra ambient (kcps)} & "
             r"\multicolumn{2}{c}{Gap, unit~3 $-$ unit~1 (deg)} \\",
             r"\cmidrule(lr){3-6}\cmidrule(lr){7-10}\cmidrule(l){11-12}",
             r"Zone & $d$ (m) & \multicolumn{2}{c}{unit~3} & \multicolumn{2}{c}{unit~1} & \multicolumn{2}{c}{unit~3} & "
             r"\multicolumn{2}{c}{unit~1} & camp.~1 & camp.~2 \\",
             r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}\cmidrule(lr){9-10}",
             r" & & camp.~1 & camp.~2 & camp.~1 & camp.~2 & camp.~1 & camp.~2 & camp.~1 & camp.~2 & & \\", r"\midrule"]
    for roi in (16, 4):
        for d in DIST:
            c31, p31 = out[(1, d, roi, 3)]
            c32, p32 = out[(2, d, roi, 3)]
            c11, p11 = out[(1, d, roi, 1)]
            c12, p12 = out[(2, d, roi, 1)]
            zone = r"$16\times16$" if roi == 16 else r"$4\times4$"
            lines.append(f"{zone} & {d:g} & {c31:.2f} & {c32:.2f} & {c11:.2f} & {c12:.2f} & {p31:.0f} & {p32:.0f} & {p11:.0f} & "
                         f"{p12:.0f} & ${c31 - c11:+.2f}$ & ${c32 - c12:+.2f}$ \\\\")
            NOTES.append(f"swap table {roi}x{roi} {d}: unit3 cross {c31:.2f}/{c32:.2f} peak {p31:.0f}/{p32:.0f}; "
                         f"unit1 cross {c11:.2f}/{c12:.2f} peak {p11:.0f}/{p12:.0f}")
        if roi == 16:
            lines.append(r"\midrule")
    lines += [r"\bottomrule", r"\end{tabular}", r"\\[2pt]",
              r"{\footnotesize Unit~3 crossed earlier than unit~1 in the full array and later in the window in both campaigns, "
              r"whichever position (A or B) it occupied: the gap between the units keeps its sign after the swap. The peak is "
              r"the largest cell mean of the sensor's own extra ambient rate. A swap cannot separate a unit's receiver from its "
              r"emitter (Section~\ref{sec:geommodel}).}", r"\end{table*}"]
    OUTT.mkdir(exist_ok=True, parents=True)
    (OUTT / "table_swap.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    fig_timetrace()
    fig_scatter()
    fig_threshold()
    fig_results()
    fig_methods()
    unit_table()
    (PROJECT / "arxiv" / "analysis_swap_numbers.txt").write_text("\n".join(NOTES) + "\n", encoding="utf-8")
    print("\n".join(NOTES))


if __name__ == "__main__":
    main()
