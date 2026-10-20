"""The four figures listed in the procedure.

1. Extra ambient rate against dtheta, 2 ROI x 2 distances, predicted and
   fitted crossovers marked.
2. SD ratio against dtheta, same layout.
3. Extra dropout rate against dtheta.
4. One A+B run, range against time, to check for drift.

Each figure is saved as PNG and PDF with the author set to Jessica and the
plotting library's own creator/producer stamps removed.

Author: Jessica
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import numpy as np                # noqa: E402
import pandas as pd               # noqa: E402

from .analysis import logistic   # noqa: E402

PDF_META = {"Author": "Jessica", "Creator": None, "Producer": None}
PNG_META = {"Author": "Jessica", "Software": None}
COLOURS = {(16, 0): "#1f5fa8", (16, 1): "#7aa6db", (4, 0): "#b8452e", (4, 1): "#e79a86"}


def _save(fig, path: Path) -> None:
    fig.savefig(path.with_suffix(".png"), dpi=200, metadata=PNG_META, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), metadata={**PDF_META, "Title": path.stem}, bbox_inches="tight")
    plt.close(fig)


def _curves(ax, summ: pd.DataFrame, metric: str, transform=None) -> None:
    main = summ[summ["tag"] == ""]
    dists = sorted(main["distance_m"].unique())
    for (d, roi), g in main.groupby(["distance_m", "roi"]):
        g = g.sort_values("dtheta_deg")
        colour = COLOURS.get((int(roi), dists.index(d)), None)
        m, lo, hi = (g[f"{metric}_mean"], g[f"{metric}_ci_lo"], g[f"{metric}_ci_hi"])
        if transform:
            m, lo, hi = transform(m), transform(lo), transform(hi)
        yerr = np.vstack([m - lo, hi - m])
        ax.errorbar(g["dtheta_deg"], m, yerr=np.nan_to_num(yerr), fmt="o-", ms=4, lw=1.2, capsize=3,
                    color=colour, label=f"{d:g} m, ROI {int(roi)}x{int(roi)}")
    ax.set_xlabel("Toe-out between the sensors, dtheta (deg)")
    ax.grid(alpha=0.3)


def fig_extra_ambient(summ: pd.DataFrame, xo: pd.DataFrame, out: Path) -> None:
    fig, (ax, axr) = plt.subplots(1, 2, figsize=(12, 4.6))
    _curves(ax, summ, "extra_ambient")
    dists = sorted(summ["distance_m"].unique())
    for _, r in xo.iterrows():
        colour = COLOURS.get((int(r["roi"]), dists.index(r["distance_m"]))) if r["distance_m"] in dists else None
        if np.isfinite(r["top"]):
            xs = np.linspace(0, max(summ["dtheta_deg"].max(), 1), 200)
            ax.plot(xs, logistic(xs, r["top"], r["x0"], r["w"]), "-", lw=0.8, alpha=0.6, color=colour)
        for a in (ax, axr):
            if np.isfinite(r["predicted_deg"]):
                a.axvline(r["predicted_deg"], ls="--", lw=0.9, color=colour)
        if np.isfinite(r["crossover_deg"]):
            ax.plot([r["crossover_deg"]], [0], marker="v", ms=8, color=colour)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("Extra ambient rate, A+B minus solo (kcps)")
    ax.set_title("Extra ambient light (fit and crossover use this)\n"
                 "dashed: predicted crossover, triangle: measured 10% point", fontsize=10)
    ax.legend(fontsize=8)
    _curves(axr, summ, "rel_extra_ambient", transform=lambda v: 100 * v)
    axr.axhline(0, color="k", lw=0.6)
    axr.set_ylabel("Extra ambient, % of the solo level")
    axr.set_title("Same, relative to each ROI's own solo ambient", fontsize=10)
    _save(fig, out / "fig1_extra_ambient")


def fig_sd_ratio(summ: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    _curves(ax, summ, "log_sd_ratio", transform=np.exp)
    ax.axhline(1, color="k", lw=0.6)
    ax.set_ylabel("Range SD ratio, A+B / solo (geometric mean)")
    ax.set_title("Range scatter with the other sensor emitting", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, out / "fig2_sd_ratio")


def fig_dropout(summ: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    _curves(ax, summ, "extra_dropout", transform=lambda v: 100 * v)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("Extra invalid readings, A+B minus solo (%)")
    ax.set_title("Dropouts (range status not 0)", fontsize=10)
    ax.legend(fontsize=8)
    _save(fig, out / "fig3_dropout")


def fig_drift(readings: pd.DataFrame, rs: pd.DataFrame, out: Path) -> None:
    both = rs[(rs["condition"] == "AB") & (rs["tag"] == "")].sort_values(["dtheta_deg", "distance_m", "run_id"])
    if both.empty:
        return
    run_id = both.iloc[0]["run_id"]
    info = both.iloc[0]
    g = readings[readings["run_id"] == run_id]
    fig, axes = plt.subplots(2, 1, figsize=(7.5, 5.2), sharex=True)
    t0 = g["t_int_us"].min()
    for sensor, colour in (("A", "#1f5fa8"), ("B", "#b8452e")):
        s = g[g["sensor"] == sensor]
        t = (s["t_int_us"] - t0) / 1e6
        valid = s["range_status"] == 0
        axes[0].plot(t[valid], s["range_mm"][valid], ".", ms=2, color=colour, alpha=0.5, label=sensor)
        axes[0].plot(t[valid], s["range_mm"][valid].rolling(25, center=True, min_periods=5).mean(), "-",
                     color=colour, lw=1.2)
        axes[1].plot(t, s["ambient_rate"].rolling(25, center=True, min_periods=5).mean(), "-", color=colour,
                     lw=1.2, label=sensor)
    axes[0].set_ylabel("Range (mm)")
    axes[1].set_ylabel("Ambient, 1 s mean (kcps)")
    axes[1].set_xlabel("Time in run (s)")
    axes[0].legend(fontsize=8, markerscale=4)
    axes[0].set_title(f"Run {run_id}: both sensors ranging, dtheta = {info['dtheta_deg']:g} deg, "
                      f"{info['distance_m']:g} m, ROI {int(info['roi'])}x{int(info['roi'])}", fontsize=10)
    for ax in axes:
        ax.grid(alpha=0.3)
    _save(fig, out / "fig4_drift")


def make_all(data, rs, pairs, summ, xo, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fig_extra_ambient(summ, xo, out)
    fig_sd_ratio(summ, out)
    fig_dropout(summ, out)
    fig_drift(data.readings, rs, out)
