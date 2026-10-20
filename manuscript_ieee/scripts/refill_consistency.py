"""Are refill blocks consistent with the in-session blocks of the cell they sit in?

For every cell (zone, dtheta) that holds both main-session and refill blocks, compare each refill block's pooled extra ambient
with the mean and standard deviation of the main-session blocks. Percentages are meaningless where the value is at the noise
floor (about 0 +/- 0.3 kcps), so read the absolute difference and the z score there.

Run:   python manuscript_ieee/scripts/refill_consistency.py
Out:   manuscript_ieee/analysis/refill_consistency.csv

Author: Jessica
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import crossover_analysis as ca  # noqa: E402


def main():
    rows = []
    for d, name in ca.DISTANCES.items():
        pairs = ca.block_table(name)
        bv = pairs.groupby(["roi", "dtheta_deg", "block_id", "provenance"], as_index=False)["extra_ambient"].mean()
        bv["is_refill"] = bv.provenance.str.startswith("refill")
        for (roi, dth), g in bv.groupby(["roi", "dtheta_deg"]):
            if not g.is_refill.any() or g.is_refill.all():
                continue
            main_v = g[~g.is_refill].extra_ambient.to_numpy()
            sd = main_v.std(ddof=1) if len(main_v) > 1 else np.nan
            for v in g[g.is_refill].extra_ambient.to_numpy():
                rows.append({"distance_m": d, "zone": f"{roi}x{roi}", "dtheta": dth, "n_main": len(main_v),
                             "n_refill": int(g.is_refill.sum()), "main_mean": main_v.mean(), "main_sd": sd,
                             "refill_value": v, "diff": v - main_v.mean(),
                             "z_vs_main_sd": (v - main_v.mean()) / sd if sd and sd > 0 else np.nan,
                             "diff_pct_of_main": 100 * (v - main_v.mean()) / main_v.mean() if main_v.mean() else np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(ca.OUT / "refill_consistency.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
