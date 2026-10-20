"""Redraw the crossover diagnostic figure from the saved estimates, without rerunning the bootstrap.

Run:   python manuscript_ieee/scripts/make_fig_crossover_methods.py
Out:   manuscript_ieee/figures/fig_crossover_methods.pdf / .png

Author: Jessica
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crossover_analysis as ca  # noqa: E402

if __name__ == "__main__":
    store = {}
    for d, name in ca.DISTANCES.items():
        pairs = ca.block_table(name)
        for roi in ca.ZONES:
            store[(d, roi)] = ca.cell_arrays(pairs, roi)
    est = pd.read_csv(ca.OUT / "crossover_estimates.csv")
    ca.figure(store, est)
    print("wrote", ca.FIG / "fig_crossover_methods.pdf")
