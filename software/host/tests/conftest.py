"""Author: Jessica"""
import sys
from dataclasses import replace
from pathlib import Path

import pytest

HOST = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOST))

from rig.device import Device               # noqa: E402
from rig.matrix import Config               # noqa: E402
from rig.simulator import SimTransport      # noqa: E402


@pytest.fixture
def small_cfg() -> Config:
    cfg = Config(name="test", distances_m=(0.3,), theta_per_side_deg=(0, 10), rois=(16,), repeats=2,
                 run_ms=1000, warmup_s=1, seed=7)
    cfg.validate()
    return cfg


@pytest.fixture
def sim():
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    return t, dev


def cfg_with(cfg: Config, **kw) -> Config:
    c = replace(cfg, **kw)
    c.validate()
    return c
