# Two-sensor crosstalk rig: software

Author: Jessica

Firmware for the ESP32-S3 that runs the two VL53L1X sensors, and laptop
software that runs the procedure in `deliverables/Procedure - two-sensor
crosstalk test.pdf`, logs every reading and produces the statistics and
figures.

| Folder / file | Contents |
|---|---|
| `firmware/` | PlatformIO project (Arduino on ESP32-S3) |
| `host/` | Python package `rig`: device control, session runner, analysis, simulator |
| `PROTOCOL.md` | serial protocol between the two |
| `HARDWARE_INTERFACE.md` | pins, timing, init sequences, diagnostics, bench checklist |
| `IMPLEMENTATION_PLAN.md` | architecture and milestones |
| `IMPLEMENTATION_PROGRESS.md` | status, tests, known issues |
| `run_all_tests.py` | every automated check in one command |

## Install

```
python -m pip install platformio ziglang pytest pyserial numpy scipy pandas matplotlib
```

`ziglang` provides the C++ compiler for the firmware's PC-side unit tests.

## Firmware

The flash type differs between the two ESP32-S3 boards, so each has its own
build. Name the board every time; the wrong one boot-loops (reflash with the
right one, nothing is damaged).

| Rig | Board | Build |
|---|---|---|
| Local | DevKitC-style board, module ESP32-S3-N16R8 | `esp32s3_n16r8` |
| Jessica's | ESP32-S3-DevKitC-1, ESP32-S3-WROOM-2 (32 MB) | `esp32s3_wroom2` |

```
cd firmware
python -m platformio run -e esp32s3_n16r8                                  # build
python -m platformio run -e esp32s3_n16r8 -t upload --upload-port COM5    # flash
```

Use the USB port wired to the USB-UART chip: marked UART on the DevKitC-1; on
the N16R8 board it is the port next to the CH343 chip (the right-hand one with
the antenna at the top). The other USB-C port is the ESP32's built-in USB and
gives no data with this firmware. Windows port names are not reliable (both
ports can show as "USB Serial Device"), so check with:

```
python -m rig ports
```

It reads each port's USB vendor ID: 1A86 (CH343), 10C4 (CP210x) or 0403 (FTDI)
is the right port; 303A is the built-in USB. `python -m rig info --port COM5`
then shows `board=n16r8` or `board=wroom2`.

## Using the rig

Run these from `host/`:

```
python -m rig ports                                   # find the port
python -m rig info --port COM5
python -m rig scan --port COM5                        # wiring check
python -m rig selftest --port COM5                    # hardware self-test
python -m rig session --port COM5 --config configs/rq3_current_fixture.json --out data
python -m rig analyze data/<session folder>
```

The session prompts before every change of target distance or puck angle and
asks for the room temperature. Ctrl+C stops safely. The command it prints
continues the session with `--resume`. Special checks from the procedure use a
tag, which keeps them apart in the analysis:

```
python -m rig session --port COM5 --config configs/rq3_current_fixture.json --tag divider
python -m rig session --port COM5 --config configs/rq3_current_fixture.json --tag swapped
```

`configs/rq3_fine_steps.json` is ready for the longer arm with 1 degree steps.

## Without hardware

```
python -m rig simulate --config configs/rq3_current_fixture.json --out data --run-ms 5000
```

This runs the whole session against a simulated rig and analyses it. The
simulator's true crossover is printed alongside the fitted one.

## Tests

```
python run_all_tests.py
```

## Notes from the September 2026 bench session

- **Plate angles.** Per side: 0, 5, 10, 15 (inner arm hole) and 2.5, 7.5, 12.5 (outer arm hole). Read the
  numbers engraved next to the plate holes on your own plate and use those. `configs/rq3_current_fixture.json`
  has all seven.
- **Check the geometry after every physical change.** Run `python -m rig selftest --port COM5` (17 of 17 must
  pass) and look at the 16x16 solo ranges. On the local rig at 0.3 m they read about 285 to 290 mm (A and B),
  at 0.8 m about 795 to 810 mm, and A and B agree within about 10 mm. A pin in the wrong hole or a target that
  is not square shows up as a range shift of 10 mm or more, and it happened twice.
- **Squaring the target.** Square it with the tape first: measure from one straight reference to each end of
  the board and make the two equal. Over a 1.2 m board, 10 mm out is half a degree. With the pucks straight
  ahead the sensors barely feel a tilt, because it reaches them only through their 20 mm spacing (0.35 mm of
  B minus A per degree); with the pucks turned they feel it strongly (1.8 mm per degree at 10 degrees per side,
  6.8 at 30), so read the tilt at the largest angle. `python tools/live_ranges.py 288 --port COM5` then prints A, B, B minus A and the tilt
  that difference implies, averaged over `--average` seconds. The two sensors have their own range offsets, so
  a square target does not read zero: measure that difference once and pass it as `--offset`, and put it in the
  config as `square_offset_mm`. Press Ctrl+C before starting a run (it holds the serial port).
