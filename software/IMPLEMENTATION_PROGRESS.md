# Implementation progress

Author: Jessica
Last updated: 2026-09-26

## Status

| Milestone | State |
|---|---|
| M1 serial protocol (spec + C++ parser/formatter) | done, unit tested |
| M2 run state machine | done, unit tested against fakes |
| M3 hardware layer (mux, VL53L1X channel, interrupt capture, diagnostics) | done; verified on the local rig |
| M4 firmware integration | done, no warnings; verified on the local rig |
| M5 host protocol, transport, device client, simulator | done, tested |
| M6 session runner (plan, shuffling, warm-up, acceptance, ambient check, CSV, resume) | done, tested end to end on the simulator |
| M7 analysis, crossover fit, bootstrap, figures | done, tested; recovers a known crossover |
| M8 hardware bring-up | **local rig: H1-H4, H7, H8 pass; bench pilot session 18/18 runs accepted (not yet against the grey board).** Jessica's rig: not started |

The local rig (see *Hardware verified*) has run the whole chain: firmware,
session runner, acceptance checks and analysis. Jessica's rig has not been
connected yet.

## Completed components

**Firmware** (`firmware/`, PlatformIO, Arduino on ESP32-S3):

- `rig_core` (pure C++): command parser and validation, output formatting,
  result-block decoding, run state machine, self-test statistics.
- `rig_hw`: TCA9548A driver with read-back, VL53L1X channel (init, settings
  with full read-back, burst result read), ISR timestamping of GPIO1 edges,
  bus scan and a 17-check self-test.
- `vl53l1x_uld`: ST's driver, vendored and patched so I2C faults are reported
  (see *Known issues*, item 1).
- `main.cpp`: command loop, boot reason report, settings re-check before
  every run.

**Host** (`host/rig`, Python):

- `protocol`, `transport`, `device`: typed messages, serial port, and command
  handling that detects timeouts and resets.
- `session`: the procedure's run order, operator prompts, warm-up per
  distance, run and block acceptance, 10% ambient rule, redo of failed
  blocks, CSV logs, resume after interruption.
- `analysis`, `figures`: per-run statistics, within-block paired effects,
  t-test and Wilcoxon with 95% CIs, logistic crossover with bootstrap CI,
  prediction, the four figures.
- `simulator`: protocol-exact fake rig with fault injection.
- `cli`: `ports`, `info`, `scan`, `selftest`, `session`, `analyze`, `simulate`.

## Remaining components

| Item | Blocked on |
|---|---|
| H5/H6 (logic analyser), H9 (pilot at 0.3 m on the grey board) | the grey board on the local rig; the analyser is optional so far |
| 4x4 ROI validity rule (known issue 11) | Jessica's decision, then a bench check at 0.3 m |
| Jessica's rig bring-up (`esp32s3_wroom2`) | Jessica's assembled rig |
| Final angle list for the longer arm | fixture redesign; `configs/rq3_fine_steps.json` is provisional |
| RQ1, RQ2, RQ4 software (six sensors, gimbal scanning, throughput) | hardware not purchased (no extra sensors, TMC2209 or NEMA17 in the parts list) |

## Files

All new, under `software/`:

```
README.md  IMPLEMENTATION_PLAN.md  IMPLEMENTATION_PROGRESS.md  PROTOCOL.md  HARDWARE_INTERFACE.md  run_all_tests.py
firmware/platformio.ini
firmware/include/rig_config.h
firmware/src/main.cpp
firmware/lib/rig_core/src/{rig_types.h, protocol.h/.cpp, uld_decode.h/.cpp, run_controller.h/.cpp, run_stats.h/.cpp}
firmware/lib/rig_hw/src/{tca9548a, tof_channel, int_capture, hw_bank, diagnostics}.h/.cpp
firmware/lib/vl53l1x_uld/{src/*, PATCHES.md, LICENSE-ST.md, library.json}
firmware/test_native/{test_core.cpp, run_native_tests.py}
host/pyproject.toml
host/rig/{__init__, __main__, protocol, transport, device, geometry, matrix, session, simulator, analysis, figures, cli}.py
host/configs/{rq3_current_fixture.json, rq3_fine_steps.json}
host/tests/{conftest, test_protocol, test_geometry, test_device, test_session, test_analysis}.py
```

Existing project files: `build_wiring_twosensor.py` only gained optional label parameters (its sheet output is unchanged). `build_wiring_v2.py` is new.

## Tests performed

`python run_all_tests.py`, all passing on 2026-09-26:

| Suite | Result | Covers |
|---|---|---|
| Firmware core, native C++ (zig c++, UBSan) | 112 checks pass | parser edge cases, formatting, 32-bit rates, status mapping, result-block byte map, run controller: normal, solo, stray edge, silent sensor, read errors, stuck line, busy, leftover edges; timing checks |
| Firmware build, ESP32-S3 | both builds succeed, 0 warnings (`-Wall -Wextra`), RAM 6.4%, flash 10.4% | `esp32s3_n16r8` (`qio_opi`, 16 MB) and `esp32s3_wroom2` (`opi_opi`, 32 MB) |
| Host, pytest | 75 pass | protocol (golden lines shared with the C++ tests), prediction equals issued values, device client faults, full sessions with injected faults (stray, I2C, reset, ambient jump, lost settings, missed results), resume, self-test failure, analysis maths, crossover recovery, figure metadata |

A mutation check confirmed the C++ tests catch a broken stray-edge rule.

## Hardware verified

**Local rig** (ESP32-S3-N16R8, CJMCU TCA9548A, 2 x VL53LXX-V2), 2026-09-26, firmware 1.0.2:

| Check | Result |
|---|---|
| H1 wiring and power (meter) | pass after fixes: sensor A and B VIN were not on the 3V3 wire; mux RST 3.3 V, A0-A2 0 V (on-board resistors, no jumpers needed) |
| H2 flash `esp32s3_n16r8` over the CH343 port (COM4) | pass; `BOOT/INFO board=n16r8` |
| H3 `rig info` | pass: readyA=1 readyB=1 verified=1, i2c 400 kHz |
| H4 `rig scan` | pass: 0x70 main, 0x29 on ch 1 and ch 2 (sensor A moved to ch 2, see bug 5), nothing else |
| H7 `rig selftest` | 17/17 pass: model ID 0xEACC on both (genuine VL53L1X), settings read back, 25 readings/s per sensor, period 39.9 / 40.1 ms, max gap 40.4 ms, 25/25 valid, silent after stop, INT lines idle high, 0 I2C errors |
| 4x4 ROI | pass: written and read back on both sensors |
| GPIO1 falling-edge interrupts | pass (implied by the timing above) |
| H5/H6 logic analyser | not run (not needed so far) |
| H8 pilot session | pass. 0.3 m config, dtheta 0, ROI 16 and 4, 3 repeats, 5 s runs: 6/6 blocks and 18/18 runs accepted, 0 missed readings, 0 I2C errors, 0 stray edges. Sensors aimed at the desk scene, not the grey board, so this checks the chain, not the physics. |
| Pilot data, ROI 16 | B steady (SD 3 to 5 mm); A steady (SD 5 to 8 mm) except two A solo runs where something moved in its view (SD 30 and 114 mm) |
| Pilot data, ROI 4 | ranges steady (SD about 14 mm) but 99% of readings have status 2: known issue 11 |
| H9 pilot at 0.3 m on the grey board | not run yet |

Bugs found and fixed on the bench:

1. Stream counter read from the wrong byte (0x0095, the phase low byte, instead of
   0x008B). Fixed; the correct register then read a constant 1 in timed ranging,
   so missed-reading detection moved to interrupt-timestamp gaps (firmware
   self-test and host session).
2. The first settings write after power-up failed: ULD `SetDistanceMode`
   re-applies the current timing budget, which reads as 0 straight after
   `SensorInit`. Fixed by preloading a 33 ms budget. The error message now tells
   a bus fault from a driver refusal.
3. A sensor that browns out comes back at 0x29 with its configuration lost.
   `CFG` now fully re-initialises both sensors every time (0.34 s).
4. I2C speed is a build setting (`RIG_I2C_HZ`); the local rig runs at the
   designed 400 kHz with no errors once all boards are powered.
5. Mux channel 0 on the local CJMCU board stopped passing signals. The first
   sensor A was taken to be faulty and replaced, but the new one was also
   silent on channel 0 and both work on channel 2, so the first sensor A is
   probably fine (keep it as a spare). The sensor channels are now build
   settings (`RIG_CH_A`, `RIG_CH_B`); the local build sets `RIG_CH_A=2`, `INFO`
   reports `chA`/`chB`, and `rig scan` checks against them. The local wiring
   sheet shows sensor A on SD2/SC2.
6. Early pilot failures on the local rig were wiring: a loose VIN on sensor A
   (dropout after 1 s, spurious INT_A edges) and a broken SC0 jumper. An
   unpowered sensor left on the bus corrupts reads on its channel.

## Changes since the first release

