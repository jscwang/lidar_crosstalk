"""Crossover analysis for the pair13 campaign: five estimators, bootstrap and sensitivity to analytical choices.

The question: at which angle between the sensors, dtheta, does the extra ambient light caused by running both
sensors fall to a given fraction of its reference level? The project's own estimator (rig.analysis.crossover)
fits a monotone logistic and reads off 10% of its fitted value at dtheta = 0. At 0.6 and 0.9 m the 4x4 zone
is not monotone (its largest sampled value is at dtheta = 4, not 0), so that estimator is applied to data
its shape cannot describe. This script compares estimators that do and do not assume monotonicity.

Unit of analysis: the block. For every (distance, zone, dtheta, block) the extra ambient is the mean over
sensors A and B of [ambient in the A+B run minus ambient in that sensor's solo run], in kcps, as computed
by rig.analysis.pair_effects. Five blocks per dtheta level.

Estimators, each returning a crossover for a threshold fraction phi of its reference level:
  M1  logistic, 3 parameters, fitted to all levels; reference = fitted value at dtheta = 0 (the project's own).
  M2  the same logistic fitted only from the observed peak level outward; reference = fitted value there.
      Identical to M1 whenever the peak is at dtheta = 0.
  M3  piecewise-linear interpolation of the block-mean curve; reference = observed peak mean; first crossing
      after the peak.
  M4  PCHIP (shape-preserving cubic) interpolation of the block-mean curve, same reference and crossing rule.
  M5  tilted logistic top*(1 + b*x)/(1 + exp((x - x0)/w)), 4 parameters, fitted to all levels; it can rise
      before it falls. Reference = its own maximum over [0, 24] deg; first crossing after that maximum.

Uncertainty: block bootstrap, resampling the five blocks within each dtheta level with replacement, 2,000
draws, one common set of draws for all estimators (so differences between estimators have their own
interval). Percentile 95% intervals. A draw in which an estimator fails is dropped for that estimator.

Run:   python manuscript_ieee/scripts/crossover_analysis.py
       CROSSOVER_CAMPAIGN=2 python manuscript_ieee/scripts/crossover_analysis.py   # unit-swap campaign, nodiv_swap_*
Out:   manuscript_ieee/analysis[_campaignN]/crossover_estimates.csv     every estimator, cell, threshold
       manuscript_ieee/analysis/crossover_bracket.csv       model-free bracket of the 10% crossing
       manuscript_ieee/analysis/crossover_bump_tests.csv    peak location and dtheta 4 vs 0 tests
       manuscript_ieee/analysis/crossover_per_sensor.csv    A and B separately
       manuscript_ieee/analysis/crossover_aic.csv           M1 against M5
       manuscript_ieee/analysis/extinction.csv              angle at 1% of peak against the geometric prediction
       manuscript_ieee/figures/fig_crossover_methods.pdf/png  diagnostic figure

Author: Jessica
"""
from __future__ import annotations

import math
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.interpolate import PchipInterpolator

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parent
sys.path.insert(0, str(ROOT / "software" / "host"))
from rig import analysis as an  # noqa: E402
from rig import geometry  # noqa: E402

DATA = PROJECT / "data_pair13"
CAMPAIGN = os.environ.get("CROSSOVER_CAMPAIGN", "1")
OUT = PROJECT / ("analysis" if CAMPAIGN == "1" else f"analysis_campaign{CAMPAIGN}")
FIG = PROJECT / ("figures" if CAMPAIGN == "1" else f"analysis_campaign{CAMPAIGN}")
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

DISTANCES = ({0.3: "nodiv_0p3", 0.6: "nodiv_0p6", 0.9: "nodiv_0p9"} if CAMPAIGN == "1"
             else {0.3: "swap_0p3", 0.6: "swap_0p6", 0.9: "swap_0p9"})
ZONES = (4, 16)
N_BOOT = int(os.environ.get("CROSSOVER_NBOOT", 2000))
SEED = 20261011
PHIS = (0.05, 0.10, 0.20)          # thresholds; 0.10 is the primary
METHODS = ("M1", "M2", "M3", "M4", "M5")
XMAX = 24.0                        # largest sampled dtheta


