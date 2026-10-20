"""New Figs. 4, 5 and 6 added for the revision following Jessica's comments (Comments v1.docx, 14 Oct 2026):
Fig. 4  time traces of ambient and range for one block, sensor A alone then with B (0.3 m, theta=0, roi=16).
Fig. 5  range SD ratio (A+B over solo) against extra ambient / own signal, every accepted (block, sensor) in the
        no-divider sweep, all three distances and both zones.
Fig. 6  (a) per-reading signal histogram, solo vs A+B, 4x4 window at 0.6 m, sensor A, dtheta=6 deg (the cleanest
        demonstration: solo signal already straddles the threshold there, so the small extra background
        measurably moves accepted readings below it); (b) change in accepted share (A+B minus solo) against the
        solo accepted share, for every partly accepted 4x4 cell of both campaigns (six cells; Jessica's comment on
        the v5 redline: a step-function restatement of the threshold rule carries no information panel (a)
        doesn't already show).

Figs. 4 and 5, and panel (a) of Fig. 6, are computed from manuscript_ieee/data_pair13/nodiv_0p3/0p6/0p9 (campaign
1, the no-divider sweep) only; nothing there is carried over from the swap or divider campaigns. Panel (b) of
Fig. 6 draws on both campaigns (nodiv_* and swap_*), as noted above.

Run:   python manuscript_ieee/scripts/make_fig_demo_figures.py
Out:   figures/fig_timetrace.pdf/png, figures/fig_scatter_ratio.pdf/png, figures/fig_signal_threshold.pdf/png

Author: Jessica
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crossover_analysis as ca  # noqa: E402
from rig import analysis as an  # noqa: E402

# Figs. 4 and 5, and panel (a) of Fig. 6, always read campaign 1 (the no-divider sweep); only the save location
# is configurable, via FIG_OUT, so the arxiv rebuild (which also wants the updated Fig. 6 panel (b), drawing on
# both campaigns) does not overwrite the main letter's figures. Independent of CROSSOVER_CAMPAIGN.
C1 = {0.3: "nodiv_0p3", 0.6: "nodiv_0p6", 0.9: "nodiv_0p9"}
C2 = {0.3: "swap_0p3", 0.6: "swap_0p6", 0.9: "swap_0p9"}
FIG = Path(os.environ["FIG_OUT"]) if os.environ.get("FIG_OUT") else ca.PROJECT / "figures"
FIG.mkdir(exist_ok=True, parents=True)
COL = {0.3: "#0072B2", 0.6: "#009E73", 0.9: "#D55E00"}
MK = {0.3: "o", 0.6: "s", 0.9: "D"}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42})


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=600)
    fig.savefig(FIG / f"{name}.pdf", metadata={"Creator": "", "Producer": "", "Author": "Jessica"})
    plt.close(fig)


# ------------------------------------------------------------------ Fig. 4: time trace, one block
def fig_timetrace():
    data = an.load(ca.DATA / "nodiv_0p3")
    runs = an.usable_runs(data)
    blk = runs[runs.block_id == "d030_t000_r1_roi16"]
    run_of = dict(zip(blk.condition, blk.run_id))
    rd = data.readings
    solo = rd[(rd.run_id == run_of["A"]) & (rd.sensor == "A")].sort_values("t_int_us")
    both = rd[(rd.run_id == run_of["AB"]) & (rd.sensor == "A")].sort_values("t_int_us")
    t0 = solo.t_int_us.iloc[0]
    t_solo = (solo.t_int_us.to_numpy() - t0) / 1e6
    gap = t_solo[-1] + (t_solo[1] - t_solo[0])
    t_both = (both.t_int_us.to_numpy() - both.t_int_us.iloc[0]) / 1e6 + gap

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.45, 3.3), sharex=True)
    ax1.plot(t_solo, solo.ambient_rate, color="#0072B2", lw=0.6)
    ax1.plot(t_both, both.ambient_rate, color="#D55E00", lw=0.6)
    ax1.axvline(gap, color="gray", lw=0.6, ls=":")
    ax1.set_ylabel("ambient rate (kcps)")
    ax1.text(gap / 2, ax1.get_ylim()[1] * 0.92, "A alone", ha="center", va="top", fontsize=7)
    ax1.text(gap + (t_both[-1] - gap) / 2, ax1.get_ylim()[1] * 0.92, "A with B", ha="center", va="top", fontsize=7,
              color="#D55E00")

    ax2.plot(t_solo, solo.range_mm, color="#0072B2", lw=0.5, marker=".", ms=1.5, ls="none")
    ax2.plot(t_both, both.range_mm, color="#D55E00", lw=0.5, marker=".", ms=1.5, ls="none")
    ax2.axvline(gap, color="gray", lw=0.6, ls=":")
    ax2.set_ylabel("range (mm)")
    ax2.set_xlabel("elapsed time (s)")

    fig.tight_layout()
    save(fig, "fig_timetrace")
    print(f"fig_timetrace: solo mean ambient {solo.ambient_rate.mean():.1f} kcps, "
          f"A+B mean ambient {both.ambient_rate.mean():.1f} kcps, ratio {both.ambient_rate.mean()/solo.ambient_rate.mean():.1f}x; "
          f"solo mean range {solo.range_mm.mean():.2f} mm, A+B mean range {both.range_mm.mean():.2f} mm")


# ------------------------------------------------------------------ Fig. 5: scatter, sd_ratio vs extra_ambient/signal
def fig_scatter_ratio():
    rows = []
    for d, name in C1.items():
        data = an.load(ca.DATA / name)
        rs = an.run_stats(data)
        pairs = an.pair_effects(rs)
        # own (solo) signal and valid fraction per (block, sensor), to normalise extra ambient and to drop
        # cells where the range SD is computed from too few valid readings to be meaningful (Jessica's comment
        # on the v5 redline: the two outliers near sd_ratio=0.37 come from a solo valid fraction of 0.5-0.7%).
        solo = rs[rs["condition"] == rs["sensor"]][["block_id", "sensor", "mean_signal", "dropout"]]
        solo = solo.rename(columns={"dropout": "solo_dropout"})
        both = rs[rs["condition"] == "AB"][["block_id", "sensor", "dropout"]].rename(columns={"dropout": "ab_dropout"})
        m = pairs.merge(solo, on=["block_id", "sensor"], how="left").merge(both, on=["block_id", "sensor"], how="left")
        m["eas"] = m.extra_ambient / m.mean_signal
        m["distance_m"] = d
        m["min_valid_frac"] = 1.0 - np.maximum(m.solo_dropout, m.ab_dropout)
        rows.append(m)
    df = pd.concat(rows, ignore_index=True)
    n_before = len(df[np.isfinite(df.sd_ratio) & np.isfinite(df.eas)])
    df = df[np.isfinite(df.sd_ratio) & np.isfinite(df.eas) & (df.min_valid_frac >= 0.20)]
    print(f"fig_scatter_ratio: dropped {n_before - len(df)} of {n_before} points with <20% valid readings "
          f"(solo or A+B)")

    fig, ax = plt.subplots(figsize=(3.45, 2.6))
    for d in (0.3, 0.6, 0.9):
        for roi, mk, mfc in ((16, MK[d], COL[d]), (4, MK[d], "none")):
            g = df[(df.distance_m == d) & (df.roi == roi)]
            ax.plot(g.eas, g.sd_ratio, marker=mk, ls="none", ms=3.2, mfc=mfc, mec=COL[d], mew=0.6,
                    label=f"{d:g} m, {roi}x{roi}" if False else None)
    # build a compact legend: colour = distance, fill = zone
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker=MK[d], ls="none", mfc=COL[d], mec=COL[d], label=f"{d:g} m, 16x16") for d in (0.3, 0.6, 0.9)]
    handles += [Line2D([], [], marker=MK[d], ls="none", mfc="none", mec=COL[d], label=f"{d:g} m, 4x4") for d in (0.3, 0.6, 0.9)]
    ax.legend(handles=handles, fontsize=5.5, ncol=2, loc="upper left", frameon=False)
    ax.set_xlabel("extra ambient / own signal")
    ax.set_ylabel("range SD ratio (A+B / solo)")
    ax.axhline(1.0, color="gray", lw=0.5, ls="--")
    fig.tight_layout()
    save(fig, "fig_scatter_ratio")
    n_full = df[df.roi == 16]
    print(f"fig_scatter_ratio: n={len(df)} points plotted (of {len(pd.concat(rows))} total; "
          f"the rest have no valid-range SD, mostly the 4x4 window beyond 0.3 m); "
          f"16x16 correlation(eas, sd_ratio) = {np.corrcoef(n_full.eas, n_full.sd_ratio)[0,1]:.2f}")
    return df


# ------------------------------------------------------------------ Fig. 6: signal histogram + six-cell summary
def six_partly_accepted_cells():
    """Every (distance, dtheta, sensor) 4x4-window cell with a partly accepted solo share (0.01 < share < 0.995),
    across both campaigns (Jessica's comment on the v5 redline: six such cells; a step-function restatement of the
    threshold rule in panel (b) carries no information beyond panel (a), so panel (b) is this summary instead)."""
    rows = []
    for camp, D in (("1", C1), ("2", C2)):
        for d, name in D.items():
            data = an.load(ca.DATA / name)
            rs = an.run_stats(data)
            for sensor in ("A", "B"):
                g = rs[(rs.roi == 4) & (rs.sensor == sensor)]
                for dth, gg in g.groupby("dtheta_deg"):
                    solo = gg[gg.condition == sensor]
                    both = gg[gg.condition == "AB"]
                    if len(solo) == 0 or len(both) == 0:
                        continue
                    n_solo, nv_solo = solo.n.sum(), solo.n_valid.sum()
                    solo_frac = nv_solo / n_solo if n_solo else np.nan
                    if not (0.01 < solo_frac < 0.995):
                        continue
                    n_ab, nv_ab = both.n.sum(), both.n_valid.sum()
                    ab_frac = nv_ab / n_ab if n_ab else np.nan
                    rows.append({"camp": camp, "d": d, "dtheta": dth, "sensor": sensor,
                                 "solo_pct": 100 * solo_frac, "ab_pct": 100 * ab_frac,
                                 "delta_pts": 100 * (ab_frac - solo_frac)})
    return pd.DataFrame(rows)


def fig_signal_threshold():
    data = an.load(ca.DATA / "nodiv_0p6")
    runs = an.usable_runs(data)
    sel = runs[(runs.roi == 4) & (runs.dtheta_deg == 6)]
    solo_runs = sel[sel.condition == "A"].run_id
    ab_runs = sel[sel.condition == "AB"].run_id
    rd = data.readings
    solo = rd[(rd.run_id.isin(solo_runs)) & (rd.sensor == "A")]
    both = rd[(rd.run_id.isin(ab_runs)) & (rd.sensor == "A")]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.6, 1.9))
    bins = np.arange(900, 1200, 10)
    ax1.hist(solo.signal_rate, bins=bins, histtype="step", color="#0072B2", lw=0.9, label="alone")
    ax1.hist(both.signal_rate, bins=bins, histtype="step", color="#D55E00", lw=0.9, label="with B")
    ax1.axvline(1024, color="gray", lw=0.6, ls=":")
    ax1.set_xlabel("signal rate (kcps)")
    ax1.set_ylabel("readings")
    ax1.legend(fontsize=5.5, frameon=False, loc="upper left")

    six = six_partly_accepted_cells()
    colors = {"1": "#0072B2", "2": "#D55E00"}
    for camp, g in six.groupby("camp"):
        ax2.scatter(g.solo_pct, g.delta_pts, s=14, color=colors[camp], label=f"campaign {camp}")
    ax2.axhline(0, color="gray", lw=0.6, ls=":")
    ax2.axvline(50, color="gray", lw=0.5, ls="--")
    ax2.set_xlabel("solo accepted share (%)")
    ax2.set_ylabel("change, A+B $-$ solo (pts)")
    ax2.legend(fontsize=5.5, frameon=False, loc="upper right")

    fig.tight_layout()
    save(fig, "fig_signal_threshold")
    print(f"fig_signal_threshold (0.6 m, 4x4, sensor A, dtheta=6): "
          f"solo accepted {np.mean(solo.range_status==0):.3f} (median signal {solo.signal_rate.median():.0f}), "
          f"A+B accepted {np.mean(both.range_status==0):.3f} (median signal {both.signal_rate.median():.0f})")
    print("six partly-accepted 4x4 cells:")
    print(six.round(1).to_string(index=False))


if __name__ == "__main__":
    fig_timetrace()
    fig_scatter_ratio()
    fig_signal_threshold()
