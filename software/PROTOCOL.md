# Rig serial protocol, version 1

Author: Jessica

ASCII lines over the board's USB-UART port (marked **UART** on the DevKitC-1; the
port that shows up as a CH340/CH343/CP210x COM port on other boards), 921600 baud, 8N1. Every line ends with `\n`; the firmware ignores `\r`.
Commands are case sensitive, at most 160 characters, and take `key=value`
arguments separated by single spaces.

Implemented by `firmware/lib/rig_core/src/protocol.cpp` (device) and
`host/rig/protocol.py` (host). Both are unit tested against this document.

## Host to device

| Command | Arguments | Reply |
|---|---|---|
| `PING` | none | `OK PING` |
| `INFO` | none | `INFO ...` then `OK INFO` |
| `STATUS` | none | `STATUS state=idle\|running run=<id\|-> buserr=<n>` then `OK STATUS` |
| `SCAN` | none | 9 `SCAN` lines then `OK SCAN` |
| `CFG` | `roi= tb= imp= mode=` (all four) | `CFG roi= tb= imp= mode=` then `OK CFG` |
| `SELFTEST` | none | `TEST` lines, `SELFTEST failed=<n>`, `OK SELFTEST` |
| `RUN` | `id= cond= dur=` | `OK RUN id=<id>`, then `D` lines, then `RUNEND` |
| `ABORT` | none | `RUNEND ... abort=host` (if running) then `OK ABORT` |
| `STOPALL` | none | `OK STOPALL` |
| `LED state=ok\|bad\|off` | `state` | `OK LED`. Green LED on GPIO7 (ok), red on GPIO15 (bad), or both off. Allowed during a run. An older firmware answers `ERR ? code=unknown_cmd`, which the host treats as "no lights fitted" |
| `REG sensor=A\|B addr=0x00DE len=2` | `sensor`, `addr` (hex or decimal), `len` 1 to 16 | `REG sensor=A addr=0x00DE data=0A3C`, then `OK REG`. Raw register read for diagnostics (`rig regs`); changes nothing |
| `TRACE sensor=A or B ms=50..3000 [path=run]` | `sensor`, `ms`, optional `path=run` | `TRACE sensor=A edges=N reads=M overflow=0`, then `TRACE_E sensor=A level=0 t=<us>` per edge (both edges) and `TRACE_R sensor=A t=<us> range= amb= sig=` per result read, then `OK TRACE`. Ranges one sensor alone, handling each falling edge like a run, and records the data-ready line at the pin (`rig edges`). With `path=run` it starts a real run of that sensor instead (`READING` lines, `RUNEND`, then `TRACE` and `TRACE_E` lines, `reads=0`). Needs CFG first |

While a run is active, only `PING`, `STATUS` and `ABORT` are accepted; any
other command gets `ERR <cmd> code=busy`.

### Argument rules

| Key | Values |
|---|---|
| `roi` | 4 to 16, ROI width = height in SPADs, centred on the factory optical centre |
| `tb` | timing budget ms: 20, 33, 50, 100, 200, 500; 15 only with `mode=short` |
| `imp` | inter-measurement period ms, `tb` to 5000 |
| `mode` | `short` or `long` |
| `id` | 1 to 24 characters of `A-Z a-z 0-9 _ -` |
| `cond` | `A` (A ranges, B stopped), `B` (B ranges, A stopped), `AB` (both) |
| `dur` | run length ms, 100 to 3 600 000 |

`CFG` stops both sensors, writes the settings to both and reads every
setting back. `RUN` is refused until a `CFG` has been verified.

## Device to host

| Line | Meaning |
|---|---|
| `BOOT fw=<ver> board=<n16r8\|wroom2> proto=1 reset=<reason>` | after every reset; `reset=brownout` means a power problem |
| `READY` | initialisation finished |
| `LOG level=<I\|W\|E> msg=<text>` | unsolicited message |
| `OK <cmd> [...]` | command accepted or finished |
| `ERR <cmd> code=<code> msg=<text>` | command refused |
| `INFO fw= board= proto= sda= scl= i2c_hz= mux= chA= chB= intA= intB= readyA= readyB= centreA= centreB= verified= roi= tb= imp= mode=` | configuration |
| `SCAN bus=main addrs=<hex,...\|none>` / `SCAN ch=<0-7> addrs=<hex,...\|none\|error>` | bus scan (mux address omitted on channels) |
| `TEST name=<name> result=<PASS\|FAIL\|INFO> detail=<text>` | one self-test check |
| `D <id> <A\|B> <t_int_us> <t_read_us> <range_mm> <status> <signal_kcps> <ambient_kcps> <spads> <stream>` | one reading |
| `RUNEND id= cond= t0= t1= nA= nB= edgesA= edgesB= overrunA= overrunB= rderrA= rderrB= buserr= abort=` | end of run |

`msg=` and `detail=` are always the last field and run to the end of the line.

Error codes: `unknown_cmd`, `bad_args`, `busy`, `not_ready`, `i2c`, `verify`, `int_stuck`.

### Reading fields

| Field | Source |
|---|---|
| `t_int_us` | ESP32 `esp_timer` (us since boot), captured in the GPIO1 falling-edge ISR |
| `t_read_us` | same clock, when the result block had been read |
| `range_mm` | `RESULT__FINAL_CROSSTALK_CORRECTED_RANGE_MM_SD0` |
| `status` | ULD range status, 0 = valid (mapping in `uld_decode.cpp`) |
| `signal_kcps`, `ambient_kcps` | peak signal and ambient rates, all SPADs, kcps |
| `spads` | effective SPAD count |
| `stream` | `RESULT__STREAM_COUNT` (0x008B), raw. On the bench it reads 1 on every result in timed ranging, so it is logged but not used; missed readings are found from gaps in `t_int_us` |

### Run end fields

| Field | Meaning |
|---|---|
| `nA`, `nB` | readings logged |
| `edgesA`, `edgesB` | GPIO1 falling edges seen during the run |
| `overrunA`, `overrunB` | edges that arrived while the previous one was unserviced |
| `rderrA`, `rderrB` | failed result reads |
| `buserr` | failed I2C transactions during the run |
| `abort` | `none`; `host` (ABORT); `i2c` (3 failed reads in a row); `stray` (the stopped sensor raised an interrupt, so it was still ranging); `timeout` (a ranging sensor was silent for 5 inter-measurement periods) |

The host accepts a run only if `abort=none`, `buserr=0`, both `rderr` are 0,
and the non-participating sensor has 0 edges.
