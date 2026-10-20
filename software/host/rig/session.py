"""Runs the crosstalk procedure and logs everything to CSV.

Output directory:
  session.json        config, firmware INFO, self-test, host version, tag
  blocks.csv          one row per block attempt, with the accept decision
  runs.csv            one row per run (all attempts, accepted or not)
  readings.csv        every reading (procedure fields first)
  warmup.csv          readings from the warm-up runs
  events.log          human-readable log, including every shuffled order

Acceptance rules
  run:   RUNEND problems empty (no abort, no I2C or read errors, stopped sensor
         silent), each ranging sensor within 5% of the expected count, and at
         most 1% missed results (gaps in the interrupt timestamps).
  block: all three runs accepted, and each sensor's solo ambient within the
         tolerance (10%) of the previous accepted block at the same distance,
         angle and ROI. Failing blocks are redone, up to max_block_attempts.
         Readings of rejected runs are kept but marked, never deleted.

Author: Jessica
"""
from __future__ import annotations

import csv
import json
import logging
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol

from . import __version__
from . import protocol as p
from .device import Device, DeviceError, DeviceReset
from .matrix import Block, Config, plan

log = logging.getLogger("rig.session")

READING_FIELDS = ["run_id", "t_int_us", "sensor", "condition", "dtheta", "roi", "d_m", "range_mm",
                  "range_status", "signal_rate", "ambient_rate", "spads", "stream", "t_read_us"]
RUN_FIELDS = ["run_id", "block_id", "attempt", "seq_in_block", "condition", "distance_m", "theta_deg",
              "dtheta_deg", "roi", "repeat", "tag", "start_utc", "room_temp_c", "tb_ms", "imp_ms", "mode",
              "n_A", "n_B", "edges_A", "edges_B", "rderr_A", "rderr_B", "buserr", "abort",
              "missed_A", "missed_B", "expected_per_sensor", "accepted", "reject_reason"]
BLOCK_FIELDS = ["block_id", "attempt", "distance_m", "theta_deg", "dtheta_deg", "roi", "repeat", "tag",
                "order", "solo_ambient_A", "solo_ambient_B", "ref_ambient_A", "ref_ambient_B",
                "accepted", "reason"]


class Operator(Protocol):
    def setup(self, distance_m: float, theta_deg: float, new_distance: bool) -> Optional[float]:
        """Asks for the physical change; returns room temperature in C, or None."""

    def notify(self, message: str) -> None: ...


class ConsoleOperator:
    def setup(self, distance_m, theta_deg, new_distance):
        print()
        if new_distance:
            print(f"  Set the target at {distance_m:.2f} m from the aperture plane, square to the boresight.")
        print(f"  Set puck A to -{theta_deg:g} deg and puck B to +{theta_deg:g} deg "
              f"(dtheta = {2 * theta_deg:g} deg).")
        while True:
            raw = input("  Room temperature in C (Enter to skip), then Enter to start: ").strip()
            if not raw:
                return None
            try:
                return float(raw)
            except ValueError:
                print("  Please type a number, e.g. 22.5")

    def notify(self, message):
        print(f"  {message}")


@dataclass
class RunResult:
    run_id: str
    condition: str
    accepted: bool
    reason: str
    solo_ambient: Optional[float]   # mean ambient of the ranging sensor for a solo run
    ambient: dict = field(default_factory=dict)   # sensor -> mean ambient of this run