- **Range against angle.** A turned sensor reads a little longer, because the nearest part of the target leaves
  the middle of its 27 degree field: on the local rig the 0.3 m range rose by about 6 mm at 15 degrees per side.
  For a wide sweep, give `expected_range_mm` an angle table for that distance instead of one number
  (`{"0.3": {"0": 288, "30": 318}}`, degrees per side to mm, read straight between the points). Measure its
  points with `tools/live_ranges.py` at a squared target.
- **Tagged runs and the crossover fit.** The crossover fit only uses untagged runs. A session started with
  `--tag ...` still gets its statistics per angle, but the crossover table stays empty. To fit it anyway:
  `python tools/analyze_all_tags.py <session_dir>` (analyses a copy with the tags blanked and writes into the
  session's `analysis/` folder).
- **A board left streaming.** If the host program dies in the middle of a run, the board keeps ranging.
  `Device.connect()` now stops it instead of waiting for it to finish.
- **Interrupt pin on the local rig.** Sensor B is on GPIO6 in the `esp32s3_n16r8` build; see
  `HARDWARE_INTERFACE.md`.

## Guided session and the skip rule

```
python -m rig session --guided --port COM5 --config configs/rq3_guided.json --out data
```

At every change the software says what to set, waits for one Enter when the pucks change (the ranges do not change
with the puck angle, so it cannot see a pin move), then reads both sensors every two seconds and shows the distance and
squareness. It says what to do ("27 mm too far: move it closer", "B-A is +35 mm: turn target, B-side edge closer"),
lights a green LED (and prints OK in green) when the distance, the squareness and the self-test are all right for
three readings in a row, and then starts the run by itself. `--angle-wait 60` waits 60 s instead of an Enter.

In `configs/rq3_guided.json`, `adaptive_stop_ratio` turns on the skip rule: angles run in ascending order and, at each
distance, the higher angles are skipped once the worst A+B over solo ambient ratio (both zones, both sensors) is at or
below the limit. The decision is saved in `adaptive_stops.json`, so `--resume` keeps it. Set `expected_range_mm`
for your rig (read it with `tools/live_ranges.py`). `python -m rig led ok|bad|off` tests the lights.

## Clock check (`rig regs`)

`python -m rig regs --port COM5` reads each sensor's oscillator calibration and period registers and then measures the
real measuring period from the interrupt timestamps. The settings read-back in the firmware decodes the period with the
same oscillator value that wrote it, so it cannot show a wrong clock; this command can. A sensor that measures at 20 ms
when 40 ms was asked for (self-test: 50 readings in a second instead of 25) shows as WRONG with the raw values beside it.
`--imp 80` tests another requested period.

## A measurement that stops by itself (`rig read`)

```
python -m rig read --port COM5 --seconds 30        stop after 30 s
python -m rig read --port COM5 --count 500         stop when each sensor has 500 readings
python -m rig read --port COM5 --seconds 60 --count 500    whichever comes first
```

Both sensors are read by default (`--sensors A` or `B` for one). `--roi`, `--tb`, `--imp` and `--mode` set the sensor
settings (defaults 16, 33, 40, short). With no limit it runs 30 s. The readings are saved to `data/read_<date>_<time>.csv`
(or the file given with `--out`), at most the asked-for count per sensor, and a short summary is printed. The longest single
measurement is one hour. `tools/live_ranges.py` also stops by itself, after `--seconds` (default 600).

## One Excel workbook (`rig export`)

`python -m rig export "data\<session folder>"` writes `<session folder>\<session name>.xlsx`: a Read me sheet, the written
Summary, the Crossover, Effects summary, Effects by sensor, Pair effects and Run stats tables, the Runs and Blocks tables,
the Figures, and the raw Readings (one row per reading, with a filter on the header row). It runs the analysis first if the
session has none. It needs `openpyxl` (`python -m pip install openpyxl`, already listed in `pyproject.toml`). If the workbook
is open in Excel, close it before exporting again.

## Interrupt line check (`rig edges`)

`python -m rig edges --port COM5 --sensor A` ranges one sensor alone and records both edges of its data-ready line at
the ESP32 pin with microsecond timestamps, together with the moment the firmware had read the result and cleared the
interrupt. A healthy sensor shows one falling edge per measurement, about 0.7 ms low, then nothing until the next
period. Use it when `rig regs` reports readings repeated half the time (the line falls twice per measurement).

It then repeats the recording with the sensor started and read exactly as a real run does (`TRACE ... path=run`), and
prints the pin's falls beside the interrupts the run counted, so a fault in the capture path can be told apart from a
fault on the line itself.