# ------------------------------------------------------------------ data
def block_table(name: str) -> pd.DataFrame:
    """One row per (block, sensor): extra ambient, with distance, zone and dtheta."""
    data = an.load(DATA / name)
    data.runs["tag"] = ""
    data.blocks["tag"] = ""
    pairs = an.pair_effects(an.run_stats(data))
    prov = data.blocks[data.blocks["accepted"]][["block_id", "provenance"]].drop_duplicates("block_id")
    return pairs.merge(prov, on="block_id", how="left")


def cell_arrays(pairs: pd.DataFrame, roi: int, sensor: str | None = None, main_only: bool = False):
    """(levels, [array of block values per level]) for one zone; sensor None pools A and B within a block.
    main_only drops blocks that came from a refill session (provenance 'refill:...')."""
    g = pairs[pairs.roi == roi]
    if main_only:
        g = g[g.provenance == "main"]
    if sensor is None:
        bv = g.groupby(["dtheta_deg", "block_id"], as_index=False)["extra_ambient"].mean()
    else:
        bv = g[g.sensor == sensor][["dtheta_deg", "block_id", "extra_ambient"]]
    levels = np.array(sorted(bv.dtheta_deg.unique()), dtype=float)
    vals = [bv[bv.dtheta_deg == lv].sort_values("block_id")["extra_ambient"].to_numpy(float) for lv in levels]
    return levels, vals


def flat(levels, vals):
    x = np.concatenate([np.full(len(v), lv) for lv, v in zip(levels, vals)])
    y = np.concatenate(vals)
    return x, y


# ------------------------------------------------------------------ estimators
def logistic(x, top, x0, w):
    return top / (1.0 + np.exp((x - x0) / w))


def tilted(x, top, b, x0, w):
    return top * (1.0 + b * x) / (1.0 + np.exp((x - x0) / w))


def fit_logistic(x, y):
    if len(np.unique(x)) < 3:
        return None
    top0 = max(float(np.mean(y[x == x.min()])), 1e-6)
    ymax = max(float(np.max(np.abs(y))), 1e-6)
    p0 = (top0, float(np.median(x)), 2.0)
    bounds = ([0.0, -30.0, 0.1], [10 * ymax, 90.0, 30.0])
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = optimize.curve_fit(logistic, x, y, p0=p0, bounds=bounds, maxfev=20000)
    except (RuntimeError, ValueError):
        return None
    return popt


def fit_tilted(x, y, start=None):
    ymax = max(float(np.max(np.abs(y))), 1e-6)
    base = start if start is not None else fit_logistic(x, y)
    if base is None:
        return None
    # b is bounded so that 1 + b*x stays positive on [0, XMAX]
    bounds = ([0.0, -1.0 / XMAX + 1e-3, -30.0, 0.1], [10 * ymax, 1.0, 90.0, 30.0])
    best = None
    for b0 in (0.0, 0.02, 0.1):
        p0 = (base[0], b0, base[1], base[2])
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                popt, _ = optimize.curve_fit(tilted, x, y, p0=p0, bounds=bounds, maxfev=20000)
        except (RuntimeError, ValueError):
            continue
        rss = float(np.sum((y - tilted(x, *popt)) ** 2))
        if best is None or rss < best[0]:
            best = (rss, popt)
    return None if best is None else best[1]


def logistic_cross(top, x0, w, ref, phi):
    """x where logistic(x) = phi*ref; nan if the logistic never gets that low."""
    target = phi * ref
    if not (top > 0 and w > 0 and 0 < target < top):
        return float("nan")
    return x0 + w * math.log(top / target - 1.0)


def _first_cross_after_peak(levels, means, phi):
    ipk = int(np.argmax(means))
    ref = means[ipk]
    if ref <= 0:
        return None
    for j in range(ipk + 1, len(levels)):
        if means[j] <= phi * ref:
            return ipk, j, ref
    return None


def est_m1(x, y, levels, means, phis):
    p = fit_logistic(x, y)
    if p is None:
        return {phi: float("nan") for phi in phis}
    ref = float(logistic(0.0, *p))
    return {phi: logistic_cross(*p, ref=ref, phi=phi) for phi in phis}


