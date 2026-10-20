"""Figure 1: measurement geometry (schematic, top view, not to scale).

Shows what the Methodology defines: sensors A and B a distance s apart, turned by -theta and +theta so that their
axes toe out by dtheta = 2 theta, a flat target at distance d, B's lit spot (emitter cone) and A's receive field,
the footprint where they overlap on the target, and the optional divider.

It is a schematic. Cone half-angles are drawn at a generic size and are NOT labelled with numbers, because the
datasheet (DS12385 Rev 8) gives diagonal fields of view only and no emitter beam angle; lengths are exaggerated
(s = 20 mm against d = 300-900 mm in the experiment). Nothing here is measured.

Run:   python manuscript_ieee/scripts/make_fig_setup.py
Out:   manuscript_ieee/figures/fig_setup.pdf (vector) and fig_setup.png (600 dpi)

Author: Jessica
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch, Polygon, Rectangle

FIG = Path(__file__).resolve().parent.parent / "figures"
FIG.mkdir(exist_ok=True)

BLUE, ORANGE, GREY, GREEN = "#0072B2", "#D55E00", "#555555", "#009E73"

S = 1.5            # drawn spacing between the two apertures (exaggerated)
D = 7.2            # drawn target distance
THETA = 5.0        # drawn angle per side, degrees (small enough that the cones still overlap)
HALF = 14.0        # drawn cone half-angle, degrees (generic)


def wedge(x0, phi_deg, half_deg, length, colour, alpha):
    a1, a2 = math.radians(phi_deg - half_deg), math.radians(phi_deg + half_deg)
    pts = [(x0, 0), (x0 + length * math.sin(a1) / math.cos(a1) * 1.0, length),
           (x0 + length * math.sin(a2) / math.cos(a2) * 1.0, length)]
    return Polygon(pts, closed=True, facecolor=colour, edgecolor="none", alpha=alpha, zorder=1)


def interval(x0, phi_deg, half_deg, y):
    return (x0 + y * math.tan(math.radians(phi_deg - half_deg)), x0 + y * math.tan(math.radians(phi_deg + half_deg)))


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.linewidth": 0.6, "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(3.45, 2.35))
    xa, xb = -S / 2, S / 2
    phi_a, phi_b = -THETA, +THETA

    # receive field of A, emitter cone of B, drawn to the target plane
    ax.add_patch(wedge(xa, phi_a, HALF, D, BLUE, 0.20))
    ax.add_patch(wedge(xb, phi_b, HALF, D, ORANGE, 0.20))

    # overlap footprint on the target
    ra, eb = interval(xa, phi_a, HALF, D), interval(xb, phi_b, HALF, D)
    lo, hi = max(ra[0], eb[0]), min(ra[1], eb[1])
    if hi > lo:
        ax.plot([lo, hi], [D, D], color=GREEN, lw=3.2, solid_capstyle="butt", zorder=4)
        ax.annotate("common\nfootprint", xy=((lo + hi) / 2, D), xytext=((lo + hi) / 2 + 2.6, D + 1.7), fontsize=6.5,
                    color=GREEN, ha="center", arrowprops=dict(arrowstyle="-", color=GREEN, lw=0.6))

    # target
    xs = 6.4
    ax.plot([-xs, xs], [D, D], color=GREY, lw=2.2, solid_capstyle="butt", zorder=3)
    ax.text(-xs + 0.1, D + 0.45, "flat target", fontsize=6.5, color=GREY, ha="left", va="bottom")

    # axes (boresights) and the angle arcs
    for x0, phi, name in ((xa, phi_a, "A"), (xb, phi_b, "B")):
        ex = x0 + 6.0 * math.tan(math.radians(phi))
        ax.plot([x0, ex], [0, 6.0], color="black", lw=0.7, ls=(0, (4, 2)), zorder=2)
        ax.plot([x0, x0], [0, 6.0], color="#999999", lw=0.5, ls=":", zorder=2)
    ax.text(xa - 0.45, 2.1, r"$-\theta$", fontsize=7.5, ha="right", va="center")
    ax.text(xb + 0.45, 2.1, r"$+\theta$", fontsize=7.5, ha="left", va="center")

    # delta theta between the axes
    yd = 4.6
    xl = xa + yd * math.tan(math.radians(-THETA))
    xr = xb + yd * math.tan(math.radians(THETA))
    ax.annotate("", xy=(xr, yd), xytext=(xl, yd),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color="black", shrinkA=0, shrinkB=0))
    ax.text(0, yd + 0.25, r"$\Delta\theta = 2\theta$", fontsize=7.5, ha="center", va="bottom",
            bbox=dict(facecolor="white", edgecolor="none", pad=0.8, alpha=0.9), zorder=7)

    # sensors
    for x0, name in ((xa, "A"), (xb, "B")):
        ax.add_patch(Rectangle((x0 - 0.16, -0.32), 0.32, 0.32, facecolor="black", zorder=6))
        ax.text(x0 + (-0.35 if name == "A" else 0.35), -0.55, name, fontsize=8, fontweight="bold", ha="center", va="top")

    # spacing
    ax.annotate("", xy=(xb, -1.45), xytext=(xa, -1.45), arrowprops=dict(arrowstyle="<->", lw=0.6, shrinkA=0, shrinkB=0))
    ax.text(0, -1.6, r"$s$ = 20 mm", fontsize=7, ha="center", va="top")

    # divider (tests only)
    ax.add_patch(Rectangle((-0.04, 0.0), 0.08, 0.9, facecolor="black", zorder=6))
    ax.annotate("divider\n(tests only)", xy=(0.04, 0.7), xytext=(2.6, -0.9), fontsize=6, ha="left", va="top",
                arrowprops=dict(arrowstyle="-", lw=0.5, color="black"))

    # distance
    ax.annotate("", xy=(-6.0, D), xytext=(-6.0, 0), arrowprops=dict(arrowstyle="<->", lw=0.6, shrinkA=0, shrinkB=0))
    ax.text(-6.15, D / 2, r"$d$ = 0.3, 0.6, 0.9 m", fontsize=7, rotation=90, ha="right", va="center")

    # legend
    ax.add_patch(Rectangle((2.5, D - 1.85), 0.45, 0.28, facecolor=BLUE, alpha=0.35, edgecolor="none"))
    ax.text(3.1, D - 1.71, "receive field of A", fontsize=6.3, va="center")
    ax.add_patch(Rectangle((2.5, D - 2.45), 0.45, 0.28, facecolor=ORANGE, alpha=0.35, edgecolor="none"))
    ax.text(3.1, D - 2.31, "emitter cone of B", fontsize=6.3, va="center")

    ax.set_xlim(-7.4, 6.9)
    ax.set_ylim(-3.0, D + 2.3)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout(pad=0.2)
    fig.savefig(FIG / "fig_setup.png", dpi=600)
    fig.savefig(FIG / "fig_setup.pdf", metadata={"Creator": "", "Producer": "", "Author": "Jessica"})
    plt.close(fig)
    print("wrote", FIG / "fig_setup.pdf")


if __name__ == "__main__":
    main()
