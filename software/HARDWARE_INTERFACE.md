# Hardware interface

Author: Jessica

Source of truth for the wiring: `deliverables/Wiring diagram - two-sensor test setup.pdf`.
Firmware constants: `firmware/include/rig_config.h`.

## Parts

| Part | Role |
|---|---|
| ESP32-S3-DevKitC-1, ESP32-S3-WROOM-2 (32 MB octal flash, octal PSRAM); local rig: DevKitC-style board with ESP32-S3-N16R8 (16 MB quad flash, 8 MB octal PSRAM) | controller; same pinout, separate firmware builds |
| SparkFun Qwiic Mux BOB-16784 (TCA9548A) at 0x70 | separates the two sensors, which share address 0x29 |
| 2 x Pololu 3415 (VL53L1X carrier) | sensor A on mux channel 0, sensor B on channel 1 |
| SLogic Combo 8 | bench check of timing and I2C only, not used during runs |

## Pin map

| Signal | ESP32-S3 | DevKitC J1 pin | Goes to | Electrical |
|---|---|---|---|---|
| SDA | GPIO8 | 12 | mux Main, Qwiic blue | 3.3 V, 400 kHz |
| SCL | GPIO9 | 15 | mux Main, Qwiic yellow | 3.3 V |
| INT_A | GPIO4 | 4 | sensor A GPIO1 (jumper, not through the mux) | open drain, carrier pulls up to its 2.8 V VDD through 47k |
| INT_B | GPIO5 | 5 | sensor B GPIO1 | as INT_A |
| 3V3 | 3V3 | 1 | mux Main red; the mux passes it to both sensors' VIN | |
| GND | GND | 22 | mux Main black | |
| Serial | UART0 via USB | port marked UART | laptop | 921600 baud 8N1 |
| LED green (optional) | GPIO7 | 7 | LED anode through about 330 ohm, cathode to GND | lit while the target setting is right |
| LED red (optional) | GPIO15 | 8 | LED anode through about 330 ohm, cathode to GND | lit while it is not |

