# Consolidation of the pair13 sessions

Built by `manuscript_ieee/scripts/consolidate_pair13.py`. Each canonical folder below is a single session folder that `rig.analysis.load()` can read. Refill blocks replace the gave-up blocks they were run for; redundant repeats the planner regenerated are dropped.

## nodiv_0p3  (nodiv, 0.3 m)

- main: `0p3_nodiv_main` — 120 blocks, 119 accepted, 1 gave up
  - gaps: d030_t050_r5_roi16
- relabelled refill block `d030_t050_r1_roi16` -> `d030_t050_r5_roi16` (repeat 5); the refill config ran one repeat, so it was numbered 1
- refill: `0p3_nodiv_refill_t5` — 1 accepted; using 1, dropping 0 as redundant
  - used: d030_t050_r5_roi16
- duplicate `B` run in accepted block `d030_t000_r5_roi4`: dropped `r00028` (started 2026-10-07T05:20:41.729+00:00), kept `r00029` (started 2026-10-07T05:36:16.993+00:00)
- built `nodiv_0p3`: 120 accepted blocks, 366 runs, 369418 readings, no gaps

## nodiv_0p6  (nodiv, 0.6 m)

- main: `0p6_nodiv_resquared` — 130 blocks, 130 accepted, 0 gave up
- built `nodiv_0p6`: 130 accepted blocks, 396 runs, 399771 readings, no gaps

## nodiv_0p9  (nodiv, 0.9 m)

- main: `0p9_nodiv_main` — 120 blocks, 113 accepted, 7 gave up
  - gaps: d090_t080_r2_roi4, d090_t080_r3_roi4, d090_t080_r4_roi4, d090_t100_r2_roi4, d090_t100_r3_roi4, d090_t100_r4_roi4, d090_t100_r5_roi4
- refill: `0p9_nodiv_refill_t8` — 5 accepted; using 3, dropping 2 as redundant
  - used: d090_t080_r2_roi4, d090_t080_r3_roi4, d090_t080_r4_roi4
  - dropped (already present and accepted in the main sweep): d090_t080_r1_roi4, d090_t080_r5_roi4
- refill: `0p9_nodiv_refill_t10` — 5 accepted; using 4, dropping 1 as redundant
  - used: d090_t100_r2_roi4, d090_t100_r3_roi4, d090_t100_r4_roi4, d090_t100_r5_roi4
  - dropped (already present and accepted in the main sweep): d090_t100_r1_roi4
- built `nodiv_0p9`: 120 accepted blocks, 363 runs, 366306 readings, no gaps

## div_0p3  (div, 0.3 m)

- main: `0p3_div` — 20 blocks, 20 accepted, 0 gave up
- built `div_0p3`: 20 accepted blocks, 60 runs, 60547 readings, no gaps

## div_0p6  (div, 0.6 m)

- main: `0p6_div_resquared` — 30 blocks, 30 accepted, 0 gave up
- built `div_0p6`: 30 accepted blocks, 96 runs, 96889 readings, no gaps

## div_0p9  (div, 0.9 m)

- main: `0p9_div` — 20 blocks, 20 accepted, 0 gave up
- built `div_0p9`: 20 accepted blocks, 60 runs, 60526 readings, no gaps

## swap_0p9  (swap, 0.9 m)

- main: `0p9_swap_main` — 130 blocks, 129 accepted, 1 gave up
  - gaps: d090_t010_r2_roi4
- refill: `0p9_swap_refill_t010_roi4` — 5 accepted; using 1, dropping 4 as redundant
  - used: d090_t010_r2_roi4
  - dropped (already present and accepted in the main sweep): d090_t010_r1_roi4, d090_t010_r3_roi4, d090_t010_r4_roi4, d090_t010_r5_roi4
- built `swap_0p9`: 130 accepted blocks, 399 runs, 402915 readings, no gaps

## div_swap_0p9  (div_swap, 0.9 m)

- main: `0p9_divider_swap_main` — 30 blocks, 26 accepted, 4 gave up
  - gaps: d090_t020_r2_roi4, d090_t020_r3_roi4, d090_t020_r4_roi4, d090_t020_r5_roi4
- refill: `0p9_divider_swap_refill_t020_roi4` — 5 accepted; using 4, dropping 1 as redundant
  - used: d090_t020_r2_roi4, d090_t020_r3_roi4, d090_t020_r4_roi4, d090_t020_r5_roi4
  - dropped (already present and accepted in the main sweep): d090_t020_r1_roi4
- built `div_swap_0p9`: 30 accepted blocks, 90 runs, 90843 readings, no gaps

## div_swap_0p6  (div_swap, 0.6 m)

- main: `0p6_divider_swap` — 30 blocks, 30 accepted, 0 gave up
- built `div_swap_0p6`: 30 accepted blocks, 96 runs, 96896 readings, no gaps

## swap_0p6  (swap, 0.6 m)

- main: `0p6_swap_main` — 120 blocks, 120 accepted, 0 gave up
- built `swap_0p6`: 120 accepted blocks, 372 runs, 375501 readings, no gaps

## div_swap_0p3  (div_swap, 0.3 m)

- main: `0p3_divider_swap` — 30 blocks, 30 accepted, 0 gave up
- built `div_swap_0p3`: 30 accepted blocks, 90 runs, 90773 readings, no gaps

## swap_0p3  (swap, 0.3 m)

- main: `0p3_swap_main` — 130 blocks, 130 accepted, 0 gave up
- built `swap_0p3`: 130 accepted blocks, 393 runs, 395696 readings, no gaps

## Result

- built: nodiv_0p3, nodiv_0p6, nodiv_0p9, div_0p3, div_0p6, div_0p9, swap_0p9, div_swap_0p9, div_swap_0p6, swap_0p6, div_swap_0p3, swap_0p3
