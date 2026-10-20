"""Typeset the letter's two tables on their own and export each as a vector PDF and a 600 dpi PNG.

The tables are the generated files tables/table_crossover.tex (Table I) and tables/table_divider.tex
(Table S1), so the images match the PDF exactly. The caption is left out (journals ask for captions in the
text, not in the artwork); the footnote line under Table I is kept.

Run:   python manuscript_ieee/scripts/make_table_images.py
Out:   manuscript_ieee/figures/table_crossover.pdf / .png   and   table_divider.pdf / .png

Author: Jessica
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"

WRAPPER = r"""\documentclass[border=6pt,varwidth=7.2in]{standalone}
\usepackage{amsmath,amssymb,booktabs,siunitx}
\usepackage[pdfauthor={Jessica},pdfcreator={},pdfproducer={}]{hyperref}
\sisetup{range-phrase=--, range-units=single, group-separator={,}}
\pdfsuppressptexinfo=-1
\newcommand{\dth}{\Delta\theta}
\makeatletter
\renewenvironment{table}[1][]{\par\centering}{\par}
\renewenvironment{table*}[1][]{\par\centering}{\par}
\renewcommand{\caption}[1]{}
\makeatother
\begin{document}
\input{%s}
\end{document}
"""


def build(name: str, tex: Path):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # the footnote of Table I refers to a numbered section of the LaTeX letter; as a stand-alone image
        # (and in the Word file, whose headings are unnumbered) it has to name the section instead
        body = tex.read_text(encoding="utf-8").replace("Section~" + chr(92) + "ref{sec:method}", "the Methodology section")
        (td / f"{name}_body.tex").write_text(body, encoding="utf-8")
        (td / f"{name}.tex").write_text(WRAPPER % f"{name}_body.tex", encoding="utf-8")
        for _ in range(2):
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{name}.tex"], cwd=td,
                               capture_output=True, text=True)
        pdf = td / f"{name}.pdf"
        if not pdf.exists():
            raise SystemExit(f"pdflatex failed for {name}:\n{r.stdout[-1500:]}")
        shutil.copy(pdf, FIG / f"{name}.pdf")
    doc = fitz.open(FIG / f"{name}.pdf")
    pix = doc[0].get_pixmap(dpi=600, alpha=False)
    pix.set_dpi(600, 600)
    pix.save(FIG / f"{name}.png")
    print(f"{name}: {pix.width}x{pix.height} px at 600 dpi")


if __name__ == "__main__":
    build("table_crossover", ROOT / "tables" / "table_crossover.tex")
    build("table_divider", ROOT / "tables" / "table_divider.tex")
