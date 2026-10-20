"""The crossover prediction must match build_rq3.py and the issued tables.

Author: Jessica
"""
import importlib.util
import math
import sys
from pathlib import Path

import pytest

from rig import geometry

PROJECT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("roi,d,expected", [(16, 0.3, 23.4), (16, 0.8, 25.6), (4, 0.3, 17.3), (4, 0.8, 19.7)])
def test_issued_values(roi, d, expected):
    assert round(geometry.predicted_crossover(roi, d), 1) == expected


def test_satisfies_the_design_equation():
    for f in (27.0, 15.0):
        for d in (0.3, 0.8):
            x = math.radians(geometry.crossover_deg(f, d))
            lhs = 0.020 + 2 * d * math.tan(x / 2)
            rhs = d * (math.tan(math.radians(13.5)) + math.tan(math.radians(f / 2)))
            assert lhs == pytest.approx(rhs, rel=1e-12)


def test_no_prediction_without_a_measured_field():
    assert geometry.predicted_crossover(8, 0.3) is None


def test_matches_build_rq3_when_available():
    path = PROJECT / "build_rq3.py"
    if not path.exists():
        pytest.skip("build_rq3.py not found")
    sys.path.insert(0, str(PROJECT))
    try:
        spec = importlib.util.spec_from_file_location("build_rq3", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:   # needs reportlab; the table test above still covers the values
        pytest.skip(f"build_rq3 not importable: {e}")
    for f in (27.0, 15.0):
        for d in (0.3, 0.8):
            assert geometry.crossover_deg(f, d) == pytest.approx(mod.crossover(f, d), abs=1e-9)
