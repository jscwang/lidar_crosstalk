"""Fig. 1 (concept: sensor array, overlapping beams) and Fig. 2 (principle: histogram sketch and overlap
geometry), added for the revision following Jessica's comments (Comments v1.docx, 14 Oct 2026). Both are
schematic -- no data is plotted -- and illustrate the apparatus and the overlap-geometry formula already in
the Methodology (Eq. in sections/methodology.tex). A real setup photo or CAD render (Fig. 3) is still needed
from Jessica; these two do not substitute for it.

Run:   python manuscript_ieee/scripts/make_fig_concept_and_principle.py
Out:   figures/fig_concept.pdf/png, figures/fig_principle.pdf/png

Author: Jessica
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Wedge, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

FIG = Path(__file__).resolve().parent.parent / "figures"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6, "pdf.fonttype": 42})


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=600)
    fig.savefig(FIG / f"{name}.pdf", metadata={"Creator": "", "Producer": "", "Author": "Jessica"})
    plt.close(fig)


# ------------------------------------------------------------------ Fig. 1: concept
def fig_concept():
    fig, ax = plt.subplots(figsize=(3.45, 2.0))
    ax.set_xlim(-1.5, 6.5)
    ax.set_ylim(-1.0, 3.2)
    ax.axis("off")

    # a small array of four sensors, side by side, each with an emitter+receive cone
    xs = [0, 1.4, 2.8, 4.2]
    cone = 32
    for i, x in enumerate(xs):
        ax.add_patch(Rectangle((x - 0.2, 0), 0.4, 0.4, fc="#444444", ec="none"))
        w = Wedge((x, 0.4), 3.0, 90 - cone / 2, 90 + cone / 2, fc="#D55E00" if i in (1, 2) else "#0072B2",
                  alpha=0.18, ec="none")
        ax.add_patch(w)
        ax.plot([x, x], [0.4, 0.4], marker="s", ms=0, color="none")
    ax.text(xs[1], -0.55, "sensor $i$", ha="center", fontsize=7)
    ax.text(xs[2], -0.55, "sensor $i{+}1$", ha="center", fontsize=7)
    # highlight the shared overlap region between sensors 1 and 2 (indices 1,2)
    ax.annotate("overlap", xy=((xs[1] + xs[2]) / 2, 2.05), xytext=((xs[1] + xs[2]) / 2, 2.6),
                ha="center", fontsize=7, arrowprops=dict(arrowstyle="->", color="black", lw=0.8))
    ax.text((xs[1] + xs[2]) / 2, 0.75, "target", ha="center", fontsize=6.5, color="gray")
    ax.plot([-1.0, 5.6], [2.9, 2.9], color="gray", lw=3, solid_capstyle="butt")
    ax.text(5.8, 2.9, "target\nsurface", ha="left", va="center", fontsize=6)

    fig.tight_layout()
    save(fig, "fig_concept")


# ------------------------------------------------------------------ Fig. 2: principle (histogram + geometry)
def fig_principle():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(3.45, 1.7))

    # (a) histogram sketch: own peak + neighbour's flat floor
    t = np.linspace(0, 10, 600)
    own_peak = 1.0 * np.exp(-0.5 * ((t - 4.2) / 0.18) ** 2)
    floor = 0.10 + 0.0 * t
    ax1.fill_between(t, 0, floor, color="#D55E00", alpha=0.35, lw=0)
    ax1.plot(t, own_peak + floor, color="#0072B2", lw=1.0)
    ax1.plot(t, floor, color="#D55E00", lw=0.9, ls="--")
    ax1.annotate("own return\n(signal)", xy=(4.2, 1.05), xytext=(5.6, 0.95), fontsize=6,
                 arrowprops=dict(arrowstyle="->", lw=0.6))
    ax1.annotate("neighbor's light\n(ambient floor)", xy=(1.2, 0.10), xytext=(0.0, 0.45), fontsize=6,
                 arrowprops=dict(arrowstyle="->", lw=0.6))
    ax1.set_xlabel("photon arrival time")
    ax1.set_ylabel("photon count")
    ax1.set_xticks([]); ax1.set_yticks([])
    ax1.set_title("(a)", fontsize=7.5, loc="left")

    # (b) overlap geometry, matching Eq. (the s, d, E, F, dtheta_g of the Methodology)
    d = 2.2
    s = 0.35
    half_E = np.radians(16)
    half_F = np.radians(10)
    dthg = np.radians(10)
    Ax, Ay = -s / 2, 0.0
    Bx, By = s / 2, 0.0
    ax2.plot([Ax], [Ay], marker="s", ms=5, color="#0072B2", zorder=5)
    ax2.plot([Bx], [By], marker="s", ms=5, color="#D55E00", zorder=5)
    ax2.text(Ax - 0.25, Ay - 0.05, "A", ha="right", va="center", fontsize=7.5, color="#0072B2")
    ax2.text(Bx + 0.25, By - 0.05, "B", ha="left", va="center", fontsize=7.5, color="#D55E00")
    # B's emitter cone (half-angle E/2, toed in by dthg/2 from vertical, toward A's side)
    axis_b = np.pi / 2 + dthg / 2
    a0, a1 = axis_b - half_E, axis_b + half_E
    for a in (a0, a1):
        ax2.plot([Bx, Bx + 1.3 * d * np.cos(a)], [By, 1.3 * d * np.sin(a)], color="#D55E00", lw=0.8)
    # A's receive cone (half-angle F/2, toed in by dthg/2 from vertical, toward B's side)
    axis_a = np.pi / 2 - dthg / 2
    a0, a1 = axis_a - half_F, axis_a + half_F
    for a in (a0, a1):
        ax2.plot([Ax, Ax + 1.3 * d * np.cos(a)], [Ay, 1.3 * d * np.sin(a)], color="#0072B2", lw=0.8)
    ax2.axhline(d, color="gray", lw=0.6, ls=":", xmin=0.05, xmax=0.95)
    ax2.text(0, d + 0.15, "common footprint", ha="center", fontsize=6.5)
    ax2.text(Bx + 0.55, 0.75, r"$E/2$", fontsize=7, color="#D55E00")
    ax2.text(Ax - 0.65, 0.55, r"$F/2$", fontsize=7, color="#0072B2")
    ax2.text(0, -0.28, r"$\Delta\theta_g$", fontsize=7, ha="center")
    ax2.text(-1.55, d / 2, r"$d$", fontsize=7, ha="center", va="center")
    ax2.set_xlim(-1.8, 1.8); ax2.set_ylim(-0.5, d * 1.25)
    ax2.set_aspect("equal")
    ax2.axis("off")
    ax2.set_title("(b)", fontsize=7.5, loc="left")

    fig.tight_layout()
    save(fig, "fig_principle")


if __name__ == "__main__":
    fig_concept()
    fig_principle()
    print("wrote fig_concept and fig_principle")