def est_m2(x, y, levels, means, phis):
    xpk = levels[int(np.argmax(means))]
    keep = x >= xpk
    p = fit_logistic(x[keep], y[keep])
    if p is None:
        return {phi: float("nan") for phi in phis}
    ref = float(logistic(xpk, *p))
    return {phi: logistic_cross(*p, ref=ref, phi=phi) for phi in phis}


def est_m3(x, y, levels, means, phis):
    out = {}
    for phi in phis:
        r = _first_cross_after_peak(levels, means, phi)
        if r is None:
            out[phi] = float("nan")
            continue
        ipk, j, ref = r
        t = phi * ref
        x0, x1, y0, y1 = levels[j - 1], levels[j], means[j - 1], means[j]
        out[phi] = float(x0 + (y0 - t) / (y0 - y1) * (x1 - x0)) if y0 != y1 else float(x1)
    return out


def est_m4(x, y, levels, means, phis):
    f = PchipInterpolator(levels, means)
    out = {}
    for phi in phis:
        r = _first_cross_after_peak(levels, means, phi)
        if r is None:
            out[phi] = float("nan")
            continue
        ipk, j, ref = r
        t = phi * ref
        lo, hi = levels[j - 1], levels[j]
        if f(lo) - t < 0:                  # noise: the level before the crossing is already below t
            out[phi] = float(lo)
            continue
        try:
            out[phi] = float(optimize.brentq(lambda z: f(z) - t, lo, hi))
        except ValueError:
            out[phi] = float("nan")
    return out


_GRID = np.linspace(0.0, 60.0, 6001)


def est_m5(x, y, levels, means, phis):
    p = fit_tilted(x, y)
    if p is None:
        return {phi: float("nan") for phi in phis}
    f = tilted(_GRID, *p)
    ipk = int(np.argmax(f[: int(XMAX / 0.01) + 1]))
    ref = f[ipk]
    out = {}
    for phi in phis:
        below = np.flatnonzero(f[ipk:] <= phi * ref)
        if not len(below) or below[0] == 0:
            out[phi] = float("nan")
            continue
        k = ipk + below[0]
        x0, x1, y0, y1 = _GRID[k - 1], _GRID[k], f[k - 1], f[k]
        out[phi] = float(x0 + (y0 - phi * ref) / (y0 - y1) * (x1 - x0))
    return out


FUNCS = {"M1": est_m1, "M2": est_m2, "M3": est_m3, "M4": est_m4, "M5": est_m5}


def estimate_all(levels, vals, phis):
    """{phi: {method: crossover}} for the observed data."""
    x, y = flat(levels, vals)
    means = np.array([v.mean() for v in vals])
    per = {k: FUNCS[k](x, y, levels, means, phis) for k in METHODS}
    return {phi: {k: per[k][phi] for k in METHODS} for phi in phis}


def bootstrap(levels, vals, phis, n_boot, rng):
    """{phi: {method: array of draws}}, one common set of resamples for every method and threshold."""
    out = {phi: {k: np.full(n_boot, np.nan) for k in METHODS} for phi in phis}
    for i in range(n_boot):
        rs = [v[rng.integers(0, len(v), len(v))] for v in vals]
        x, y = flat(levels, rs)
        means = np.array([v.mean() for v in rs])
        for k in METHODS:
            res = FUNCS[k](x, y, levels, means, phis)
            for phi in phis:
                out[phi][k][i] = res[phi]
    return out


def pct(a):
    a = a[np.isfinite(a)]
    return (np.percentile(a, 2.5), np.percentile(a, 97.5), len(a)) if len(a) >= 50 else (np.nan, np.nan, len(a))


