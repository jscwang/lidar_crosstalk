"""Copy every logged session that feeds the manuscript into a permanently named folder, with a checksum manifest.

Why: the sessions arrived through scratch folders (`newdata`, `newdata1`, `newdata2`, `newdata2-session`) that were reused,
overwritten and once deleted during the project. The consolidation must not depend on names like those. This script copies
(never moves) each session to `Jessica-data/pair13_sources/<name>/`, leaves the scratch folders and every original untouched,
and writes `SOURCES.md` listing the original path, file sizes and MD5 of each CSV.

Run:   python manuscript_ieee/scripts/archive_sources.py
Out:   Jessica-data/pair13_sources/<name>/{readings,runs,blocks,warmup}.csv, session.json, events.log
       Jessica-data/pair13_sources/SOURCES.md

Author: Jessica
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "Jessica-data"
DST = SRC / "pair13_sources"

FILES = ("readings.csv", "runs.csv", "blocks.csv", "warmup.csv", "session.json", "events.log")

# permanent name -> (original folder, what it is)
SESSIONS = {
    "0p3_nodiv_main": (SRC / "0.3m-main-sweep",
                       "0.3 m main sweep, 7 Oct 2026 (copied from newdata2/readings.zip on 10 Oct)"),
    "0p3_nodiv_refill_t5": (SRC / "rerun-0.3m-5degrees" / "rq3-jessica-0p3-pair13_refill_20261007_163108",
                            "0.3 m refill of the 5 deg 16x16 repeat-5 block (configured with one repeat, so numbered 1)"),
    "0p6_nodiv_main": (SRC, "0.6 m main sweep, 6 Oct 2026 (files at the root of Jessica-data, restored 7 Oct)"),
    "0p6_nodiv_refill_t12": (SRC / "newdata2", "0.6 m refill, 12 deg, both zones, 10 Oct 2026"),
    "0p9_nodiv_main": (SRC / "newdata1", "0.9 m main sweep, 9 Oct 2026"),
    "0p9_nodiv_refill_t8": (SRC / "0.9m-8deg-refill" / "rq3-jessica-0p9-pair13-refill-t8t10-roi4_refill_20261009_191349",
                            "0.9 m refill, 8 deg roi4 (its 10 deg half was skipped by the adaptive stop)"),
    "0p9_nodiv_refill_t10": (SRC / "newdata2-session", "0.9 m refill, 10 deg roi4, adaptive stop off, 10 Oct 2026"),
    "0p3_div": (SRC / "0.3m-divider" / "rq3-jessica-0p3-pair13-divider_divider_20261007_201317",
                "0.3 m divider check"),
    "0p6_div_first": (SRC / "0.6m-divider" / "rq3-jessica-0p6-divider_divider_20261007_224124",
                      "0.6 m divider check, first run (strip protruding more); kept as a replicate"),
    "0p6_div_second": (SRC / "newdata",
                       "0.6 m divider check, second run (strip protruding less), 8 Oct 04:16 UTC; the set used"),
    "0p9_div": (SRC / "0.9m-divider" / "rq3-jessica-0p9-pair13-divider_divider_20261008_210057", "0.9 m divider check"),
    "0p9_swap_main": (SRC / "blocks 90cm Swap",
                      "0.9 m swap sweep, 12 Oct 2026: unit 1 in position A, unit 3 in position B (the earlier 0.9 m "
                      "sessions had unit 3 in A, unit 1 in B); adds theta=1 deg to the usual sweep"),
    "0p9_swap_refill_t010_roi4": (SRC / "90cm Swap 1 Degree Rerun",
                                  "0.9 m swap refill, 13 Oct 2026: d090_t010_r2_roi4, which gave up on a "
                                  "solo-ambient-B drift in the swap sweep"),
    "0p9_divider_swap_main": (SRC / "90cm divider swap 2 dgree failed",
                              "0.9 m divider check with the swap, 12 Oct 2026: unit 1 in A, unit 3 in B, "
                              "theta 1/2/5 deg per side. 4 roi4 blocks at theta=2 gave up on a sustained "
                              "one-direction rise in sensor B's solo ambient (5.92 to 6.5-7.1 kcps over the "
                              "four blocks); not seen at theta=1 or 5, and not reproduced in the standalone "
                              "refill, so read as a session-time disturbance, not the divider's geometry"),
    "0p9_divider_swap_refill_t020_roi4": (SRC / "90cm divider swamp refill 2 degree",
                                          "0.9 m divider-swap refill, 13 Oct 2026: the four theta=2 roi4 "
                                          "blocks that gave up in the main divider-swap session"),
    "0p6_divider_swap": (SRC / "60cm Swap with Divider",
                         "0.6 m divider check with the swap, 13 Oct 2026: unit 1 in A, unit 3 in B, theta "
                         "1/2/5 deg per side, run after Jessica re-squared the board (see pair13_sources/"
                         "SOURCES.md and MANUSCRIPT_PROGRESS.md on the 0.6 m board-position finding). 30/30 "
                         "accepted, no refill needed"),
    "0p6_swap_main": (SRC / "60cm Swap no divider",
                      "0.6 m swap sweep, 13 Oct 2026: unit 1 in position A, unit 3 in position B, theta 0-12 "
                      "deg per side, same re-squared board as the divider-swap session. 120/120 accepted "
                      "(theta=12 skipped by the adaptive stop, as in the original nodiv_0p6 session), no "
                      "refill needed"),
    "0p3_divider_swap": (SRC / "30cm swap with Divider",
                        "0.3 m divider check with the swap, 13 Oct 2026: unit 1 in A, unit 3 in B, theta "
                        "1/2/5 deg per side, tape checked square. 30/30 accepted, 0 rejected attempts, the "
                        "cleanest swap session so far"),
    "0p3_swap_main": (SRC / "30cm swap no divider",
                      "0.3 m swap sweep, 14 Oct 2026: unit 1 in position A, unit 3 in position B, theta 0-12 "
                      "deg per side, tape checked square, same swap as the 0.3 m divider-swap session. "
                      "130/130 accepted, 1 rejected run (a single crosstalk-ratio retry at theta=12, zone 4, "
                      "sensor A, within the streak tolerance), 0 skipped, no refill needed"),
}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    DST.mkdir(exist_ok=True)
    lines = ["# pair13 source sessions", "",
             "Copies of every logged session used in the manuscript, made by `manuscript_ieee/scripts/archive_sources.py`. "
             "The originals (scratch folders included) are untouched. MD5 is of the copy, equal to the original at copy time.", ""]
    for name, (origin, note) in SESSIONS.items():
        out = DST / name
        out.mkdir(exist_ok=True)
        lines += [f"## {name}", f"{note}", f"- original: `{origin}`"]
        for fn in FILES:
            s = origin / fn
            if not s.exists():
                if fn == "events.log":
                    lines.append(f"- {fn}: not present in the original")
                    continue
                raise FileNotFoundError(s)
            d = out / fn
            if not d.exists():
                shutil.copy2(s, d)
            if md5(s) != md5(d):
                raise RuntimeError(f"copy of {s} differs from the original")
            lines.append(f"- `{fn}`: {d.stat().st_size:,} bytes, md5 {md5(d)}")
        lines.append("")
    (DST / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"archived {len(SESSIONS)} sessions to {DST}")


if __name__ == "__main__":
    main()
