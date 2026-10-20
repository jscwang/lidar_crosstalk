"""Command line: `python -m rig <command>` (or `rig <command>` once installed).

  ports                          list serial ports
  info      --port COM5          firmware and wiring configuration
  scan      --port COM5          I2C scan of the main bus and every mux channel
  selftest  --port COM5          hardware self-test (exit code 1 on any FAIL)
  led       ok|bad|off --port COM5   set the status lights (green, red, both off)
  regs      --port COM5          clock check: raw oscillator registers against the real measuring period
  edges     --port COM5          what a sensor's data-ready line does at the ESP32 pin (both edges)
  read      --port COM5 --seconds 30   a plain measurement that stops by itself (--seconds, --count, or both); saves a CSV
  session   --port COM5 --config configs/x.json --out data/
                                 run the procedure (add --resume DIR to continue)
  analyze   DIR                  statistics, crossover fit, figures
  export    DIR                  one Excel workbook: readings, runs, blocks, analysis tables, figures
  simulate  --config configs/x.json --out data/
                                 whole session against the simulated rig

Every device command also accepts --sim instead of --port.

Author: Jessica
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .device import Device, DeviceError
from .matrix import load_config, plan


def _device(args) -> Device:
    if args.sim:
        from .simulator import SimTransport
        transport = SimTransport()
    else:
        if not args.port:
            sys.exit("give --port (see `rig ports`) or --sim")
        from serial import SerialException
        from .transport import SerialTransport
        try:
            transport = SerialTransport(args.port, args.baud)
        except SerialException:
            sys.exit(f"cannot open {args.port}: is the USB cable plugged in? `rig ports` lists the ports it can see.")
    dev = Device(transport)
    dev.connect()
    return dev


def cmd_ports(args) -> int:
    from .transport import list_ports
    ports = list_ports()
    if not ports:
        print("No serial ports found. Plug the ESP32 in through its USB-UART port "
              "(marked UART on the DevKitC-1; on the N16R8 board, the port next to the CH343 chip).")
    for dev, desc, ids, role in ports:
        print(f"{dev:8s} {ids:10s} {role}")
        print(f"{'':8s} {'':10s} ({desc})")
    return 0


def cmd_info(args) -> int:
    dev = _device(args)
    for k, v in dev.info.items():
        print(f"{k:10s} {v}")
    return 0


def cmd_scan(args) -> int:
    dev = _device(args)
    found = dev.scan()
    # the sensors' channels come from the firmware, so a rig that moved a
    # sensor to another channel is checked against its own wiring
    expected = {"main": (0x70,), dev.info.get("chA", "0"): (0x29,), dev.info.get("chB", "1"): (0x29,)}
    ok = True
    for where, addrs in found.items():
        shown = "error" if addrs is None else (", ".join(f"0x{a:02X}" for a in addrs) or "none")
        want = expected.get(where, ())
        flag = "" if addrs is not None and tuple(addrs) == want else "   <-- expected " + \
            (", ".join(f"0x{a:02X}" for a in want) or "none")
        ok &= not flag
        label = "main bus" if where == "main" else f"channel {where}"
        print(f"{label:10s} {shown}{flag}")
    print("wiring matches the diagram" if ok else "wiring does NOT match the diagram")
    return 0 if ok else 1


def cmd_selftest(args) -> int:
    dev = _device(args)
    cfg = load_config(args.config) if args.config else None
    s = cfg.settings(cfg.rois[0]) if cfg else None
    if s:
        dev.configure(s)
    else:
        from .protocol import Settings
        dev.configure(Settings())
    failed, tests = dev.selftest()
    for t in tests:
        print(f"{t.result:4s}  {t.name:18s} {t.detail}")
    print(f"\n{failed} check(s) failed" if failed else "\nall checks passed")
    return 1 if failed else 0


def cmd_edges(args) -> int:
    from .diag import edge_report
    dev = _device(args)
    lines, ok = edge_report(dev, args.sensor, args.imp, args.ms)
    print(chr(10).join(lines))
    return 0 if ok else 1


def cmd_regs(args) -> int:
    from .diag import clock_report
    dev = _device(args)
    lines, ok = clock_report(dev, args.imp)
    print("\n".join(lines))
    return 0 if ok else 1


def cmd_led(args) -> int:
    dev = _device(args)
    if not dev.led(args.state):
        print("this firmware has no LED command: flash the current firmware")
        return 1
    print(f"LED {args.state}")
    if args.hold:
        import time
        print(f"holding it for {args.hold} s, then turning the lights off (Ctrl+C to stop early)")
        try:
            time.sleep(args.hold)
        except KeyboardInterrupt:
            pass
        dev.led("off")
        print("LED off")
    return 0


def _session_dir(args, cfg) -> Path:
    if args.resume:
        return Path(args.resume)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = f"_{args.tag}" if args.tag else ""
    return Path(args.out) / f"{cfg.name}{tag}_{stamp}"


def cmd_session(args) -> int:
    from .session import ConsoleOperator, Session
    cfg = load_config(args.config)
    out = _session_dir(args, cfg)
    blocks = plan(cfg)
    runs = len(blocks) * len(cfg.conditions)
    print(f"{cfg.name}: {len(blocks)} blocks, {runs} runs of {cfg.run_ms / 1000:g} s "
          f"(about {runs * (cfg.run_ms / 1000 + 1) / 3600:.1f} h of ranging), output {out}")
    dev = _device(args)
    if args.guided:
        from .guided import GuidedOperator
        op = GuidedOperator(dev, cfg, color=not args.no_color, angle_wait=args.angle_wait)
    else:
        op = ConsoleOperator()
    sess = Session(dev, cfg, out, op, tag=args.tag, warmup=not args.no_warmup,
                   require_selftest=not args.skip_selftest)
    try:
        summary = sess.run()
    except KeyboardInterrupt:
        print(f"\nStopped. Continue later with:  rig session --port {args.port} --config {args.config} "
              f"--resume \"{out}\"")
        return 130
    finally:
        if args.guided:
            try:
                dev.led("off")
            except Exception:
                pass
    print(f"\nDone: {summary}. Analyse with:  rig analyze \"{out}\"")
    return 0


def cmd_analyze(args) -> int:
    from .analysis import analyze
    res = analyze(args.dir, args.out, n_boot=args.boot)
    print((res["out"] / "summary.md").read_text(encoding="utf-8"))
    return 0


def cmd_export(args) -> int:
    try:
        from .export import export_session
    except ModuleNotFoundError as e:
        sys.exit(f"{e}: install it with  python -m pip install openpyxl")
    try:
        path = export_session(args.dir, args.out, n_boot=args.boot)
    except (FileNotFoundError, PermissionError) as e:
        sys.exit(str(e))
    print(f"Wrote {path}")
    return 0


def cmd_read(args) -> int:
    from . import capture as cap
    from .protocol import Settings
    settings = Settings(args.roi, args.tb, args.imp, args.mode)
    if settings.problem():
        sys.exit(settings.problem())
    try:
        cap.plan(settings, args.sensors, args.seconds, args.count)
    except cap.CaptureError as e:
        sys.exit(str(e))
    dev = _device(args)
    rows, summary = cap.capture(dev, settings, args.sensors, args.seconds, args.count)
    path = cap.write_csv(Path(args.out) if args.out else cap.default_path(), rows)
    print(chr(10).join(cap.report(summary, path)))
    return 0 if rows else 1


def cmd_simulate(args) -> int:
    from .analysis import analyze
    from .session import Session
    from .simulator import SimOperator, SimTransport
    cfg = load_config(args.config)
    if args.run_ms:
        from dataclasses import replace
        cfg = replace(cfg, run_ms=args.run_ms, warmup_s=min(cfg.warmup_s, 5))
    out = Path(args.out) / f"{cfg.name}_simulated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    transport = SimTransport()
    dev = Device(transport)
    dev.connect()
    sim_op = SimOperator(transport.device)
    op = sim_op
    if args.guided:
        from .guided import GuidedOperator
        op = GuidedOperator(dev, cfg, color=False, angle_wait=None, sleep=lambda s: None,
                            on_change=lambda d, t: sim_op.setup(d, t, True))
    Session(dev, cfg, out, op, tag=args.tag).run()
    res = analyze(out, n_boot=args.boot)
    print((res["out"] / "summary.md").read_text(encoding="utf-8"))
    ph = transport.device.physics
    print("Simulator truth (10% points):",
          ", ".join(f"{d:g} m ROI {r}: {_truth(ph, d, r):.1f} deg" for d in cfg.distances_m for r in cfg.rois))
    return 0


def _truth(ph, d, roi) -> float:
    old = ph.d_m
    ph.d_m = d
    v = ph.true_x10(roi)
    ph.d_m = old
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rig", description=f"Two-sensor crosstalk rig, host software {__version__}")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def device_args(p):
        p.add_argument("--port", help="serial port, e.g. COM5 or /dev/ttyUSB0")
        p.add_argument("--baud", type=int, default=921600)
        p.add_argument("--sim", action="store_true", help="use the simulated rig")

    sub.add_parser("ports").set_defaults(fn=cmd_ports)
    for name, fn in (("info", cmd_info), ("scan", cmd_scan)):
        p = sub.add_parser(name)
        device_args(p)
        p.set_defaults(fn=fn)
    p = sub.add_parser("selftest")
    device_args(p)
    p.add_argument("--config", help="apply this config's settings first (first ROI)")
    p.set_defaults(fn=cmd_selftest)

    p = sub.add_parser("regs")
    device_args(p)
    p.add_argument("--imp", type=int, default=40, help="inter-measurement period to test, ms")
    p.set_defaults(fn=cmd_regs)

    p = sub.add_parser("edges")
    device_args(p)
    p.add_argument("--sensor", choices=["A", "B"], default="A")
    p.add_argument("--imp", type=int, default=40, help="inter-measurement period to request, ms")
    p.add_argument("--ms", type=int, default=400, help="how long to record, ms")
    p.set_defaults(fn=cmd_edges)

    p = sub.add_parser("led")
    device_args(p)
    p.add_argument("state", choices=["ok", "bad", "off"])
    p.add_argument("--hold", type=int, default=0, metavar="SECONDS",
                   help="keep the light on for this long, then turn it off (for measuring with a meter)")
    p.set_defaults(fn=cmd_led)

    p = sub.add_parser("session")
    device_args(p)
    p.add_argument("--config", required=True)
    p.add_argument("--out", default="data")
    p.add_argument("--resume", help="continue an interrupted session directory")
    p.add_argument("--tag", default="", help="label for special runs, e.g. divider or swapped")
    p.add_argument("--no-warmup", action="store_true")
    p.add_argument("--skip-selftest", action="store_true")
    p.add_argument("--guided", action="store_true",
                   help="watch the target position and squareness live, show green (and light the LED) when "
                        "right, then start each run by itself")
    p.add_argument("--angle-wait", default="enter",
                   help="with --guided, how to wait for the pucks to be set: enter (press Enter) or seconds")
    p.add_argument("--no-color", action="store_true", help="with --guided: plain text, no colours")
    p.set_defaults(fn=cmd_session)

    p = sub.add_parser("analyze")
    p.add_argument("dir")
    p.add_argument("--out")
    p.add_argument("--boot", type=int, default=2000, help="bootstrap resamples")
    p.set_defaults(fn=cmd_analyze)

    p = sub.add_parser("export")
    p.add_argument("dir", help="the session folder (the one `rig session` made)")
    p.add_argument("--out", help="workbook path (default: <session folder>/<session name>.xlsx)")
    p.add_argument("--boot", type=int, default=2000, help="bootstrap resamples, if the analysis has to be made first")
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("read")
    device_args(p)
    p.add_argument("--seconds", type=float, help="stop after this many seconds")
    p.add_argument("--count", type=int, help="stop when every sensor has this many readings")
    p.add_argument("--sensors", default="AB", choices=["A", "B", "AB"], help="which sensors to read (default both)")
    p.add_argument("--roi", type=int, default=16)
    p.add_argument("--tb", type=int, default=33, help="timing budget, ms")
    p.add_argument("--imp", type=int, default=40, help="inter-measurement period, ms")
    p.add_argument("--mode", default="short", choices=["short", "long"])
    p.add_argument("--out", help="CSV file to write (default data/read_<date>_<time>.csv)")
    p.set_defaults(fn=cmd_read)

    p = sub.add_parser("simulate")
    p.add_argument("--config", required=True)
    p.add_argument("--out", default="data")
    p.add_argument("--tag", default="")
    p.add_argument("--run-ms", type=int, help="shorter runs for a quick check")
    p.add_argument("--boot", type=int, default=500)
    p.add_argument("--guided", action="store_true", help="use the guided operator against the simulator")
    p.set_defaults(fn=cmd_simulate)

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        return args.fn(args)
    except DeviceError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
