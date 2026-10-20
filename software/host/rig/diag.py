"""Clock diagnostic: does each sensor really measure at the period it was asked for?

The firmware writes the inter-measurement period as ticks of the sensor's own oscillator, scaled by the
oscillator calibration value (register 0x00DE), and reads the setting back with the same value. If that value is
wrong, the read-back still agrees with the request while the real period is off. This command reads the raw
registers and then measures the real period from the interrupt timestamps, so the two can be compared.

It also checks for repeated readings. A sensor with a 33 ms timing budget cannot finish a new measurement every
20 ms, so if the interrupts come at half the requested period and every second reading is identical to the one
before, the sensor measures at the right period and its interrupt line fires twice per measurement.

Author: Jessica
"""
from __future__ import annotations

from . import protocol as p
from .device import Device

REG_OSC_CAL = 0x00DE        # RESULT__OSC_CALIBRATE_VAL (2 bytes)
REG_PERIOD = 0x006C         # SYSTEM__INTERMEASUREMENT_PERIOD (4 bytes)
REG_TIMEOUT_A = 0x005E      # RANGE_CONFIG__TIMEOUT_MACROP_A_HI (2 bytes)
REG_TIMEOUT_B = 0x0061      # RANGE_CONFIG__TIMEOUT_MACROP_B_HI (2 bytes)
TOLERANCE = 0.05            # real period within 5% of the request counts as right
CLOSE_MS = 5.0              # an interrupt this soon after the previous one is not a new measurement
REPEAT_LIMIT = 0.30         # more than 30% of readings identical to the previous one counts as repeated


def snapshot(dev: Device) -> dict:
    out = {}
    for s in p.SENSORS:
        osc = int.from_bytes(dev.read_regs(s, REG_OSC_CAL, 2), "big")
        out[s] = {
            "osc": osc,
            "pll": osc & 0x3FF,
            "period": int.from_bytes(dev.read_regs(s, REG_PERIOD, 4), "big"),
            "toa": int.from_bytes(dev.read_regs(s, REG_TIMEOUT_A, 2), "big"),
            "tob": int.from_bytes(dev.read_regs(s, REG_TIMEOUT_B, 2), "big"),
        }
    return out


def measure(dev: Device, run_ms: int = 3000, cond: str = "AB") -> dict:
    """Per sensor in `cond`: mean time between interrupts (ms), share of readings identical to the one before,
    and how many readings were taken."""
    stamps = {s: [] for s in p.SENSORS}
    values = {s: [] for s in p.SENSORS}

    def keep(r: p.Reading) -> None:
        stamps[r.sensor].append(r.t_int_us)
        values[r.sensor].append((r.range_mm, r.signal_kcps, r.ambient_kcps, r.spads))

    dev.run("clockchk", cond, run_ms, keep)
    out = {}
    for s in cond:
        t, v = stamps[s], values[s]
        gaps = [(b - a) / 1000.0 for a, b in zip(t, t[1:])]
        same = sum(1 for a, b in zip(v, v[1:]) if a == b)
        out[s] = {"period": (sum(gaps) / len(gaps)) if gaps else float("nan"),
                  "repeat": (same / (len(v) - 1)) if len(v) > 1 else float("nan"), "n": len(v),
                  "close": sum(1 for g in gaps if g < CLOSE_MS), "gaps": len(gaps)}
    return out


def measure_periods(dev: Device, run_ms: int = 3000) -> dict:
    return {s: m["period"] for s, m in measure(dev, run_ms).items()}