- Local rig hardware differs from Jessica's: VL53LXX-V2 sensor boards, a CJMCU
  TCA9548A breakout and an ESP32-S3-N16R8 board (16 MB quad flash). Firmware
  1.0.1 adds a second build, `esp32s3_n16r8` (`qio_opi`), next to
  `esp32s3_wroom2` (`opi_opi`); both build with no warnings, image headers
  confirmed (16 MB and 32 MB). `BOOT` and `INFO` now report `board=`.
- Local-rig wiring sheet: `deliverables/Wiring diagram - two-sensor test setup (VL53LXX-V2).pdf`
  (sensor A on channel 2 since 2026-09-26).
- Firmware 1.0.2: bench fixes 1 to 5 above; `rig ports` shows VID:PID and
  which port is the USB-UART bridge; the CLI explains a missing COM port
  instead of printing a traceback.

## Known issues and findings

1. **The SparkFun/ST driver swallowed I2C errors.** Upstream `VL53L1_I2CWrite`
   always returns 0, and `VL53L1_I2CRead` returns 0 even on a NACK or a short
   read, leaving stale bytes. The driver is vendored with a minimal, documented
   patch (`PATCHES.md`), and every call is checked against a failure counter.
2. **Driver inter-measurement read-back is wrong above about 120 ms** (it
   truncates to 16 bits before scaling). The firmware decodes the register
   itself.
3. **The ULD's rate accessors wrap above about 64 Mcps** (a 16-bit value x 8).
   The firmware keeps rates in 32 bits.
4. **Four angle settings cannot locate the crossover.** In simulation, the
   current plate (dtheta 0/10/20/30) gave crossover errors up to 2.25 deg with
   a bootstrap interval only 0.3 deg wide. The 1 deg-step config gave 0.02 deg.
   The simulator is idealised, so real errors will be larger for both, but the
   difference stands. The analysis flags any result with fewer than 5 levels.
   This supports building the longer arm.
5. **Two forms of the prediction formula** appear in the PDFs; they differ by
   up to 0.2 deg. The software uses the `build_rq3.py` form, which matches every
   table already issued.
6. **Room temperature** is typed in at each setup change (about every 15 min),
   not per run: there is no temperature sensor in the parts list.
7. **Battery voltage** (RQ3 PDF) is not logged: the rig is USB powered, as the
   newer procedure says.
8. **Ambient 10% rule** compares each block with the previous accepted block
   at the same distance, angle and ROI. Across angle changes the sensor looks
   at a different part of the target, so no comparison is made there.
9. **PlatformIO verbose mode (`-v`) crashes** while printing a command line (a
   tool bug). Normal builds are unaffected.
