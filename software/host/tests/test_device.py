"""Device client against the simulated rig, including fault handling.

Author: Jessica
"""
from collections import deque

import pytest

from rig import protocol as p
from rig.device import Device, DeviceError, DeviceReset, DeviceTimeout
from rig.simulator import SimTransport


def test_connect_reads_info(sim):
    t, dev = sim
    assert dev.info["proto"] == "1" and dev.info["mux"] == "0x70"
    assert t.sent[-2:] == ["PING", "INFO"]


def test_scan_matches_wiring(sim):
    _, dev = sim
    found = dev.scan()
    assert found["main"] == (0x70,) and found["0"] == (0x29,) and found["1"] == (0x29,)
    assert all(found[str(c)] == () for c in range(2, 8))


def test_configure_and_run(sim):
    t, dev = sim
    dev.configure(p.Settings(4, 33, 40, "short"))
    got = []
    end = dev.run("r1", "AB", 1000, got.append)
    assert end.problems() == []
    assert end.n == {"A": 25, "B": 25} and len(got) == 50
    assert {r.sensor for r in got} == {"A", "B"}
    assert all(r.run_id == "r1" for r in got)


def test_solo_run_keeps_other_sensor_silent(sim):
    _, dev = sim
    dev.configure(p.Settings())
    got = []
    end = dev.run("r2", "B", 1000, got.append)
    assert end.edges["A"] == 0 and {r.sensor for r in got} == {"B"}


def test_bad_settings_never_reach_the_device(sim):
    t, dev = sim
    before = len(t.sent)
    with pytest.raises(ValueError):
        dev.configure(p.Settings(16, 50, 40, "short"))
    assert len(t.sent) == before


def test_run_before_cfg_is_refused(sim):
    _, dev = sim
    with pytest.raises(DeviceError) as e:
        dev.run("r1", "AB", 1000, lambda r: None)
    assert e.value.code == "not_ready"


@pytest.mark.parametrize("fault,expect", [("stray", "stopped sensor"), ("i2c", "I2C errors")])
def test_faulty_runs_are_flagged(sim, fault, expect):
    t, dev = sim
    dev.configure(p.Settings())
    t.device.inject(fault, {"bad"})
    end = dev.run("bad", "A", 1000, lambda r: None)
    assert any(expect in x for x in end.problems())


def test_reset_mid_run_raises(sim):
    t, dev = sim
    dev.configure(p.Settings())
    t.device.inject("reset", {"r9"})
    with pytest.raises(DeviceReset) as e:
        dev.run("r9", "AB", 1000, lambda r: None)
    assert e.value.boot.reset == "poweron"


def test_log_lines_and_boot_noise_are_tolerated(sim):
    t, dev = sim
    t.queue.extend(["ESP-ROM:esp32s3-20210327", "LOG level=W msg=something odd"])
    dev.stop_all()
    assert dev.logs and dev.logs[-1].msg == "something odd"


class SilentTransport:
    def __init__(self):
        self.sent = []

    def write_line(self, line):
        self.sent.append(line)

    def read_line(self, timeout):
        return None

    def close(self):
        pass


def test_no_answer_times_out():
    with pytest.raises(DeviceTimeout):
        Device(SilentTransport()).connect(attempts=2)


class ScriptedTransport:
    """Answers each command with the next group of scripted lines."""

    def __init__(self, groups):
        self.groups = deque(groups)
        self.queue = deque()
        self.sent = []

    def write_line(self, line):
        self.sent.append(line)
        if self.groups:
            self.queue.extend(self.groups.popleft())

    def read_line(self, timeout):
        return self.queue.popleft() if self.queue else None

    def close(self):
        pass


def test_protocol_version_mismatch():
    t = ScriptedTransport([["OK PING"], ["INFO fw=9 proto=2", "OK INFO"]])
    with pytest.raises(DeviceError, match="protocol 2"):
        Device(t).connect()


def test_cfg_echo_must_match():
    t = ScriptedTransport([["CFG roi=16 tb=33 imp=40 mode=short", "OK CFG"]])
    with pytest.raises(DeviceError, match="does not match"):
        Device(t).configure(p.Settings(4, 33, 40, "short"))


def test_reading_from_another_run_is_an_error():
    t = ScriptedTransport([["OK RUN id=r1", "D r0 A 1 2 300 0 10 10 10 1"]])
    with pytest.raises(DeviceError, match="reading for run r0"):
        Device(t).run("r1", "A", 1000, lambda r: None)


def test_silent_run_is_aborted():
    t = ScriptedTransport([["OK RUN id=r1", "D r1 A 1 2 300 0 10 10 10 1"], ["OK ABORT"]])
    dev = Device(t, reply_timeout=0.01)
    with pytest.raises(DeviceTimeout):
        dev.run("r1", "A", 100, lambda r: None, margin_s=0.01)
    assert t.sent[-1] == "ABORT"


class StreamingTransport:
    """A board still in a run: one reading per read until it is told to ABORT (or never)."""

    def __init__(self, obeys_abort=True):
        self.obeys_abort = obeys_abort
        self.streaming = True
        self.sent = []
        self.queue = deque()

    def write_line(self, line):
        self.sent.append(line)
        if line == "ABORT" and self.obeys_abort:
            self.streaming = False
            self.queue.extend(["OK ABORT"])
        elif line == "STOPALL":
            self.queue.extend(["OK STOPALL"])
        elif line == "PING":
            self.queue.extend(["OK PING"])
        elif line == "INFO":
            self.queue.extend(["INFO fw=1 proto=%d" % p.PROTOCOL_VERSION, "OK INFO"])

    def read_line(self, timeout):
        if self.queue:
            return self.queue.popleft()
        return "D r1 A 1 2 300 0 10 10 10 1" if self.streaming else None

    def close(self):
        pass


def test_connect_stops_a_run_left_over_from_a_dead_host():
    t = StreamingTransport()
    info = Device(t).connect()
    assert t.sent[:2] == ["ABORT", "STOPALL"]          # stopped it, did not wait it out
    assert info["proto"] == str(p.PROTOCOL_VERSION) or info["proto"] == p.PROTOCOL_VERSION


def test_connect_gives_up_on_a_board_that_will_not_stop(monkeypatch):
    import rig.device as dev_mod
    clock = iter(i * 3.0 for i in range(1000))          # every read looks 3 s later
    monkeypatch.setattr(dev_mod.time, "monotonic", lambda: next(clock))
    with pytest.raises(DeviceError, match="press RST") as e:
        Device(StreamingTransport(obeys_abort=False)).connect()
    assert e.value.code == "busy"


def test_port_roles_from_vendor_id():
    from rig.transport import classify_port
    assert "use this port" in classify_port(0x1A86)       # CH343, local N16R8 board
    assert "use this port" in classify_port(0x10C4)       # CP2102N, DevKitC-1
    assert "use this port" in classify_port(0x0403)       # FT232 variant
    assert "flashing only" in classify_port(0x303A)       # ESP32-S3 built-in USB
    assert "not an ESP32" in classify_port(None)
