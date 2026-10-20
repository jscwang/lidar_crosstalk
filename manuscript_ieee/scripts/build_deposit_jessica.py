"""Build an anonymized copy of the data-and-code deposit: every occurrence of "Jessica"/"Jessica" and
"Jessica" (in file contents, file names and folder names) becomes "Jessica". Source files are only read,
never modified; this script writes a new, separate zip.

Scope is the same as build_data_software_deposit.py: software/, Jessica-data/pair13_sources/,
manuscript_ieee/scripts/, analysis/, analysis_campaign2/, data_pair13/, excel_diagnostics/, minus build
junk and manuscript text sources.

Run:   python manuscript_ieee/scripts/build_deposit_jessica.py --zip

Author: Jessica
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
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
              "MANIFEST_jessica.csv", "pair13_deposit.zip", "pair13_data_software.zip",
              "pair13_deposit_jessica.zip"}

TEXT_SUFFIX = {
    ".py", ".h", ".hpp", ".c", ".cpp", ".cc", ".ini", ".toml", ".md", ".json", ".txt",
    ".csv", ".cfg", ".yaml", ".yml", ".ps1", ".cff",
}

# Longest / most specific patterns first.
REPLACEMENTS = [
    (re.compile(r"Jessica\s+Li"), "Jessica"),
    (re.compile(r"Jessica"), "Jessica"),
    (re.compile(r"jessica"), "jessica"),
    (re.compile(r"Jessica"), "Jessica"),
    (re.compile(r"jessica"), "jessica"),
]


def wanted(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return False
    if p.suffix.lower() in SKIP_SUFFIX or p.name in SKIP_NAMES:
        return False
    return p.is_file()


def anonymize_text(s: str) -> str:
    for pat, repl in REPLACEMENTS:
        s = pat.sub(repl, s)
    return s


def anonymized_arcname(rel_posix: str) -> str:
    parts = rel_posix.split("/")
    parts = [anonymize_text(part) for part in parts]
    return "/".join(parts)


def anonymize_xlsx(data: bytes) -> bytes:
    """Patch only inline-string / sharedStrings text inside an .xlsx; leave everything else untouched."""
    buf_in = io.BytesIO(data)
    buf_out = io.BytesIO()
    with zipfile.ZipFile(buf_in) as zin, zipfile.ZipFile(buf_out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            raw = zin.read(item.filename)
            if item.filename.startswith("xl/worksheets/") or item.filename == "xl/sharedStrings.xml":
                text = raw.decode("utf-8")
                text = anonymize_text(text)
                raw = text.encode("utf-8")
            zout.writestr(item, raw)
    return buf_out.getvalue()


def md5_bytes(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    files = sorted(p for r in ROOTS for p in r.rglob("*") if wanted(p))
    manifest_path = OUT / "MANIFEST_jessica.csv"
    total = 0
    n_patched = 0
    with open(manifest_path, "w", newline="", encoding="utf-8") as mf:
        w = csv.writer(mf)
        w.writerow(["path", "bytes", "md5"])
        zip_path = OUT / "pair13_deposit_jessica.zip"
        do_zip = "--zip" in sys.argv
        zout = zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) if do_zip else None
        try:
            for p in files:
                rel = p.relative_to(ROOT).as_posix()
                arcname = anonymized_arcname(rel)
                raw = p.read_bytes()
                if p.suffix.lower() == ".xlsx":
                    new_raw = anonymize_xlsx(raw)
                    if new_raw != raw:
                        n_patched += 1
                    raw = new_raw
                elif p.suffix.lower() in TEXT_SUFFIX:
                    try:
                        text = raw.decode("utf-8")
                        new_text = anonymize_text(text)
                        if new_text != text:
                            n_patched += 1
                        raw = new_text.encode("utf-8")
                    except UnicodeDecodeError:
                        pass  # leave as-is if it is not actually UTF-8 text
                size = len(raw)
                total += size
                w.writerow([arcname, size, md5_bytes(raw)])
                if zout is not None:
                    zout.writestr(arcname, raw)
        finally:
            if zout is not None:
                zout.close()
    print(f"{len(files)} files, {total / 1e6:.1f} MB listed in {manifest_path}; {n_patched} files patched")
    if do_zip:
        print(f"wrote {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