class Session:
    def __init__(self, device: Device, cfg: Config, out_dir: Path, operator: Operator,
                 tag: str = "", warmup: bool = True, require_selftest: bool = True):
        self.dev = device
        self.cfg = cfg
        self.out = Path(out_dir)
        self.op = operator
        self.tag = tag
        self.warmup = warmup
        self.require_selftest = require_selftest
        self.run_counter = 0
        self.done_blocks: set[str] = set()
        self.ambient_ref: dict = {}   # (d, theta, roi, sensor) -> last accepted solo ambient
        self.room_temp: Optional[float] = None
        self._configured_roi: Optional[int] = None
        self._ratios: dict = {}   # (distance, theta) -> {(roi, sensor): [A+B over solo ambient, per block]}
        self.stops: dict = {}     # distance -> angle after which the higher angles are skipped (saved, so a resume keeps it)

    # ------------------------------------------------------------------ files
    def _open(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        self._events = open(self.out / "events.log", "a", encoding="utf-8")
        self._files = {}
        self._writers = {}
        for name, fields in (("readings", READING_FIELDS), ("runs", RUN_FIELDS), ("blocks", BLOCK_FIELDS),
                             ("warmup", READING_FIELDS)):
            path = self.out / f"{name}.csv"
            new = not path.exists()
            f = open(path, "a", newline="", encoding="utf-8")
            w = csv.DictWriter(f, fieldnames=fields)
            if new:
                w.writeheader()
            self._files[name], self._writers[name] = f, w

    def _close(self) -> None:
        for f in self._files.values():
            f.close()
        self._events.close()

    def event(self, msg: str) -> None:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._events.write(f"{stamp}  {msg}\n")
        self._events.flush()
        log.info(msg)

    def _load_progress(self) -> None:
        """Resume support: skip blocks already decided, continue run numbering."""
        runs = self.out / "runs.csv"
        if runs.exists():
            with open(runs, newline="", encoding="utf-8") as f:
                ids = [r["run_id"] for r in csv.DictReader(f)]
            nums = [int(i[1:]) for i in ids if i.startswith("r") and i[1:].isdigit()]
            self.run_counter = max(nums, default=0)
        stops = self.out / "adaptive_stops.json"
        if stops.exists():
            self.stops = {float(d): float(t) for d, t in json.loads(stops.read_text(encoding="utf-8")).items()}
        blocks = self.out / "blocks.csv"
        if blocks.exists():
            with open(blocks, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            for r in rows:
                if r["accepted"] == "True" or r["reason"].startswith("gave up"):
                    self.done_blocks.add(r["block_id"])
                if r["accepted"] == "True":
                    for s in p.SENSORS:
                        if r[f"solo_ambient_{s}"]:
                            key = (float(r["distance_m"]), float(r["theta_deg"]), int(r["roi"]), s)
                            self.ambient_ref[key] = float(r[f"solo_ambient_{s}"])

    def _write_session_json(self, selftest: Optional[tuple]) -> None:
        path = self.out / "session.json"
        meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"starts": []}
        meta["config"] = self.cfg.to_json()
        meta["tag"] = self.tag
        meta["author"] = "Jessica"
        meta["starts"].append({
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "host_software": __version__,
            "python": platform.python_version(),
            "firmware_info": self.dev.info,
            "selftest": None if selftest is None else {
                "failed": selftest[0],
                "checks": [{"name": t.name, "result": t.result, "detail": t.detail} for t in selftest[1]]},
        })
        path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ device
    def _configure(self, roi: int) -> None:
        if self._configured_roi != roi:
            self.dev.configure(self.cfg.settings(roi))
            self._configured_roi = roi

    def _recover_from_reset(self, e: DeviceReset) -> None:
        self.event(f"DEVICE RESET (reason: {e.boot.reset}); reconnecting and reapplying settings")
        self._configured_roi = None
        self.dev.connect()

    # ------------------------------------------------------------------ main
    def run(self) -> dict:
        self._open()
        try:
            self._load_progress()
            selftest = None
            if self.require_selftest:
                self._configure(self.cfg.rois[0])
                selftest = self.dev.selftest()
                failed = [t for t in selftest[1] if t.result == "FAIL"]
                for t in failed:
                    self.event(f"SELFTEST FAIL {t.name}: {t.detail}")
                if selftest[0]:
                    self._write_session_json(selftest)
                    raise DeviceError(f"self-test failed {selftest[0]} check(s); fix the rig first", "selftest")
                self.event("self-test passed")
            self._write_session_json(selftest)
            return self._run_plan()
        except KeyboardInterrupt:
            self.event("interrupted by operator; stopping the sensors")
            try:
                self.dev.abort()
                self.dev.stop_all()
            except Exception as e:   # the port may be gone; the data is already on disk
                self.event(f"could not stop the device cleanly: {e}")
            raise
        finally:
            self._close()

    def _run_plan(self) -> dict:
        blocks = plan(self.cfg)
        todo = [b for b in blocks if b.block_id not in self.done_blocks]
        self.event(f"plan: {len(blocks)} blocks, {len(todo)} to do, tag={self.tag or '-'}")
        summary = {"accepted": 0, "gave_up": 0, "runs": 0, "rejected_runs": 0}
        last_d, last_theta = None, None
        adaptive = self.cfg.adaptive_stop_ratio > 0
        streak: dict = {}
        skipped = 0
        for i, b in enumerate(todo):
            if b.distance_m in self.stops and b.theta_deg > self.stops[b.distance_m]:
                skipped += 1              # the crosstalk was already gone at a lower angle at this distance
                continue
            new_d = b.distance_m != last_d
            if new_d or b.theta_deg != last_theta:
                self.room_temp = self.op.setup(b.distance_m, b.theta_deg, new_d)
                self._configured_roi = None    # an operator may have used the sensors: send CFG again
                self.event(f"setup d={b.distance_m} m theta={b.theta_deg} deg room_temp={self.room_temp}")
                if new_d and self.warmup:
                    self._warm_up(b)
                last_d, last_theta = b.distance_m, b.theta_deg
            ok, stats = self._run_block(b)
            summary["accepted" if ok else "gave_up"] += 1
            summary["runs"] += stats[0]
            summary["rejected_runs"] += stats[1]
            nxt = todo[i + 1] if i + 1 < len(todo) else None
            if adaptive and (nxt is None or (nxt.distance_m, nxt.theta_deg) != (b.distance_m, b.theta_deg)):
                self._check_stop(b.distance_m, b.theta_deg, streak)
        if adaptive:
            summary["skipped"] = skipped
        self.event(f"session finished: {summary}")
        return summary

    def _check_stop(self, d: float, theta: float, streak: dict) -> None:
        """After the last block at an angle: is the crosstalk gone (every zone and sensor at or below the ratio)?"""
        groups = self._ratios.get((d, theta))
        if not groups:
            return
        means = {k: sum(v) / len(v) for k, v in groups.items()}
        worst_key = max(means, key=means.get)
        worst = means[worst_key]
        if worst <= self.cfg.adaptive_stop_ratio:
            streak[d] = streak.get(d, 0) + 1
        else:
            streak[d] = 0
        self.event(f"crosstalk check d={d} m theta={theta} deg: worst ratio {worst:.2f} "
                   f"(zone {worst_key[0]}, sensor {worst_key[1]}), limit {self.cfg.adaptive_stop_ratio:.2f}, "
                   f"streak {streak[d]}/{self.cfg.adaptive_confirm}")
        if streak[d] >= self.cfg.adaptive_confirm:
            self.stops[d] = theta
            (self.out / "adaptive_stops.json").write_text(
                json.dumps({str(k): v for k, v in self.stops.items()}), encoding="utf-8")
            self.op.notify(f"Crosstalk is gone at {theta:g} deg per side at {d:g} m: skipping the higher angles there.")
            self.event(f"adaptive stop at d={d} m after theta={theta} deg")

    def _warm_up(self, b: Block) -> None:
        self._configure(self.cfg.rois[0])
        self.op.notify(f"Warming up both sensors for {self.cfg.warmup_s} s")
        run_id = f"warmup_d{round(b.distance_m * 100):03d}"
        w = self._writers["warmup"]

        def keep(r: p.Reading) -> None:
            w.writerow(self._reading_row(r, "AB", b, self.cfg.rois[0]))

        try:
            end = self.dev.run(run_id, "AB", self.cfg.warmup_s * 1000, keep)
            self.event(f"warm-up {run_id}: nA={end.n['A']} nB={end.n['B']} abort={end.abort}")
        except DeviceReset as e:
            self._recover_from_reset(e)
        self._files["warmup"].flush()

    # ------------------------------------------------------------------ blocks
    def _run_block(self, b: Block) -> tuple[bool, tuple[int, int]]:
        runs, rejected = 0, 0
        for attempt in range(1, self.cfg.max_block_attempts + 1):
            self.event(f"block {b.block_id} attempt {attempt}: order {' '.join(b.conditions)}")
            results = []
            for seq, cond in enumerate(b.conditions, start=1):
                r = self._run_one(b, attempt, seq, cond)
                results.append(r)
                runs += 1
                rejected += not r.accepted
            ok, reason, solo, refs = self._judge_block(b, results)
            self._writers["blocks"].writerow({
                "block_id": b.block_id, "attempt": attempt, "distance_m": b.distance_m, "theta_deg": b.theta_deg,
                "dtheta_deg": b.dtheta_deg, "roi": b.roi, "repeat": b.repeat, "tag": self.tag,
                "order": " ".join(b.conditions),
                "solo_ambient_A": _fmt(solo.get("A")), "solo_ambient_B": _fmt(solo.get("B")),
                "ref_ambient_A": _fmt(refs.get("A")), "ref_ambient_B": _fmt(refs.get("B")),
                "accepted": ok, "reason": reason})
            self._files["blocks"].flush()
            if ok:
                for s, v in solo.items():
                    self.ambient_ref[(b.distance_m, b.theta_deg, b.roi, s)] = v
                both = next((r for r in results if r.condition == "AB"), None)
                if both is not None:
                    for s, v in solo.items():
                        if v and s in both.ambient and v > 0:
                            self._ratios.setdefault((b.distance_m, b.theta_deg), {}).setdefault(
                                (b.roi, s), []).append(both.ambient[s] / v)
                self.event(f"block {b.block_id} accepted")
                return True, (runs, rejected)
            self.event(f"block {b.block_id} attempt {attempt} rejected: {reason}")
        self.op.notify(f"Block {b.block_id} failed {self.cfg.max_block_attempts} times; moving on. "
                       f"Check events.log.")
        self._writers["blocks"].writerow({
            "block_id": b.block_id, "attempt": self.cfg.max_block_attempts + 1, "distance_m": b.distance_m,
            "theta_deg": b.theta_deg, "dtheta_deg": b.dtheta_deg, "roi": b.roi, "repeat": b.repeat,
            "tag": self.tag, "order": " ".join(b.conditions), "solo_ambient_A": "", "solo_ambient_B": "",
            "ref_ambient_A": "", "ref_ambient_B": "", "accepted": False,
            "reason": f"gave up after {self.cfg.max_block_attempts} attempts"})
        self._files["blocks"].flush()
        return False, (runs, rejected)

    def _judge_block(self, b: Block, results: list[RunResult]):
        solo = {r.condition: r.solo_ambient for r in results if r.condition in p.SENSORS and r.accepted}
        refs = {s: self.ambient_ref.get((b.distance_m, b.theta_deg, b.roi, s)) for s in p.SENSORS}
        bad = [r for r in results if not r.accepted]
        if bad:
            return False, "; ".join(f"{r.run_id} {r.condition}: {r.reason}" for r in bad), solo, refs
        # The rule asks that the room light has not changed since the last accepted block at this setting. It is a
        # share of the reference, which cannot work when the reference is near zero: in a dark room the 4x4 solo
        # ambient is about 1 kcps, where the photon noise alone moves it by 20%. Below ambient_floor_kcps the same
        # tolerance is applied to the floor instead, so the allowance never falls under that absolute size.
        for s in p.SENSORS:
            ref, now = refs[s], solo.get(s)
            if ref and now is not None:
                allowed = self.cfg.ambient_tolerance * max(ref, self.cfg.ambient_floor_kcps)
                if abs(now - ref) > allowed:
                    return (False, f"solo ambient {s} moved {now - ref:+.2f} kcps from {ref:.2f} "
                                   f"(limit {allowed:.2f})", solo, refs)
        return True, "", solo, refs

    # ------------------------------------------------------------------ runs
    def _reading_row(self, r: p.Reading, cond: str, b: Block, roi: int) -> dict:
        return {"run_id": r.run_id, "t_int_us": r.t_int_us, "sensor": r.sensor, "condition": cond,
                "dtheta": b.dtheta_deg, "roi": roi, "d_m": b.distance_m, "range_mm": r.range_mm,
                "range_status": r.status, "signal_rate": r.signal_kcps, "ambient_rate": r.ambient_kcps,
                "spads": r.spads, "stream": r.stream, "t_read_us": r.t_read_us}

    def _run_one(self, b: Block, attempt: int, seq: int, cond: str) -> RunResult:
        self.run_counter += 1
        run_id = f"r{self.run_counter:05d}"
        start = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        buf: list[p.Reading] = []
        end: Optional[p.RunEnd] = None
        reason = ""
        try:
            self._configure(b.roi)
            end = self.dev.run(run_id, cond, self.cfg.run_ms, buf.append)
        except DeviceReset as e:
            reason = f"device reset ({e.boot.reset})"
            self._recover_from_reset(e)
        except DeviceError as e:
            reason = f"device error: {e}"
            self.event(f"{run_id}: {reason}")
            if e.code in ("verify", "not_ready"):
                self._configured_roi = None   # settings lost on the device: send CFG again

        expected = (self.cfg.run_ms - self.cfg.tb_ms) // self.cfg.imp_ms + 1
        missed = {s: _missed([r.t_int_us for r in buf if r.sensor == s], self.cfg.imp_ms) for s in p.SENSORS}
        if end is not None and not reason:
            problems = end.problems()
            for s in p.SENSORS:
                if p.participates(cond, s):
                    if abs(end.n[s] - expected) > 0.05 * expected:
                        problems.append(f"{s} logged {end.n[s]} readings, expected about {expected}")
                    if missed[s] > 0.01 * expected:
                        problems.append(f"{s} missed {missed[s]} results (gaps in the interrupt timing)")
            reason = "; ".join(problems)
        accepted = not reason

        for r in buf:
            self._writers["readings"].writerow(self._reading_row(r, cond, b, b.roi))
        n = end.n if end else {s: sum(1 for r in buf if r.sensor == s) for s in p.SENSORS}
        self._writers["runs"].writerow({
            "run_id": run_id, "block_id": b.block_id, "attempt": attempt, "seq_in_block": seq,
            "condition": cond, "distance_m": b.distance_m, "theta_deg": b.theta_deg, "dtheta_deg": b.dtheta_deg,
            "roi": b.roi, "repeat": b.repeat, "tag": self.tag, "start_utc": start,
            "room_temp_c": "" if self.room_temp is None else self.room_temp,
            "tb_ms": self.cfg.tb_ms, "imp_ms": self.cfg.imp_ms, "mode": self.cfg.mode,
            "n_A": n["A"], "n_B": n["B"],
            "edges_A": end.edges["A"] if end else "", "edges_B": end.edges["B"] if end else "",
            "rderr_A": end.rderr["A"] if end else "", "rderr_B": end.rderr["B"] if end else "",
            "buserr": end.buserr if end else "", "abort": end.abort if end else "",
            "missed_A": missed["A"], "missed_B": missed["B"], "expected_per_sensor": expected,
            "accepted": accepted, "reject_reason": reason})
        self._files["readings"].flush()
        self._files["runs"].flush()
        if not accepted:
            self.event(f"{run_id} {cond} rejected: {reason}")

        solo = None
        if cond in p.SENSORS and accepted:
            amb = [r.ambient_kcps for r in buf if r.sensor == cond]
            solo = sum(amb) / len(amb) if amb else None
        per_sensor = {}
        for s in p.SENSORS:
            vals = [r.ambient_kcps for r in buf if r.sensor == s]
            if vals:
                per_sensor[s] = sum(vals) / len(vals)
        return RunResult(run_id, cond, accepted, reason, solo, per_sensor)


def _missed(times_us: list[int], imp_ms: int) -> int:
    """Readings lost, from gaps between interrupt timestamps.

    The VL53L1X's stream counter stays at 1 in timed ranging (seen on the
    bench), so a gap of k periods counts as k - 1 missed readings instead.
    """
    period = imp_ms * 1000.0
    return sum(max(round((b - a) / period) - 1, 0) for a, b in zip(times_us, times_us[1:]))


def _fmt(v: Optional[float]) -> str:
    return "" if v is None else f"{v:.1f}"