def clock_report(dev: Device, imp_ms: int = 40) -> tuple[list[str], bool]:
    """Lines to print and whether both sensors run at the requested period."""
    dev.configure(p.Settings(16, 33, imp_ms, "short"))
    before = snapshot(dev)
    meas = measure(dev)
    after = snapshot(dev)
    # the same run with one sensor at a time: tells a fault that needs both sensors ranging from one that does not
    alone = {}
    for s in p.SENSORS:
        alone.update(measure(dev, 2000, s))
    lines = [f"Requested inter-measurement period: {imp_ms} ms (timing budget 33 ms, 16x16 zone).", ""]
    ok = True
    repeated = False
    for s in p.SENSORS:
        b, a, m = before[s], after[s], meas[s]
        implied = b["period"] / (b["pll"] * 1.075) if b["pll"] else float("nan")
        ratio = m["period"] / imp_ms if imp_ms else float("nan")
        good = abs(ratio - 1.0) <= TOLERANCE
        ok &= good
        repeated |= (not good) and m["repeat"] > REPEAT_LIMIT
        lines += [
            f"Sensor {s}",
            f"  OSC_CALIBRATE_VAL (0x00DE)         before ranging 0x{b['osc']:04X} (pll {b['pll']}),"
            f" after ranging 0x{a['osc']:04X} (pll {a['pll']})",
            f"  INTERMEASUREMENT_PERIOD (0x006C)   {b['period']} ticks, reads back as {implied:.1f} ms",
            f"  TIMEOUT_MACROP_A / B (0x005E/61)   0x{b['toa']:04X} / 0x{b['tob']:04X}",
            f"  real period from the interrupts    {m['period']:.2f} ms  ({ratio:.2f} x the request)  "
            f"{'OK' if good else 'WRONG'}",
            f"  readings identical to the previous {100 * m['repeat']:.0f}% of {m['n']}",
            f"  interrupts under {CLOSE_MS:g} ms after the previous one  {m.get('close', 0)} of {m.get('gaps', 0)}",
            f"  same, sensor ranging alone         {alone[s]['period']:.2f} ms between interrupts, "
            f"{100 * alone[s]['repeat']:.0f}% identical of {alone[s]['n']}",
            "",
        ]
    if ok:
        lines.append("Both sensors run at the requested period.")
    elif repeated:
        solo_ok = all(abs(alone[s]["period"] / imp_ms - 1.0) <= TOLERANCE for s in p.SENSORS)
        lines += ["The interrupts come at the wrong period AND every second reading repeats the one before. The sensor",
                  "finishes one measurement per requested period, and the firmware counts two interrupts for each."]
        pairs = sum(meas[s].get("close", 0) for s in p.SENSORS)
        gaps = sum(meas[s].get("gaps", 0) for s in p.SENSORS)
        if gaps and pairs / gaps > 0.3:
            lines += ["Many of them come within a few milliseconds of the previous one: one falling edge is counted twice,",
                      "so the cause is in the interrupt capture, not in the sensor settings."]
        else:
            lines += ["That is a problem on the interrupt line, not in the sensor settings."]
        if solo_ok:
            lines += ["Each sensor alone is fine, so the fault only appears while both sensors range at the same time."]
        else:
            lines += ["It also happens with each sensor ranging alone."]
        lines += ["Send this whole output to Jessica."]
    else:
        lines += ["At least one sensor does not run at the requested period, and the readings are not repeats. The settings",
                  "read-back cannot see this, because it decodes the register with the same oscillator value that wrote",
                  "it. Send this whole output to Jessica."]
    return lines, ok


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else float("nan")


