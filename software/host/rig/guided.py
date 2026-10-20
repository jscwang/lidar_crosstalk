"""Guided operator: watches the target position and squareness live, shows when the setting is right, then
lets the run start by itself.

At every physical change the session asks its operator to set the rig. This operator prints what to change,
waits for the pucks to be set (one Enter, or a timed wait, because the ranges do not change with the puck
angle and the software cannot see a pin move), then reads both sensors every couple of seconds and checks
three things until they hold for a few readings in a row:

  * both 16x16 ranges are near the range expected at that distance (cfg.expected_range_mm, else the nominal
    distance), within cfg.range_tol_mm. A distance may carry an angle table instead of one number, because a
    turned sensor reads a little longer once the nearest part of the target leaves the middle of its field;
  * B minus A is near cfg.square_offset_mm, the value measured once with a target squared by hand, within
    cfg.square_tol_mm. The line also prints the tilt this implies: the sensors are 20 mm apart, so 1 mm of
    unexpected difference is about 3 degrees of tilt;
  * the hardware self-test passes (catches a wire disturbed by the handling).

While it waits it says what to do ("target 27 mm too far", "turn the target so the edge on puck B's side comes
closer"). If the firmware has the LED command, a green LED lights when everything is right and a red one while
it is not, so the person at the target does not need to see the screen. Then it returns, and the run starts.

Author: Jessica
"""
from __future__ import annotations

import math
import os
import sys
import time
from typing import Callable, Optional

from . import protocol as p
from .device import Device, DeviceError

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def _between(table: dict, x: float) -> float:
    """The table's value at x, read straight between its two nearest points and held flat outside them."""
    points = sorted(table.items())
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


