# Swap sweeps: units exchanged, 1 degree per side added

Author: Jessica. 12 October 2026.

Three run configs, one per distance. Each is the earlier config for that distance with exactly four things changed
(checked by loading both and comparing every field):

| Changed | From | To |
|---|---|---|
| `name` (this becomes the session folder name) | `rq3-jessica-0p3-pair13` | `rq3-jessica-0p3-pair13-swap` (same at 0.6 and 0.9 m) |
| `theta_per_side_deg` | 0, 2, 3, ... 12 | 0, **1**, 2, 3, ... 12 |
| `square_offset_mm` | +2.5 (+3.0 at 0.9 m) | 0.0, see step 3 below |
| `notes` | empty | says which unit is in which position; it is saved in `session.json` |

Everything else is unchanged: both zones, 5 repeats, 30 s runs, the seed, the 600 s warm-up, the expected ranges and
tolerances. The program code is unchanged; only these config files are new.

| Distance | Config | Session folder (inside `data/swap/`) |
|---|---|---|
| 0.3 m | `configs/swap/rq3_jessica_0p3_pair13_swap.json` | `rq3-jessica-0p3-pair13-swap_<date>_<time>` |
| 0.6 m | `configs/swap/rq3_jessica_0p6_pair13_swap.json` | `rq3-jessica-0p6-pair13-swap_<date>_<time>` |
| 0.9 m | `configs/swap/rq3_jessica_0p9_pair13_swap.json` | `rq3-jessica-0p9-pair13-swap_<date>_<time>` |

## Before each distance

1. **Swap the units.** Unit 1 goes in position A and unit 3 in position B (the earlier sweeps had unit 3 in A and unit 1
   in B). The software knows only positions A and B, so write down which unit is where, and take a photo of the labels.
2. **Self-test** must pass (17 of 17) after the handling, and the board must be squared with the tape, measured from
   the laser surface to the board surface as before.
3. **Measure B minus A** with the board squared and the pucks at 0 degrees:
   `python tools/live_ranges.py 290 --port COM7` (use 570 at 0.6 m and 891 at 0.9 m). Write down both ranges and
   B minus A. Before the swap B minus A was about +2.5 mm (+3.0 mm at 0.9 m). If it is now about -2.5, the offset follows
   the units; if it is still about +2.5, it follows the position (the mounting, the path or the board). This is the
   first evidence for the swap question, so keep the number. The config starts at 0.0, which is within `square_tol_mm` (10 mm) of either case, so
   the run works without editing it; you may put the measured value in `square_offset_mm` if you like.

## Run

```
python -m rig session --guided --port COM7 --config configs/swap/rq3_jessica_0p3_pair13_swap.json --out data/swap
python -m rig session --guided --port COM7 --config configs/swap/rq3_jessica_0p6_pair13_swap.json --out data/swap
python -m rig session --guided --port COM7 --config configs/swap/rq3_jessica_0p9_pair13_swap.json --out data/swap
```

## Drift check (optional, about 30 minutes per distance)

`rq3_jessica_0p3_pair13_swap_drift.json` (and the 0.6 and 0.9 m versions) repeat three of the sweep's angles, 12, 6 and 0
degrees per side, in that order, with three repeats of both zones, 18 blocks and about 0.5 hours of ranging. Run it
directly after the swap sweep for the same distance, with nothing on the rig touched in between: the same units, board and
lighting. The sweep ends at 12 degrees, so the first angle needs no pin move; then move the pins down to 6 and 0.

```
python -m rig session --guided --port COM7 --config configs/swap/rq3_jessica_0p3_pair13_swap_drift.json --out data/swap
```

Add `--no-warmup` only if the rig has been on and ranging since the sweep. The adaptive stop is off in these configs, so
no angle is skipped. The rig's own analysis prints a crossover table for the session; ignore it, because three angles
cannot fix a crossover. The check is read by comparing each cell's mean with the same cell of the sweep: a difference
larger than the spread of the blocks means the rig or the room drifted during the sweep. Do not merge the drift session
into the sweep.

Do not use `--tag`: tagged sessions are left out of the crossover fit. Each distance now has 130 blocks instead of 120,
about 3.4 hours of ranging (3.1 before), plus the warm-up. Adding 1 degree per side puts a measurement at an angle of
2 degrees between the sensors, which the earlier sweeps did not have.
