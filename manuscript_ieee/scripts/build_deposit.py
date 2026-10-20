"""Assemble the file list (and, on request, a zip) for a public data-and-code deposit.

Writes deposit/MANIFEST.csv (path, bytes, md5) for everything that belongs in the archive, and with --zip also builds
deposit/pair13_deposit.zip. It never uploads anything: creating the archive record (Zenodo or similar) publishes under the
authors' account and is theirs to do.

Included
  software/                         firmware, host analysis package, configs, tools (no build output, caches or .git)
  Jessica-data/pair13_sources/        the 11 logged sessions, with SOURCES.md and checksums
  manuscript_ieee/                  scripts, analysis tables, figures, tables, merged data (data_pair13), text sources, notes
Excluded
  LaTeX build files, preview images, the manifest and zip themselves, scratch folders (newdata*), and the compiled manuscript PDF.

Run:   python manuscript_ieee/scripts/build_deposit.py            (manifest only)
       python manuscript_ieee/scripts/build_deposit.py --zip      (also the archive, about 220 MB)

Author: Jessica
"""
from __future__ import annotations

import csv
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "manuscript_ieee" / "deposit"

ROOTS = [ROOT / "software", ROOT / "Jessica-data" / "pair13_sources", ROOT / "manuscript_ieee"]
SKIP_DIRS = {".pio", "__pycache__", ".git", "build_preview", ".vscode", "node_modules"}
SKIP_SUFFIX = {".pyc", ".aux", ".log", ".out", ".bbl", ".blg", ".toc", ".fls", ".fdb_latexmk"}
SKIP_NAMES = {"_measure.py", "main.pdf", "MANIFEST.csv", "pair13_deposit.zip"}


def wanted(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return False
    if p.suffix.lower() in SKIP_SUFFIX or p.name in SKIP_NAMES:
        return False
    return p.is_file()


def md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    files = sorted(p for r in ROOTS for p in r.rglob("*") if wanted(p))
    total = 0
    with open(OUT / "MANIFEST.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "bytes", "md5"])
        for p in files:
            size = p.stat().st_size
            total += size
            w.writerow([p.relative_to(ROOT).as_posix(), size, md5(p)])
    print(f"{len(files)} files, {total / 1e6:.1f} MB listed in {OUT / 'MANIFEST.csv'}")
    if "--zip" in sys.argv:
        z = OUT / "pair13_deposit.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                zf.write(p, p.relative_to(ROOT).as_posix())
        print(f"wrote {z} ({z.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