# ------------------------------------------------------------------ main analysis
def analyse_cell(args):
    """All analyses for one (distance, zone) cell. Runs in a worker process; returns plain rows."""
    d, roi, name = args
    pairs = block_table(name)
    rng = np.random.default_rng([SEED, int(round(d * 10)), roi])
    levels, vals = cell_arrays(pairs, roi)
    means = np.array([v.mean() for v in vals])
    ipk = int(np.argmax(means))
    pred = geometry.predicted_crossover(roi, d)
    zone = f"{roi}x{roi}"
    rows = {"est": [], "diff": [], "brk": [], "bump": [], "aic": [], "ext": [], "ps": []}

    # ---- estimates with bootstrap at each threshold
    pt = estimate_all(levels, vals, PHIS)
    bs = bootstrap(levels, vals, PHIS, N_BOOT, rng)
    for phi in PHIS:
        spread = np.nanmax(list(pt[phi].values())) - np.nanmin(list(pt[phi].values()))
        for k in METHODS:
            lo, hi, n_ok = pct(bs[phi][k])
            rows["est"].append({"distance_m": d, "zone": zone, "phi": phi, "method": k,
                                "crossover_deg": pt[phi][k], "ci_lo": lo, "ci_hi": hi, "boot_ok": n_ok,
                                "method_spread_deg": spread})
    for a, b in (("M1", "M4"), ("M1", "M5"), ("M4", "M5"), ("M3", "M4")):
        lo, hi, _ = pct(bs[0.10][a] - bs[0.10][b])
        rows["diff"].append({"distance_m": d, "zone": zone, "pair": f"{a}-{b}",
                             "diff_deg": pt[0.10][a] - pt[0.10][b], "ci_lo": lo, "ci_hi": hi})

    # ---- sensitivity to provenance: the same estimators on main-session blocks only (refill blocks excluded)
    lm, vm = cell_arrays(pairs, roi, main_only=True)
    ptm = estimate_all(lm, vm, (0.10,))[0.10]
    n_per = [len(v) for v in vm]
    rows.setdefault("prov", []).append({
        "distance_m": d, "zone": zone, **{f"{k}_main_only": ptm[k] for k in METHODS},
        **{f"{k}_all": pt[0.10][k] for k in METHODS},
        "min_blocks_per_level_main_only": int(min(n_per)), "levels_main_only": len(lm)})

    # ---- model-free bracket of the 10% crossing, after the observed peak
    r = _first_cross_after_peak(levels, means, 0.10)
    if r is not None:
        _, j, ref = r
        rows["brk"].append({"distance_m": d, "zone": zone, "peak_level_deg": levels[ipk],
                            "peak_mean_kcps": means[ipk], "ten_pct_kcps": 0.1 * ref,
                            "last_above_deg": levels[j - 1], "first_at_or_below_deg": levels[j],
                            "mean_at_last_above": means[j - 1], "mean_at_first_below": means[j]})

    # ---- is the peak off dtheta = 0? dtheta 4 against 0, block level, Welch and rank tests
    if len(levels) > 1 and levels[0] == 0 and levels[1] == 4:
        a, b = vals[1], vals[0]
        t = stats.ttest_ind(a, b, equal_var=False)
        u = stats.mannwhitneyu(a, b, alternative="two-sided")
        diff = a.mean() - b.mean()
        va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
        se = math.sqrt(va + vb)
        dfw = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
        h = stats.t.ppf(0.975, dfw) * se
        rows["bump"].append({"distance_m": d, "zone": zone, "peak_level_deg": levels[ipk],
                             "mean_at_0": b.mean(), "mean_at_4": a.mean(), "diff_4_minus_0": diff,
                             "diff_ci_lo": diff - h, "diff_ci_hi": diff + h, "diff_pct_of_0": 100 * diff / b.mean(),
                             "welch_p": t.pvalue, "mannwhitney_p": u.pvalue, "n_each": len(a)})

    # ---- M1 against M5 by AIC (same data, 3 against 4 parameters)
    x, y = flat(levels, vals)
    p1, p5 = fit_logistic(x, y), fit_tilted(x, y)
    n = len(y)
    if p1 is not None and p5 is not None:
        rss1 = float(np.sum((y - logistic(x, *p1)) ** 2))
        rss5 = float(np.sum((y - tilted(x, *p5)) ** 2))
        aic1, aic5 = n * math.log(rss1 / n) + 6, n * math.log(rss5 / n) + 8
        rows["aic"].append({"distance_m": d, "zone": zone, "n": n, "rss_M1": rss1, "rss_M5": rss5,
                            "aic_M1": aic1, "aic_M5": aic5, "delta_aic_M1_minus_M5": aic1 - aic5,
                            "M5_b_per_deg": p5[1], "rmse_M1": math.sqrt(rss1 / n), "rmse_M5": math.sqrt(rss5 / n)})

    # ---- extinction: angle at which the response reaches 1% of its peak (PCHIP), against the prediction
    ref = means[ipk]
    f = PchipInterpolator(levels, means)
    grid = np.linspace(levels[ipk], levels[-1], 4801)
    below = np.flatnonzero(f(grid) <= 0.01 * ref)
    rows["ext"].append({"distance_m": d, "zone": zone, "peak_mean_kcps": ref,
                        "mean_at_24_pct_of_peak": 100 * means[-1] / ref,
                        "angle_at_1pct_deg": float(grid[below[0]]) if len(below) else float("nan"),
                        "reached_within_sampled_range": bool(len(below)), "geometric_prediction_deg": pred})

    # ---- per sensor: A and B separately, M1 and M4, paired bootstrap of the A - B difference
    g = pairs[pairs.roi == roi].pivot_table(index=["dtheta_deg", "block_id"], columns="sensor",
                                            values="extra_ambient").dropna().reset_index()
    lv = np.array(sorted(g.dtheta_deg.unique()), dtype=float)
    pa = [g[g.dtheta_deg == v]["A"].to_numpy(float) for v in lv]
    pb = [g[g.dtheta_deg == v]["B"].to_numpy(float) for v in lv]
    one = (0.10,)
    ptp = {}
    for s, vv in (("A", pa), ("B", pb)):
        xs, ys = flat(lv, vv)
        ms = np.array([v.mean() for v in vv])
        ptp[s] = {k: FUNCS[k](xs, ys, lv, ms, one)[0.10] for k in ("M1", "M4")}
    draws = {(s, k): np.full(N_BOOT, np.nan) for s in "AB" for k in ("M1", "M4")}
    for i in range(N_BOOT):
        idx = [rng.integers(0, len(v), len(v)) for v in pa]
        for s, vv in (("A", pa), ("B", pb)):
            rs = [v[ix] for v, ix in zip(vv, idx)]
            xs, ys = flat(lv, rs)
            ms = np.array([v.mean() for v in rs])
            for k in ("M1", "M4"):
                draws[(s, k)][i] = FUNCS[k](xs, ys, lv, ms, one)[0.10]
    for k in ("M1", "M4"):
        lo, hi, _ = pct(draws[("A", k)] - draws[("B", k)])
        la, ha, _ = pct(draws[("A", k)])
        lb, hb, _ = pct(draws[("B", k)])
        rows["ps"].append({"distance_m": d, "zone": zone, "method": k,
                           "A_deg": ptp["A"][k], "A_ci_lo": la, "A_ci_hi": ha,
                           "B_deg": ptp["B"][k], "B_ci_lo": lb, "B_ci_hi": hb,
                           "A_minus_B_deg": ptp["A"][k] - ptp["B"][k], "diff_ci_lo": lo, "diff_ci_hi": hi,
                           "A_peak_level": lv[int(np.argmax([v.mean() for v in pa]))],
                           "B_peak_level": lv[int(np.argmax([v.mean() for v in pb]))]})
    return rows, (d, roi, levels, vals)


