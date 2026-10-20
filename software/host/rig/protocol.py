"""Rig serial protocol, version 1 (see PROTOCOL.md).

Parses device lines into typed messages and builds command lines. The
validation rules mirror firmware/lib/rig_core/src/protocol.cpp so bad
settings are refused on the host before anything is sent.

Author: Jessica
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Union

PROTOCOL_VERSION = 1
SENSORS = ("A", "B")
CONDITIONS = ("A", "B", "AB")
TIMING_BUDGETS_MS = (15, 20, 33, 50, 100, 200, 500)
_RUN_ID = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
_TAIL_KEYS = ("msg", "detail")   # always last, may contain spaces


class ProtocolError(ValueError):
    """A device line that does not follow the protocol."""


# --------------------------------------------------------------------- settings
@dataclass(frozen=True)
class Settings:
    roi: int = 16
    tb: int = 33
    imp: int = 40
    mode: str = "short"

    def problem(self) -> str | None:
        """Same rules as validateSettings() in the firmware."""
        if not 4 <= self.roi <= 16:
            return "roi must be 4..16"
        if self.mode not in ("short", "long"):
            return "mode must be short or long"
        if self.tb not in TIMING_BUDGETS_MS or (self.tb == 15 and self.mode != "short"):
            return "tb must be 20,33,50,100,200,500 (15 in short mode only)"
        if self.imp < self.tb:
            return "imp must be >= tb"
        if self.imp > 5000:
            return "imp must be <= 5000"
        return None

    def command(self) -> str:
        bad = self.problem()
        if bad:
            raise ValueError(bad)
        return f"CFG roi={self.roi} tb={self.tb} imp={self.imp} mode={self.mode}"


MIN_RUN_MS = 100
MAX_RUN_MS = 3_600_000


def run_command(run_id: str, cond: str, dur_ms: int) -> str:
    if not _RUN_ID.match(run_id):
        raise ValueError("run id must be 1-24 chars of A-Z a-z 0-9 _ -")
    if cond not in CONDITIONS:
        raise ValueError("cond must be A, B or AB")
    if not MIN_RUN_MS <= dur_ms <= MAX_RUN_MS:
        raise ValueError("dur must be 100..3600000 ms")
    return f"RUN id={run_id} cond={cond} dur={dur_ms}"


def participates(cond: str, sensor: str) -> bool:
    return cond == "AB" or cond == sensor


# --------------------------------------------------------------------- messages
@dataclass(frozen=True)
class Reading:
    run_id: str
    sensor: str
    t_int_us: int
    t_read_us: int
    range_mm: int
    status: int
    signal_kcps: int
    ambient_kcps: int
    spads: int
    stream: int


@dataclass(frozen=True)
class RunEnd:
    run_id: str
    cond: str
    t0_us: int
    t1_us: int
    n: dict
    edges: dict
    overrun: dict
    rderr: dict
    buserr: int
    abort: str

    def problems(self) -> list[str]:
        """Reasons the run cannot be used; empty when it is acceptable."""
        out = []
        if self.abort != "none":
            out.append(f"aborted ({self.abort})")
        if self.buserr:
            out.append(f"{self.buserr} I2C errors")
        for s in SENSORS:
            if self.rderr[s]:
                out.append(f"{self.rderr[s]} failed reads on {s}")
            if not participates(self.cond, s) and self.edges[s]:
                out.append(f"stopped sensor {s} raised {self.edges[s]} interrupts")
        return out


@dataclass(frozen=True)
class Ok:
    cmd: str
    fields: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Err:
    cmd: str
    code: str
    msg: str


@dataclass(frozen=True)
class Boot:
    fw: str
    proto: int
    reset: str


@dataclass(frozen=True)
class Ready:
    pass


@dataclass(frozen=True)
class Log:
    level: str
    msg: str


@dataclass(frozen=True)
class Info:
    fields: dict


@dataclass(frozen=True)
class Status:
    state: str
    run: str
    buserr: int


@dataclass(frozen=True)
class CfgEcho:
    settings: Settings


@dataclass(frozen=True)
class Scan:
    where: str          # "main" or the channel number as a string
    addrs: tuple        # ints; empty for none
    error: bool = False


@dataclass(frozen=True)
class Test:
    name: str
    result: str         # PASS, FAIL or INFO
    detail: str


@dataclass(frozen=True)
class SelfTestDone:
    failed: int


@dataclass(frozen=True)
class TraceHead:
    sensor: str
    edges: int
    reads: int
    overflow: bool


@dataclass(frozen=True)
class TraceEdge:
    sensor: str
    level: int          # pin level after the edge: 0 after a falling edge, 1 after a rising one
    t_us: int


@dataclass(frozen=True)
class TraceRead:
    sensor: str
    t_us: int           # when the firmware had read the result and cleared the interrupt
    range_mm: int
    ambient_kcps: int
    signal_kcps: int


@dataclass(frozen=True)
class RegData:
    sensor: str
    addr: int
    data: bytes         # as read, first byte first (the chip's registers are big-endian)


Message = Union[Reading, RunEnd, Ok, Err, Boot, Ready, Log, Info, Status, CfgEcho, Scan, Test, SelfTestDone, RegData,
                 TraceHead, TraceEdge, TraceRead]


def _kv(tokens: list[str], line: str) -> dict:
    """key=value pairs; msg= and detail= take the rest of the line."""
    out = {}
    for i, tok in enumerate(tokens):
        key, sep, value = tok.partition("=")
        if not sep or not key:
            raise ProtocolError(f"expected key=value, got {tok!r} in {line!r}")
        if key in _TAIL_KEYS:
            out[key] = " ".join([value] + tokens[i + 1:])
            break
        out[key] = value
    return out


def _int(fields: dict, key: str, line: str) -> int:
    try:
        return int(fields[key])
    except (KeyError, ValueError):
        raise ProtocolError(f"missing or bad {key}= in {line!r}") from None


def parse_line(line: str) -> Message:
    line = line.rstrip("\r\n")
    tokens = line.split(" ")
    head, rest = tokens[0], tokens[1:]
    if not head:
        raise ProtocolError("empty line")

    if head == "D":
        if len(rest) != 10:
            raise ProtocolError(f"reading needs 10 fields: {line!r}")
        run_id, sensor = rest[0], rest[1]
        if sensor not in SENSORS:
            raise ProtocolError(f"bad sensor in {line!r}")
        try:
            v = [int(x) for x in rest[2:]]
        except ValueError:
            raise ProtocolError(f"non-numeric field in {line!r}") from None
        return Reading(run_id, sensor, *v)

    if head == "READY":
        return Ready()
    if head == "OK":
        if not rest:
            raise ProtocolError(f"OK without command: {line!r}")
        return Ok(rest[0], _kv(rest[1:], line))
    if head == "ERR":
        if not rest:
            raise ProtocolError(f"ERR without command: {line!r}")
        f = _kv(rest[1:], line)
        return Err(rest[0], f.get("code", "?"), f.get("msg", ""))

    kv = _kv(rest, line)
    if head == "RUNEND":
        try:
            return RunEnd(
                run_id=kv["id"], cond=kv["cond"], t0_us=_int(kv, "t0", line), t1_us=_int(kv, "t1", line),
                n={s: _int(kv, "n" + s, line) for s in SENSORS},
                edges={s: _int(kv, "edges" + s, line) for s in SENSORS},
                overrun={s: _int(kv, "overrun" + s, line) for s in SENSORS},
                rderr={s: _int(kv, "rderr" + s, line) for s in SENSORS},
                buserr=_int(kv, "buserr", line), abort=kv["abort"])
        except KeyError as e:
            raise ProtocolError(f"RUNEND missing {e} in {line!r}") from None
    if head == "BOOT":
        return Boot(kv.get("fw", "?"), _int(kv, "proto", line), kv.get("reset", "?"))
    if head == "LOG":
        return Log(kv.get("level", "?"), kv.get("msg", ""))
    if head == "INFO":
        return Info(kv)
    if head == "STATUS":
        return Status(kv.get("state", "?"), kv.get("run", "-"), _int(kv, "buserr", line))
    if head == "TRACE":
        return TraceHead(kv["sensor"], _int(kv, "edges", line), _int(kv, "reads", line), _int(kv, "overflow", line) == 1)
    if head == "TRACE_E":
        return TraceEdge(kv["sensor"], _int(kv, "level", line), _int(kv, "t", line))
    if head == "TRACE_R":
        return TraceRead(kv["sensor"], _int(kv, "t", line), _int(kv, "range", line), _int(kv, "amb", line),
                         _int(kv, "sig", line))
    if head == "REG":
        try:
            return RegData(kv["sensor"], int(kv["addr"], 16), bytes.fromhex(kv["data"]))
        except (KeyError, ValueError):
            raise ProtocolError(f"bad REG line: {line!r}") from None
    if head == "CFG":
        return CfgEcho(Settings(_int(kv, "roi", line), _int(kv, "tb", line), _int(kv, "imp", line), kv["mode"]))
    if head == "SCAN":
        where = kv.get("bus") or kv.get("ch")
        if where is None:
            raise ProtocolError(f"SCAN without bus= or ch=: {line!r}")
        raw = kv.get("addrs", "none")
        if raw == "error":
            return Scan(where, (), True)
        addrs = () if raw == "none" else tuple(int(a, 16) for a in raw.split(","))
        return Scan(where, addrs)
    if head == "TEST":
        return Test(kv.get("name", "?"), kv.get("result", "?"), kv.get("detail", ""))
    if head == "SELFTEST":
        return SelfTestDone(_int(kv, "failed", line))
    raise ProtocolError(f"unknown line type: {line!r}")
