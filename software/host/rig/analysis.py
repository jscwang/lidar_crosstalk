"""Analysis of a logged session, following the procedure PDF.

* The run is the unit, not the reading (readings in a run are correlated).
* Per run and sensor: mean and SD of range (valid readings), dropout
  fraction (status not 0), mean ambient and signal rates.
* Crosstalk effect, per block and sensor: A+B run minus that sensor's solo
  run in the same block (SD ratio, bias, extra dropouts, extra ambient).
* At each dtheta: paired t-test across repeats, Wilcoxon signed-rank as a
  robustness check, effect sizes with 95% confidence intervals.
* Crossover: logistic fit of extra ambient against dtheta for each ROI and
  distance; report the dtheta where the fitted effect falls to 10% of its
  value at dtheta = 0, with a bootstrap interval, next to the prediction.

Only runs accepted by the session, inside accepted block attempts, are used.

Author: Jessica
"""
from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize, stats

from . import geometry

METRICS = ("extra_ambient", "rel_extra_ambient", "log_sd_ratio", "bias_mm", "extra_dropout")


# ------------------------------------------------------------------ loading
@dataclass
class SessionData:
    readings: pd.DataFrame
    runs: pd.DataFrame
    blocks: pd.DataFrame
    meta: dict
    path: Path


def load(session_dir: str | Path) -> SessionData:
    d = Path(session_dir)
    readings = pd.read_csv(d / "readings.csv")
    runs = pd.read_csv(d / "runs.csv", keep_default_na=False, dtype={"tag": str, "reject_reason": str})
    blocks = pd.read_csv(d / "blocks.csv", keep_default_na=False, dtype={"tag": str, "reason": str})
    meta = json.loads((d / "session.json").read_text(encoding="utf-8"))
    for df in (runs, blocks):
        df["accepted"] = df["accepted"].astype(str) == "True"
    return SessionData(readings, runs, blocks, meta, d)


def usable_runs(data: SessionData) -> pd.DataFrame:
    """Accepted runs belonging to the accepted attempt of their block."""
    ok_blocks = data.blocks[data.blocks["accepted"]][["block_id", "attempt"]]
    runs = data.runs[data.runs["accepted"]]
    return runs.merge(ok_blocks, on=["block_id", "attempt"], how="inner")


# ------------------------------------------------------------------ per run
def run_stats(data: SessionData) -> pd.DataFrame:
    runs = usable_runs(data)
    rd = data.readings[data.readings["run_id"].isin(runs["run_id"])]
    rows = []
    for (run_id, sensor), g in rd.groupby(["run_id", "sensor"], sort=False):
        valid = g[g["range_status"] == 0]["range_mm"]
        rows.append({
            "run_id": run_id, "sensor": sensor, "n": len(g), "n_valid": len(valid),
            "mean_mm": valid.mean() if len(valid) else np.nan,
            "sd_mm": valid.std(ddof=1) if len(valid) > 1 else np.nan,
            "dropout": 1.0 - len(valid) / len(g),
            "mean_ambient": g["ambient_rate"].mean(),
            "mean_signal": g["signal_rate"].mean(),
        })
    per = pd.DataFrame(rows)
    if per.empty:
        return per
    meta = runs[["run_id", "block_id", "condition", "distance_m", "theta_deg", "dtheta_deg", "roi", "repeat", "tag"]]
    return per.merge(meta, on="run_id")


# ------------------------------------------------------------------ paired effects
def pair_effects(rs: pd.DataFrame) -> pd.DataFrame:
    """One row per (block, sensor): that sensor in A+B minus the same sensor solo."""
    rows = []
    for (block_id, sensor), g in rs.groupby(["block_id", "sensor"]):
        solo = g[g["condition"] == sensor]
        both = g[g["condition"] == "AB"]
        if len(solo) != 1 or len(both) != 1:
            continue
        s, b = solo.iloc[0], both.iloc[0]
        ratio = b["sd_mm"] / s["sd_mm"] if s["sd_mm"] > 0 else np.nan   # nan-safe: nan > 0 is False
        rows.append({
            "block_id": block_id, "sensor": sensor, "distance_m": s["distance_m"], "roi": s["roi"],
            "theta_deg": s["theta_deg"], "dtheta_deg": s["dtheta_deg"], "repeat": s["repeat"], "tag": s["tag"],
            "solo_ambient": s["mean_ambient"], "extra_ambient": b["mean_ambient"] - s["mean_ambient"],
            "rel_extra_ambient": (b["mean_ambient"] - s["mean_ambient"]) / s["mean_ambient"]
            if s["mean_ambient"] > 0 else np.nan,
            "sd_ratio": ratio, "log_sd_ratio": math.log(ratio) if ratio > 0 else np.nan,
            "bias_mm": b["mean_mm"] - s["mean_mm"], "extra_dropout": b["dropout"] - s["dropout"],
        })
    return pd.DataFrame(rows)


