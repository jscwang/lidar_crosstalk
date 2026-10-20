"""Experiment configuration and run order.

Order follows the procedure: the pucks move as rarely as possible. For each
distance, for each angle setting, every repeat, ROI and condition is run
before the pucks are touched. Inside a repeat the ROI order is shuffled, and
inside each block (one repeat of one ROI) the three conditions are shuffled.
Every shuffle comes from one seeded generator and is written to the log.

Author: Jessica
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .protocol import CONDITIONS, Settings


@dataclass(frozen=True)
class Config:
    name: str
    distances_m: tuple
    theta_per_side_deg: tuple   # puck angle each side; dtheta = 2 x theta
    rois: tuple
    repeats: int
    run_ms: int
    tb_ms: int = 33
    imp_ms: int = 40
    mode: str = "short"
    spacing_mm: float = 20.0
    warmup_s: int = 600
    ambient_tolerance: float = 0.10
    # The solo ambient rule is a share of the previous block's value. In a dark room that value can be about
    # 1 kcps, where photon noise alone moves it by a fifth, so below this floor the tolerance is taken on the
    # floor instead (0.10 of 5 kcps = 0.5 kcps).
    ambient_floor_kcps: float = 5.0
    max_block_attempts: int = 3
    seed: int = 1
    conditions: tuple = CONDITIONS
    notes: str = ""
    # Adaptive stop (0 = off). With it on, angles run in ascending order and, at each distance, the higher
    # angles are skipped once the worst A+B over solo ambient ratio (over zones and sensors) is at or
    # below adaptive_stop_ratio for adaptive_confirm angles in a row.
    adaptive_stop_ratio: float = 0.0
    adaptive_confirm: int = 1
    # Used by the guided operator: the 16x16 range each sensor should read at a distance (metres -> mm),
    # how far it may be off, and how far sensor B may differ from sensor A (a square target).
    # A distance may instead carry its own angle table (degrees per side -> mm), read between its points:
    # the reported range grows once a turned sensor no longer has the nearest part of the target in the
    # middle of its 27 degree field, so one number cannot fit a wide angle sweep.
    expected_range_mm: dict = field(default_factory=dict, compare=False)
    range_tol_mm: float = 15.0
    square_tol_mm: float = 10.0
    # B minus A, in mm, measured once with a target squared by hand: the two sensors have their own range
    # offsets, so squareness is judged against this value and not against zero.
    square_offset_mm: float = 0.0

    def validate(self) -> None:
        if not self.distances_m or any(d <= 0 for d in self.distances_m):
            raise ValueError("distances_m must be positive")
        if not self.theta_per_side_deg or any(t < 0 for t in self.theta_per_side_deg):
            raise ValueError("theta_per_side_deg must be >= 0")
        if len(set(self.theta_per_side_deg)) != len(self.theta_per_side_deg):
            raise ValueError("theta_per_side_deg has duplicates")
        if sorted(self.conditions) != sorted(CONDITIONS):
            raise ValueError("conditions must be A, B and AB")
        if self.repeats < 1:
            raise ValueError("repeats must be >= 1")
        if not 0 < self.ambient_tolerance < 1:
            raise ValueError("ambient_tolerance must be between 0 and 1")
        for roi in self.rois:
            bad = self.settings(roi).problem()
            if bad:
                raise ValueError(f"roi {roi}: {bad}")
        if not 100 <= self.run_ms <= 3_600_000:
            raise ValueError("run_ms must be 100..3600000")
        if self.adaptive_stop_ratio != 0 and self.adaptive_stop_ratio <= 1.0:
            raise ValueError("adaptive_stop_ratio must be 0 (off) or above 1.0")
        if self.adaptive_confirm < 1:
            raise ValueError("adaptive_confirm must be at least 1")
        if self.range_tol_mm <= 0 or self.square_tol_mm <= 0:
            raise ValueError("range_tol_mm and square_tol_mm must be positive")
        for d, value in self.expected_range_mm.items():
            if isinstance(value, dict) and not value:
                raise ValueError(f"expected_range_mm[{d:g}] has an empty angle table")

    def settings(self, roi: int) -> Settings:
        return Settings(roi, self.tb_ms, self.imp_ms, self.mode)

    def to_json(self) -> dict:
        return asdict(self)


def load_config(path: str | Path) -> Config:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = {k: v for k, v in raw.items() if not k.startswith("_")}   # "_comment" keys
    for key in ("distances_m", "theta_per_side_deg", "rois", "conditions"):
        if key in raw:
            raw[key] = tuple(raw[key])
    if "expected_range_mm" in raw:
        raw["expected_range_mm"] = {
            float(k): ({float(a): float(mm) for a, mm in v.items()} if isinstance(v, dict) else float(v))
            for k, v in raw["expected_range_mm"].items()}
    cfg = Config(**raw)
    cfg.validate()
    return cfg


@dataclass(frozen=True)
class Block:
    block_id: str
    distance_m: float
    theta_deg: float
    repeat: int
    roi: int
    conditions: tuple = field(default=CONDITIONS)

    @property
    def dtheta_deg(self) -> float:
        return 2 * self.theta_deg


def plan(cfg: Config) -> list[Block]:
    rng = random.Random(cfg.seed)
    blocks = []
    thetas = sorted(cfg.theta_per_side_deg) if cfg.adaptive_stop_ratio > 0 else cfg.theta_per_side_deg
    for d in cfg.distances_m:
        for theta in thetas:
            for rep in range(1, cfg.repeats + 1):
                rois = list(cfg.rois)
                rng.shuffle(rois)
                for roi in rois:
                    conds = list(cfg.conditions)
                    rng.shuffle(conds)
                    bid = f"d{round(d * 100):03d}_t{round(theta * 10):03d}_r{rep}_roi{roi}"
                    blocks.append(Block(bid, d, theta, rep, roi, tuple(conds)))
    return blocks