def edge_report(dev: Device, sensor: str = "A", imp_ms: int = 40, ms: int = 400) -> tuple[list[str], bool]:
    """What the data-ready line does at the ESP32 pin while one sensor ranges alone.

    Prints the first events as a timeline (falling edge, rising edge, and the moment the firmware had read the result
    and cleared the interrupt) and says whether the line falls once or twice per measurement."""
    dev.configure(p.Settings(16, 33, imp_ms, "short"))
    edges, reads = dev.trace(sensor, ms)
    falls = [e.t_us for e in edges if e.level == 0]
    rises = [e.t_us for e in edges if e.level == 1]
    gaps = [(b - a) / 1000.0 for a, b in zip(falls, falls[1:])]
    widths = []
    for f in falls:
        nxt = [r for r in rises if r > f]
        if nxt:
            widths.append((nxt[0] - f) / 1000.0)
    values = [(r.range_mm, r.ambient_kcps, r.signal_kcps) for r in reads]
    same = sum(1 for a, b in zip(values, values[1:]) if a == b)
    repeat = same / (len(values) - 1) if len(values) > 1 else float("nan")
    med = _median(gaps)
    lines = [f"Data-ready line of sensor {sensor} at the ESP32 pin, {ms} ms, sensor ranging alone, {imp_ms} ms requested.", ""]
    if not falls:
        return lines + ["No edges were seen at all."], False
    t0 = edges[0].t_us
    events = sorted([(e.t_us, "fall" if e.level == 0 else "rise") for e in edges]
                    + [(r.t_us, f"read and clear (range {r.range_mm} mm, ambient {r.ambient_kcps})") for r in reads])
    lines.append("First events (milliseconds after the first edge):")
    for t, what in events[:16]:
        lines.append(f"  {(t - t0) / 1000.0:9.3f}  {what}")
    lines += ["",
              f"Falling edges: {len(falls)}   median gap between them: {med:.2f} ms   "
              f"low pulse width: {_median(widths):.2f} ms",
              f"Readings identical to the previous one: {100 * repeat:.0f}% of {len(values)}"]
    half = imp_ms / 2.0
    twice = abs(med - half) <= 0.1 * half
    right = abs(med - imp_ms) <= 0.1 * imp_ms
    if right:
        lines.append("The line falls once per measurement, at the requested period. This sensor is fine.")
    elif twice and repeat > REPEAT_LIMIT:
        lines.append("The line falls twice per measurement, evenly, half a period apart, and the firmware reads the same "
                     "result both times.")
    else:
        lines.append("The line does not fall once per requested period and the pattern is not the simple double fall. "
                     "Send this whole output to Jessica.")
    run_lines, run_ok = run_path_report(dev, sensor, imp_ms)
    return lines + [""] + run_lines, right and run_ok


def run_path_report(dev: Device, sensor: str, imp_ms: int = 40, ms: int = 800) -> tuple[list[str], bool]:
    """The same pin, but the sensor is started and read exactly as in a real run (the path `regs` and every session
    use), with the pin recorded beside the run's own interrupt timestamps."""
    edges, readings = dev.trace_run(sensor, ms)
    falls = [e.t_us for e in edges if e.level == 0]
    stamps = [r.t_int_us for r in readings]
    fall_gaps = [(b - a) / 1000.0 for a, b in zip(falls, falls[1:])]
    run_gaps = [(b - a) / 1000.0 for a, b in zip(stamps, stamps[1:])]
    values = [(r.range_mm, r.signal_kcps, r.ambient_kcps, r.spads) for r in readings]
    same = sum(1 for a, b in zip(values, values[1:]) if a == b)
    repeat = same / (len(values) - 1) if len(values) > 1 else float("nan")
    lines = [f"Same sensor, started and read the way a real run does it ({ms} ms).", ""]
    if not falls or not stamps:
        return lines + ["No edges or no readings came back from the run. Send this whole output to Jessica."], False
    t0 = min(falls[0], stamps[0])
    events = sorted([(t, "pin falls") for t in falls] + [(e.t_us, "pin rises") for e in edges if e.level == 1]
                    + [(t, "run counts an interrupt") for t in stamps])
    lines.append("First events (milliseconds after the first one):")
    for t, what in events[:16]:
        lines.append(f"  {(t - t0) / 1000.0:9.3f}  {what}")
    pin_gap, run_gap = _median(fall_gaps), _median(run_gaps)
    lines += ["",
              f"Pin falls: {len(falls)}   median gap {pin_gap:.2f} ms",
              f"Interrupts the run counted: {len(stamps)}   median gap {run_gap:.2f} ms   "
              f"readings identical to the previous one: {100 * repeat:.0f}%"]
    def near(x, target):
        return abs(x - target) <= 0.1 * target
    pin_right, pin_twice = near(pin_gap, imp_ms), near(pin_gap, imp_ms / 2.0)
    run_right, run_twice = near(run_gap, imp_ms), near(run_gap, imp_ms / 2.0)
    if pin_right and run_right:
        lines.append("Started like a real run, the pin falls once per measurement and the run counts one interrupt each.")
        return lines, True
    if pin_right and run_twice:
        lines.append("The pin falls once per measurement, but the run counts two interrupts for each. The wiring is fine: "
                     "the fault is in how the firmware captures the interrupt.")
    elif pin_twice:
        lines.append("Started like a real run, the pin itself falls twice per measurement. The sensor does this after "
                     "the run start sequence, so the cause is in the start-up, not in the capture.")
    else:
        lines.append("The pattern does not match either case. Send this whole output to Jessica.")
    return lines, False