class GuidedOperator:
    OK_NEEDED = 3           # consecutive good readings before the setting is accepted

    def __init__(self, device: Device, cfg, out=None, color: bool = True, angle_wait="enter",
                 on_change: Optional[Callable] = None, on_poll: Optional[Callable] = None,
                 sleep: Callable = time.sleep, input_fn: Callable = input, check_ms: int = 2000,
                 selftest_after: bool = True, max_polls: Optional[int] = None):
        self.dev = device
        self.cfg = cfg
        self.out = out or sys.stdout
        self.color = color
        self.angle_wait = angle_wait          # "enter", a number of seconds, or None for no wait
        self.on_change = on_change            # simulation and tests: applies the physical change
        self.on_poll = on_poll                # simulation and tests: called after every reading
        self.sleep = sleep
        self.input_fn = input_fn
        self.check_ms = check_ms
        self.selftest_after = selftest_after
        self.max_polls = max_polls
        self.first = True
        self.last_theta: Optional[float] = None
        self.has_led = True
        if color and os.name == "nt":
            os.system("")                     # switches on ANSI colours in the Windows console

    # ------------------------------------------------------------------ output
    def _c(self, text: str, code: str) -> str:
        return f"{code}{text}{RESET}" if self.color else text

    def _say(self, text: str = "") -> None:
        print(text, file=self.out, flush=True)

    def notify(self, message: str) -> None:
        self._say(f"  {message}")

    def _led(self, state: str) -> None:
        if not self.has_led:
            return
        try:
            self.has_led = self.dev.led(state)
        except DeviceError:
            pass

    # ------------------------------------------------------------------ the Operator interface
    def setup(self, distance_m: float, theta_deg: float, new_distance: bool) -> Optional[float]:
        angle_changed = self.first or theta_deg != self.last_theta
        self._say()
        if new_distance:
            self._say(f"ACTION: target to {distance_m:.2f} m, square.")
        if angle_changed:
            self._say(f"ACTION: pucks A -{theta_deg:g} deg, B +{theta_deg:g} deg")
            self._say("        (dtheta {:g}). Check with the gauge.".format(2 * theta_deg))
        if self.on_change:
            self.on_change(distance_m, theta_deg)
        if angle_changed:
            self._wait_for_pucks()
        self._wait_for_geometry(distance_m, theta_deg)
        self.first = False
        self.last_theta = theta_deg
        return None

    # ------------------------------------------------------------------ steps
    def _wait_for_pucks(self) -> None:
        w = self.angle_wait
        if w in (None, 0, "0"):
            return
        if w == "enter":
            self.input_fn("Press Enter when the pucks are set: ")
            return
        secs = int(w)
        for left in range(secs, 0, -1):
            self._say(f"  pucks: {left} s left to set them")
            self.sleep(1)

    def expected(self, distance_m: float, theta_deg: float = 0.0) -> float:
        """The range to aim for at this distance, and at this puck angle if the config gives an angle table."""
        for d, value in self.cfg.expected_range_mm.items():
            if abs(d - distance_m) < 1e-6:
                return value if not isinstance(value, dict) else _between(value, abs(theta_deg))
        return distance_m * 1000.0

    def tilt_deg(self, a: float, b: float, theta_deg: float = 0.0) -> float:
        """Target tilt implied by B minus A, in degrees.

        The sensors are cfg.spacing_mm apart and turned by theta, so the difference a tilt produces grows with
        the angle: about 0.35 mm per degree straight ahead, 1.8 at 10 degrees per side and 6.8 at 30, from the
        range model r * (1/cos(theta - phi) - 1/cos(theta + phi)). The sensitivity is used at the given angle.
        At 0 degrees this reduces to the spacing term, so the value is only an estimate away from 0."""
        off = (b - a) - self.cfg.square_offset_mm
        th = math.radians(abs(theta_deg))
        if th < 1e-6:
            return math.degrees(math.atan2(off, self.cfg.spacing_mm))
        mm_per_rad = 2.0 * ((a + b) / 2.0) * math.sin(th) / math.cos(th) ** 2
        return math.degrees(off / mm_per_rad)

    def _measure(self):
        """Mean valid 16x16 range of A and B, or (None, None).

        Each sensor ranges alone. With both ranging, the other sensor's light shifts the reported range, by
        0.4 mm on the local rig and by about 3 mm on one other rig, and it comes and goes with the beat between
        the two measurement periods, so a reading taken with both running is no use for setting the geometry."""
        got = {"A": [], "B": []}

        def keep(r: p.Reading) -> None:
            if r.status == 0:
                got[r.sensor].append(r.range_mm)

        half = max(p.MIN_RUN_MS, self.check_ms // 2)
        self.dev.run("guideA", "A", half, keep)
        self.dev.run("guideB", "B", half, keep)
        if not got["A"] or not got["B"]:
            return None, None
        return sum(got["A"]) / len(got["A"]), sum(got["B"]) / len(got["B"])

    def judge(self, a: float, b: float, expected_mm: float, theta_deg: float = 0.0):
        """(ok, [what to change]) for the readings of sensors A and B."""
        tol, sq = self.cfg.range_tol_mm, self.cfg.square_tol_mm
        todo = []
        mean_dev = ((a - expected_mm) + (b - expected_mm)) / 2
        if abs(mean_dev) > tol:
            todo.append(f"{abs(mean_dev):.0f} mm too {'far: move it closer' if mean_dev > 0 else 'close: move it back'}")
        diff = (b - a) - self.cfg.square_offset_mm
        if abs(diff) > sq:
            side = "closer" if diff > 0 else "farther away"
            todo.append(f"tilt {self.tilt_deg(a, b, theta_deg):+.1f} deg: turn target, B-side edge {side}")
        return not todo, todo

    def _wait_for_geometry(self, distance_m: float, theta_deg: float = 0.0) -> None:
        self.dev.configure(p.Settings(16, self.cfg.tb_ms, self.cfg.imp_ms, self.cfg.mode))
        exp = self.expected(distance_m, theta_deg)
        self._say(f"Aim: A and B near {exp:.0f} mm, B-A near {self.cfg.square_offset_mm:+.0f} mm "
                  f"(within {self.cfg.square_tol_mm:g} mm).")
        if not self.cfg.expected_range_mm:
            self._say("(nominal distance: set expected_range_mm in the config)")
        good, polls = 0, 0
        self._led("bad")
        while True:
            try:
                a, b = self._measure()
            except DeviceError as e:
                self._say(self._c(f"  device: {e}", RED))
                self._led("bad")
                good = 0
                self.sleep(1)
                a = b = None
            polls += 1
            if a is not None:
                ok, todo = self.judge(a, b, exp, theta_deg)
                good = good + 1 if ok else 0
                head = f"  A {a:4.0f}  B {b:4.0f}  B-A {b - a:+3.0f}  tilt {self.tilt_deg(a, b, theta_deg):+4.1f}d"
                if ok:
                    self._say(self._c(f"{head}  OK ({good}/{self.OK_NEEDED})", GREEN))
                else:
                    self._say(self._c(f"{head}  {todo[0]}", YELLOW))
                    for extra in todo[1:]:
                        self._say(self._c(f"{' ' * 24}{extra}", YELLOW))
                self._led("ok" if ok else "bad")
            else:
                if a is None and good:
                    good = 0
                self._say(self._c("  no valid readings: target in front of both?", YELLOW))
                self._led("bad")
            if self.on_poll:
                self.on_poll(polls)
            if good >= self.OK_NEEDED:
                if self.selftest_after and not self._selftest_passes():
                    good = 0
                    self._led("bad")
                    continue
                break
            if self.max_polls is not None and polls >= self.max_polls:
                self._led("off")
                raise TimeoutError("the setting was not right within the allowed time")
        self._say(self._c("READY: setting is right, starting the run.", GREEN))
        self._led("ok")

    def _selftest_passes(self) -> bool:
        failed, tests = self.dev.selftest()
        if not failed:
            return True
        self._say(self._c(f"  self-test failed {failed} check(s), fix and it goes on:", RED))
        for t in tests:
            if t.result == "FAIL":
                self._say(self._c(f"    {t.name}: {t.detail}", RED))
        return False
