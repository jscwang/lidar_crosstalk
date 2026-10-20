"""A plain measurement that ends by itself: after a set time, after a fixed number of readings, or whichever comes first.

`rig read --port COM5 --seconds 30` or `--count 500`. The readings are saved as a CSV file that opens in Excel, and a short
summary is printed. Nothing has to be stopped by hand.

Author: Jessica
"""
from __future__ import annotations

import csv
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import protocol as p
from .device import Device

MAX_RUN_MS = 3_600_000          # the firmware's longest single run
COLUMNS = ["t_s", "sensor", "range_mm", "status", "signal_kcps", "ambient_kcps", "spads", "t_int_us", "t_read_us"]


class CaptureError(ValueError):
    pass


def plan(settings: p.Settings, sensors: str, seconds: Optional[float], count: Optional[int]) -> tuple[int, str]:
    """Run length in ms and the rule that ends the run. Raises CaptureError for a request that cannot be run."""
    if sensors not in ("A", "B", "AB"):
        raise CaptureError("sensors must be A, B or AB")
    if seconds is None and count is None:
        seconds = 30.0
    if seconds is not None and seconds <= 0:
        raise CaptureError("seconds must be more than 0")
    if count is not None and count < 1:
        raise CaptureError("count must be at least 1")
    if seconds is not None:
        limit_ms = int(math.ceil(seconds * 1000))
    else:
        # long enough for every sensor to deliver `count` readings; the run is stopped as soon as they are in
        limit_ms = int(count * max(settings.imp, settings.tb) * 1.05) + 2000
    limit_ms = max(limit_ms, 100)
    if limit_ms > MAX_RUN_MS:
        raise CaptureError("that is longer than one hour: the board runs at most one hour at a time, so use a smaller "
                           "count or fewer seconds")
    rule = []
    if seconds is not None:
        rule.append(f"{seconds:g} s")
    if count is not None:
        rule.append(f"{count} readings per sensor")
    return limit_ms, " or ".join(rule) + (" (whichever comes first)" if len(rule) == 2 else "")


def capture(dev: Device, settings: p.Settings, sensors: str = "AB", seconds: Optional[float] = None,
            count: Optional[int] = None) -> tuple[list[dict], dict]:
    """Runs the measurement. Returns (rows, summary); rows are in time order and hold at most `count` per sensor."""
    dur_ms, rule = plan(settings, sensors, seconds, count)
    dev.configure(settings)
    kept: dict[str, list[p.Reading]] = {s: [] for s in sensors}

    def on_reading(r: p.Reading):
        if count is None or len(kept[r.sensor]) < count:
            kept[r.sensor].append(r)
        return count is not None and all(len(v) >= count for v in kept.values())

    end = dev.run("read", sensors, dur_ms, on_reading)
    allr = sorted((r for v in kept.values() for r in v), key=lambda r: r.t_int_us)
    t0 = allr[0].t_int_us if allr else 0
    rows = [{"t_s": round((r.t_int_us - t0) / 1e6, 4), "sensor": r.sensor, "range_mm": r.range_mm, "status": r.status,
             "signal_kcps": r.signal_kcps, "ambient_kcps": r.ambient_kcps, "spads": r.spads,
             "t_int_us": r.t_int_us, "t_read_us": r.t_read_us} for r in allr]
    reached = count is not None and all(len(v) >= count for v in kept.values())
    summary = {"rule": rule, "stopped_by": "count" if reached else "time", "run_ms": dur_ms,
               "abort": end.abort, "sensors": {}}
    for s, v in kept.items():
        good = [r.range_mm for r in v if r.status == 0]
        summary["sensors"][s] = {
            "n": len(v), "valid": len(good),
            "range_mean": statistics.fmean(good) if good else float("nan"),
            "range_sd": statistics.stdev(good) if len(good) > 1 else float("nan"),
            "ambient_mean": statistics.fmean(r.ambient_kcps for r in v) if v else float("nan"),
            "seconds": (v[-1].t_int_us - v[0].t_int_us) / 1e6 if len(v) > 1 else 0.0,
        }
    return rows, summary


def write_csv(path: Path, rows: list[dict]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def default_path(out_dir: str = "data") -> Path:
    return Path(out_dir) / f"read_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def report(summary: dict, path: Optional[Path] = None) -> list[str]:
    if summary["stopped_by"] == "count":
        stopped = "it reached the number of readings asked for"
    elif "readings" in summary["rule"]:
        stopped = "the time limit came before every sensor had that many readings"
    else:
        stopped = "the time was up"
    lines = [f"Measurement finished by itself: {stopped}. Asked for: {summary['rule']}.", ""]
    for s, m in summary["sensors"].items():
        lines.append(f"Sensor {s}: {m['n']} readings in {m['seconds']:.1f} s, {m['valid']} valid")
        if m["valid"] > 1:
            lines.append(f"  range {m['range_mean']:.1f} mm, standard deviation {m['range_sd']:.1f} mm, "
                         f"ambient {m['ambient_mean']:.0f} kcps")
        else:
            lines.append(f"  no usable range (is a target in front of the sensor?), ambient {m['ambient_mean']:.0f} kcps")
    if summary["abort"] not in ("none", "host"):
        lines += ["", f"The board ended the run early: {summary['abort']}. Check the cables and run it again."]
    if path:
        lines += ["", f"Saved: {path}"]
    return lines
