"""Build canonical pair13 session folders for the IEEE manuscript, from the sessions Jessica logged.

The pair13 campaign (unit 3 in position A, unit 1 in position B) was run as one main angle sweep per
distance plus, where blocks gave up on an ambient-drift check, a separate refill session. The divider
check was run as its own session at each distance. The analysis code (rig/analysis.py) reads one session
folder at a time, so this script merges each distance's sessions into a single folder it can read.

Two rules matter, both because of how rig.analysis works:

  * block_id must stay unique. pair_effects() groups by (block_id, sensor) and skips any group that does
    not hold exactly one solo run and one A+B run, so appending a refill block next to the gave-up block
    it replaces would silently drop that block from the results. A refill block therefore replaces the
    original rows rather than joining them.
  * run_id must stay unique. Every session numbers its runs from r00001, so refill run ids collide with
    the main sweep's. Refill runs are renumbered with a per-source prefix, in runs.csv and readings.csv
    together.

A refill session reruns every repeat at its angle, because the session planner cannot target one repeat.
Only the repeats that were actually missing are taken; the rest are dropped as redundant, and listed in
the report so the choice is visible.

Run:   python manuscript_ieee/scripts/consolidate_pair13.py
Out:   manuscript_ieee/data_pair13/<series>_<distance>/{readings,runs,blocks,warmup}.csv, session.json
       manuscript_ieee/data_pair13/consolidation_report.md

Author: Jessica
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent                      # manuscript_ieee/
ROOT = PROJECT.parent                      # E:/work/freelance/Jessica
SRC = ROOT / "Jessica-data"
OUT = PROJECT / "data_pair13"


@dataclass
class Source:
    """One logged session folder that feeds a canonical folder."""
    path: Path
    role: str                              # "main", "refill" or "only"
    note: str = ""
    relabel: dict = field(default_factory=dict)   # refill block_id -> the gave-up block_id it replaces


@dataclass
class Target:
    """One canonical folder to build."""
    name: str
    series: str                            # "nodiv" or "div"
    distance_m: float
    sources: list = field(default_factory=list)


ARCH = SRC / "pair13_sources"      # permanent copies made by archive_sources.py; scratch folders are not read

TARGETS = [
    Target("nodiv_0p3", "nodiv", 0.3, [
        Source(ARCH / "0p3_nodiv_main", "main", "0.3 m main sweep, 7 October, resumed once"),
        Source(ARCH / "0p3_nodiv_refill_t5", "refill",
               "refill of d030_t050_r5_roi16, which gave up on a solo-ambient-B drift",
               relabel={"d030_t050_r1_roi16": "d030_t050_r5_roi16"}),
    ]),
    Target("nodiv_0p6", "nodiv", 0.6, [
        Source(ARCH / "0p6_nodiv_resquared", "only",
               "0.6 m main sweep, 17 October, rerun after Jessica found the original 0.6 m board was closer and "
               "not fully square (see MANUSCRIPT_PROGRESS.md); same unit positions (unit 3 at A, unit 1 at B), "
               "re-squared to the same true distance as the swap-campaign board, 13 theta levels (0-12 deg, "
               "1 deg steps, finer than the original 12-level sweep). 130/130 accepted, no refill needed. "
               "Replaces the original 0.6 m sweep (kept in pair13_sources/0p6_nodiv_main / "
               "0p6_nodiv_refill_t12 for the record)."),
    ]),
    Target("nodiv_0p9", "nodiv", 0.9, [
        Source(ARCH / "0p9_nodiv_main", "main", "0.9 m main sweep, 9 October"),
        Source(ARCH / "0p9_nodiv_refill_t8", "refill",
               "refill of the three 8 deg roi4 blocks; its 10 deg half was skipped by the adaptive stop"),
        Source(ARCH / "0p9_nodiv_refill_t10", "refill",
               "refill of the four 10 deg roi4 blocks, rerun with the adaptive stop off"),
    ]),
    Target("div_0p3", "div", 0.3, [
        Source(ARCH / "0p3_div", "only", "0.3 m divider check"),
    ]),
    Target("div_0p6", "div", 0.6, [
        Source(ARCH / "0p6_div_resquared", "only",
               "0.6 m divider check, 17 October, rerun on the same re-squared board as the no-divider rerun; "
               "unit 3 at A, unit 1 at B; theta 1/2/5 deg per side (adds theta=1 deg to the original "
               "divider check's theta 2/5). 30/30 accepted, no refill needed. Replaces the original 0.6 m "
               "divider check (kept in pair13_sources/0p6_div_first and 0p6_div_second for the record)."),
    ]),
    Target("div_0p9", "div", 0.9, [
        Source(ARCH / "0p9_div", "only", "0.9 m divider check"),
    ]),
    Target("swap_0p9", "swap", 0.9, [
        Source(ARCH / "0p9_swap_main", "main",
               "0.9 m swap sweep, 12 October: unit 1 in position A, unit 3 in position B (the earlier 0.9 m "
               "sessions had unit 3 in A, unit 1 in B); adds theta=1 deg to the usual sweep. Config "
               "square_offset_mm was left at +3.0, the pre-swap value; not yet confirmed against the tape"),
        Source(ARCH / "0p9_swap_refill_t010_roi4", "refill",
               "refill of d090_t010_r2_roi4, which gave up on a solo-ambient-B drift"),
    ]),
    Target("div_swap_0p9", "div_swap", 0.9, [
        Source(ARCH / "0p9_divider_swap_main", "main",
               "0.9 m divider check with the swap, 12 October: unit 1 in A, unit 3 in B, theta 1/2/5 deg "
               "per side. The four theta=2 roi4 blocks that gave up are read as a session-time disturbance "
               "in sensor B's solo ambient, not the divider's geometry (see pair13_sources/SOURCES.md)"),
        Source(ARCH / "0p9_divider_swap_refill_t020_roi4", "refill",
               "refill of the four theta=2 roi4 blocks"),
    ]),
    Target("div_swap_0p6", "div_swap", 0.6, [
        Source(ARCH / "0p6_divider_swap", "only",
               "0.6 m divider check with the swap, 13 October: unit 1 in A, unit 3 in B, run after Jessica "
               "re-squared the board; the true board distance differs measurably from the original nodiv_0p6 "
               "session (see MANUSCRIPT_PROGRESS.md)"),
    ]),
    Target("swap_0p6", "swap", 0.6, [
        Source(ARCH / "0p6_swap_main", "only",
               "0.6 m swap sweep, 13 October: unit 1 in A, unit 3 in B, same re-squared board as "
               "div_swap_0p6; the true board distance differs measurably from the original nodiv_0p6 session "
               "(see MANUSCRIPT_PROGRESS.md)"),
    ]),
    Target("div_swap_0p3", "div_swap", 0.3, [
        Source(ARCH / "0p3_divider_swap", "only",
               "0.3 m divider check with the swap, 13 October: unit 1 in A, unit 3 in B, tape checked "
               "square"),
    ]),
    Target("swap_0p3", "swap", 0.3, [
        Source(ARCH / "0p3_swap_main", "only",
               "0.3 m swap sweep, 14 October: unit 1 in A, unit 3 in B, tape checked square, same swap as "
               "div_swap_0p3. 130/130 accepted, 1 rejected run, no refill needed"),
    ]),
]

CSVS = ("readings.csv", "runs.csv", "blocks.csv", "warmup.csv")


def read_session(path: Path) -> dict:
    out = {}
    for name in CSVS:
        f = path / name
        if not f.exists():
            raise FileNotFoundError(f"{f} is missing")
        kw = {"keep_default_na": False, "dtype": {"tag": str}} if name in ("runs.csv", "blocks.csv") else {}
        out[name] = pd.read_csv(f, **kw)
    out["session.json"] = json.loads((path / "session.json").read_text(encoding="utf-8"))
    return out


def accepted_block_ids(blocks: pd.DataFrame) -> set:
    return set(blocks.loc[blocks["accepted"].astype(str) == "True", "block_id"])


def gave_up_block_ids(blocks: pd.DataFrame) -> set:
    """Blocks with no accepted attempt: every attempt was rejected, or the give-up row was written."""
    return set(blocks["block_id"]) - accepted_block_ids(blocks)


def renumber(runs: pd.DataFrame, readings: pd.DataFrame, prefix: str):
    """Give every run a globally unique id, in runs.csv and readings.csv together."""
    mapping = {old: f"{prefix}{old}" for old in runs["run_id"].unique()}
    runs = runs.copy()
    readings = readings.copy()
    runs["run_id"] = runs["run_id"].map(mapping)
    readings["run_id"] = readings["run_id"].map(lambda r: mapping.get(r, r))
    return runs, readings


def build(target: Target, report: list) -> bool:
    report.append(f"\n## {target.name}  ({target.series}, {target.distance_m:g} m)\n")
    missing = [s for s in target.sources if not (s.path / "blocks.csv").exists()]
    if missing or not target.sources:
        for s in missing:
            report.append(f"- MISSING source: `{s.path}`")
        report.append(f"- **{target.name} NOT BUILT.**")
        return False

    main = next((s for s in target.sources if s.role in ("main", "only")), None)
    if main is None:
        report.append("- No main session on disk, only refills. **NOT BUILT.**")
        for s in target.sources:
            report.append(f"- on disk: {s.role} `{s.path.name}` ({s.note})")
        return False

    base = read_session(main.path)
    blocks, runs, readings, warmup = (base["blocks.csv"], base["runs.csv"],
                                      base["readings.csv"], base["warmup.csv"])
    blocks = blocks.assign(provenance="main")
    runs = runs.assign(provenance="main")
    have = accepted_block_ids(blocks)
    gaps = gave_up_block_ids(blocks)
    report.append(f"- main: `{main.path.name}` — {len(set(blocks['block_id']))} blocks, "
                  f"{len(have)} accepted, {len(gaps)} gave up")
    if gaps:
        report.append(f"  - gaps: {', '.join(sorted(gaps))}")

    for i, s in enumerate(s for s in target.sources if s.role == "refill"):
        r = read_session(s.path)
        if s.relabel:
            # The refill session was configured with one repeat, so its block carries repeat number 1 although it
            # was run to replace a different repeat. Relabel block_id and the repeat column so it takes that place.
            for old_id, new_id in s.relabel.items():
                new_rep = int(new_id.split("_r")[1].split("_")[0])
                for nm in ("blocks.csv", "runs.csv"):
                    df = r[nm]
                    hit = df["block_id"] == old_id
                    df.loc[hit, "block_id"] = new_id
                    df.loc[hit, "repeat"] = new_rep
                report.append(f"- relabelled refill block `{old_id}` -> `{new_id}` (repeat {new_rep}); "
                              f"the refill config ran one repeat, so it was numbered 1")
        r_blocks = r["blocks.csv"]
        r_ok = accepted_block_ids(r_blocks)
        take = sorted(r_ok & gaps)                  # only what the main sweep is actually missing
        drop = sorted(r_ok - gaps)                  # repeats the planner regenerated but we already have
        report.append(f"- refill: `{s.path.name}` — {len(r_ok)} accepted; "
                      f"using {len(take)}, dropping {len(drop)} as redundant")
        if take:
            report.append(f"  - used: {', '.join(take)}")
        if drop:
            report.append(f"  - dropped (already present and accepted in the main sweep): {', '.join(drop)}")
        if not take:
            continue

        r_blocks = r_blocks[r_blocks["block_id"].isin(take)]
        r_runs = r["runs.csv"][r["runs.csv"]["block_id"].isin(take)]
        r_readings = r["readings.csv"][r["readings.csv"]["run_id"].isin(set(r_runs["run_id"]))]
        r_runs, r_readings = renumber(r_runs, r_readings, f"f{i + 1}")
        r_blocks = r_blocks.assign(provenance=f"refill:{s.path.name}")
        r_runs = r_runs.assign(provenance=f"refill:{s.path.name}")

        # Replace, never append: drop every row of the gave-up block before adding the refill's rows.
        blocks = blocks[~blocks["block_id"].isin(take)]
        dead_runs = set(runs.loc[runs["block_id"].isin(take), "run_id"])
        runs = runs[~runs["block_id"].isin(take)]
        readings = readings[~readings["run_id"].isin(dead_runs)]

        blocks = pd.concat([blocks, r_blocks], ignore_index=True)
        runs = pd.concat([runs, r_runs], ignore_index=True)
        readings = pd.concat([readings, r_readings], ignore_index=True)
        gaps -= set(take)

    # ---- one run per condition in each accepted block. A session interrupted between two runs of a block can leave
    # an earlier run of the same condition beside the one the block was judged on. rig.analysis.pair_effects skips
    # a (block, sensor) that has two solo runs, which would leave that block with one sensor in the pooled value.
    # Keep the latest-started run of each condition and log what is dropped; the source sessions are untouched.
    ok_pairs = blocks.loc[blocks["accepted"].astype(str) == "True", ["block_id", "attempt"]]
    acc_runs = runs[runs["accepted"].astype(str) == "True"].merge(ok_pairs, on=["block_id", "attempt"])
    dup = acc_runs[acc_runs.duplicated(["block_id", "attempt", "condition"], keep=False)]
    dropped_runs = []
    for (bid, att, cond), g in dup.groupby(["block_id", "attempt", "condition"]):
        g = g.sort_values("start_utc")
        for _, r in g.iloc[:-1].iterrows():
            dropped_runs.append(r["run_id"])
            report.append(f"- duplicate `{cond}` run in accepted block `{bid}`: dropped `{r['run_id']}` "
                          f"(started {r['start_utc']}), kept `{g.iloc[-1]['run_id']}` "
                          f"(started {g.iloc[-1]['start_utc']})")
    if dropped_runs:
        runs = runs[~runs["run_id"].isin(dropped_runs)]
        readings = readings[~readings["run_id"].isin(dropped_runs)]

    # ---- checks that the merged folder is internally consistent
    problems = []
    if runs["run_id"].duplicated().any():
        problems.append("duplicate run_id after merge")
    acc = blocks[blocks["accepted"].astype(str) == "True"]
    if acc["block_id"].duplicated().any():
        problems.append("a block_id is accepted twice")
    orphan = set(readings["run_id"]) - set(runs["run_id"])
    if orphan:
        problems.append(f"{len(orphan)} reading run_ids with no row in runs.csv")
    for p in problems:
        report.append(f"  - **PROBLEM: {p}**")

    out = OUT / target.name
    out.mkdir(parents=True, exist_ok=True)
    readings.to_csv(out / "readings.csv", index=False)
    runs.to_csv(out / "runs.csv", index=False)
    blocks.to_csv(out / "blocks.csv", index=False)
    warmup.to_csv(out / "warmup.csv", index=False)
    meta = base["session.json"]
    meta["_consolidated"] = {
        "target": target.name, "series": target.series, "distance_m": target.distance_m,
        "sources": [{"path": s.path.relative_to(SRC).as_posix(), "role": s.role, "note": s.note} for s in target.sources],
    }
    (out / "session.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    report.append(f"- built `{out.name}`: {len(acc)} accepted blocks, {len(runs)} runs, "
                  f"{len(readings)} readings"
                  + (f", {len(gaps)} gap(s) still unfilled: {', '.join(sorted(gaps))}" if gaps else
                     ", no gaps"))
    return not problems


def main() -> int:
    report = ["# Consolidation of the pair13 sessions",
              "",
              "Built by `manuscript_ieee/scripts/consolidate_pair13.py`. Each canonical folder below is a "
              "single session folder that `rig.analysis.load()` can read. Refill blocks replace the "
              "gave-up blocks they were run for; redundant repeats the planner regenerated are dropped.",
              ]
    built = []
    for t in TARGETS:
        if build(t, report):
            built.append(t.name)
    report.append("\n## Result\n")
    report.append(f"- built: {', '.join(built) if built else 'none'}")
    not_built = [t.name for t in TARGETS if t.name not in built]
    if not_built:
        report.append(f"- **not built: {', '.join(not_built)}**")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "consolidation_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if not not_built else 1


if __name__ == "__main__":
    sys.exit(main())
