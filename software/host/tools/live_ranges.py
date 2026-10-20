"""
Live range readout for squaring the target: prints one line every --average seconds with the mean 16x16 range
of sensor A and sensor B, their difference and the target tilt that difference implies. It stops by itself
after --seconds (default 600; Ctrl+C also stops it, and it holds the serial port until then).

    python tools/live_ranges.py 288 --port COM5

The number is the range you expect at this distance. The line says OK when both sensors are within --tol of
it and the difference is within --square of --offset.

Each sensor ranges alone, one after the other. With both ranging, the other sensor's light shifts the reported
range, and it comes and goes with the beat between the two measurement periods, so the number jumps between two
values and is no use for setting the geometry. Pass --both to range them together and see that for yourself.

Squaring the target: with the pucks straight ahead the sensors barely feel a tilt, because it reaches them only
through their 20 mm spacing, about 0.35 mm of B minus A per degree. Turned pucks are far more sensitive, because
each sensor then looks along a slanted path to the plane: about 1.8 mm per degree at 10 degrees per side, 3.9 at
20 and 6.8 at 30. So set the target square with the tape, measuring from one straight reference to each end of the
board and making the two equal (over a 1.2 m board, 10 mm out is half a degree), then read the tilt here with the
pucks at the largest angle, where the sensors can see it.

The two sensors have their own range offsets, and these are larger than the tilt signal: one pair read 8 mm
apart on a target that was square. So a square target does not read B minus A of zero. Measure that difference
once with a target squared by the tape and pass it as --offset (and put it in the config as square_offset_mm).
Until that is done the tilt column means nothing.

Author: Jessica
"""
import argparse
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rig import protocol as p
from rig.device import Device
from rig.transport import SerialTransport


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("expected_mm", type=float, nargs="?", default=800.0)
    ap.add_argument("--port", default="COM4")
    ap.add_argument("--seconds", type=float, default=600.0, help="stop by itself after this many seconds")
    ap.add_argument("--average", type=float, default=2.0, help="seconds averaged into each line")
    ap.add_argument("--tol", type=float, default=12.0, help="how far each range may be from expected_mm")
    ap.add_argument("--square", type=float, default=8.0, help="how far B minus A may be from --offset")
    ap.add_argument("--offset", type=float, default=0.0, help="B minus A measured with a squared target, mm")
    ap.add_argument("--spacing", type=float, default=20.0, help="distance between the two sensors, mm")
    ap.add_argument("--theta", type=float, default=0.0,
                    help="puck angle per side, degrees: the tilt is scaled to it, and the range is judged only up to 12")
    ap.add_argument("--both", action="store_true",
                    help="range both sensors together instead of one at a time (shows the crosstalk jump)")
    args = ap.parse_args()

    dev = Device(SerialTransport(args.port, 921600))
    dev.connect()
    dev.configure(p.Settings(16, 33, 40, "short"))
    how = "both sensors together" if args.both else "one sensor at a time"
    print(f"Aim: A and B both near {args.expected_mm:.0f} mm (within {args.tol:g} mm) and B-A near "
          f"{args.offset:+.0f} mm (within {args.square:g} mm). Each line averages {args.average:g} s, {how}. "
          f"It stops by itself after {args.seconds:g} s; Ctrl+C stops it sooner.\n", flush=True)

    bucket = defaultdict(list)

    def collect(cond, ms):
        bucket.clear()

        def keep(r):
            if r.status == 0:
                bucket[r.sensor].append(r.range_mm)

        dev.run(f"live{cond}", cond, max(p.MIN_RUN_MS, int(ms)), keep)

    def line():
        if not (bucket["A"] and bucket["B"]):
            print("no valid readings: is the target in front of both sensors?", flush=True)
            return
        a = sum(bucket["A"]) / len(bucket["A"])
        b = sum(bucket["B"]) / len(bucket["B"])
        diff = (b - a) - args.offset
        th = math.radians(abs(args.theta))
        if th < 1e-6:
            tilt = math.degrees(math.atan2(diff, args.spacing))
        else:
            # the difference a tilt makes grows with the puck angle: 2 r sin(th) / cos^2(th) per radian
            tilt = math.degrees(diff / (2.0 * ((a + b) / 2.0) * math.sin(th) / math.cos(th) ** 2))
        square = abs(diff) <= args.square
        judged = abs(args.theta) <= 12.0       # beyond 12 degrees per side the view runs past the board's edge
        near = (abs(a - args.expected_mm) <= args.tol and abs(b - args.expected_mm) <= args.tol) if judged else True
        if not judged:
            note = ("turn target: B-side edge " + ("closer" if diff > 0 else "farther away")) if not square                 else "range not judged past 12 deg (the view runs past the board's edge)"
        elif square and near:
            note = "OK"
        elif not square:
            note = f"turn target: B-side edge {'closer' if diff > 0 else 'farther away'}"
        else:
            note = "move target " + ("closer" if (a + b) / 2 > args.expected_mm else "back")
        print(f"A {a:6.1f} mm   B {b:6.1f} mm   B-A {b - a:+6.1f} mm   tilt {tilt:+5.1f} deg   {note}",
              flush=True)

    end = time.monotonic() + args.seconds
    try:
        while time.monotonic() < end:
            if args.both:
                collect("AB", args.average * 1000)
            else:
                collect("A", args.average * 500)
                half = dict(bucket)
                collect("B", args.average * 500)
                bucket["A"] = half.get("A", [])
            line()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            dev.abort()
            dev.stop_all()
        except Exception:
            pass
        print("stopped", flush=True)


if __name__ == "__main__":
    main()