def main():
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(d, roi, name) for d, name in DISTANCES.items() for roi in ZONES]
    with ProcessPoolExecutor(max_workers=min(len(jobs), 12)) as ex:
        results = list(ex.map(analyse_cell, jobs))
    merged = {k: [] for k in ("est", "diff", "brk", "bump", "aic", "ext", "ps", "prov")}
    store = {}
    for rows, (d, roi, levels, vals) in results:
        for k in merged:
            merged[k].extend(rows[k])
        store[(d, roi)] = (levels, vals)
    files = {"est": "crossover_estimates.csv", "diff": "crossover_method_differences.csv",
             "brk": "crossover_bracket.csv", "bump": "crossover_bump_tests.csv", "aic": "crossover_aic.csv",
             "ext": "extinction.csv", "ps": "crossover_per_sensor.csv",
             "prov": "crossover_provenance_sensitivity.csv"}
    for k, fn in files.items():
        pd.DataFrame(merged[k]).to_csv(OUT / fn, index=False)
    est = pd.DataFrame(merged["est"])
    figure(store, est)
    summarize(est)


def summarize(est: pd.DataFrame):
    e = est[est.phi == 0.10]
    wide = e.pivot_table(index=["distance_m", "zone"], columns="method", values="crossover_deg")
    spread = e.groupby(["distance_m", "zone"])["method_spread_deg"].first()
    half = e[e.method == "M4"].set_index(["distance_m", "zone"]).eval("(ci_hi - ci_lo) / 2")
    out = wide.copy()
    out["spread"] = spread
    out["M4_boot_halfwidth"] = half
    print("\nCrossover at 10% of reference, degrees (dtheta):")
    print(out.round(2).to_string())


