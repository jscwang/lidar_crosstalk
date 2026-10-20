"""Assemble a data-and-code-only deposit for Jessica (she already has the LaTeX/Word manuscript files).

Writes deposit/MANIFEST_data_software.csv (path, bytes, md5) and, with --zip, deposit/pair13_data_software.zip.
Never uploads anything.

Included
  software/                              firmware, host analysis package, configs, tools
  Jessica-data/pair13_sources/              the 11 raw logged sessions, with SOURCES.md and checksums
  manuscript_ieee/scripts/                analysis codebase (python)
  manuscript_ieee/analysis/               derived analysis tables (CSV/MD)
  manuscript_ieee/analysis_campaign2/     derived analysis tables, campaign 2
  manuscript_ieee/data_pair13/            merged/consolidated data tables
  manuscript_ieee/excel_diagnostics/      raw crosstalk diagnostics workbook
Excluded
  All manuscript text sources (.docx, .pdf, .tex, .bib), figures rendered for the paper, build junk,
  scratch folders, caches, and the arxiv/ draft-history folder.

Run:   python manuscript_ieee/scripts/build_data_software_deposit.py            (manifest only)
       python manuscript_ieee/scripts/build_data_software_deposit.py --zip      (also the archive)

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

ROOTS = [
    ROOT / "software",
    ROOT / "Jessica-data" / "pair13_sources",
    ROOT / "manuscript_ieee" / "scripts",
    ROOT / "manuscript_ieee" / "analysis",
    ROOT / "manuscript_ieee" / "analysis_campaign2",
    ROOT / "manuscript_ieee" / "data_pair13",
    ROOT / "manuscript_ieee" / "excel_diagnostics",
]
SKIP_DIRS = {".pio", "__pycache__", ".git", "build_preview", ".vscode", "node_modules"}
SKIP_SUFFIX = {
    ".pyc", ".aux", ".log", ".out", ".bbl", ".blg", ".toc", ".fls", ".fdb_latexmk",
    ".docx", ".pdf", ".tex", ".bib", ".emf", ".bak",
}
SKIP_NAMES = {"_measure.py", "main.pdf", "MANIFEST.csv", "MANIFEST_data_software.csv",
              "pair13_deposit.zip", "pair13_data_software.zip"}


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
    manifest_path = OUT / "MANIFEST_data_software.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "bytes", "md5"])
        for p in files:
            size = p.stat().st_size
            total += size
            w.writerow([p.relative_to(ROOT).as_posix(), size, md5(p)])
    print(f"{len(files)} files, {total / 1e6:.1f} MB listed in {manifest_path}")
    if "--zip" in sys.argv:
        z = OUT / "pair13_data_software.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files:
                zf.write(p, p.relative_to(ROOT).as_posix())
        print(f"wrote {z} ({z.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
