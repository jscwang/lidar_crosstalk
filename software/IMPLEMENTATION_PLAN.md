# Two-sensor crosstalk rig: software implementation plan

Author: Jessica

## 1. What the project inspection found

The repository contains only hardware design and documentation. There is no
firmware and no data-collection or analysis code.

| Source | What it defines |
|---|---|
| `Lidar Research Hardware.xlsx` | Purchased hardware: ESP32-S3-DevKitC-1 (WROOM-2, 32 MB flash), 2 x Pololu 3415 VL53L1X, SparkFun Qwiic Mux (TCA9548A), SLogic Combo 8, IKEA grey board as target |
| `deliverables/Wiring diagram - two-sensor test setup.pdf` | Pin map: SDA GPIO8, SCL GPIO9, mux 0x70, sensor A on mux ch 0, B on ch 1 (both 0x29), A GPIO1 to ESP32 GPIO4, B GPIO1 to GPIO5, XSHUT and VDD not connected, USB via the port marked UART |
| `deliverables/Procedure - two-sensor crosstalk test.pdf` | Firmware settings, run conditions, logged fields, run matrix, validity checks, statistics and figures |
| `deliverables/RQ3 crosstalk test - design and procedure.pdf` | Same test, plus the crossover prediction |
| `build_rq3.py` | Crossover prediction formula (`crossover()`) |
| `Paper v1 Draft Skeleton.docx` | Whole-paper scope, RQ1 to RQ5 |

### Scope decision

The hardware that has been bought is the two-sensor RQ3 rig. The six-sensor
array, gimbal, TMC2209 drivers and NEMA17 motors in the paper skeleton were
not purchased. Software for RQ1, RQ2 and RQ4 (throughput scaling, gimbal
scanning) is therefore **out of scope until that hardware exists**. It is
listed as a blocked dependency, not written against invented specifications.

### Inconsistencies found

1. **Angle presets.** The procedure lists delta-theta = 0, 6, 10, 14, 20, 24, 30 deg.
   The fixture actually built (pin-index plate) has 0, 5, 10, 15 deg per side
   (delta-theta = 0, 10, 20, 30), and a longer arm with 1 deg steps from 8 to 15 deg
   per side is being designed. The software takes the angle list from a
   config file and never hard-codes it.
2. **Battery voltage.** The RQ3 PDF logs battery voltage. The rig is USB
   powered with no battery, so the newer two-sensor procedure logs room
   temperature instead. The software follows the newer procedure.

## 2. Architecture

```
 Laptop (Python, host/)                        ESP32-S3 (C++, firmware/)
 +-------------------------------+   USB-UART   +-------------------------------+
 | cli.py      operator commands | <----------> | main.cpp    command loop      |
 | session.py  run matrix, order |   text lines | core/ protocol   (pure C++)   |
 | link.py     transport, parse  |              | core/ run_controller (pure)   |
 | protocol.py line format       |              | hw/ int_capture  ISR stamps   |
 | simulator.py fake device      |              | hw/ tca9548a     mux          |
 | analysis.py statistics        |              | hw/ tof_channel  VL53L1X+mux  |
 | figures.py  plots             |              | hw/ diagnostics  scan, test   |
 | geometry.py crossover model   |              +-------------------------------+
 +-------------------------------+                   | I2C 400 kHz   | GPIO4/5
                                                   TCA9548A 0x70    INT_A/INT_B
                                                   ch0: VL53L1X A   (GPIO1 of A, B)
                                                   ch1: VL53L1X B
```

Rules that shape the split:

- Everything that decides *what* happens (command parsing, validation, the
  run state machine) is plain C++ with no Arduino dependency, so it is unit
  tested on the laptop.
- Everything that touches hardware is a thin layer behind an interface
  (`SensorBank`), so the run logic is tested against a fake bank.
- The host never trusts the firmware blindly: every run summary reports
  interrupt counts, overruns, I2C errors and edges from the sensor that
  should have been stopped, and the host rejects runs that fail these.
- A Python device simulator speaks the same protocol, so the whole host
  pipeline (session, logging, analysis, figures) is tested end-to-end
  without hardware.

## 3. Hardware-to-software map

| Hardware | Interface | Software module | Verification |
|---|---|---|---|
| TCA9548A 0x70 | I2C write of channel mask | `hw/tca9548a` | read-back of control register |
| VL53L1X A (ch 0), B (ch 1), 0x29 | I2C via ST ULD (SparkFun library) | `hw/tof_channel` | model ID 0xEACC, boot state, settings read back |
| A GPIO1 -> GPIO4, B GPIO1 -> GPIO5 | falling-edge interrupt, open drain | `hw/int_capture` | idle level, period vs inter-measurement period |
| USB-UART (port marked UART) | UART0, 921600 baud | `main.cpp`, `host/link.py` | `PING`/`INFO` handshake |
| SLogic Combo 8 | none (bench tool) | bring-up checklist | manual, PulseView |

Details: `HARDWARE_INTERFACE.md`.

## 4. Milestones

| # | Milestone | Test that closes it |
|---|---|---|
| M1 | Serial protocol spec + C++ parser/formatter | native C++ unit tests |
| M2 | Run controller state machine | native tests with a fake sensor bank |
| M3 | Hardware layer: mux, VL53L1X channel, interrupt capture, diagnostics | firmware compiles for ESP32-S3; bench checklist (hardware) |
| M4 | Firmware integration (`main.cpp`) | compiles, size report; bench self-test (hardware) |
| M5 | Host protocol, transport, simulator | pytest |
| M6 | Session runner: matrix, shuffling, warm-up, ambient check, CSV logging | pytest end-to-end against the simulator |
| M7 | Analysis, crossover fit, bootstrap, figures | pytest: recovers a known simulated crossover |
| M8 | Hardware bring-up on the real rig | `rig selftest`, logic-analyser checks, one pilot block |

M8 needs the physical rig and is done by the operator using the checklist
in `HARDWARE_INTERFACE.md`.

## 5. Blocked or open items

| Item | Needed from | Effect until resolved |
|---|---|---|
| Final angle presets (longer arm) | fixture redesign | default config uses 0/5/10/15 deg per side |
| Exact ESP32 module variant (flash/PSRAM mode) | label on the module | firmware assumes WROOM-2 octal flash + PSRAM (`opi_opi`) |
| GPIO1 polarity and edge timing on the real board | logic analyser | firmware configures active low, falling edge |
| RQ1/RQ2/RQ4 hardware (6 sensors, gimbal, drivers) | purchase | not implemented |