# ------------------------------------------------------------------ figure
def figure(store, est):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.linewidth": 0.6, "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.4), sharex=True)
    colour = {"M1": "#0072B2", "M4": "#009E73", "M5": "#D55E00"}
    grid = np.linspace(0, 24, 481)
    for r, roi in enumerate((16, 4)):
        for c, d in enumerate((0.3, 0.6, 0.9)):
            ax = axes[r, c]
            levels, vals = store[(d, roi)]
            means = np.array([v.mean() for v in vals])
            sds = np.array([v.std(ddof=1) for v in vals])
            ref = means.max()
            ax.errorbar(levels, 100 * means / ref, yerr=100 * sds / ref, fmt="o", ms=3, color="black", capsize=1.5,
                        elinewidth=0.6, zorder=5, label="block mean ± SD (n = 5)")
            x, y = flat(levels, vals)
            p1, p5 = fit_logistic(x, y), fit_tilted(x, y)
            if p1 is not None:
                ax.plot(grid, 100 * logistic(grid, *p1) / ref, color=colour["M1"], lw=0.9, label="M1 logistic")
            if p5 is not None:
                ax.plot(grid, 100 * tilted(grid, *p5) / ref, color=colour["M5"], lw=0.9, ls="--", label="M5 tilted logistic")
            f = PchipInterpolator(levels, means)
            ax.plot(grid, 100 * f(grid) / ref, color=colour["M4"], lw=0.7, ls=":", label="M4 PCHIP")
            e = est[(est.distance_m == d) & (est.zone == f"{roi}x{roi}") & (est.phi == 0.10)].set_index("method")
            for k, ms_, z in (("M4", 7.0, 5.5), ("M5", 5.0, 6.0), ("M1", 4.0, 6.5)):
                v = e.loc[k, "crossover_deg"]
                if np.isfinite(v):
                    ax.plot([v], [10], marker="v", ms=ms_, color=colour[k], mec="black", mew=0.4, zorder=z)
            pred = geometry.predicted_crossover(roi, d)
            ax.axvline(pred, color="#777777", lw=0.7, ls="-.")
            ax.axhline(10, color="#999999", lw=0.5, ls="--")
            ax.set_ylim(-8, 118)
            ax.set_xlim(-0.5, 27)
            ax.set_title(f"{roi}×{roi}, {d:.1f} m", fontsize=7.5, loc="left", fontweight="bold")
            if c == 0:
                ax.set_ylabel("Extra ambient\n(% of observed peak)")
            if r == 1:
                ax.set_xlabel("Δθ (degrees)")
    h, l = axes[0, 0].get_legend_handles_labels()
    h.append(plt.Line2D([], [], color="#777777", lw=0.7, ls="-.")); l.append("geometric prediction")
    h.append(plt.Line2D([], [], marker="v", ls="", color="#999999", mec="black", mew=0.4, ms=4.5)); l.append("10% crossing (colour = estimator)")
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=6.5, frameon=False)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(FIG / "fig_crossover_methods.png", dpi=600, metadata={"Software": None})
    fig.savefig(FIG / "fig_crossover_methods.pdf", metadata={"Creator": "", "Producer": "", "Author": "Jessica"})
    plt.close(fig)


if __name__ == "__main__":
    main()