def _ci(x: np.ndarray, level: float = 0.95) -> tuple[float, float, float]:
    n = len(x)
    if n == 0:   # e.g. a metric with no valid readings in any block
        return np.nan, np.nan, np.nan
    m = float(np.mean(x))
    if n < 2:
        return m, np.nan, np.nan
    half = stats.t.ppf(0.5 + level / 2, n - 1) * np.std(x, ddof=1) / math.sqrt(n)
    return m, m - half, m + half


def summarize(pairs: pd.DataFrame, pool_sensors: bool = True) -> pd.DataFrame:
    """Effect size, CI and paired tests at each dtheta.

    With pool_sensors, A's and B's effects in a block are averaged first, so
    the unit is the block (the two paths are mirror images of each other).
    """
    keys = ["tag", "distance_m", "roi", "dtheta_deg"]
    df = pairs
    if pool_sensors:
        df = pairs.groupby(keys + ["block_id"], as_index=False)[list(METRICS)].mean()
        df["sensor"] = "AB-pooled"
    rows = []
    for key, g in df.groupby(keys + ["sensor"]):
        row = dict(zip(keys + ["sensor"], key))
        row["n_blocks"] = len(g)
        for m in METRICS:
            x = g[m].to_numpy(dtype=float)
            x = x[np.isfinite(x)]
            mean, lo, hi = _ci(x)
            row[f"{m}_mean"], row[f"{m}_ci_lo"], row[f"{m}_ci_hi"] = mean, lo, hi
            sd = np.std(x, ddof=1) if len(x) > 1 else np.nan
            row[f"{m}_dz"] = mean / sd if sd and np.isfinite(sd) and sd > 0 else np.nan
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                row[f"{m}_t_p"] = stats.ttest_1samp(x, 0.0).pvalue if len(x) > 1 else np.nan
                row[f"{m}_wilcoxon_p"] = (stats.wilcoxon(x).pvalue if len(x) > 1 and np.any(x != 0)
                                          else np.nan)
        rows.append(row)
    out = pd.DataFrame(rows)
    if "log_sd_ratio_mean" in out:
        out["sd_ratio_geomean"] = np.exp(out["log_sd_ratio_mean"])
    return out


# ------------------------------------------------------------------ crossover
def logistic(x, top, x0, w):
    return top / (1.0 + np.exp((x - x0) / w))


def x10(top: float, x0: float, w: float) -> float:
    """dtheta at which the logistic falls to 10% of its value at dtheta = 0."""
    if not (top > 0 and w > 0):
        return float("nan")
    return x0 + w * math.log(10 * (1 + math.exp(-x0 / w)) - 1)


def fit_logistic(x: np.ndarray, y: np.ndarray):
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


