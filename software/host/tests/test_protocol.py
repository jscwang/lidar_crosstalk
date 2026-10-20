"""Protocol parsing and validation. Golden lines are the exact strings the
firmware's native tests assert (firmware/test_native/test_core.cpp), so the
two implementations are held to the same format.

Author: Jessica
"""
import pytest

from rig import protocol as p

GOLDEN_READING = "D run1 B 12345678901 12345679900 301 0 600000 1234 44 200"
GOLDEN_RUNEND = ("RUNEND id=r7 cond=A t0=1 t1=2 nA=750 nB=0 edgesA=751 edgesB=0 overrunA=0 overrunB=0 "
                 "rderrA=0 rderrB=0 buserr=0 abort=stray")


def test_golden_reading():
    r = p.parse_line(GOLDEN_READING)
    assert r == p.Reading("run1", "B", 12345678901, 12345679900, 301, 0, 600000, 1234, 44, 200)


def test_golden_runend():
    e = p.parse_line(GOLDEN_RUNEND)
    assert isinstance(e, p.RunEnd)
    assert (e.run_id, e.cond, e.t0_us, e.t1_us, e.abort) == ("r7", "A", 1, 2, "stray")
    assert e.n == {"A": 750, "B": 0} and e.edges == {"A": 751, "B": 0}
    assert "aborted (stray)" in e.problems()


def test_runend_problems():
    ok = p.parse_line("RUNEND id=x cond=AB t0=0 t1=1 nA=5 nB=5 edgesA=5 edgesB=5 overrunA=0 overrunB=0 "
                      "rderrA=0 rderrB=0 buserr=0 abort=none")
    assert ok.problems() == []
    stray = p.parse_line("RUNEND id=x cond=A t0=0 t1=1 nA=5 nB=0 edgesA=5 edgesB=2 overrunA=0 overrunB=0 "
                         "rderrA=1 rderrB=0 buserr=4 abort=none")
    probs = " | ".join(stray.problems())
    assert "stopped sensor B raised 2" in probs and "4 I2C errors" in probs and "1 failed reads on A" in probs


@pytest.mark.parametrize("line,cls", [
    ("OK PING", p.Ok), ("OK RUN id=r00001", p.Ok), ("READY", p.Ready),
    ("BOOT fw=1.0.0 proto=1 reset=brownout", p.Boot), ("LOG level=E msg=TCA9548A not found at 0x70", p.Log),
    ("STATUS state=idle run=- buserr=0", p.Status), ("CFG roi=4 tb=33 imp=40 mode=short", p.CfgEcho),
    ("SCAN bus=main addrs=70", p.Scan), ("SELFTEST failed=2", p.SelfTestDone),
    ("TEST name=run_A_A result=FAIL detail=n=20 period_ms=41.10 problem=too few readings", p.Test),
    ("ERR RUN code=not_ready msg=send CFG first", p.Err),
])
def test_line_types(line, cls):
    assert isinstance(p.parse_line(line), cls)


def test_tail_fields_keep_spaces():
    e = p.parse_line("ERR CFG code=verify msg=sensor B: settings did not read back as written")
    assert e == p.Err("CFG", "verify", "sensor B: settings did not read back as written")
    t = p.parse_line("TEST name=stop_quiet result=PASS detail=edges after stop: A=0 B=0")
    assert t.detail == "edges after stop: A=0 B=0"
    assert p.parse_line("BOOT fw=1.0.0 proto=1 reset=poweron").reset == "poweron"


def test_scan_forms():
    assert p.parse_line("SCAN ch=0 addrs=29").addrs == (0x29,)
    assert p.parse_line("SCAN ch=3 addrs=none").addrs == ()
    assert p.parse_line("SCAN bus=main addrs=70,29").addrs == (0x70, 0x29)
    assert p.parse_line("SCAN ch=5 addrs=error").error


@pytest.mark.parametrize("line", [
    "", "D run1 B 1 2 3", "D run1 C 1 2 3 4 5 6 7 8", "D run1 A x 2 3 4 5 6 7 8",
    "RUNEND id=x", "WHAT is=this", "OK", "INFO novalue",
])
def test_malformed(line):
    with pytest.raises(p.ProtocolError):
        p.parse_line(line)


# Same cases as testParseCfg() in the firmware tests.
@pytest.mark.parametrize("s,ok", [
    (p.Settings(4, 33, 40, "short"), True), (p.Settings(16, 100, 100, "long"), True),
    (p.Settings(3, 33, 40, "short"), False), (p.Settings(17, 33, 40, "short"), False),
    (p.Settings(16, 34, 40, "short"), False), (p.Settings(16, 15, 40, "long"), False),
    (p.Settings(16, 15, 40, "short"), True), (p.Settings(16, 50, 40, "short"), False),
    (p.Settings(16, 33, 40, "medium"), False), (p.Settings(16, 33, 5001, "short"), False),
])
def test_settings_rules(s, ok):
    assert (s.problem() is None) == ok
    if ok:
        assert s.command() == f"CFG roi={s.roi} tb={s.tb} imp={s.imp} mode={s.mode}"
    else:
        with pytest.raises(ValueError):
            s.command()


def test_run_command_rules():
    assert p.run_command("d03-t10-r1-full-AB", "AB", 30000) == "RUN id=d03-t10-r1-full-AB cond=AB dur=30000"
    assert p.run_command("x" * 24, "A", 100)
    for bad in (("x" * 25, "A", 1000), ("bad.id", "A", 1000), ("x", "C", 1000), ("x", "A", 99),
                ("x", "A", 3_600_001), ("", "A", 1000)):
        with pytest.raises(ValueError):
            p.run_command(*bad)
