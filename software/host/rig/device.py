"""Client for the rig firmware: commands, replies, runs, and fault detection.

Author: Jessica
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from . import protocol as p

log = logging.getLogger("rig.device")


class DeviceError(RuntimeError):
    """The device refused a command or answered unexpectedly."""

    def __init__(self, msg: str, code: str = ""):
        super().__init__(msg)
        self.code = code


class DeviceReset(DeviceError):
    """A BOOT line arrived: the ESP32 reset (brownout, crash or cable)."""

    def __init__(self, boot: p.Boot):
        super().__init__(f"device reset (reason: {boot.reset})", "reset")
        self.boot = boot


class DeviceTimeout(DeviceError):
    pass


class Device:
    def __init__(self, transport, reply_timeout: float = 3.0):
        self.t = transport
        self.reply_timeout = reply_timeout
        self.info: dict = {}
        self.logs: list[p.Log] = []

    # ------------------------------------------------------------------ basics
    def _next(self, timeout: float) -> Optional[p.Message]:
        """Next protocol message; LOG lines are recorded, noise is skipped."""
        while True:
            line = self.t.read_line(timeout)
            if line is None:
                return None
            if not line.strip():
                continue
            try:
                msg = p.parse_line(line)
            except p.ProtocolError as e:
                # Boot ROM text at reset is not protocol; note it and carry on.
                log.warning("unparsed line: %s", e)
                continue
            if isinstance(msg, p.Log):
                self.logs.append(msg)
                (log.error if msg.level == "E" else log.info)("device: %s", msg.msg)
                continue
            return msg

    def command(self, line: str, timeout: Optional[float] = None, allow_boot: bool = False) -> list:
        """Sends one command and returns every message up to its OK.

        Raises DeviceError on ERR and DeviceReset if the device reboots.
        """
        name = line.split(" ", 1)[0]
        self.t.write_line(line)
        got = []
        timeout = self.reply_timeout if timeout is None else timeout
        while True:
            msg = self._next(timeout)
            if msg is None:
                raise DeviceTimeout(f"no reply to {name} within {timeout:.1f} s", "timeout")
            if isinstance(msg, p.Boot) and not allow_boot:
                raise DeviceReset(msg)
            if isinstance(msg, p.Err) and msg.cmd in (name, "?"):
                raise DeviceError(f"{name} refused: {msg.code}: {msg.msg}", msg.code)
            if isinstance(msg, p.Ok) and msg.cmd == name:
                return got
            got.append(msg)

    def _drain(self, limit_s: float) -> bool:
        """Reads until the line goes quiet. False if it was still talking after limit_s."""
        t0 = time.monotonic()
        while self._next(0.3) is not None:
            if time.monotonic() - t0 > limit_s:
                return False
        return True

    def connect(self, attempts: int = 5) -> dict:
        """Waits for the firmware to answer PING, then reads INFO."""
        # Drain whatever is buffered (BOOT, READY, boot ROM text). A board that is still
        # streaming readings never goes quiet: an earlier host died mid-run and the run is
        # still going. Stop it instead of waiting for it (a warm-up run is ten minutes).
        if not self._drain(2.0):
            log.warning("board is still streaming: stopping a run left over from an earlier host")
            # Not command(): it has no overall deadline, and a board that keeps streaming would
            # hold it forever. Send both, then drain (OK, ERR and RUNEND lines are just noise
            # here) with a hard limit.
            self.t.write_line("ABORT")
            self.t.write_line("STOPALL")
            if not self._drain(5.0):
                raise DeviceError("the board keeps streaming after ABORT: press RST on it and retry",
                                  "busy")
        for i in range(attempts):
            try:
                self.command("PING", timeout=1.0, allow_boot=True)
                break
            except DeviceTimeout:
                if i == attempts - 1:
                    raise
        infos = [m for m in self.command("INFO") if isinstance(m, p.Info)]
        if not infos:
            raise DeviceError("INFO returned nothing")
        self.info = infos[0].fields
        proto = int(self.info.get("proto", -1))
        if proto != p.PROTOCOL_VERSION:
            raise DeviceError(f"firmware speaks protocol {proto}, host speaks {p.PROTOCOL_VERSION}")
        return self.info

    # ------------------------------------------------------------------ commands
    def status(self) -> p.Status:
        return next(m for m in self.command("STATUS") if isinstance(m, p.Status))

    def scan(self) -> dict:
        return {m.where: (None if m.error else m.addrs)
                for m in self.command("SCAN", timeout=5.0) if isinstance(m, p.Scan)}

    def configure(self, s: p.Settings) -> p.Settings:
        echo = [m for m in self.command(s.command(), timeout=5.0) if isinstance(m, p.CfgEcho)]
        if not echo or echo[0].settings != s:
            raise DeviceError(f"CFG echo {echo[0].settings if echo else None} does not match {s}", "verify")
        return echo[0].settings

    def selftest(self) -> tuple[int, list[p.Test]]:
        msgs = self.command("SELFTEST", timeout=30.0)
        tests = [m for m in msgs if isinstance(m, p.Test)]
        done = [m for m in msgs if isinstance(m, p.SelfTestDone)]
        if not done:
            raise DeviceError("SELFTEST ended without a summary")
        return done[0].failed, tests

    def stop_all(self) -> None:
        self.command("STOPALL")

    def read_regs(self, sensor: str, addr: int, n: int) -> bytes:
        """Raw register read of one sensor (diagnostics only). Needs a firmware with the REG command."""
        got = [m for m in self.command(f"REG sensor={sensor} addr=0x{addr:04X} len={n}", timeout=2.0)
               if isinstance(m, p.RegData)]
        if not got:
            raise DeviceError("REG returned no data")
        return got[0].data

    def trace(self, sensor: str, ms: int = 400) -> tuple[list, list]:
        """Both edges of one sensor's data-ready line while it ranges alone, and the results read from it.
        Returns (edges, reads). Needs the settings applied first (configure)."""
        msgs = self.command(f"TRACE sensor={sensor} ms={ms}", timeout=ms / 1000.0 + 5.0)
        return ([m for m in msgs if isinstance(m, p.TraceEdge)], [m for m in msgs if isinstance(m, p.TraceRead)])

    def trace_run(self, sensor: str, ms: int = 800) -> tuple[list, list]:
        """A real run of one sensor alone (the production path) with the pin recorded beside it.
        Returns (edges, readings): the readings carry the run's own interrupt timestamps."""
        msgs = self.command(f"TRACE sensor={sensor} ms={ms} path=run", timeout=ms / 1000.0 + 8.0)
        return ([m for m in msgs if isinstance(m, p.TraceEdge)], [m for m in msgs if isinstance(m, p.Reading)])

    def led(self, state: str) -> bool:
        """Sets the status lights: ok (green), bad (red) or off. False on a firmware without the command."""
        if state not in ("ok", "bad", "off"):
            raise ValueError("state must be ok, bad or off")
        try:
            self.command(f"LED state={state}", timeout=1.0)
            return True
        except DeviceError as e:
            if e.code == "unknown_cmd":
                return False
            raise

    def abort(self) -> None:
        self.command("ABORT", timeout=5.0)

    def run(self, run_id: str, cond: str, dur_ms: int,
            on_reading: Callable[[p.Reading], Optional[bool]], margin_s: float = 5.0) -> p.RunEnd:
        """Runs one condition and streams every reading to `on_reading`.

        If `on_reading` returns True the run is stopped there (an ABORT is sent) and the RUNEND summary of the
        shortened run is returned: this is how a run ends after a fixed number of readings.

        Returns the RUNEND summary. If the device goes quiet for longer than
        the run plus `margin_s`, the run is aborted and DeviceTimeout raised.
        """
        self.command(p.run_command(run_id, cond, dur_ms))
        quiet_limit = dur_ms / 1000.0 + margin_s
        stopping = False
        while True:
            msg = self._next(quiet_limit)
            if msg is None:
                try:
                    self.abort()
                finally:
                    raise DeviceTimeout(f"run {run_id}: no RUNEND", "timeout")
            if isinstance(msg, p.Boot):
                raise DeviceReset(msg)
            if isinstance(msg, p.Reading):
                if msg.run_id != run_id:
                    raise DeviceError(f"reading for run {msg.run_id} during run {run_id}")
                if on_reading(msg) and not stopping:
                    stopping = True
                    self.t.write_line("ABORT")
            elif isinstance(msg, p.RunEnd):
                if msg.run_id != run_id:
                    raise DeviceError(f"RUNEND for {msg.run_id} during run {run_id}")
                if stopping:
                    self._drain_abort_reply()
                return msg
            elif isinstance(msg, p.Ok) and msg.cmd == "ABORT" and stopping:
                continue
            else:
                log.warning("unexpected message during run: %r", msg)

    def _drain_abort_reply(self) -> None:
        """After a stop requested mid-run, the board answers OK ABORT right behind the RUNEND: take it off the line so
        it is not mistaken for the reply to the next command."""
        for _ in range(5):
            msg = self._next(1.0)
            if msg is None or (isinstance(msg, p.Ok) and msg.cmd == "ABORT"):
                return