def crossover(pairs: pd.DataFrame, metric: str = "extra_ambient", n_boot: int = 2000,
              seed: int = 1, spacing_m: float = 0.020) -> pd.DataFrame:
    """Fitted crossover per (distance, ROI), untagged runs only."""
    rng = np.random.default_rng(seed)
    main = pairs[pairs["tag"] == ""]
    block_level = main.groupby(["distance_m", "roi", "dtheta_deg", "block_id"], as_index=False)[metric].mean()
    rows = []
    for (d, roi), g in block_level.groupby(["distance_m", "roi"]):
        x = g["dtheta_deg"].to_numpy(dtype=float)
        y = g[metric].to_numpy(dtype=float)
        levels = np.unique(x)
        popt = fit_logistic(x, y)
        est = x10(*popt) if popt is not None else float("nan")
        boots, failed = [], 0
        groups = [np.flatnonzero(x == lv) for lv in levels]
        for _ in range(n_boot if popt is not None else 0):
            idx = np.concatenate([rng.choice(gi, size=len(gi), replace=True) for gi in groups])
            bp = fit_logistic(x[idx], y[idx])
            v = x10(*bp) if bp is not None else float("nan")
            if np.isfinite(v):
                boots.append(v)
            else:
                failed += 1
        lo, hi = (np.percentile(boots, [2.5, 97.5]) if len(boots) >= 20 else (np.nan, np.nan))
        pred = geometry.predicted_crossover(int(roi), float(d), spacing_m)
        note = []
        if len(levels) < 5:
            # Found in simulation: with 4 levels (0/10/20/30) the estimate was off by up to 2.3 deg
            # while the bootstrap interval was only 0.3 deg wide, because the curve shape between
            # levels is guessed and resampling within levels cannot see that.
            note.append(f"only {len(levels)} dtheta levels: crossover weakly constrained and the "
                        f"interval understates the uncertainty")
        if popt is None:
            note.append("logistic fit failed")
        elif est > levels.max():
            note.append("10% point lies beyond the largest dtheta tested")
        rows.append({
            "distance_m": d, "roi": roi, "metric": metric, "n_levels": len(levels), "n_blocks": len(g),
            "top": popt[0] if popt is not None else np.nan, "x0": popt[1] if popt is not None else np.nan,
            "w": popt[2] if popt is not None else np.nan,
            "crossover_deg": est, "ci_lo": lo, "ci_hi": hi, "boot_ok": len(boots), "boot_failed": failed,
            "predicted_deg": pred if pred is not None else np.nan, "note": "; ".join(note),
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ report
def analyze(session_dir: str | Path, out_dir: str | Path | None = None, n_boot: int = 2000,
            figures: bool = True) -> dict:
    data = load(session_dir)
    out = Path(out_dir) if out_dir else data.path / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    spacing = float(data.meta.get("config", {}).get("spacing_mm", 20.0)) / 1000.0

    rs = run_stats(data)
    pairs = pair_effects(rs) if not rs.empty else pd.DataFrame()
    summ = summarize(pairs) if not pairs.empty else pd.DataFrame()
    per_sensor = summarize(pairs, pool_sensors=False) if not pairs.empty else pd.DataFrame()
    xo = crossover(pairs, n_boot=n_boot, spacing_m=spacing) if not pairs.empty else pd.DataFrame()

    rs.to_csv(out / "run_stats.csv", index=False)
    pairs.to_csv(out / "pair_effects.csv", index=False)
    summ.to_csv(out / "effects_summary.csv", index=False)
    per_sensor.to_csv(out / "effects_by_sensor.csv", index=False)
    xo.to_csv(out / "crossover.csv", index=False)

    counts = {
        "runs_logged": int(len(data.runs)),
        "runs_usable": int(len(usable_runs(data))),
        "blocks_accepted": int(data.blocks["accepted"].sum()),
        "blocks_given_up": int(data.blocks["reason"].str.startswith("gave up").sum()),
    }
    _write_summary(out / "summary.md", data, counts, xo)
    if figures and not pairs.empty:
        from . import figures as fig
        fig.make_all(data, rs, pairs, summ, xo, out / "figures")
    return {"out": out, "counts": counts, "crossover": xo, "summary": summ}


def _write_summary(path: Path, data: SessionData, counts: dict, xo: pd.DataFrame) -> None:
    cfg = data.meta.get("config", {})
    lines = [
        "# Crosstalk session analysis", "", "Author: Jessica", "",
        f"Session: `{data.path.name}`, config `{cfg.get('name', '?')}`", "",
        f"Runs logged {counts['runs_logged']}, usable {counts['runs_usable']}; "
        f"blocks accepted {counts['blocks_accepted']}, given up {counts['blocks_given_up']}.", "",
        "## Crossover (extra ambient falls to 10% of its dtheta = 0 value)", "",
        "| Distance (m) | ROI | Measured (deg) | 95% bootstrap CI | Predicted (deg) | dtheta levels | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in xo.iterrows():
        ci = f"{r['ci_lo']:.1f} to {r['ci_hi']:.1f}" if np.isfinite(r["ci_lo"]) else "n/a"
        meas = f"{r['crossover_deg']:.1f}" if np.isfinite(r["crossover_deg"]) else "n/a"
        pred = f"{r['predicted_deg']:.1f}" if np.isfinite(r["predicted_deg"]) else "n/a"
        lines.append(f"| {r['distance_m']:g} | {int(r['roi'])}x{int(r['roi'])} | {meas} | {ci} | {pred} | "
                     f"{int(r['n_levels'])} | {r['note']} |")
    lines += ["", "Effect sizes, confidence intervals and paired tests at every dtheta: `effects_summary.csv` "
              "(blocks pooled over sensors) and `effects_by_sensor.csv`.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