10. **Assumptions awaiting the bench** (Jessica's rig): GPIO1 edge speed, I2C
    pull-up strength, module variant. Listed under "Open questions" in
    `HARDWARE_INTERFACE.md`.
11. **4x4 ROI readings fall below the sensor's default signal limit.** In the
    bench pilot every 4x4 reading had a signal rate of 128 to 912 kcps (median
    288), and every 16x16 reading 1136 kcps or more. The split is exactly the
    ULD default minimum signal rate, 1024 kcps (register 0x0066), so 99% of
    4x4 readings carry status 2 (signal fail) although their ranges are steady.
    A 4x4 ROI uses about 14 SPADs against about 220, so it gets roughly a
    sixteenth of the signal; the dark grey board at 0.3 and 0.8 m is not
    expected to lift it over 1024 kcps. The procedure counts status not 0 as a
    dropout, so the 4x4 condition would have no usable baseline. Options: a
    lower signal limit for the 4x4 condition (new CFG field, logged per run),
    or counting status 2 as valid for 4x4 in the analysis. Needs Jessica's
    decision and a bench check on the grey board at 0.3 m.

## Next milestone

**M8, hardware bring-up**: on the local rig, a pilot block on the grey board at
0.3 m (H9) and a decision on known issue 11. Then Jessica's rig: build
`esp32s3_wroom2`, H1 to H9.

## Update 2026-09-30

Full RQ3 matrix run on the local rig (0.3 m and 0.8 m, seven angles per side, no divider; divider test at 2.5 and
5 degrees). Result: the crosstalk falls with angle and is gone at about dtheta 10 degrees for the 4x4 zone and
17 to 19 degrees for the 16x16 zone (measured earlier than predicted). The divider made no difference.

Changes made during the session:
- Outer plate holes are 2.5, 7.5 and 12.5 degrees (were 3, 7, 12 in the first configs). Configs corrected.
- `Device.connect()` stops a board that is still streaming from a dead host (with two tests).
- `RIG_INT_B` build flag; the local rig uses GPIO6 for INT_B (see `HARDWARE_INTERFACE.md`). `rig info` reports it.
- `tools/live_ranges.py` (live A and B ranges for squaring the target) and `tools/analyze_all_tags.py`
  (crossover fit for tagged sessions).
- All checks pass: native firmware tests, both firmware builds, 77 host tests.

Known behaviour, not a bug: the crossover fit ignores tagged runs by design (tags mark side experiments).
The acceptance rule compares a block with the previous accepted block at the same distance, angle and zone, so
a 10 percent light change between blocks rejects them; three failed attempts give up the block.

## Update 2026-09-30 (later): guided session, LED, skip rule

- `rig/guided.py`: `GuidedOperator` (`rig session --guided`). Live distance and squareness check, hardware self-test after
  each change, green/red LED, automatic start. One Enter (or `--angle-wait N`) for a puck change, because ranges do not change
  with the puck angle.
- Firmware: `LED state=ok|bad|off` command (GPIO7 green, GPIO15 red, optional hardware). Host: `Device.led()`, `rig led`.
- Skip rule: `adaptive_stop_ratio` and `adaptive_confirm` in the config; ascending angles; decision saved in `adaptive_stops.json`.
- Config: `expected_range_mm`, `range_tol_mm`, `square_tol_mm`; example `configs/rq3_guided.json`.
- Tests: 119 native firmware, both builds, 94 host. Not yet run on real hardware: the LED lines and `--guided` on a rig.

## Update 2026-10-02: clock check

Jessica's DevKitC-1 rig (Pololu 3415 boards) failed the four timing checks of the self-test: 50 readings in 1 s instead of
about 25 (real periods 19.6 ms and 19.8 ms for a 40 ms request). Her reading of the code is right: `apply()` verifies the
period by decoding the register with the same OSC_CALIBRATE_VAL that wrote it, so a wrong calibration value is invisible
to the read-back. Added `REG` (raw register read, firmware) and `rig regs` (`rig/diag.py`), which print the raw
registers beside the period measured from the interrupts. Cause not yet confirmed; waiting for her `rig regs` output.

Jessica's `rig regs` output (2026-10-02): oscillator values and period registers identical to the local rig, real period
exactly half the request, and 50% of readings identical to the previous one. So the sensors measure at the right period
and the data-ready line falls twice per measurement. Added `TRACE` (firmware) and `rig edges` to record the line.
Local rig reference: one fall, 0.7 ms low, next fall 39.9 ms later, 0% repeats.

Jessica's `rig edges` (2026-10-02): both sensors alone show one fall per 40 ms and 0% repeats, matching the local rig. Her
updated `rig regs` shows 51% repeats with each sensor ranging alone, so the fault needs no second sensor but appears only
through the run path. `edges` records with its own CHANGE interrupt and a plain start; runs use the falling-edge capture
and the run start sequence (stop, wait, clear, start). Added `TRACE ... path=run` (firmware) and a second section in
`rig edges`: a real run of one sensor with the pin recorded beside the run's own interrupt timestamps. Local rig: pin and
run both once per 39.9 ms. Verdicts: pin once + run twice = capture path; pin twice = sensor after the run start.

Jessica's `rig edges` with the run-path section (2026-10-02): pin falls once and the run counts once, 40.05 ms, both clean.
The only difference left between that run and `rig regs` was the interrupt type: the trace run captured with a both-edges
interrupt that checks the pin level, the normal run with a falling-edge-only interrupt. `regs` reports the MEAN gap, so
interrupts in pairs microseconds apart would give the same 20 ms mean and 50% repeats (the earlier "evenly half a period
apart" reading was an inference, not measured). Changed the production capture to the both-edges form counted when the pin
reads low (`int_capture.cpp`), and `rig regs` now prints how many interrupts come under 5 ms after the previous one.
Local rig after the change: regs 39.92 ms / 40.10 ms, 0% repeats, 0 close interrupts, self-test 17 checks passed.


Confirmed on Jessica's rig (2026-10-02, DevKitC-1 WROOM-2, COM7) with the both-edges capture: `rig regs` 40.06 ms (A) and 40.45 ms
(B), 0% repeats, 0 interrupts under 5 ms; self-test 17 checks passed (run_* 25 readings each, max gap equal to the period).
Before the change the same board gave 19.9 ms mean, 50% repeats and self-test max gap 39 ms (pairs of interrupts a few
microseconds apart). The cause of the double count in the falling-edge-only interrupt on that board is not identified; the
sensors, wiring and settings were fine. B's oscillator is about 1% slower than A's (40.45 vs 40.06 ms), within tolerance.

Jessica asked for everything in one Excel workbook (2026-10-02). Added `rig export DIR` (`rig/export.py`): Read me, Summary,
the analysis tables, Runs, Blocks, Figures (the PNGs) and the raw Readings, in openpyxl write-only mode (230k readings take
about 17 s and 14 MB). Author Jessica; the writer's name is removed from `docProps/app.xml`. `openpyxl` added to the
dependencies. Tests: `tests/test_export.py` (115 host tests pass).

Jessica asked for a measurement that stops by itself after a set time or a fixed number of readings (2026-10-02). Sessions
already end each run at its set length; the open-ended case was the live tool and any plain reading. Added `rig read`
(`rig/capture.py`): `--seconds`, `--count` or both (whichever first), CSV output and a summary. `Device.run` now stops the
run (ABORT, then takes the `OK ABORT` off the line) when the reading callback returns True, so a count ends the run at once.
`tools/live_ranges.py` takes `--seconds`. Tested on the simulator (121 host tests pass); the stop-by-count path on the real
board is still to be run.


Jessica's rig, geometry check (2026-10-05). Her guided sessions stalled: the ranges rose with the puck angle and the
squareness check flickered between OK and adjust. Two causes, both in the check rather than in her rig alone.
(1) Squareness: the sensors are 20 mm apart, so B minus A of 10 mm (the default square_tol_mm) is a target tilt of
27 degrees; the check was far too loose to align with, and it assumed a square target reads zero, although the two
sensors have their own range offsets (the local rig read B minus A of about +4 mm). Added `square_offset_mm` to the
config and a tilt readout in degrees to the guided lines and to `tools/live_ranges.py`, which now averages over
`--average` seconds and says which way to turn the board. (2) Range against angle: a turned sensor reads longer once
the nearest part of the target leaves the middle of its 27 degree field (the local rig rose about 6 mm at 15 degrees
per side at 0.3 m), so one expected value cannot fit a wide sweep. `expected_range_mm` now takes an angle table per
distance (degrees per side to mm), read straight between its points. Host tests 124 pass.

Jessica's live readout, 2026-10-05. Her 0.3 m lines alternated between two values on sensor A (291.4 and 294.8 mm) while
B stayed at 283.4, and the alternation vanished at 30 degrees per side. Her two measurement periods are 40.06 and
40.45 ms, so the crosstalk beat is 40.06*40.45/0.39 = 4.16 s, and the tool averaged 2 s per line: consecutive lines
sampled opposite phases of the beat. The swing is the crosstalk shifting her A range by about 3.4 mm. On the local
rig the same comparison (readings in an A+B run above and below twice the solo ambient, 0.3 m, 16x16, five blocks)
gives -0.44 mm for A and -0.11 mm for B, so her range effect is several times ours. Because of this the geometry
check and `tools/live_ranges.py` now range each sensor alone, one after the other (`--both` keeps the old way).
Her B minus A is -8 mm at 0 degrees and +2 mm at 30 degrees; a tilt cannot produce that pattern (at 0 degrees a tilt
only enters through the 20 mm spacing, 0.7 mm at 2 degrees), so most of the -8 mm is a per-sensor range offset, which
is what square_offset_mm is for. The tilt column is meaningless until that offset is measured on a squared target.

Jessica's first full 0.3 m session (rq3-jessica_20261004_232529, 2026-10-05, 03:36 to 09:48 UTC, 540 runs, 12 angles per
side from 0 to 12 in 1 degree steps). The 16x16 zone is complete, five accepted blocks at every angle, and it
replicates the local rig: her fitted crossover is 15.8 degrees against our 16.6, with 2 degree steps in dtheta
instead of our 5. Her crosstalk is relatively larger because her room is darker: the A+B over solo ambient ratio at
dtheta 0 is 26.5 (A) and 14.4 (B) for 16x16, against 8.2 and 5.9 here, and her SD ratio is 1.70 against our 1.17.
The 4x4 zone is full of holes: all 22 given-up blocks and 80 of the 82 rejected attempts are 4x4, and 79 of those
name sensor A. Cause: her 4x4 solo ambient is 1.4 kcps (A) and 2.2 (B), against 13.0 and 9.8 here, because she runs
in a dark room with the screen covered. At 1.4 kcps the photon noise alone moves the value by a fifth between blocks
(median consecutive change 6.2%, 90th percentile 20.9%), so a 10% share-of-reference rule is below the noise floor.
Added `ambient_floor_kcps` (default 5.0): the tolerance is taken on the larger of the reference and the floor, so the
allowance never falls under 0.5 kcps. Replaying her 82 rejections against the new rule, 72 would pass. Host tests 126.
