"""A measurement that ends by itself: after a count, after a time, and what is saved.

Author: Jessica
"""
import csv

import pytest

from rig import capture as cap
from rig import protocol as p
from rig.cli import main
from rig.device import Device
from rig.simulator import SimTransport


def _dev():
    dev = Device(SimTransport())
    dev.connect()
    return dev


def test_count_stops_the_run_and_keeps_exactly_that_many_per_sensor():
    rows, summary = cap.capture(_dev(), p.Settings(), "AB", count=30)
    assert summary["stopped_by"] == "count"
    assert sum(r["sensor"] == "A" for r in rows) == 30 and sum(r["sensor"] == "B" for r in rows) == 30
    assert [r["t_s"] for r in rows] == sorted(r["t_s"] for r in rows) and rows[0]["t_s"] == 0


def test_seconds_stops_the_run_at_the_time():
    rows, summary = cap.capture(_dev(), p.Settings(), "A", seconds=2)
    assert summary["stopped_by"] == "time" and {r["sensor"] for r in rows} == {"A"}
    assert 40 <= len(rows) <= 55 and summary["run_ms"] == 2000


def test_seconds_and_count_whichever_comes_first():
    _, by_count = cap.capture(_dev(), p.Settings(), "AB", seconds=20, count=10)
    assert by_count["stopped_by"] == "count"
    _, by_time = cap.capture(_dev(), p.Settings(), "AB", seconds=1, count=500)
    assert by_time["stopped_by"] == "time"
    assert "time limit came before" in chr(10).join(cap.report(by_time))


def test_the_line_is_clean_after_a_stopped_run():
    dev = _dev()
    cap.capture(dev, p.Settings(), "AB", count=10)
    assert dev.status().state == "idle"          # no leftover OK ABORT confusing the next command


def test_requests_that_cannot_run_are_refused():
    s = p.Settings()
    with pytest.raises(cap.CaptureError):
        cap.plan(s, "AB", None, 200_000)         # more than an hour
    with pytest.raises(cap.CaptureError):
        cap.plan(s, "AB", 0, None)
    with pytest.raises(cap.CaptureError):
        cap.plan(s, "AB", None, 0)
    assert cap.plan(s, "AB", None, None)[0] == 30_000      # no limit given: 30 s


def test_command_line_read_saves_a_csv(tmp_path, capsys):
    out = tmp_path / "x.csv"
    assert main(["read", "--sim", "--count", "20", "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "finished by itself" in text and "Saved" in text
    with open(out, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 40 and list(rows[0].keys()) == cap.COLUMNS