Not connected: sensor VDD (the carrier's own 2.8 V output), sensor XSHUT, and
the 5V pin. The ESP32 pins for INT_A and INT_B are inputs **without** internal
pull-ups, because a pull-up to 3.3 V would back-feed the carrier's 2.8 V rail.

**Logic level margin.** GPIO1 idles at 2.8 V. The ESP32-S3 input-high threshold
is 0.75 x 3.3 V = 2.48 V, which leaves about 0.3 V of margin. This is adequate,
but it is the first thing to measure if interrupts are missed.

### Rig variants (sensor board and mux)

The firmware source is the same for both rigs (both muxes are TCA9548A at 0x70). Sensor A is on channel 0 and B on channel 1, except on the local rig, where channel 0 of the CJMCU board is faulty and sensor A uses channel 2 (`RIG_CH_A=2` in the `esp32s3_n16r8` build). `INFO` reports `chA=` and `chB=`, and `rig scan` checks against them.

Sensor B's interrupt is on **GPIO6** on the local rig (`-DRIG_INT_B=6` in the `esp32s3_n16r8` build), not GPIO5. On 2026-09-29 the GPIO5 contact picked up false interrupts (20 to 100 000 extra edges per run) that followed the pin, not the wire; moving the wire to GPIO6 and reflashing removed it. `INFO` reports `intA=` and `intB=`. The `esp32s3_wroom2` build keeps GPIO5, so the pin map above holds for the DevKitC-1 rig. If INT_B misbehaves on any rig, `rig selftest` shows it as too many readings in a run, a stray interrupt on the stopped sensor, or "GPIO1 line held low".

| | Jessica's rig: Pololu 3415 | Local rig: VL53LXX-V2 (HU108) |
|---|---|---|
| ESP32 module | ESP32-S3-WROOM-2, 32 MB octal flash: build `esp32s3_wroom2` | ESP32-S3-N16R8, 16 MB quad flash, 8 MB octal PSRAM: build `esp32s3_n16r8`; header pinout identical to the DevKitC-1 |
| Header | 7 pins: VDD, VIN, GND, SDA, SCL, XSHUT, GPIO1 | 6 pins: VIN, GND, SCL, SDA, GPIO1, XSHUT (SCL before SDA) |
| GPIO1 pull-up | 47k to the carrier's 2.8 V | 10k to the board's own regulator (voltage not stated; measure, must be over 2.5 V) |
| SDA/SCL | level-shifted, 10k to VIN | level-shifted, 10k to VIN |
| Mounting | two M2 holes, 12.7 mm apart | two holes in end ears, 19.30 mm apart |
| Mux | SparkFun Qwiic Mux: Qwiic ports, passes 3.3 V and GND to each channel | CJMCU TCA9548A breakout: channel n is the pin pair SDn/SCn, no power on the channels, RST and A0-A2 set by on-board resistors (meter check) |
| Sensor channels | A on ch 0, B on ch 1 | A on ch 2 (SD2/SC2), B on ch 1; ch 0 faulty on this board (two different sensors silent on it, both fine on ch 2) |
| Connections | Qwiic cables | jumper wires; separate 3V3 and GND lines to each sensor |
| Wiring sheet | `Wiring diagram - two-sensor test setup` | `Wiring diagram - two-sensor test setup (VL53LXX-V2)` |

The V2 supplier's schematic shows a VL53L0X symbol; the supplier confirmed the
fitted chip is a VL53L1X (the schematic is a shared template). `rig selftest`
checks the model ID (0xEACC) on every start, so a wrong chip is caught.

## Timing

| Item | Value | Basis |
|---|---|---|
| Ranging | short mode, 33 ms budget, 40 ms period, 25 readings/s per sensor | procedure PDF |
| Data ready | GPIO1 falling edge (configured active low) | set in `TofChannel::init`, read back |
| Timestamp | `esp_timer_get_time()` in the ISR, 1 us resolution | `int_capture.cpp` |
| Result read | 2-byte index write + 17-byte burst read + 1-byte interrupt clear, about 0.6 ms at 400 kHz | calculated |
| Mux switch | 1-byte write + 1-byte read-back, about 0.1 ms, only when the channel changes | calculated |
| I2C load | under 4% of the bus at 2 x 25 readings/s | calculated |
| Serial load | about 3 kB/s of 92 kB/s | calculated |

## Initialisation, per sensor (`TofChannel::init`)

1. Select the mux channel and read the control register back.
2. Read the model ID at 0x010F; it must be 0xEACC.
3. Stop ranging and clear the interrupt. XSHUT is not wired, so an ESP32 reset
   does not reset the sensors, and one may still be ranging from before.
4. Poll FIRMWARE__SYSTEM_STATUS (0x00E5) until non-zero, 100 ms limit.
5. ULD `SensorInit`: default register block, one dummy measurement, VHV setup.
6. Set GPIO1 active low and read the polarity back.
7. Read the factory optical centre (0x013E); small ROIs are centred on it.

Then `CFG` (for both sensors): distance mode, timing budget, inter-measurement
period, ROI, in that order (the ULD's budget table depends on the mode), and
every value read back and compared. The ULD's own inter-measurement read-back
truncates a 32-bit register to 16 bits, so the firmware decodes it itself.

## Run sequence (`RunController::start`)

1. Stop both sensors. Wait one timing budget + 5 ms for a measurement in flight.
2. Clear both interrupts, reset the edge counters.
3. Both GPIO1 lines must be high (idle). If not: `ERR RUN code=int_stuck`.
4. Start the sensors in the condition (A, B or both).
5. On each edge: read the result block, clear the interrupt, send a `D` line.
6. Abort at once if the stopped sensor raises an interrupt (`stray`), if a
   ranging sensor is silent for 5 periods (`timeout`), or after 3 failed reads
   in a row (`i2c`). At the end, stop both sensors and send `RUNEND`.

## Diagnostics

| Tool | What it shows |
|---|---|
| `BOOT ... reset=` | why the ESP32 started; `brownout` means a power problem |
| `rig scan` | main bus must show only 0x70; the two sensor channels (`chA`, `chB` from `INFO`) only 0x29 |
| `rig selftest` | 17 pass/fail checks: mux, IDs, boot, settings read-back, timed runs per condition, silence after stop, idle lines, I2C errors; plus information lines (ROI centre, median range) |
| `RUNEND` | per run: readings, edges, overruns, read errors, bus errors, abort reason |
| `runs.csv` | per run: all of the above plus missed results by stream count |
| driver patch | every failed I2C transaction is counted (see `firmware/lib/vl53l1x_uld/PATCHES.md`) |

## Bench bring-up checklist (hardware verification)

Nothing in this list has been run yet; the software was built and tested
without the hardware. Record results in `IMPLEMENTATION_PROGRESS.md`.

| # | Step | Pass when |
|---|---|---|
| H1 | Check the wiring against the diagram before power; nothing on the 5V pin | matches |
| H2 | `pio run -e <build> -t upload --upload-port COMx` in `firmware/` (build per board, see README) | flashes; `BOOT ... board=` names the build; a boot loop means the wrong build for the module |
| H3 | `python -m rig info --port COMx` | `readyA=1 readyB=1 verified=1`, `centreA/B` near 199 |
| H4 | `python -m rig scan --port COMx` | "wiring matches the diagram" |
| H5 | Logic analyser on INT_A, INT_B, SDA, SCL (10 MHz), then `rig selftest` | lines idle high; one falling edge per 40 ms per ranging sensor; after each edge a burst read of 17 bytes from 0x0089 then a write to 0x0086, after which the line returns high; no NACKs; SCL about 400 kHz |
| H6 | Same capture: time from INT falling edge to start of the I2C read | under 1 ms |
| H7 | `rig selftest` | all PASS; `run_*_range` medians match a tape measurement to the nearest object |
| H8 | One 30 s run of each condition (first block of a session) | `missed_A/B = 0` in `runs.csv` (missed readings are counted from interrupt-timestamp gaps) |
| H9 | Pilot block at 0.3 m against the grey board | range within about 10 mm of the tape; solo ambient steady between repeats |

## Open questions that need the hardware

| Question | Why it matters | How to answer |
|---|---|---|
| Exact module variant on Jessica's board (N32R8V or N32R16V) | the `esp32s3_wroom2` build assumes octal flash and PSRAM (`opi_opi`), correct for both | label on the module can. Local rig: answered, ESP32-S3-N16R8, build `esp32s3_n16r8` (`qio_opi`) |
| GPIO1 polarity and edge speed on the real carrier | timestamps are taken on the falling edge | H5 |
| Stream counter behaviour | missed-result detection | answered on the local rig: it stays at 1 in timed ranging, so detection now uses timestamp gaps |
| I2C pull-ups on the mux Main side | 400 kHz needs adequate pull-ups | H5 rise times; drop to 100 kHz in `rig_config.h` if edges are slow |
