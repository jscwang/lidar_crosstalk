"""Clock diagnostic and the REG command, against the simulator and a scripted wrong-clock board.

Author: Jessica
"""
from collections import deque

import pytest

from rig import protocol as p
from rig.device import Device
from rig.diag import clock_report, measure_periods, snapshot
from rig.simulator import SimTransport


def test_reg_line_parses():
    m = p.parse_line("REG sensor=A addr=0x00DE data=0A3C")
    assert isinstance(m, p.RegData) and m.sensor == "A" and m.addr == 0xDE and m.data == bytes([0x0A, 0x3C])
    with pytest.raises(p.ProtocolError):
        p.parse_line("REG sensor=A addr=0x00DE data=ZZ")


def test_read_regs_through_the_simulator():
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    assert dev.read_regs("A", 0x00DE, 2) == (0x0A3C).to_bytes(2, "big")
    assert len(dev.read_regs("B", 0x006C, 4)) == 4
    snap = snapshot(dev)
    assert snap["A"]["pll"] == 0x0A3C & 0x3FF and snap["B"]["osc"] == 0x0A4B


def test_clock_report_says_ok_when_the_period_is_right():
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    lines, ok = clock_report(dev, 40)
    text = "\n".join(lines)
    assert ok and "Both sensors run at the requested period" in text and "OSC_CALIBRATE_VAL" in text
    real = measure_periods(dev, 2000)
    assert all(abs(v - 40.0) < 2.0 for v in real.values())


def test_clock_report_flags_a_sensor_running_twice_as_fast(monkeypatch):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    import rig.diag as diag
    fake = {"A": {"period": 19.63, "repeat": 0.02, "n": 50}, "B": {"period": 19.84, "repeat": 0.0, "n": 50}}
    monkeypatch.setattr(diag, "measure", lambda d, run_ms=3000, cond="AB": fake)
    lines, ok = clock_report(dev, 40)
    text = "\n".join(lines)
    assert not ok and "WRONG" in text and "cannot see this" in text and "0.49 x the request" in text
    assert "not repeats" in text


def test_clock_report_recognises_an_interrupt_that_fires_twice(monkeypatch):
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    import rig.diag as diag
    fake = {"A": {"period": 19.9, "repeat": 0.49, "n": 50}, "B": {"period": 20.1, "repeat": 0.51, "n": 50}}
    monkeypatch.setattr(diag, "measure", lambda d, run_ms=3000, cond="AB": fake)
    lines, ok = clock_report(dev, 40)
    text = "\n".join(lines)
    assert not ok and "counts two interrupts" in text and "interrupt line" in text and "49% of 50" in text


def test_measure_counts_repeated_readings():
    from rig.diag import measure
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    dev.configure(p.Settings())
    m = measure(dev, 2000)
    assert m["A"]["repeat"] < 0.1 and m["B"]["repeat"] < 0.1 and m["A"]["n"] > 30


def test_command_line_regs_on_the_simulator(capsys):
    from rig.cli import main
    assert main(["regs", "--sim"]) == 0
    assert "Requested inter-measurement period: 40 ms" in capsys.readouterr().out


def test_trace_messages_parse():
    h = p.parse_line("TRACE sensor=A edges=12 reads=6 overflow=0")
    e = p.parse_line("TRACE_E sensor=A level=0 t=123456")
    r = p.parse_line("TRACE_R sensor=A t=123700 range=288 amb=250 sig=19000")
    assert h.edges == 12 and not h.overflow and e.level == 0 and e.t_us == 123456 and r.range_mm == 288


def test_edge_report_fine_sensor():
    from rig.diag import edge_report
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    lines, ok = edge_report(dev, "A", 40, 400)
    text = chr(10).join(lines)
    assert ok and "falls once per measurement" in text and "First events" in text


def test_edge_report_recognises_a_line_that_falls_twice():
    from rig.diag import edge_report
    t = SimTransport()
    t.device.double_int = True
    dev = Device(t)
    dev.connect()
    lines, ok = edge_report(dev, "B", 40, 400)
    text = chr(10).join(lines)
    assert not ok and "falls twice per measurement" in text and "100% of" not in text


def test_command_line_edges_on_the_simulator(capsys):
    from rig.cli import main
    assert main(["edges", "--sim", "--sensor", "B"]) == 0
    assert "Data-ready line of sensor B" in capsys.readouterr().out


def test_clock_report_tells_apart_a_fault_that_needs_both_sensors(monkeypatch):
    import rig.diag as diag
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    bad = {"A": {"period": 19.9, "repeat": 0.49, "n": 150}, "B": {"period": 20.1, "repeat": 0.51, "n": 148}}
    good = {"A": {"period": 40.0, "repeat": 0.0, "n": 50}, "B": {"period": 40.2, "repeat": 0.0, "n": 50}}
    monkeypatch.setattr(diag, "measure", lambda d, run_ms=3000, cond="AB": bad if cond == "AB" else {s: good[s] for s in cond})
    text = chr(10).join(diag.clock_report(dev, 40)[0])
    assert "only appears while both sensors range at the same time" in text and "ranging alone" in text
    monkeypatch.setattr(diag, "measure", lambda d, run_ms=3000, cond="AB": {s: bad[s] for s in cond})
    text = chr(10).join(diag.clock_report(dev, 40)[0])
    assert "also happens with each sensor ranging alone" in text


def _edge_text(**hooks):
    from rig.diag import edge_report
    t = SimTransport()
    for k, v in hooks.items():
        setattr(t.device, k, v)
    dev = Device(t)
    dev.connect()
    lines, ok = edge_report(dev, "A", 40, 400)
    return chr(10).join(lines), ok


def test_run_path_trace_fine_sensor():
    text, ok = _edge_text()
    assert ok and "started and read the way a real run does it" in text and "the run counts one interrupt each" in text


def test_run_path_trace_finds_a_firmware_capture_fault():
    text, ok = _edge_text(isr_double=True)
    assert not ok and "The pin falls once per measurement, but the run counts two interrupts" in text
    assert "falls once per measurement, at the requested period" in text   # the own-path trace was clean


def test_run_path_trace_finds_a_pin_that_falls_twice_in_a_run():
    text, ok = _edge_text(double_int=True)
    assert not ok and "the pin itself falls twice per measurement" in text


def test_clock_report_names_the_capture_when_interrupts_come_in_pairs(monkeypatch):
    import rig.diag as diag
    t = SimTransport()
    dev = Device(t)
    dev.connect()
    fake = {"A": {"period": 19.9, "repeat": 0.5, "n": 150, "close": 74, "gaps": 149},
            "B": {"period": 20.1, "repeat": 0.5, "n": 148, "close": 73, "gaps": 147}}
    monkeypatch.setattr(diag, "measure", lambda d, run_ms=3000, cond="AB": fake if cond == "AB" else {s: fake[s] for s in cond})
    text = chr(10).join(diag.clock_report(dev, 40)[0])
    assert "one falling edge is counted twice" in text and "74 of 149" in text
