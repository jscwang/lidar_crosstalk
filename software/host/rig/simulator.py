"""Simulated rig: speaks protocol v1 with a simple physical crosstalk model.

Used by the tests and by `rig simulate` to exercise the whole host pipeline
(session, logging, analysis, figures) without hardware. Runs complete in
virtual time, so a 30 s run costs milliseconds.

The model is deliberately simple. It exists to check that the software
recovers a known answer, not to predict the real sensors:

* overlap(dtheta) = 1 / (1 + exp((dtheta - x_c) / w)), with x_c from the same
  geometry as the prediction but using the simulator's own "true" emitter cone;
* while the other sensor emits, overlap drives extra ambient, extra range
  noise, a small bias and dropouts, modulated by a slow drift in the relative
  phase of the two sensors' pulses.

Author: Jessica
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from . import geometry
from . import protocol as p


@dataclass
class Physics:
    d_m: float = 0.30
    theta_deg: float = 0.0              # per side; dtheta = 2 * theta
    spacing_m: float = 0.020
    true_emitter_cone_deg: float = 27.0
    true_receive_field_deg: dict = field(default_factory=lambda: {16: 27.0, 4: 15.0})
    falloff_deg: float = 1.5
    ambient_full_kcps: float = 450.0
    xtalk_ambient_full_kcps: float = 2500.0
    range_sd_mm: float = 1.5
    drift_period_s: float = 6.0
    osc_error: tuple = (0.004, -0.006)  # per-sensor inter-measurement clock error

    def receive_field(self, roi: int) -> float:
        if roi in self.true_receive_field_deg:
            return self.true_receive_field_deg[roi]
        lo, hi = self.true_receive_field_deg[4], self.true_receive_field_deg[16]
        return lo + (hi - lo) * (roi - 4) / 12.0

    def crossover(self, roi: int) -> float:
        return geometry.crossover_deg(self.receive_field(roi), self.d_m, self.spacing_m,
                                      self.true_emitter_cone_deg)

    def overlap(self, roi: int) -> float:
        x = 2 * self.theta_deg - self.crossover(roi)
        return 1.0 / (1.0 + math.exp(x / self.falloff_deg))

    def true_x10(self, roi: int) -> float:
        """dtheta where the mean crosstalk effect falls to 10% of its value at 0."""
        xc, w = self.crossover(roi), self.falloff_deg
        return xc + w * math.log(10 * (1 + math.exp(-xc / w)) - 1)


class SimulatedDevice:
    FW = "sim-1.0.0"

    def __init__(self, physics: Optional[Physics] = None, seed: int = 1):
        self.physics = physics or Physics()
        self.rng = random.Random(seed)
        self.now_us = 5_000_000
        self.settings: Optional[p.Settings] = None
        self.stream = [0, 0]
        self.ambient_drift = 0.0          # slow room-light drift, fraction
        self.faults: dict[str, set] = {}  # kind -> run ids (or {"*"})
        self.runs_started: list[str] = []
        self.led = "off"
        self.double_int = False   # test hook: the data-ready line fires twice per measurement
        self.isr_double = False   # test hook: the pin falls once, but the firmware's capture counts each edge twice

    # ---------------------------------------------------------------- faults
    def inject(self, kind: str, run_ids) -> None:
        """kinds: stray, i2c, reset, ambient_jump, missed, settings_lost."""
        self.faults.setdefault(kind, set()).update(run_ids)

    def _fault(self, kind: str, run_id: str) -> bool:
        ids = self.faults.get(kind, set())
        if run_id in ids:
            ids.discard(run_id)   # one-shot per run id
            return True
        return "*" in ids

    # ---------------------------------------------------------------- protocol
    def boot_lines(self) -> list[str]:
        return [f"BOOT fw={self.FW} board=sim proto=1 reset=poweron", "READY"]

    def handle(self, line: str) -> list[str]:
        name = line.split(" ", 1)[0]
        try:
            return self._dispatch(name, line)
        except ValueError as e:
            return [f"ERR {name} code=bad_args msg={e}"]

    def _dispatch(self, name: str, line: str) -> list[str]:
        kv = dict(t.split("=", 1) for t in line.split(" ")[1:] if "=" in t)
        if name == "PING":
            return ["OK PING"]
        if name == "INFO":
            s = self.settings or p.Settings()
            return [f"INFO fw={self.FW} board=sim proto=1 sda=8 scl=9 i2c_hz=400000 mux=0x70 chA=0 chB=1 intA=4 intB=5 "
                    f"readyA=1 readyB=1 centreA=199 centreB=199 verified={int(self.settings is not None)} "
                    f"roi={s.roi} tb={s.tb} imp={s.imp} mode={s.mode}", "OK INFO"]
        if name == "STATUS":
            return ["STATUS state=idle run=- buserr=0", "OK STATUS"]
        if name == "SCAN":
            out = ["SCAN bus=main addrs=70"]
            out += [f"SCAN ch={c} addrs={'29' if c in (0, 1) else 'none'}" for c in range(8)]
            return out + ["OK SCAN"]
        if name == "STOPALL":
            return ["OK STOPALL"]
        if name == "TRACE":
            if self.settings is None:
                return ["ERR TRACE code=not_ready msg=send CFG first"]
            sensor, ms = kv.get("sensor"), int(kv.get("ms", "0"))
            if sensor not in ("A", "B") or not 50 <= ms <= 3000:
                raise ValueError("TRACE needs sensor=A|B ms=50..3000")
            if kv.get("path") == "run":
                return self._trace_run(sensor, ms)
            period = self.settings.imp * 1000
            t0 = self.now_us
            edges, reads = [], []
            k = 0
            while k * period < ms * 1000:
                fall = t0 + k * period + 20_000
                value = (1500 + k, 400 + k % 7, 20000 + k % 11)      # one measurement
                for extra in ((0, period // 2) if self.double_int else (0,)):
                    edges.append((fall + extra, 0))
                    reads.append((fall + extra + 300,) + value)       # a repeated interrupt reads the same value again
                    edges.append((fall + extra + 900, 1))
                k += 1
            out = [f"TRACE sensor={sensor} edges={len(edges)} reads={len(reads)} overflow=0"]
            out += [f"TRACE_E sensor={sensor} level={lvl} t={t}" for t, lvl in edges]
            out += [f"TRACE_R sensor={sensor} t={t} range={r} amb={a} sig={g}" for t, r, a, g in reads]
            return out + ["OK TRACE"]
        if name == "REG":
            try:
                addr, n = int(kv["addr"], 0), int(kv["len"])
            except (KeyError, ValueError):
                raise ValueError("REG needs exactly sensor= addr= len=")
            if kv.get("sensor") not in ("A", "B") or not 1 <= n <= 16:
                raise ValueError("REG needs sensor=A|B and len 1..16")
            osc = 0x0A3C if kv["sensor"] == "A" else 0x0A4B      # a plausible oscillator calibration value
            blocks = {0x00DE: osc.to_bytes(2, "big"), 0x006C: int(osc * 40 * 1.075).to_bytes(4, "big"),
                      0x005E: (0x0600).to_bytes(2, "big"), 0x0061: (0x0900).to_bytes(2, "big")}
            data = (blocks.get(addr, b"") + bytes(16))[:n]
            return [f"REG sensor={kv['sensor']} addr=0x{addr:04X} data={data.hex().upper()}", "OK REG"]
        if name == "LED":
            if kv.get("state") not in ("ok", "bad", "off"):
                raise ValueError("LED needs exactly state=ok|bad|off")
            self.led = kv["state"]
            return ["OK LED"]
        if name == "ABORT":
            return ["OK ABORT"]
        if name == "CFG":
            try:
                s = p.Settings(int(kv["roi"]), int(kv["tb"]), int(kv["imp"]), kv["mode"])
            except (KeyError, ValueError):
                raise ValueError("CFG needs exactly roi= tb= imp= mode=")
            if s.problem():
                raise ValueError(s.problem())
            self.settings = s
            return [f"CFG roi={s.roi} tb={s.tb} imp={s.imp} mode={s.mode}", "OK CFG"]
        if name == "SELFTEST":
            if self.settings is None:
                return ["ERR SELFTEST code=not_ready msg=send CFG first"]
            tests = ["mux_present", "mux_select_A", "mux_select_B", "sensor_id_A", "boot_A", "settings_A",
                     "sensor_id_B", "boot_B", "settings_B", "run_A_A", "run_B_B", "run_AB_A", "run_AB_B",
                     "stop_quiet", "int_idle_A", "int_idle_B", "i2c_errors"]
            return [f"TEST name={t} result=PASS detail=simulated" for t in tests] + \
                   ["SELFTEST failed=0", "OK SELFTEST"]
        if name == "RUN":
            if self.settings is None:
                return ["ERR RUN code=not_ready msg=send CFG first"]
            if self._fault("settings_lost", kv.get("id", "")):
                self.settings = None   # as the firmware does after a failed read-back
                return ["ERR RUN code=verify msg=sensor B: settings changed since CFG (power loss?); "
                        "send CFG again"]
            p.run_command(kv.get("id", ""), kv.get("cond", ""), int(kv.get("dur", "0")))   # validates
            return self._run(kv["id"], kv["cond"], int(kv["dur"]))
        return [f"ERR {name} code=unknown_cmd msg=unknown command"]

    def _trace_run(self, sensor: str, ms: int) -> list[str]:
        """A real run of one sensor with the pin recorded beside it (TRACE path=run)."""
        lines = self._run("edgetrace", sensor, max(ms, 100))
        readings = [ln for ln in lines if ln.startswith("D ")]
        period = self.settings.imp * 1000
        out, edges = [], []
        for ln in readings:
            f = ln.split(" ")
            t_int, t_read = int(f[3]), int(f[4])
            doubled = (0, period // 2) if self.double_int else (0,)
            for extra in doubled:
                edges += [(t_int + extra, 0), (t_int + extra + 700, 1)]
            for extra in ((0, period // 2) if (self.double_int or self.isr_double) else (0,)):
                f2 = list(f)
                f2[3], f2[4] = str(t_int + extra), str(t_read + extra)
                out.append(" ".join(f2))
        edges.sort()
        end = [ln for ln in lines if ln.startswith("RUNEND")]
        return (out + end + [f"TRACE sensor={sensor} edges={len(edges)} reads=0 overflow=0"]
                + [f"TRACE_E sensor={sensor} level={lvl} t={t}" for t, lvl in edges] + ["OK TRACE"])

    # ---------------------------------------------------------------- physics
    def _run(self, run_id: str, cond: str, dur_ms: int) -> list[str]:
        self.runs_started.append(run_id)
        s, ph, rng = self.settings, self.physics, self.rng
        out = [f"OK RUN id={run_id}"]
        if self._fault("reset", run_id):
            self.settings = None
            return out + self.boot_lines()

        self.ambient_drift += rng.gauss(0, 0.01)
        jump = 0.3 if self._fault("ambient_jump", run_id) else 0.0
        t0 = self.now_us + 50_000
        end = t0 + dur_ms * 1000
        roi_frac = max(0.1, (s.roi / 16) ** 2)
        overlap = ph.overlap(s.roi)
        phase = rng.uniform(0, 2 * math.pi)
        n = {"A": 0, "B": 0}
        edges = {"A": 0, "B": 0}
        events = []
        for i, sensor in enumerate(p.SENSORS):
            if not p.participates(cond, sensor):
                continue
            period = s.imp * 1000 * (1 + ph.osc_error[i])
            t = t0 + s.tb * 1000 + rng.uniform(0, 2000)
            while t < end:
                events.append((int(t), sensor))
                t += period
        events.sort()
        stray = self._fault("stray", run_id)
        i2c = self._fault("i2c", run_id)
        missed = self._fault("missed", run_id)
        lines = []
        for k, (t, sensor) in enumerate(events):
            idx = 0 if sensor == "A" else 1
            edges[sensor] += 1
            self.stream[idx] = 1   # the real chip reports 1 every time in timed ranging
            if missed and k == len(events) // 2:
                continue   # a reading the host never received: leaves a 2-period gap
            other_on = cond == "AB"
            drift = 0.5 + 0.5 * math.cos(2 * math.pi * (t - t0) / 1e6 / ph.drift_period_s + phase)
            x = overlap * drift if other_on else 0.0
            ambient = (ph.ambient_full_kcps * (1 + self.ambient_drift + jump) * (1 + rng.gauss(0, 0.03))
                       + ph.xtalk_ambient_full_kcps * x) * roi_frac
            signal = 9000 * (0.3 / ph.d_m) ** 2 * roi_frac * (1 + rng.gauss(0, 0.05))
            spads = int(round(190 * roi_frac * (0.8 if ph.d_m > 0.5 else 1)))
            if rng.random() < 0.002 + 0.25 * x:
                status, rng_mm = rng.choice((2, 4, 7)), rng.randint(0, 4000)
            else:
                status = 0
                rng_mm = int(round(ph.d_m * 1000 + 4 * x + rng.gauss(0, ph.range_sd_mm * (1 + 2 * x))))
            lines.append(f"D {run_id} {sensor} {t} {t + 900} {max(rng_mm, 0)} {status} "
                         f"{int(signal)} {int(ambient)} {spads} {self.stream[idx]}")
            n[sensor] += 1
        abort = "none"
        buserr = 0
        rderr = {"A": 0, "B": 0}
        t1 = end
        if stray:
            other = "B" if cond == "A" else "A"
            edges[other] = 1
            cut = len(lines) // 3
            lines = lines[:cut]
            n = {q: sum(1 for ln in lines if ln.split(" ")[2] == q) for q in p.SENSORS}
            abort, t1 = "stray", events[cut][0] if cut < len(events) else end
        elif i2c:
            buserr = 3
            first = events[0][1]
            rderr[first] = 3
            lines = lines[:10]
            n = {q: sum(1 for ln in lines if ln.split(" ")[2] == q) for q in p.SENSORS}
            abort = "i2c"
            t1 = events[12][0] if len(events) > 12 else end
        self.now_us = t1 + 200_000
        out += lines
        out.append(f"RUNEND id={run_id} cond={cond} t0={t0} t1={t1} nA={n['A']} nB={n['B']} "
                   f"edgesA={edges['A']} edgesB={edges['B']} overrunA=0 overrunB=0 "
                   f"rderrA={rderr['A']} rderrB={rderr['B']} buserr={buserr} abort={abort}")
        return out


class SimOperator:
    """Stands in for the person at the bench: applies each setup to the model."""

    def __init__(self, device: SimulatedDevice, room_temp_c: float = 22.0):
        self.device = device
        self.room_temp_c = room_temp_c
        self.setups: list[tuple] = []
        self.messages: list[str] = []

    def setup(self, distance_m: float, theta_deg: float, new_distance: bool) -> float:
        self.device.physics.d_m = distance_m
        self.device.physics.theta_deg = theta_deg
        self.setups.append((distance_m, theta_deg, new_distance))
        return self.room_temp_c

    def notify(self, message: str) -> None:
        self.messages.append(message)


class SimTransport:
    """In-process transport to a SimulatedDevice."""

    def __init__(self, device: Optional[SimulatedDevice] = None, boot: bool = True):
        self.device = device or SimulatedDevice()
        self.queue: deque[str] = deque(self.device.boot_lines() if boot else [])
        self.sent: list[str] = []

    def write_line(self, line: str) -> None:
        self.sent.append(line)
        self.queue.extend(self.device.handle(line))

    def read_line(self, timeout: float) -> Optional[str]:
        return self.queue.popleft() if self.queue else None

    def close(self) -> None:
        pass
