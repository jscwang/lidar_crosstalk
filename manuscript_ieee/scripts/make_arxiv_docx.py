"""Word version of the REVISED arXiv comprehensive preprint (arxiv/sections/*.tex, after Jessica's written comments
on the v5 redline, Lidar_Paper v5 Redline.docx, 16 Oct 2026), for her review. New or reworded text since v5 is
shown in red, exactly matching the \\new{...} markup now in arxiv/paper.tex and arxiv/sections/*.tex. A "Response
to Comments" appendix at the end answers all 36 of her numbered comments by number.

Plain single-column document (not the two-column IEEE class), matching the main letter's review-copy convention.
Reuses the LaTeX-to-Word text helpers of fill_sensors_letters_docx.py and make_revised_docx.py; CITE_NUM/SEC_NUM/
EQ_NUM/FIG_NUM/TAB_NUM are set to this document's own numbering (confirmed against the compiled arxiv/paper.pdf)
before any text is converted.

Run:   python manuscript_ieee/scripts/make_arxiv_docx.py
Out:   manuscript_ieee/arxiv/paper_v6.docx

Author: Jessica
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fill_sensors_letters_docx as F  # noqa: E402
import make_revised_docx as R  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
AFIG = ROOT / "arxiv" / "figures"
OUT = ROOT / "arxiv" / "paper_v6.docx"
TITLE = "Angle-Dependent Crosstalk Between Two Adjacent VL53L1X Time-of-Flight Sensors"
RED = RGBColor(0xC0, 0x00, 0x00)

# ----------------------------------------------------------------------- numbering (overrides F.*/R.*), matching
# the compiled arxiv/paper.pdf exactly (17 references, 5 tables, 9 figures)
F.CITE_NUM = {
    "incoronato2022": 1, "padmanabhan2019": 2, "vl53l5cx": 3, "ds12385": 4, "stforum": 5, "wermke2019": 6,
    "whyte2010": 7, "li2015": 8, "kim2015a": 9, "kim2015b": 10, "popko2020": 11, "ogurcovs2025": 12,
    "fasolino2025": 13, "um2510": 14, "tca9548a": 15, "fritsch1980": 16, "efron1993": 17,
    "stforum2": 18, "stforum3": 19,
}
F.SEC_NUM = {
    "sec:intro": "I", "sec:howitworks": "I-A", "sec:crosstalkmeans": "I-B",
    "sec:method": "II", "sec:apparatus": "II-A", "sec:acquisition": "II-B", "sec:whatcomputed": "II-C",
    "sec:crossoverdef": "II-D", "sec:geomref": "II-E", "sec:dividercheck": "II-F",
    "sec:results": "III", "sec:worstcase": "III-A", "sec:whyranging": "III-B", "sec:detectionlimit": "III-C",
    "sec:geommodel": "III-D", "sec:source": "III-E", "sec:conclusion": "IV",
}
F.EQ_NUM = {"eq:geom": "1", "eq:extra": "2", "eq:pool": "3", "eq:tilted": "4"}
F.FIG_NUM = {
    "fig:concept": "1", "fig:principle": "2", "fig:setup": "3", "fig:photo": "4", "fig:timetrace": "5",
    "fig:scatter": "6", "fig:threshold": "7", "fig:results": "8", "fig:methods": "9",
}
F.TAB_NUM = {"tab:settings": "I", "tab:sixcells": "II", "tab:cross": "III", "tab:swap": "IV",
             "tab:validshare": "V", "tab:divider": "VI"}

REFERENCES = [
    "A. Incoronato, I. Cusini, K. Pasquinelli, and F. Zappa, “Single-shot pulsed-LiDAR SPAD sensor with "
    "on-chip peak detection for background rejection,” IEEE J. Sel. Top. Quantum Electron., vol. 28, "
    "no. 5, Sep. 2022, art. no. 3804210.",
    "P. Padmanabhan, C. Zhang, and E. Charbon, “Modeling and analysis of a direct time-of-flight sensor "
    "architecture for LiDAR applications,” Sensors, vol. 19, no. 24, p. 5464, Dec. 2019.",
    "STMicroelectronics, VL53L5CX: Time-of-flight 8×8 multizone ranging sensor with wide field of view, "
    "Aug. 2021, datasheet DS13754, Rev. 2. Accessed: Oct. 15, 2026. [Online]. Available: "
    "https://www.st.com/en/imaging-and-photonics-solutions/vl53l5cx.html",
    "STMicroelectronics, VL53L1X: A new generation, long distance ranging time-of-flight sensor based on "
    "ST’s FlightSense technology, Aug. 2024, datasheet DS12385, Rev. 8. Accessed: Oct. 11, 2026. [Online]. "
    "Available: https://www.st.com/resource/en/datasheet/vl53l1x.pdf",
    "J. E. Kvam, “Reply to ‘VCSEL signals interferences for closed sensors (VL53L1X)’,” "
    "STMicroelectronics Community forum, Apr. 2021, accessed: Oct. 11, 2026. [Online]. Available: "
    "https://community.st.com/imaging-sensors-49/vcsel-signals-interferences-for-closed-sensors-vl53l1x-25089",
    "F. Wermke and B. Meffert, “Interference model of two time-of-flight cameras,” in Proc. IEEE "
    "SENSORS, Montreal, QC, Canada, Oct. 2019, pp. 1–4.",
    "R. Z. Whyte, A. D. Payne, A. A. Dorrington, and M. J. Cree, “Multiple range imaging camera operation "
    "with minimal performance impact,” in Proc. SPIE, Image Processing: Machine Vision Applications III, "
    "vol. 7538, Feb. 2010, p. 75380I.",
    "L. Li, S. Xiang, Y. Yang, and L. Yu, “Multi-camera interference cancellation of time-of-flight (TOF) "
    "cameras,” in Proc. IEEE Int. Conf. Image Process. (ICIP), Sep. 2015, pp. 556–560.",
    "G. Kim, J. Eom, and Y. Park, “An experiment of mutual interference between automotive LIDAR "
    "scanners,” in Proc. 12th Int. Conf. Inf. Technol.—New Gener. (ITNG), Apr. 2015, pp. 680–685.",
    "G. Kim, J. Eom, and Y. Park, “Investigation on the occurrence of mutual interference between pulsed "
    "terrestrial LIDAR scanners,” in Proc. IEEE Intell. Veh. Symp. (IV), Jun. 2015, pp. 437–442.",
    "G. B. Popko, T. K. Gaylord, and C. R. Valenta, “Interference measurements between single-beam, "
    "mechanical scanning, time-of-flight lidars,” Opt. Eng., vol. 59, no. 5, May 2020, art. no. 053106.",
    "A. Ogurcovs, I. Aulika, S. Cartiel, J. Garcia-Pueyo, and A. Muñoz, “Crosstalk effects in a dual "
    "ToF-based tactile–proximity sensing platform integrated in a flat PMMA light guide,” Sensors, "
    "vol. 25, no. 23, p. 7319, Dec. 2025.",
    "A. Fasolino, L. E. Andrada, R. Liguori, L. Di Benedetto, A. Rubino, D. Pau, and G. D. Licciardo, "
    "“Real-time crosstalk compensation in multizone time-of-flight sensors,” in Proc. SPIE, "
    "Real-time Processing of Image, Depth, and Video Information 2025, vol. 13526, May 2025, p. 135260D.",
    "STMicroelectronics, A guide to using the VL53L1X ultra lite driver, Dec. 2025, user manual UM2510, "
    "Rev. 7. Accessed: Oct. 3, 2026. [Online]. Available: "
    "https://www.st.com/resource/en/user_manual/um2510-a-guide-to-using-the-vl53l1x-ultra-lite-driver-"
    "stmicroelectronics.pdf",
    "Texas Instruments, TCA9548A low-voltage 8-channel I2C switch with reset, Nov. 2019, datasheet SCPS207G. "
    "Accessed: Oct. 3, 2026. [Online]. Available: https://www.ti.com/lit/gpn/TCA9548A",
    "F. N. Fritsch and R. E. Carlson, “Monotone piecewise cubic interpolation,” SIAM J. Numer. Anal., "
    "vol. 17, no. 2, pp. 238–246, 1980.",
    "B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. New York, NY, USA: Chapman & Hall, 1993.",
    "“Two VL53L1X sensors influencing their measurements,” STMicroelectronics Community forum, forum "
    "thread, accessed: Oct. 16, 2026. [Online]. Available: "
    "https://community.st.com/t5/mems-sensors/two-vl53l1x-sensors-influencing-their-measurements/"
    "td-p/272311",
    "“Multiple VL53L1X sensors and FOV interfernce [sic],” STMicroelectronics Community forum, Mar. 2020, "
    "accessed: Oct. 16, 2026. [Online]. Available: "
    "https://community.st.com/t5/mems-sensors/multiple-vl53l1x-sensors-and-fov-interfernce/td-p/275819",
]

EQS = {
    "1": r"s+2d\,\tan(\Delta\theta_g/2)=d\,[\tan(E/2)+\tan(F/2)]",
    "2": r"\Delta a_s(b)=\bar{a}_s^{AB}(b)-\bar{a}_s^{solo}(b)",
    "3": r"\Delta a(b)=\frac{1}{2}\left[\Delta a_A(b)+\Delta a_B(b)\right]",
    "4": r"g(\Delta\theta)=\frac{a\,(1+b\,\Delta\theta)}{1+\exp[(\Delta\theta-x_0)/w]}",
}


def fig(doc, path, width_in=3.6):
    R.figure(doc, path, width_in)


def set_cell(cell, text, bold=False, size=8, red=False, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = "Times New Roman"
    r.font.bold = bold
    if red:
        r.font.color.rgb = RED


# ----------------------------------------------------------------------- Table I: settings
def add_table_settings_arxiv(doc):
    rows = [
        ("Sensors", "Two VL53L1X [4] on Pololu 3415 carriers", "Target distances d", "0.3, 0.6, 0.9 m (tape; see Section II)"),
        ("Host", "ESP32-S3, via TCA9548A I²C mux [15]", "Target", "Flat dark-gray board, 1.2 m wide"),
        ("I²C clock", "400 kHz", "Room lighting", "Not recorded or varied"),
        ("Driver mode", "Short distance, ultra-lite driver [14]", "Repeats per cell", "5 blocks (A alone, B alone, A+B)"),
        ("Timing budget", "33 ms; period 40 ms", "Run length", "30 s"),
        ("ROI (zone)", "16×16 (full array) and 4×4 (window)", "Warm-up", "600 s, both sensors, each distance"),
        ("Field of view (datasheet, diagonal)", "27° and 15°", "Sensor spacing s", "20 mm (nominal)"),
        ("Angle step", "1° (pin-set plate; accuracy not verified)", "", ""),
    ]
    t = doc.add_table(rows=1, cols=4)
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(["Parameter", "Value", "Parameter", "Value"]):
        set_cell(t.rows[0].cells[i], h, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    for p1, v1, p2, v2 in rows:
        cells = t.add_row().cells
        for i, v in enumerate((p1, v1, p2, v2)):
            set_cell(cells[i], v, align=WD_ALIGN_PARAGRAPH.LEFT)
    doc.add_paragraph()

    note = doc.add_paragraph(style="Caption L-SENS")
    r = note.add_run("What differs between the two campaigns (new in this revision):")
    r.bold = True
    r.font.color.rgb = RED
    t2 = doc.add_table(rows=1, cols=3)
    F.add_table_borders(t2)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(["Parameter", "Campaign 1", "Campaign 2 (unit swap)"]):
        set_cell(t2.rows[0].cells[i], h, bold=True, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    rows2 = [
        ("Unit positions / ROI centers", "unit 3 at A, unit 1 at B", "unit 1 at A, unit 3 at B (ROI centers exchanged)"),
        ("θ sweep (Δθ=2θ)", "θ=0° and 2–12° in 1° steps (12 levels, Δθ=0,4,6,…,24°)",
         "0–12° step 1° (13 levels, Δθ=0,2,…,24°)*"),
        ("Divider angles (θ)", "2°, 5° (Δθ=4,10°)", "1°, 2°, 5° (Δθ=2,4,10°)"),
        ("Session dates (UTC)", "6–9 Oct. 2026", "12–14 Oct. 2026"),
    ]
    for p1, v1, v2 in rows2:
        cells = t2.add_row().cells
        for i, v in enumerate((p1, v1, v2)):
            set_cell(cells[i], v, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    note2 = doc.add_paragraph(style="Caption L-SENS")
    r = note2.add_run("*At 0.6 m the sweep stopped early at θ=11° (Δθ=22°) once an adaptive "
                       "range-quality check passed, so that session has no Δθ=24° level.")
    r.font.color.rgb = RED
    doc.add_paragraph()


# ----------------------------------------------------------------------- Table II: fifteen partly-accepted cells
def add_table_sixcells(doc):
    headers = ["d (m)", "Δθ (deg), unit (campaign)", "Solo %", "A+B %", "Δ (pts)"]
    rows = [
        ["0.3", "20, unit 1 (1)", "65.1", "61.8", "−3.3"],
        ["0.6", "0, unit 3 (1)", "100.0", "99.4", "−0.6"],
        ["0.6", "0, unit 1 (1)", "80.9", "61.0", "−19.9"],
        ["0.6", "0, unit 1 (2)", "18.2", "20.1", "+1.9"],
        ["0.6", "2, unit 3 (1)", "100.0", "98.4", "−1.6"],
        ["0.6", "2, unit 1 (1)", "22.2", "21.8", "−0.3"],
        ["0.6", "2, unit 1 (2)", "0.0", "0.5", "+0.5"],
        ["0.6", "4, unit 3 (1)*", "99.9", "95.1", "−4.8"],
        ["0.6", "4, unit 1 (1)", "0.0", "1.2", "+1.2"],
        ["0.6", "4, unit 3 (2)", "100.0", "99.2", "−0.8"],
        ["0.6", "6, unit 3 (1)", "97.8", "87.9", "−9.9"],
        ["0.6", "6, unit 3 (2)", "100.0", "96.8", "−3.2"],
        ["0.6", "8, unit 3 (1)", "4.7", "6.6", "+2.0"],
        ["0.6", "8, unit 3 (2)**", "94.9", "87.9", "−7.1"],
        ["0.6", "10, unit 3 (2)", "5.6", "7.3", "+1.6"],
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, bold=True, red=True)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            set_cell(cells[i], v, red=True)
    note = doc.add_paragraph(style="Caption L-SENS")
    r = note.add_run("*, **The settings of the histograms in Fig. 7a (before the swap) and 7d (after the swap). The neighbor lowers the accepted share in ten cells and raises it in five; the "
                      "raised cells all start from a solo share of about 22% or less, and all but one of the "
                      "lowered cells start from 48% or more, by 0.6 to 19.9 points (the exception, unit 1 at "
                      "dtheta=2 deg in campaign 1, starts at 22.2% and changes by only -0.3 points). A further "
                      "five near-degenerate cells, where the solo "
                      "or A+B share sits within 0.2 points of exactly 0% or 100%, change by less than 0.2 points "
                      "and are omitted as neither meaningfully partial nor informative.")
    r.font.color.rgb = RED
    doc.add_paragraph()


# ----------------------------------------------------------------------- Table III: crossover, both campaigns
def add_table_crossover_arxiv(doc):
    headers = ["Zone", "d (m)", "Campaign", "Bracket", "Crossover\n(M4, PCHIP)", "Range,\nM3–M5",
               "1 % angle", "Model", "Model,\nF in-plane"]
    rows = [
        (["16×16", "0.3", "1", "16–18", "16.15", "16.15–16.20", "19.9", "23.4", "19.5"], False),
        (["16×16", "0.3", "2", "16–18", "16.32", "16.17–16.38", "19.8", "23.4", "19.5"], True),
        (["16×16", "0.6", "1", "16–18", "17.29", "17.29–17.42", "20.9", "25.2", "21.3"], False),
        (["16×16", "0.6", "2", "16–18", "17.36", "17.36–17.50", "21.1", "25.2", "21.3"], True),
        (["16×16", "0.9", "1", "16–18", "17.90", "17.90–17.94", "21.6", "25.8", "21.9"], False),
        (["16×16", "0.9", "2", "18–20", "18.18", "18.18–18.22", "21.5", "25.8", "21.9"], True),
        (["4×4", "0.3", "1", "8–10", "8.22", "8.20–8.33", "11.4", "17.3", "15.2"], False),
        (["4×4", "0.3", "2", "8–10", "8.51", "8.51–8.70", "11.4", "17.3", "15.2"], True),
        (["4×4", "0.6", "1", "8–10", "9.72", "9.65–9.82", "12.7", "19.2", "17.1"], False),
        (["4×4", "0.6", "2", "10–12", "10.14", "10.14–10.28", "13.0", "19.2", "17.1"], True),
        (["4×4", "0.9", "1", "10–12", "10.80", "10.80–11.02", "13.1", "19.8", "17.7"], False),
        (["4×4", "0.9", "2", "10–12", "10.96", "10.96–11.19", "13.3", "19.8", "17.7"], True),
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, bold=True, red=(i in (2, 5)))
    for row, red in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            set_cell(cells[i], v, red=(red or i == 2))
    note = doc.add_paragraph(style="Caption L-SENS")
    note.add_run("Campaign 1: unit 3 at A, unit 1 at B. Campaign 2: units exchanged (Table I). Bracket is "
                 "model-free; range is across M3 (linear), M4 (PCHIP) and M5 (tilted logistic), which "
                 "together bound the 10% crossing reliably (M1, M2, the logistics read at or from Δθ=0, "
                 "can lie up to 1° from M4). Model and "
                 "model-with-in-plane-F are purely geometric and so do not depend on campaign. Bootstrap 95% "
                 "half-widths of M4 are 0.01–0.07° within either campaign; the crossover moved by "
                 "0.07–0.42° (mean 0.23°) and the 1% angle by at most 0.3° between campaigns, so "
                 "between-session reproducibility is closer to ±0.4° than the within-session bootstrap "
                 "suggests.")
    doc.add_paragraph()


# ----------------------------------------------------------------------- Table IV: unit-swap results (new)
def add_table_swap(doc):
    headers = ["Zone", "d (m)", "Crossing unit 3\ncamp. 1 / 2", "Crossing unit 1\ncamp. 1 / 2",
               "Peak unit 3 (kcps)\ncamp. 1 / 2", "Peak unit 1 (kcps)\ncamp. 1 / 2",
               "Gap unit 3 − unit 1 (°)\ncamp. 1 / 2"]
    rows = [
        ["16×16", "0.3", "15.42 / 15.25", "16.50 / 16.92", "825 / 996", "1186 / 1142", "−1.08 / −1.68"],
        ["16×16", "0.6", "16.66 / 16.68", "17.80 / 17.93", "674 / 690", "719 / 730", "−1.14 / −1.25"],
        ["16×16", "0.9", "17.30 / 17.24", "18.36 / 18.87", "272 / 318", "332 / 320", "−1.06 / −1.63"],
        ["4×4", "0.3", "8.51 / 8.67", "7.78 / 8.28", "312 / 360", "234 / 258", "+0.73 / +0.39"],
        ["4×4", "0.6", "10.05 / 10.44", "9.30 / 9.72", "83 / 79", "68 / 63", "+0.74 / +0.72"],
        ["4×4", "0.9", "11.03 / 11.19", "10.43 / 10.66", "29 / 29", "19 / 20", "+0.60 / +0.53"],
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, bold=True, red=True, size=7.5)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            set_cell(cells[i], v, red=True)
    note = doc.add_paragraph(style="Caption L-SENS")
    r = note.add_run("Campaign 1: unit 3 at A, unit 1 at B. Campaign 2: units exchanged. Crossing angle is the "
                      "10% crossing (M4, degrees) of each sensor analyzed separately; the peak is the largest "
                      "cell mean of the sensor's own extra ambient rate. Unit 3 crossed earlier than unit 1 in "
                      "the full array and later in the window in both campaigns, whichever position (A or B) it "
                      "occupied: the gap keeps its sign after the swap. A swap cannot separate a unit's "
                      "receiver from its emitter (Section III-D).")
    r.font.color.rgb = RED
    doc.add_paragraph()


# ----------------------------------------------------------------------- Table V: valid-range share (new)
def add_table_validshare(doc):
    angles = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]
    data = [
        ("0.3 m", "unit 1 (B, campaign 1)", ["100", "--", "100", "100", "100", "100", "100", "100", "100", "100", "65", "1", "0"]),
        ("0.3 m", "unit 1 (A, campaign 2)", ["100"] * 13),
        ("0.6 m", "unit 3 (A, campaign 1)", ["100", "100", "100", "98", "5", "0", "0", "0", "0", "0", "0", "0", "0"]),
        ("0.6 m", "unit 3 (B, campaign 2)", ["100", "100", "100", "100", "95", "6", "0", "0", "0", "0", "0", "0", "--"]),
        ("0.6 m", "unit 1 (B, campaign 1)", ["81", "22", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0"]),
        ("0.6 m", "unit 1 (A, campaign 2)", ["18", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "0", "--"]),
    ]
    t = doc.add_table(rows=1, cols=2 + len(angles))
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_cell(t.rows[0].cells[0], "d", bold=True, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    set_cell(t.rows[0].cells[1], "Unit (position, campaign)", bold=True, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    for i, a in enumerate(angles):
        set_cell(t.rows[0].cells[2 + i], str(a), bold=True, red=True, size=7)
    for d, label, vals in data:
        cells = t.add_row().cells
        set_cell(cells[0], d, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
        set_cell(cells[1], label, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
        for i, v in enumerate(vals):
            set_cell(cells[2 + i], v, red=True, size=7)
    note = doc.add_paragraph(style="Caption L-SENS")
    r = note.add_run("New table (Jessica's comment on 'about half', v5 redline). Full array (16×16) range is "
                      "valid throughout for both units at every angle and distance, and is omitted. Unit 3's 4×4 "
                      "window is valid at every sampled angle at 0.3 m (both campaigns) and is omitted. Neither "
                      "unit returns a valid 4×4 window reading at any angle at 0.9 m. A dash marks an angle not "
                      "sampled in that campaign; at 0.6 m, campaign 2 stopped at Δθ=22°.")
    r.font.color.rgb = RED
    doc.add_paragraph()


# ----------------------------------------------------------------------- Table VI: divider, both campaigns
def add_table_divider_arxiv(doc):
    headers = ["Zone", "d (m)", "Δθ=2° (camp. 2 only)", "Δθ=4°", "Δθ=10°"]
    camp1 = [
        ["16×16", "0.3", "--", "−1.3 (−1.8, −0.8)", "−0.7 (−1.3, −0.1)"],
        ["16×16", "0.6", "--", "−0.1 (−0.6, +0.5)", "+0.1 (−0.8, +1.1)"],
        ["16×16", "0.9", "--", "+1.6 (+1.1, +2.2)", "+2.5 (+1.1, +4.0)"],
        ["4×4", "0.3", "--", "−3.9 (−4.5, −3.3)", "−7.7 (−11.8, −4.0)"],
        ["4×4", "0.6", "--", "+2.3 (−0.3, +4.8)", "−4.3 (−6.6, −2.0)"],
        ["4×4", "0.9", "--", "+0.2 (−1.1, +1.5)", "−0.1 (−2.8, +2.7)"],
    ]
    camp2 = [
        ["16×16", "0.3", "+0.4 (−0.1, +0.9)", "+0.2 (−0.2, +0.7)", "−0.4 (−1.3, +0.5)"],
        ["16×16", "0.6", "−1.0 (−1.9, −0.1)", "−0.7 (−1.5, +0.2)", "−0.8 (−1.5, −0.1)"],
        ["16×16", "0.9", "+0.7 (−0.1, +1.4)", "+0.6 (−0.5, +1.8)", "+0.8 (−0.3, +1.7)"],
        ["4×4", "0.3", "−0.0 (−0.6, +0.8)", "−4.2 (−4.8, −3.6)", "+11.2 (+7.6, +14.4)"],
        ["4×4", "0.6", "−1.0 (−2.2, +0.3)", "−3.8 (−5.0, −2.8)", "−5.6 (−8.1, −3.0)"],
        ["4×4", "0.9", "−0.3 (−1.3, +0.8)", "+1.2 (+0.1, +2.4)", "+0.7 (−3.2, +4.5)"],
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, bold=True, red=(i == 2))
    hdr1 = doc.add_paragraph()  # placeholder spacer avoided; label rows inline instead
    hdr1._p.getparent().remove(hdr1._p)
    r1 = t.add_row().cells
    set_cell(r1[0], "Campaign 1 (unit 3 at A, unit 1 at B)", bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    for c in r1[1:]:
        set_cell(c, "")
    for row in camp1:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            set_cell(cells[i], v)
    r2 = t.add_row().cells
    set_cell(r2[0], "Campaign 2 (unit 1 at A, unit 3 at B)", bold=True, red=True, align=WD_ALIGN_PARAGRAPH.LEFT)
    for c in r2[1:]:
        set_cell(c, "", red=True)
    for row in camp2:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            set_cell(cells[i], v, red=True)
    note = doc.add_paragraph(style="Caption L-SENS")
    r = note.add_run("Campaign 2 sampled an extra divider angle, θ=1° (Δθ=2°), not present in campaign 1. "
                      "Full-array changes span −1.3 to +2.5% in campaign 1 and −1.0 to "
                      "+0.8% in campaign 2; the window spans −7.7 to +2.3% and −5.6 to +11.2%, the latter "
                      "corresponding to at most about 10 kcps absolute change in either campaign.")
    r.font.color.rgb = RED
    doc.add_paragraph()


# ----------------------------------------------------------------------- body
def build_body_arxiv(doc, styles):
    TXT = styles["Text L-SENS"]
    CAP = styles["Caption L-SENS"]

    def h1(text):
        return doc.add_paragraph(text, style="Heading 1")

    def h2(text):
        return doc.add_paragraph(text, style="Heading 2")

    def body_p(latex_text, red=False):
        p = doc.add_paragraph(style=TXT)
        R.add_rich_tracked(p, latex_text, force_red=red)
        return p

    def caption(latex_text, red=False):
        p = doc.add_paragraph(style=CAP)
        R.add_rich_tracked(p, latex_text, force_red=red)
        return p

    # ================================================================= ABSTRACT
    abstract = doc.add_paragraph(style=TXT)
    r = abstract.add_run("Abstract—")
    r.bold = True
    R.add_rich_tracked(abstract, (
        r"Time-of-flight ranging sensors mounted side by side can disturb one another, but we found no "
        r"published measurement of how this depends on the angle between them. We measured the extra ambient "
        r"light one VL53L1X sensor sees when an identical neighbor 20 millimeters away also ranges, for one "
        r"pair of sensors tested against a gray board at 0.3, 0.6 and 0.9 meters in two window sizes, with "
        r"five repeats per setting, a divider test, \new{and the whole sweep repeated after exchanging the "
        r"two sensors}. Three findings follow. First, the extra light fell to 10 percent of its peak between "
        r"16 and 18 \new{degrees of total angle between the sensors (half that per sensor)} for a full sensor "
        r"array and 8 to 11 degrees for a narrower window, and to 1 percent at about 20 to 22 and 11 to 13 "
        r"degrees, growing with distance; a geometric model using the datasheet field of view overestimated "
        r"these angles by three to seven degrees, and no single emitter beam angle fitted both windows. "
        r"\new{The extra light also arrived in bursts about every 1.9 seconds, consistent with unsynchronized "
        r"sensor clocks, and after the sensors were exchanged the angles reproduced to within about 0.7 "
        r"degrees, with the small difference in crossing angle between the two sensors following the unit, "
        r"not its mounting position.} Second, ranging itself was barely disturbed: a large rise in ambient "
        r"rate at close range shifted the mean distance by under half a millimeter. Third, near a sensor's "
        r"acceptance threshold \new{the neighbor widened the signal scatter and could change the share of "
        r"accepted readings by up to about 20 percentage points, in either direction}. A thin divider changed "
        r"the effect by no more than about 4 percent in \new{ten of twelve settings before the swap and "
        r"fifteen of eighteen after it}, \new{consistent with, but not proof of, a shared-target path rather "
        r"than direct coupling. Separating the sensors' pointing angles past this crossover is expected to "
        r"remove the effect; a barrier was not shown to help, and ranging in turn, which avoids the "
        r"interference by construction, was not tested.}"
    ))
    keywords = doc.add_paragraph(style=TXT)
    kr = keywords.add_run("Keywords—")
    kr.bold = True
    keywords.add_run("Crosstalk, interference, sensor arrays, time-of-flight sensors, VL53L1X.")
    doc.add_paragraph()

    # ================================================================= I. INTRODUCTION
    h1("I. Introduction")
    body_p(
        r"Ranging by the travel time of light is now a common way to measure distance without touching the "
        r"target. Automotive and robotic systems use pulsed time-of-flight sensors for obstacle detection and "
        r"navigation~\cite{incoronato2022}, and single-photon-avalanche-diode (SPAD) arrays of the kind inside "
        r"the sensor used here are a standard building block of these systems~\cite{padmanabhan2019}. Two "
        r"further points set the scene for this \new{paper}. First, not every such sensor scans or images a "
        r"scene: a scanning lidar sweeps a beam and is comparatively expensive, and a multizone sensor such as "
        r"the VL53L5CX reports a small grid of distances from a fixed mount~\cite{vl53l5cx}; but arrays of "
        r"cheap, single-point sensors like the VL53L1X remain common because each one is inexpensive and can be "
        r"pointed in any direction independently of the others. Second, when several such sensors are mounted "
        r"close together, as in a drone's collision-avoidance ring or a mobile robot's bumper, each can "
        r"potentially receive light meant for its neighbor (Fig.~1).")
    body_p(
        r"The VL53L1X is a compact direct time-of-flight (ToF) sensor of exactly this kind: it pairs a "
        r"\SI{940}{\nano\meter} laser emitter with an array of single-photon avalanche diodes (SPADs) and a "
        r"programmable region of interest (ROI)~\cite{ds12385}, and is \new{the sensor used throughout this "
        r"paper}. \new{A manufacturer community thread discusses whether neighboring units disturb one "
        r"another}~\cite{stforum}. Mutual interference of this kind has already been studied for other sensor "
        r"families: a model of the distance error exists for two ToF cameras~\cite{wermke2019} and methods for "
        r"operating several of them were developed~\cite{whyte2010,li2015}, and for scanning lidars, where it "
        r"was measured~\cite{kim2015a,kim2015b} and direct and scattered interference were "
        r"distinguished~\cite{popko2020}. Crosstalk between two multizone ToF sensors viewing through one light "
        r"guide has been characterized for a tactile and proximity skin~\cite{ogurcovs2025}, and crosstalk "
        r"compensation in multizone ToF sensors has been reported~\cite{fasolino2025}. For small single-point "
        r"sensors such as the VL53L1X, by contrast, we found only the forum thread above: a manufacturer "
        r"employee replied that units generally do not interfere, while relaying a report of interference at "
        r"\SI{5}{\centi\meter} when two face each other~\cite{stforum}. \new{The original poster, who was "
        r"designing a multi-sensor drone, asked whether an angle (45° or 90°) exists at which the interference "
        r"disappears; the reply gave no angle data~\cite{stforum}.} In the sources we searched (web searches of the research literature, manufacturer documents "
        r"and community posts, \new{repeated on 15 October 2026 with the terms ``VL53L1X'', ``time-of-flight "
        r"sensor crosstalk'', ``multi-sensor interference'' and ``angle'' against Google Scholar, Scopus, IEEE "
        r"Xplore and arXiv;} not an exhaustive bibliographic-database search) we found no published measurement "
        r"of how the interaction between two adjacent VL53L1X-class sensors depends on the angle between them. "
        r"This is the gap this \new{paper} addresses.")
    body_p(
        r"We chose the VL53L1X for three reasons: it is inexpensive and widely used, so results for it "
        r"\new{are relevant to many existing designs}; its field of view can be narrowed in software from the "
        r"full $16\times16$ SPAD array to a $4\times4$ window, so the same pair of units lets us test two "
        r"optical geometries without new hardware; and it reports the signal and ambient photon rates directly "
        r"(Section~\ref{sec:howitworks}), so the interference can be measured as a rate rather than inferred "
        r"from range alone.")
    body_p(
        r"This paper measures that dependence for one pair of VL53L1X sensors \SI{20}{\milli\meter} apart, in "
        r"two ROI sizes and at three distances. \new{We ask four questions.} (i)~At what angle does the extra "
        r"ambient rate fall to \SI{10}{\percent} and \SI{1}{\percent} of its peak, and how precisely can that "
        r"angle be pinned down? (ii)~Does the response fall monotonically with angle in both ROI sizes? "
        r"(iii)~Does a geometric model built from the datasheet's field-of-view figures predict the angle at "
        r"which the effect disappears? (iv)~Does a thin opaque divider between the sensors reduce the effect, "
        r"which would point to light reaching the neighbor directly rather than only via the target? "
        r"\new{Because one campaign cannot separate the properties of the two units, of their mounting "
        r"positions and of one measurement session, we repeated the sweeps after exchanging the two units "
        r"(Section~\ref{sec:method}).}")

    h2("A. How the sensor works")
    body_p(
        r"The VL53L1X emits laser pulses and times the returning photons with an array of SPADs~\cite{ds12385}. "
        r"Photons arriving within a narrow window after each pulse, reflected from the target, cluster at one "
        r"delay and form a sharp peak in the histogram of arrival times (Fig.~2a); photons arriving at other "
        r"times, from room light or any other unsynchronized source, are spread roughly uniformly across the "
        r"histogram and form a flat floor beneath the peak. The driver reports three quantities from this "
        r"histogram, each summed over the active SPADs and given in kilocounts per second (kcps): the "
        r"\emph{range}, from the position of the peak; the \emph{signal rate}, the height of the peak above the "
        r"floor; and the \emph{ambient rate}, the height of the floor itself. A reading is accepted or rejected "
        r"according to status codes defined by the manufacturer's driver~\cite{um2510}; in the data reported "
        r"here, \new{every accepted reading has a signal rate above \SI{1024}{kcps} (the lowest accepted value "
        r"across both campaigns is \SI{1032}{kcps} and \SI{1024}{kcps} itself is always rejected; rates are "
        r"quantized in \SI{8}{kcps} steps). The ultra-lite driver's own manual documents a default signal-rate "
        r"threshold of exactly \SI{1024}{kcps}~\cite{um2510}}, consistent with what we observe "
        r"(Section~\ref{sec:detectionlimit}).")

    h2("B. What crosstalk means here")
    body_p(
        r"When a second sensor is also ranging nearby, some of its emitted light can reach the first sensor's "
        r"receiver, either directly or after reflecting off the target. Because the two sensors run on "
        r"independent, unsynchronized clocks, the neighbor's photons arrive at random delays relative to the "
        r"first sensor's own pulse, so they add to the flat floor rather than to the peak (Fig.~2a): the "
        r"ambient rate rises, while the range, read from the peak, is affected only indirectly. This is what "
        r"Section~\ref{sec:method} measures as the \emph{extra ambient rate}.")
    body_p(
        r"A simple geometric picture bounds the angle at which this stops: sensor B's emitter illuminates a "
        r"cone of half-angle $E/2$ and sensor A's receiver accepts light from a cone of half-angle $F/2$ "
        r"(Fig.~2b); as the two sensors are turned apart by a relative angle $\dth$, these cones' footprints on "
        r"the target slide apart and eventually stop overlapping. Equating the point where the two footprint "
        r"edges meet gives")
    R.add_equation(doc, styles, "1", EQS)
    body_p(
        r"where $s$ is the sensor spacing, $d$ the target distance, and $\dth_g$ the predicted end-of-overlap "
        r"angle; this treats both footprints as circular cones, centered on each sensor's nominal axis. "
        r"\new{The in-plane variant used in Section~\ref{sec:geomref} instead converts the receive field to a "
        r"value appropriate for a square array, so the two assumptions are not mutually consistent and "
        r"\eqref{eq:geom} should be read as an order-of-magnitude guide rather than a precise model.} "
        r"Section~\ref{sec:geommodel} evaluates \eqref{eq:geom} against the measured crossover angles.")
    fig(doc, FIG / "fig_concept.png", 3.6)
    caption("Fig. 1. Concept: sensors in an array point in different directions, but adjacent ones' emitter and "
            "receive cones can still overlap on a shared target.")
    fig(doc, FIG / "fig_principle.png", 5.5)
    caption("Fig. 2. Principle. (a) Sketch of the photon-arrival-time histogram one sensor builds: its own "
            "return forms a sharp peak (the signal rate); unsynchronized light, including a neighbor's, "
            "spreads across the window and raises the floor (the ambient rate). (b) The overlap geometry of "
            "(1): sensor B's emitter cone (half-angle E/2) and sensor A's receive cone (half-angle F/2), "
            "rotated apart by a relative angle Δθg, stop sharing a common footprint on the target beyond the "
            "predicted angle.")

    # ================================================================= II. METHODOLOGY
    h1("II. Methodology")
    body_p(
        r"To answer the four questions above, one pair of VL53L1X sensors was turned apart by a known angle "
        r"and read while alone and together, at three distances and two field-of-view sizes, and the extra "
        r"ambient rate this produces was measured and related back to the overlap geometry of "
        r"Section~\ref{sec:crosstalkmeans}. \new{Because one campaign cannot separate the properties of the two "
        r"units, of their mounting positions and of one measurement session, the whole sweep was repeated "
        r"after exchanging the two units (campaign 2; Section~\ref{sec:apparatus}).} The rest of this section "
        r"gives the apparatus, the acquisition protocol and acceptance rules, what was computed and why, how "
        r"the crossover angle and its uncertainty were estimated, and the divider check.")

    h2("A. Apparatus and geometry")
    body_p(
        r"Two VL53L1X sensors~\cite{ds12385} on Pololu 3415 carrier boards (\new{campaign 1:} unit~3 at "
        r"position~A, unit~1 at B) were read by an ESP32-S3 through a TCA9548A I$^2$C multiplexer~\cite{tca9548a} "
        r"at \SI{400}{\kilo\hertz}. The STMicroelectronics ultra-lite driver~\cite{um2510} set short distance "
        r"mode, a \SI{33}{\milli\second} timing budget and a \SI{40}{\milli\second} period. Each "
        r"interrupt-timestamped reading gave the range, its status, and the total signal and ambient rates "
        r"(Section~\ref{sec:howitworks}). Two ROIs were used, the full $16\times16$ array and a $4\times4$ "
        r"window, each centered on the factory optical center. The datasheet gives their fields of view as "
        r"\SI{27}{\degree} and \SI{15}{\degree}, as diagonal values, and gives no emitter beam "
        r"angle~\cite{ds12385}. Table~\ref{tab:settings} lists every setting; Fig.~3 is a schematic of the "
        r"geometry it describes, and Fig.~4 shows the physical rig.")
    caption("Table I. Hardware, settings and experimental parameters")
    add_table_settings_arxiv(doc)
    body_p(
        r"The sensors, nominally $s=\SI{20}{\milli\meter}$ apart, sat on pucks turned by $-\theta$ (A) and "
        r"$+\theta$ (B), so their axes diverged by $\dth=2\theta$ (Fig.~3). Pins in a plate with holes at "
        r"\SI{1}{\degree} steps set the angles (accuracy not verified). \new{Campaign~1 covered} "
        r"$\theta=\SI{0}{\degree}$ and \SIrange{2}{12}{\degree}, so $\dth=0,4,6,\dots,\SI{24}{\degree}$ (12 "
        r"levels). \new{Campaign~2 exchanged the two units (unit~1 at A, unit~3 at B, with the ROI centers "
        r"exchanged accordingly) and repeated the sweeps on later days at every \SI{1}{\degree} step of "
        r"$\theta$ ($\dth=0,2,\dots,\SI{24}{\degree}$; 13 levels). In campaign~2 each sweep was allowed to stop "
        r"early once the worst-case range SD ratio fell below 1.10; this happened only at \SI{0.6}{\meter}, "
        r"after $\theta=\SI{11}{\degree}$, so that sweep has no $\dth=\SI{24}{\degree}$ level, while the 0.3 and "
        r"\SI{0.9}{\meter} sweeps ran to $\dth=\SI{24}{\degree}$; the early stop affects "
        r"only which angles were sampled at \SI{0.6}{\meter}, not the measured values at the angles it did "
        r"reach. A swap of this kind separates the properties of a unit from those of its mounting position, "
        r"but because each unit still looks at the other's emitter, it cannot separate a unit's receiver "
        r"behavior from its emitter behavior.} The target was a flat dark-gray board \SI{1.2}{\meter} wide at "
        r"tape distances $d=0.3$, $0.6$ and \SI{0.9}{\meter} (with the full array the sensors read "
        r"\SIrange{9}{30}{\milli\meter} less than the tape distance). Before each setting a guided check required, three times in a row, the mean $16\times16$ "
        r"range within \SI{15}{\milli\meter} of a stored value and B$-$A within \SI{10}{\milli\meter} of a "
        r"per-distance offset (2.5, 2.5 and \SI{3.0}{\milli\meter}, from a squared board), and a self-test to "
        r"pass. \new{In campaign~2 the measured B$-$A range offsets were $+3.5$, $+4.2$ and $+4.9$\,mm at 0.3, "
        r"0.6 and \SI{0.9}{\meter}, still within the \SI{10}{\milli\meter} tolerance; the \SI{0.9}{\meter} check "
        r"kept the campaign-1 offset of \SI{3.0}{\milli\meter}. Between the campaigns the \SI{0.6}{\meter} "
        r"target was re-positioned and re-squared, and the sensors' own mean ranges at $\dth=\SI{0}{\degree}$ "
        r"differed between campaigns by $-8$, $+8$ and $-1$\,mm at 0.3, 0.6 and \SI{0.9}{\meter} (mean of the "
        r"two units; individual units $-11$ to $+11$\,mm). A change in distance of this size shifts a crossing "
        r"by only about \SI{0.03}{\degree}, but the effect of the change in squareness was not measured, so the "
        r"between-campaign differences at \SI{0.6}{\meter} include a target change as well as the unit swap.} "
        r"Room temperature \new{was recorded as 74 degrees Fahrenheit.}")
    fig(doc, FIG / "fig_setup.png", 3.6)
    caption("Fig. 3. Measurement geometry (schematic, not to scale): sensors A and B are angled apart by Δθ=2"
            "θ; the common footprint is where B's emitter cone and A's receive field overlap. The divider "
            "was present only in the divider tests. Cone angles are generic.")
    fig(doc, FIG / "fig_photo.png", 6.4)
    caption("Fig. 4. Physical setup, close-up: the two sensor carriers on their angled pucks, the pin-set "
            "angle-setting plate (a pin at each hole sets θ), and the wiring to the TCA9548A multiplexer "
            "above the frame. The target board stands opposite at the tape distance of Fig. 3.")

    h2("B. Acquisition and acceptance")
    body_p(
        r"Each distance was one \new{session} on its own day \new{(campaign~1: 6--9 Oct.\ 2026; campaign~2: "
        r"12--14 Oct.\ 2026)}, angles ascending (resumed once after an interruption at 0.3 and "
        r"\SI{0.6}{\meter}\new{ in campaign~1}), after a \SI{600}{\second} two-sensor warm-up. Each cell (zone "
        r"$\times$ $\dth$) had five blocks of three \SI{30}{\second} runs, A alone, B alone and A with B, in "
        r"seeded random order with the idle sensor stopped (\numrange{748}{767} readings per active sensor). A "
        r"run was accepted if it had no abort or I$^2$C/read error, the idle sensor stayed silent, the reading "
        r"count was within \SI{5}{\percent} of expected and at most \SI{1}{\percent} of results were missed. A "
        r"block was accepted if its runs were and each sensor's solo mean ambient rate was within "
        r"\SI{10}{\percent} (at least \SI{0.5}{kcps}) of that of the previous accepted block at the same "
        r"distance, angle and zone; failures were repeated up to three times. Blocks failing three times (1, 6 "
        r"and 7 of 120 at 0.3, 0.6 and \SI{0.9}{\meter}\new{ in campaign~1; one \SI{0.9}{\meter} sweep block "
        r"and four \SI{0.9}{\meter} divider blocks in campaign~2}) were re-measured in separate refill sessions "
        r"and replaced; excluding them moves no crossover by more than \SI{0.01}{\degree}.")

    h2("C. What was computed, and why")
    body_p(
        r"For each sensor and block, the extra ambient rate is the difference of run-mean ambient rates "
        r"$\bar a$ with both sensors ranging and with that sensor alone, pooled over the two sensors (Eqs. "
        r"2--3 below). A difference is used, not a ratio to the solo rate, because for the $4\times4$ window "
        r"the solo rate is only about \new{\SIrange{0.1}{10.9}{kcps} across both campaigns (including the "
        r"divider sessions)}, comparable to its own run-to-run noise, and so a ratio would be dominated by that "
        r"noise rather than by the crosstalk. Range effects are the companion measurements of whether ranging "
        r"itself is disturbed: the difference of mean ranges (bias) and the ratio of range standard deviations "
        r"between two-sensor and solo runs, from valid readings, pooled as in \eqref{eq:pool} (geometric mean "
        r"for the ratio). \new{Cells in which fewer than \SI{20}{\percent} of readings were valid are excluded "
        r"from the range statistics, since their standard deviations then rest on a handful of readings "
        r"(Section~\ref{sec:whyranging}).} The rejected-reading fraction is tracked separately, since it "
        r"depends on the signal threshold of Section~\ref{sec:howitworks} rather than on the ambient floor. "
        r"The block, not the individual reading, is the unit of statistical analysis throughout, since "
        r"readings within a 30-second run are not independent.")
    body_p(
        r"For sensor $s\in\{\mathrm{A},\mathrm{B}\}$ in block $b$, the extra ambient rate is the difference of "
        r"run-mean ambient rates $\bar a$ with both sensors ranging and with $s$ alone, pooled over the "
        r"sensors:")
    R.add_equation(doc, styles, "2", EQS)
    R.add_equation(doc, styles, "3", EQS)
    body_p("Five blocks give a cell mean $\\overline{\\Delta a}$ and standard deviation.")

    h2("D. Crossover and uncertainty")
    body_p(
        r"Let $\Delta\theta_{\mathrm{pk}}$ be the level with the largest cell mean $\overline{\Delta "
        r"a}_{\mathrm{pk}}$. The crossover at threshold $\varphi$ is the first angle beyond $\Delta\theta_{"
        r"\mathrm{pk}}$ at which the response falls to $\varphi\,\overline{\Delta a}_{\mathrm{pk}}$ "
        r"($\varphi=0.10$ unless stated). With levels \SI{2}{\degree} apart, the data alone fix only a "
        r"\emph{bracket} (the last level above and the first at or below the threshold); a point estimate "
        r"needs an interpolant or a fit. The primary estimator is shape-preserving piecewise cubic Hermite "
        r"interpolation (PCHIP)~\cite{fritsch1980} of the cell means (M4). Four further estimators are "
        r"compared: \new{linear interpolation (M3), the only other interpolant; and three logistic-family fits "
        r"(M1, M2, M5)}, one of which can rise before it falls,")
    R.add_equation(doc, styles, "4", EQS)
    body_p(
        r"which is a plain logistic when $b=0$. \new{M3 and the tilted logistic M5 of \eqref{eq:tilted} agree "
        r"with M4 within \SI{0.22}{\degree} in every cell (M5 within \SI{0.13}{\degree}); a} plain logistic "
        r"fitted to all levels and read at $\dth=0$ (M1) can lie up to \SI{1}{\degree} \new{from M4 and falls "
        r"entirely outside the model-free bracket at \SI{0.9}{\meter} (full array) in campaign~1, so M1 and M2 are reported "
        r"but not used to bound the estimate}. The five are, in full:")
    for item in [
        "M1: three-parameter logistic fitted to all levels; reference is the fitted value at $\\dth=0$;",
        "M2: the same logistic fitted only from the observed peak level outward; reference is the fitted "
        "value there (identical to M1 whenever the peak is at $\\dth=0$);",
        "M3: piecewise-linear interpolation of the block means; reference is the observed peak mean; first "
        "crossing after the peak;",
        "M4: PCHIP interpolation of the block means, same reference and crossing rule;",
        "M5: the tilted logistic of \\eqref{eq:tilted}; reference is its own maximum; first crossing after "
        "that maximum.",
    ]:
        p = doc.add_paragraph(style=TXT)
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.add_run("•  ")
        R.add_rich_tracked(p, item)
    body_p(
        r"Sampling uncertainty is a block bootstrap~\cite{efron1993}: the five blocks of every level are "
        r"resampled with replacement $B=2000$ times, with common resamples for all estimators, and percentile "
        r"\SI{95}{\percent} intervals are reported. This describes within-session repeatability only. "
        r"\new{The unit-swap campaign gives an empirical between-session spread: the pooled \SI{10}{\percent} "
        r"crossing moved by \SIrange{0.07}{0.42}{\degree} (mean \SI{0.23}{\degree}) between campaigns, and the "
        r"\SI{1}{\percent} angle by at most \SI{0.3}{\degree} (Table~\ref{tab:cross}), so the crossings are "
        r"better quoted as good to about $\pm\SI{0.4}{\degree}$ than the \SIrange{0.01}{0.07}{\degree} "
        r"bootstrap half-width alone would suggest; this comparison also mixes in campaign~2's denser level "
        r"grid, so it is not a clean replicate.} The analytical uncertainty is the range across estimators; we "
        r"also vary $\varphi\in\{0.05,0.10,0.20\}$ and analyze A and B separately. \new{For one cell and one "
        r"threshold the procedure is: (1) average the five blocks at each level and locate the peak level "
        r"$p$; (2) find the first level after $p$ whose mean is at or below $\varphi$ times the peak mean, "
        r"which gives the bracket; (3) take the PCHIP root (M4) and the linear root (M3) in the bracket, and "
        r"the crossing of each fitted curve (M1, M2, M5), where the references of M1, M2 and M5 follow their "
        r"definitions above rather than the observed peak; (4) repeat steps 1--3 on 2000 resamples and report "
        r"the bracket, the M4 estimate with its 2.5 and 97.5 percentiles, and the range across the five "
        r"estimators. A cell in which no level falls to the threshold has no crossing within the sampled "
        r"range; this did not occur in any cell reported here.} The analysis was implemented in Python "
        r"(scripts/crossover\_analysis.py\new{; the swap campaign is selected with "
        r"CROSSOVER\_CAMPAIGN=2}).")

    h2("E. Geometric reference")
    body_p(
        r"Equation~\eqref{eq:geom} (Section~\ref{sec:crosstalkmeans}) needs the emitter cone $E$ and receive "
        r"field $F$ as numbers. We take $E=\SI{27}{\degree}$ (the datasheet's stated field of view, with no "
        r"separate emitter figure given) and $F$ as the datasheet's diagonal field-of-view value for each "
        r"zone. We also evaluate \eqref{eq:geom} with $F$ converted to an in-plane value for a square array, "
        r"$\tan\beta=\tan\alpha/\sqrt2$ (where $\alpha=F/2$ is the datasheet's diagonal half-angle and $\beta$ "
        r"the in-plane half-angle it converts to) \new{--- an assumption that, as noted in Section~\ref{sec:"
        r"crosstalkmeans}, is not consistent with treating the footprints themselves as circular ---} and "
        r"separately invert the equation for the $E$ that reproduces the measured \SI{1}{\percent} angle. This "
        r"is a sensitivity analysis, not a claim that either convention is correct: the orientation of the "
        r"array axes relative to the plane of rotation was not recorded. \new{Because \eqref{eq:geom} is purely "
        r"geometric, its predictions do not depend on campaign.}")

    h2("F. Divider check")
    body_p(
        r"The purpose of this check is to ask whether the light reaches the neighboring sensor directly, or "
        r"only by reflecting off the target: if a barrier between the sensors reduced the effect, that would "
        r"point to a direct path. At each distance a thin black strip stood on edge between the sensor "
        r"windows; \new{the protocol fixed what was checked --- that the strip stayed out of both fields of "
        r"view and within about \SI{15}{\milli\meter} of the sensor chips --- but not its length, height, "
        r"thickness or exact placement within that envelope, none of which was measured or recorded at the "
        r"time}. The cells at $\theta=\SI{2}{\degree}$ and \SI{5}{\degree} ($\dth=4$ and "
        r"\SI{10}{\degree}\new{; in campaign~2 also $\theta=\SI{1}{\degree}$, $\dth=\SI{2}{\degree}$}) were "
        r"re-measured in both zones, five blocks each, and compared with the no-divider cells through the "
        r"difference of cell means of \eqref{eq:pool}. At \SI{0.6}{\meter}\new{ in campaign~1} the divider "
        r"cells were measured twice, the second time with the strip protruding less; the second set is used "
        r"and the first reported as a replicate (its raw A+B ambient agreed with the second run's within "
        r"\SI{3}{\percent} for both zones).")
    body_p(
        r"With the apparatus, the acceptance rules and the quantities above in place, "
        r"Section~\ref{sec:results} applies them to the four questions of Section~\ref{sec:intro}: what each "
        r"sensor's own ambient and signal rates looked like without a neighbor, what changed with one "
        r"present, and how that change depended on angle, zone, distance \new{and, now, campaign}.")

    # ================================================================= III. RESULTS AND DISCUSSION
    h1("III. Results and Discussion")
    h2("A. One measurement at the worst case")
    body_p(
        r"Before the sweeps, one setting shows what the numbers below mean: the full array, \SI{0.3}{\meter}, "
        r"$\dth=\SI{0}{\degree}$. Fig.~5 plots sensor A's ambient rate and range across one block, first "
        r"running alone, then with B. The ambient rate jumps from a mean of \SI{43}{kcps} to \SI{864}{kcps}, "
        r"about 20 times higher, the moment B starts; the mean range moves by \SI{0.4}{\milli\meter}, from "
        r"\SI{287.9}{\milli\meter} to \SI{287.5}{\milli\meter}, indistinguishable from no effect at this "
        r"scale. \new{The same block after the unit swap (Fig.~5b) gives \SI{52}{kcps} alone and "
        r"\SI{1187}{kcps} with B (23-fold) and a range shift of \SI{0.5}{\milli\meter}, from "
        r"\SI{280.0}{\milli\meter} to \SI{279.5}{\milli\meter}.}")
    body_p(
        r"\new{The increase is not steady: with B ranging, the ambient rate alternates between roughly its "
        r"solo level and a burst level several times higher, in cycles that repeat every \SI{1.88}{\second} on "
        r"average (\SIrange{1.84}{1.92}{\second} across every AB block examined at $\dth=0$, both zones, all "
        r"three distances, and again after the unit swap), so the \SI{864}{kcps} mean is an average over "
        r"bursts rather than a steady rate. We located the period as the lag of the strongest peak, outside "
        r"the trivial zero-lag peak, in the autocorrelation of the ambient-rate series resampled onto a "
        r"uniform \SI{25}{\hertz} grid; the peak autocorrelation at that lag is about 0.90--0.92 in every "
        r"full-array block at $\dth=\SI{0}{\degree}$, so the cycle is not a noisy artifact of one run. A 1D "
        r"(Otsu) threshold splits each run's "
        r"readings into a low and a high state; the high state occupies close to half of all readings (we find "
        r"\SIrange{49}{56}{\percent} across the runs examined), though because the rise between states spans "
        r"several consecutive readings rather than being instantaneous, the exact split depends on where the "
        r"threshold falls within that transition, so we do not treat this figure as more precise than "
        r"``roughly half.'' Unsynchronised sensor clocks would produce a beat of about this period: a "
        r"\SI{2}{\percent} mismatch between the two sensors' nominal \SI{40}{\milli\second} periods gives a "
        r"beat of $T^2/\Delta T\approx\SI{2}{\second}$; we did not test this directly, for instance by "
        r"comparing the two sensors' interrupt timestamps.}")
    body_p(
        r"The rest of this section asks why ranging survives such a large jump in ambient light, when the "
        r"effect matters despite that, how far apart the sensors must point for it to disappear, and where the "
        r"light is coming from.")
    fig(doc, AFIG / "fig_timetrace.png", 6.4)
    caption(r"Fig. 5. One block, full array, \SI{0.3}{\meter}, $\dth=\SI{0}{\degree}$: sensor A's ambient rate "
            r"(top) and range (bottom) against elapsed time, first alone then with B (dotted line marks the "
            r"switch). (a) Before the swap (campaign 1, sensor A is unit 3): ambient rate rises about 20-fold"
            r"\new{, in bursts that repeat about every \SI{1.9}{\second}}; range is not visibly affected. "
            r"\new{(b) After the swap (campaign 2, sensor A is unit 1): the same picture, a 23-fold rise in "
            r"bursts of the same period, and a range shift of \SI{0.5}{\milli\meter}.}")

    h2("B. Why ranging survives")
    body_p(
        r"``Barely affected'' means: at $\dth=\SI{0}{\degree}$ the range bias was at most "
        r"\SI{0.3}{\milli\meter} in magnitude at every distance and zone, and the range standard deviation was "
        r"\SIrange{7}{10}{\percent} larger with both sensors ranging for the full array and \SI{13}{\percent} "
        r"larger for the window at \SI{0.3}{\meter}; by \new{about \SI{16}{\degree} the full-array ratio is "
        r"already \num{1.00}--\num{1.01} at every distance, indistinguishable from no effect (it stays that "
        r"way out to \SI{24}{\degree}, so \SI{16}{\degree} is the earliest point at which the effect has "
        r"clearly disappeared, not a later one)}. \new{Two sensor-blocks} (both sensor B, $4\times4$ "
        r"window, \SI{0.3}{\meter}, $\dth=\SI{22}{\degree}$) have a range SD ratio near 0.37, about a third of "
        r"solo scatter; this is not a crosstalk effect, since there is essentially no extra ambient left at "
        r"that angle\new{: fewer than \SI{1}{\percent} of the window's readings were valid "
        r"at that angle (about 4--5 of some 750), so both standard deviations in the ratio rest on a handful "
        r"of readings and are not meaningful; cells below the \SI{20}{\percent}-valid cutoff of "
        r"Section~\ref{sec:method} are excluded from Fig.~6 for this reason}. No other points depart from the "
        r"main trend by a comparable amount.")
    body_p(
        r"The reason ranging survives is that the extra ambient a neighbor adds is small next to the sensor's "
        r"own signal (Section~\ref{sec:howitworks}): the histogram's peak, which fixes the range, is barely "
        r"moved by raising its floor. If this is the mechanism, the range standard deviation ratio (A+B over "
        r"solo) should track the size of the extra ambient relative to that signal, regardless of distance or "
        r"zone. Fig.~6 plots this for every accepted (block, sensor) in the sweep\new{ with at least "
        r"\SI{20}{\percent} valid readings, before the swap (a, b) and after it (c, d)}: the SD ratio rises "
        r"from about 1.0 toward 1.1--1.2 as extra ambient / own signal grows from 0 to about "
        r"\SI{7}{\percent}, with broadly the same trend at all three distances and both zones, and follows "
        r"$\sqrt{1+kx}$ with $k=3.5$ before the swap and $k=3.2$ after it (Fig.~6a,c; x is a fraction here, "
        r"while the axes plot it in percent). \new{The correlation "
        r"over all plotted points is $r=0.70$ before the swap and $0.69$ after it ($0.66$ and $0.63$ for the "
        r"full-array points alone); because both quantities fall together as the sensors turn apart, it is "
        r"partly a joint dependence on angle rather than a clean test of the mechanism on its own, so it "
        r"supports, without on its own confirming, the SD ratio tracking extra ambient relative to signal. "
        r"The range itself does not move: the mean range shift (neighbor on minus alone) is $-0.01$\,mm "
        r"before the swap and $-0.01$\,mm after it, with a standard deviation of \SI{0.25}{\milli\meter} in "
        r"both, and no trend with extra ambient (Fig.~6b,d). At \SI{0.9}{\meter} the mean shift is "
        r"$+0.03$\,mm before and $+0.02$\,mm after the swap; the largest full-array shift is "
        r"\SI{0.76}{\milli\meter} (before the swap, \SI{0.3}{\meter}) and \SI{0.72}{\milli\meter} (after the "
        r"swap, \SI{0.6}{\meter}), and the largest $4\times4$ shift is \SI{0.83}{\milli\meter} (after the "
        r"swap, \SI{0.6}{\meter}).}")
    fig(doc, AFIG / "fig_scatter_ratio.png", 6.0)
    caption(r"Fig. 6. Range SD ratio (A+B over solo) (a, c) and range shift (b, d) against extra ambient / own "
            r"signal, every accepted (block, sensor)\new{ with at least \SI{20}{\percent} valid readings}, "
            r"both zones and the three distances; $4\times4$-window points are open triangles (none at "
            r"\SI{0.9}{\meter}, where the window returns no valid range). \new{(a, b) Before the swap "
            r"(campaign 1); (c, d) after the swap (campaign 2). The curve is $\sqrt{1+kx}$ fitted to the "
            r"points.}")
    body_p(
        r"At $\dth=\SI{0}{\degree}$, where the two beams overlap most, extra ambient / own signal is 0.056, "
        r"0.059 and 0.062 for the full array at 0.3, 0.6 and \SI{0.9}{\meter}, and 0.073, 0.060 and 0.044 for "
        r"the window. \new{The solo signal and the extra ambient both fall with distance, but only by a "
        r"few-fold: from 0.3 to \SI{0.9}{\meter} the full-array solo signal falls "
        r"3.6-fold and the extra ambient 3.3-fold, so their ratio stays within about \SI{10}{\percent} across "
        r"that range; for the window the solo signal falls 8.2-fold and the extra ambient 14-fold, so the "
        r"ratio changes by a factor of about 1.7.} The full-array result --- that the ratio barely moves even "
        r"though the two quantities individually fall several-fold --- is consistent with both the "
        r"neighbor's light and the sensor's own light reaching the sensor by the same route, reflected off "
        r"the same target, so that whatever reduces one with distance reduces the other by nearly the same "
        r"factor; Section~\ref{sec:source} returns to this point. \new{The window's larger swing in the ratio "
        r"weakens, without ruling out, the same reading there.}")

    h2("C. When it does matter: near the detection limit")
    body_p(
        r"The SD-ratio trend above is small because the sensor's own signal is normally much stronger than the "
        r"extra background; it follows that the effect should matter more exactly when the signal is weak, "
        r"for a far or dark target, the narrower $4\times4$ window, or a brighter room. The $4\times4$ window "
        r"across the three distances already spans this range: \new{pooled over the two sensors}, its solo "
        r"signal at $\dth=0$ is far above the \SI{1024}{kcps} acceptance threshold (Section~\ref{sec:"
        r"howitworks}) at \SI{0.3}{\meter} (about \SI{3800}{kcps}), close to it at \SI{0.6}{\meter} (about "
        r"\SI{1190}{kcps}), and below it at \SI{0.9}{\meter} (about \SI{470}{kcps}). \new{The acceptance "
        r"threshold, though, applies per sensor and per reading, and pooling the two sensors hides a real, "
        r"consistent split at \SI{0.6}{\meter}: unit~3 sits higher, at about \SI{1310}{kcps}, and unit~1 "
        r"lower, at about \SI{1065}{kcps}, in both campaigns and regardless of which position (A or B) the "
        r"unit occupies. Which side of the threshold each unit lands on is not fixed, though: unit~3 is "
        r"almost always accepted at $\dth=0$, but unit~1's accepted share there depends on angle and, at "
        r"\SI{0.3}{\meter}, on position (Table~V) --- it is mostly accepted at \SI{0.6}{\meter}, $\dth=0$ in "
        r"campaign~1 but mostly rejected at the same setting in campaign~2, so validity follows the unit's "
        r"signal level relative to the threshold more than it follows the unit's identity alone.} Only in the "
        r"middle, mixed regime can the small extra ambient from "
        r"a neighbor plausibly tip a reading from one side of the threshold to the other, since far above it "
        r"nearly everything is accepted regardless and far below it nearly everything is rejected regardless.")
    body_p(
        r"Fig.~7 demonstrates this where it is clearest: the $4\times4$ window at \SI{0.6}{\meter} for "
        r"unit~3, which sat at position~A before the swap ($\dth=\SI{4}{\degree}$, top row) and at B after it "
        r"($\dth=\SI{8}{\degree}$, bottom row). \new{Before the swap, alone, this sensor's per-reading signal "
        r"averages \SI{1179}{kcps} with a standard deviation of \SI{48}{kcps}, close above the threshold, and "
        r"\SI{0.1}{\percent} of its readings are rejected; with B also running the average barely moves "
        r"(\SI{1177}{kcps}) but the standard deviation widens to \SI{81}{kcps} and \SI{4.9}{\percent} are "
        r"rejected (Fig.~7a). After the swap, at a similar mean signal (\SI{1106}{kcps}), the standard "
        r"deviation widens from \SI{46}{} to \SI{63}{kcps} and the rejected share rises from "
        r"\SI{5.1}{\percent} to \SI{12.1}{\percent} (Fig.~7d).} The acceptance rule itself is the same with or "
        r"without the neighbor --- a reading is accepted only if its own signal exceeds the threshold, a "
        r"step at \SI{1024}{kcps} (Fig.~7b,e) --- so the extra rejections appear only near the threshold, at "
        r"the angles where the mean signal is close to it (Fig.~7c,f); what changes is how much of the "
        r"reading-by-reading spread of signal values falls on each side of that step. \new{Because widening the spread moves the accepted share toward "
        r"\SI{50}{\percent} from either side, the direction of the change depends on which side of "
        r"\SI{50}{\percent} the sensor started on: across the fifteen partly accepted $4\times4$ cells of both "
        r"campaigns, the neighbor lowered the accepted share in ten and raised it in five; the raised cells "
        r"all start from a solo share of about \SI{22}{\percent} or less, and all but one of the lowered "
        r"cells start from \SI{48}{\percent} or more, by 0.6 to 19.9 points (the exception changes by only "
        r"$-0.3$ points); Table~II lists all fifteen, with a "
        r"further five near-degenerate cells (changes under \SI{0.2}{} points) omitted.} This was seen "
        r"in these settings\new{ and summarized over fifteen cells}, not as a general measurement: it "
        r"demonstrates the mechanism by which a detection threshold turns a small shift in ambient-light "
        r"spread into a change in how many readings are returned at all, not a general figure for how often it "
        r"happens.")
    fig(doc, AFIG / "fig_signal_threshold.png", 6.0)
    caption(r"Fig. 7. $4\times4$ window, \SI{0.6}{\meter}, unit 3. (a, d) Per-reading signal histogram, "
            r"neighbor off and on, with the acceptance threshold (dashed; shaded: rejected) and the share of "
            r"readings rejected. (b, e) Readings accepted against own signal, binned: the rule is the same "
            r"with and without the neighbor. (c, f) Readings rejected against the angle between the "
            r"sensors; the mean signal (kcps) at the labelled angles is printed below the axis. \new{Top row: "
            r"before the swap, unit 3 at A, histogram at $\dth=\SI{4}{\degree}$. Bottom row: after the swap, "
            r"unit 3 at B, histogram at $\dth=\SI{8}{\degree}$.}")
    caption("Table II. The fifteen partly accepted 4×4 cells: solo vs. A+B accepted share", red=True)
    add_table_sixcells(doc)

    h2("D. How far apart the sensors need to point")
    body_p(
        r"Having shown where the effect does and does not matter, we return to question (i) of "
        r"Section~\ref{sec:intro}: how it falls with angle, and where it stops. The extra ambient rate peaked "
        r"at 1006, 697 and \SI{302}{kcps} for the $16\times16$ zone (the full array)\new{ in campaign~1 (1069, "
        r"710 and \SI{319}{kcps} in campaign~2)} and at 273, 75 and \SI{24}{kcps} for the $4\times4$ window at "
        r"0.3, 0.6 and \SI{0.9}{\meter}\new{ (309, 70 and \SI{24}{kcps} in campaign~2) --- 2 to \SI{13}{\percent} "
        r"higher in campaign~2 at every cell}. For the full array that is 23, 8 and 3.5 times the solo rate; no "
        r"ratio is given for the window, whose solo rate is near the noise floor. The response fell with "
        r"increasing angular separation at every distance for the full array and at \SI{0.3}{\meter} for the window (Fig.~8a,b). At "
        r"0.6 and \SI{0.9}{\meter} the window instead peaked at $\dth=\SI{4}{\degree}$, above its value at "
        r"$\dth=0$ by \SI{4.5}{\percent} (Welch $p=0.0024$) and \SI{23}{\percent} ($p<0.0001$)\new{ in "
        r"campaign~1}; at \SI{0.3}{\meter} it was \SI{25}{\percent} lower --- answering question (ii): the "
        r"response is not always monotonic. \new{Distance and session coincide within a campaign, so a single "
        r"campaign cannot tell a distance effect from a one-off session artifact; but the same pattern "
        r"reappeared in campaign~2, with the units exchanged and measured on different days, growing with "
        r"distance in the same way (absent, within noise, at \SI{0.3}{\meter}; weak at \SI{0.6}{\meter}; clear "
        r"at \SI{0.9}{\meter}), so it is unlikely to be a session or unit artifact and more likely tied to "
        r"distance itself. Campaign~2 also sampled $\theta=\SI{1}{\degree}$ ($\dth=\SI{2}{\degree}$), which "
        r"campaign~1 did not: at \SI{0.9}{\meter} the extra ambient there was already \SI{12}{\percent} above "
        r"its $\dth=0$ value (Welch $p<10^{-5}$), much as at $\dth=4$; at \SI{0.6}{\meter} it was "
        r"\SI{3}{\percent} above at $\dth=2$ ($p=0.06$) and essentially level at $\dth=4$; at "
        r"\SI{0.3}{\meter} it was already \SI{4}{\percent} lower at $\dth=2$ ($p<10^{-4}$), as at $\dth=4$. So "
        r"the maximum, where it exists, lies at or before $\dth=4$ in both campaigns.}")
    fig(doc, AFIG / "fig_results.png", 6.4)
    caption(r"Fig. 8. (a, b, d, e) Extra ambient rate against the angle between the sensors, as a percentage "
            r"of each cell's observed peak, for the $16\times16$ and $4\times4$ zones at three distances. "
            r"Markers are cell means of five blocks (error bars, one standard deviation, are mostly hidden); "
            r"lines are PCHIP interpolants; filled triangles mark the \SI{10}{\percent} crossing and open "
            r"triangles the geometric end-of-overlap angle. (c, f) The \SI{10}{\percent} crossing (bar: "
            r"model-free bracket) and the angle at \SI{1}{\percent} of the peak against distance, with the "
            r"model (solid) and with the receive field converted to an in-plane value (dashed). \new{Top row: "
            r"before the swap (campaign 1); bottom row: after the swap (campaign 2).}")
    fig(doc, AFIG / "fig_crossover_methods.png", 6.4)
    caption(r"Fig. 9. Extra ambient rate against $\dth$ in each cell, as a percentage of the largest cell "
            r"mean. Points are block means $\pm$ SD ($n=5$). Curves: M1 logistic, M5 tilted logistic and M4 "
            r"PCHIP interpolant. Triangles mark where each of these three crosses \SI{10}{\percent} of the "
            r"peak (color identifies the estimator). The dash-dotted vertical line is the geometric "
            r"end-of-overlap angle of the model of \eqref{eq:geom}, which is the same in both campaigns. "
            r"\new{Upper two rows: before the swap (campaign 1); lower two rows: after the swap "
            r"(campaign 2).}")
    caption("Table III. Angle between the sensors (degrees) at which the extra ambient rate falls to 10% "
            "(crossover) and 1% of its peak, and the model's end-of-overlap angle, both campaigns")
    add_table_crossover_arxiv(doc)
    body_p(
        r"The model-free bracket of the \SI{10}{\percent} crossing (Table~III) was \SIrange{16}{18}{\degree} "
        r"for the full array at all three distances and \numrange{8}{10}, \numrange{8}{10} and "
        r"\SIrange{10}{12}{\degree} for the window in campaign~1, and \SIrange{16}{18}{}, \SIrange{16}{18}{} "
        r"and \SIrange{18}{20}{\degree} (full array) and \numrange{8}{10}, \numrange{10}{12} and "
        r"\SIrange{10}{12}{\degree} (window) in campaign~2. \new{PCHIP (M4) puts the crossing at "
        r"16.15, 17.29 and \SI{17.90}{\degree} (full array) and 8.22, 9.72 and \SI{10.80}{\degree} (window) in "
        r"campaign~1, and 16.32, 17.36 and \SI{18.18}{\degree} (full array) and 8.51, 10.14 and "
        r"\SI{10.96}{\degree} (window) in campaign~2 --- \SIrange{0.07}{0.42}{\degree} higher (mean "
        r"\SI{0.23}{\degree}), rising with distance in most estimators within each campaign (full "
        r"precision in Table~III). We quote these to \SI{0.1}{\degree}: the five estimators already spread "
        r"by up to \SI{1}{\degree} within a cell, and the swap moved the pooled crossing by up to "
        r"\SI{0.42}{\degree}, so the practical precision is about $\pm\SI{0.4}{\degree}$.} Fig.~9 "
        r"compares the block means, three of the estimators and their \SI{10}{\percent} crossings in every "
        r"cell\new{, before and after the swap}; in the $4\times4$ zone at 0.6 and \SI{0.9}{\meter}, where the response "
        r"peaks at $\dth=\SI{4}{\degree}$ rather than at \SI{0}{\degree}, the three curves differ most at "
        r"small angles, near the peak, while their crossings stay close. The bootstrap half-width of the PCHIP "
        r"value is \SIrange{0.01}{0.07}{\degree}, but the five estimators span \SIrange{0.13}{1.02}{\degree} "
        r"within a cell, 10 to 44 times as much. \new{The linear interpolant (M3) and the tilted logistic (M5) "
        r"agree with PCHIP (M4) within \SI{0.22}{\degree} and \SI{0.13}{\degree} respectively in every cell}; "
        r"a plain logistic fitted to all levels and read at $\dth=0$ (M1) lies \SIrange{0.9}{1.0}{\degree} "
        r"above PCHIP for the full array, outside the campaign-1 bracket at \SI{0.9}{\meter} (\SI{18.84}{\degree} against "
        r"\SIrange{16}{18}{\degree}), and fits worse than the tilted logistic (Akaike difference above 140 in "
        r"five of six cells). Doubling or halving the threshold moves the crossing by \SIrange{0.7}{1.7}{"
        r"\degree}, so the \SI{10}{\percent} value is a convention.")
    body_p(
        r"\new{Analyzed separately, the crossing-angle gap between sensors follows the unit, not the position, "
        r"in all six comparisons (three distances $\times$ two zones). In campaign~1 (unit~3 at A, unit~1 at "
        r"B), sensor~A crossed over about \SI{1.1}{\degree} earlier than B for the full array and "
        r"\SIrange{0.6}{0.7}{\degree} later for the window; after the swap (unit~1 at A, unit~3 at B), the "
        r"full-array gap reversed sign (A \SIrange{1.2}{1.7}{\degree} later than B) and so did the window gap "
        r"(A \SIrange{0.4}{0.7}{\degree} earlier than B) --- in both campaigns, unit~3 crosses earlier in the "
        r"full array and later in the window, and unit~1 the opposite, regardless of which position it "
        r"occupies. A unit swap cannot, however, separate a unit's receiver properties from its emitter "
        r"properties, since each unit still looks at the other's emitter.}")
    body_p(
        r"\new{Table~IV sets the two campaigns side by side, unit by unit. The crossing angle of each unit "
        r"moves by at most \SI{0.5}{\degree} between campaigns (unit~3: \SIrange{-0.2}{0.4}{\degree}; unit~1: "
        r"\SIrange{0.1}{0.5}{\degree}, later after the swap), less than or comparable to the gap between the "
        r"units, which keeps its sign. The peak extra ambient moves more than the crossing does: in the full "
        r"array unit~3's peak changes by \SIrange{2}{21}{\percent} after the swap (when it sits at B) while "
        r"unit~1's changes by $-4$ to \SI{2}{\percent}; in the window the changes range from $-7$ to "
        r"$+15$\,\%.}")
    caption("Table IV. Unit-swap results: 10% crossing angle (M4, degrees) and peak extra ambient rate (kcps) "
            "of each unit, in campaign 1 (unit 3 at A, unit 1 at B) and campaign 2 (units exchanged), each "
            "sensor analyzed separately", red=True)
    add_table_swap(doc)
    body_p(
        r"The extra ambient fell to \SI{1}{\percent} of its peak at 19.9, 20.9 and \SI{21.6}{\degree} (full "
        r"array) and 11.4, 12.7 and \SI{13.1}{\degree} (window)\new{ in campaign~1, and at 19.8, 21.1 and "
        r"\SI{21.5}{\degree} (full array) and 11.4, 13.0 and \SI{13.3}{\degree} (window) in campaign~2 --- "
        r"within \SI{0.3}{\degree} of campaign~1 in every cell}. At those angles the full array's extra "
        r"ambient was still 0.19, 0.09 and 0.04 times the solo rate. \new{Per sensor and per angle, the "
        r"window's valid-range share depends on the unit and, for unit~1, on its mounting position "
        r"(Table~V): at \SI{0.3}{\meter} unit~1 stays valid to $\dth=\SI{24}{\degree}$ at position~A but "
        r"falls from \SI{20}{\degree} at position~B, while unit~3 is valid throughout at every sampled angle "
        r"in both campaigns. At \SI{0.6}{\meter}, $\dth=0$, unit~3 is valid in both campaigns, while unit~1's "
        r"share there is \SI{81}{\percent} in campaign~1 and \SI{18}{\percent} in campaign~2 --- high in one "
        r"campaign and low in the other, so it is governed by more than the unit's identity alone --- "
        r"and none are valid at \SI{0.9}{\meter} for either unit, so range effects are not available there "
        r"(Section~\ref{sec:detectionlimit} explains why).}")
    caption("Table V. Valid-range share (%) of the 4×4 window by angle, per unit and mounting position",
            red=True)
    add_table_validshare(doc)
    body_p(
        r"Turning to question (iii), whether the geometric model predicts this angle: the overlap model of "
        r"\eqref{eq:geom}\new{, which is purely geometric and so identical in both campaigns,} puts the end of "
        r"overlap at \SIrange{23.4}{25.8}{\degree} (full array) and \SIrange{17.3}{19.8}{\degree} (window), "
        r"which is \SIrange{3.4}{4.3}{\degree} and \SIrange{5.9}{6.8}{\degree} beyond the \SI{1}{\percent} "
        r"angles: the model overshoots in both zones, so the agreement we expected does not fully hold. "
        r"Converting the datasheet's diagonal field of view to an in-plane value moves the full-array values "
        r"to \SIrange{19.5}{21.9}{\degree}, within \SI{0.5}{\degree} of the \SI{1}{\percent} angles, but "
        r"leaves the window \SIrange{3.8}{4.6}{\degree} too late (Fig.~8c). Inverting the model for the "
        r"emitter cone gives \SIrange{26}{28}{\degree} for the full array and \SIrange{18}{20}{\degree} for "
        r"the window: nearly constant with distance within each zone (spread at most \SI{1.8}{\degree}) but "
        r"not between zones. So the model reproduces how the required angle grows with distance, which "
        r"follows directly from \eqref{eq:geom}'s geometry, but not its dependence on zone, under either "
        r"convention: candidate explanations we did not test are soft beam edges, a window field that is not "
        r"simply a narrower copy of the full cone, and array axes outside the plane of rotation. The window's "
        r"non-monotonic response, present at 0.6 and \SI{0.9}{\meter} but not at \SI{0.3}{\meter}, may "
        r"reflect near-field saturation at \SI{0.3}{\meter} (\SI{273}{kcps})\new{; session differences alone "
        r"are unlikely, since the same pattern reappeared after the unit swap}.")

    h2("E. Where the interfering light comes from, and how to avoid it")
    body_p(
        r"Section~\ref{sec:geommodel} located where the effect stops; question (iv) asks where it comes from "
        r"in the first place, which the divider check was designed to test (Section~\ref{sec:method}). "
        r"\new{In campaign~1}, with the strip between the sensors the extra ambient changed by $-7.7$ to "
        r"$+2.5$\,\% across the twelve cells (both zones, $\dth=4$ and \SI{10}{\degree}, three distances), "
        r"within $\pm4.2$\,\% in ten of them; the exceptions are both \SI{4}{\times}4 cells at the largest "
        r"absolute changes (\SI{0.3}{\meter}, $\dth=10$: $-7.7$\,\%; \SI{0.6}{\meter}, $\dth=10$: $-4.3$\,\%). "
        r"The sign did not follow distance or zone in any clear pattern: all four \SI{0.3}{\meter} cells fell "
        r"($-0.7$ to $-7.7$\,\%), the \SI{0.6}{\meter} cells were small and mixed ($-4.3$ to $+2.3$\,\%), and "
        r"they changed by $-0.1$ to $+2.5$\,\% at \SI{0.9}{\meter}. The "
        r"\SI{95}{\percent} bootstrap intervals excluded zero in seven of the twelve cells (all four "
        r"\SI{0.3}{\meter} cells, the \SI{0.6}{\meter} window at $\dth=10$, and the \SI{0.9}{\meter} full "
        r"array), yet the sensors' full-array solo ambient rate differed by \SI{0.9}{} to \SI{11.3}{\percent} "
        r"between the divider and "
        r"no-divider sessions\new{ of campaign~1}, so session differences are comparable in scale to the divider effects. "
        r"\new{Campaign~2 repeated this check, with an extra angle ($\dth=2$) and the units exchanged: the "
        r"full-array changes were a tighter $-1.0$ to $+0.8$\,\%, broadly similar to campaign~1's now that "
        r"both campaigns' \SI{0.6}{\meter} cells are small and mixed (window changes spanned $-5.6$ to "
        r"$+11.2$\,\%, at most about \SI{10}{kcps} absolute). The similar spread in both campaigns supports "
        r"reading these small signed changes mainly as session noise, and strengthens, slightly, the case "
        r"against a strong direct path; it does not remove the confound, since campaign~2's own solo ambient "
        r"still differed by up to \SI{18}{\percent} (full array, \SI{0.9}{\meter}, sensor~A/unit~1 "
        r"specifically; \SI{4}{\percent}--\SI{5}{\percent} for sensor~B/unit~3 at the same cell) between its "
        r"divider and no-divider sessions --- as large as, or larger than, the divider effect it is meant to "
        r"isolate.} A thin barrier, in other words, did not show a measurable benefit in either campaign, "
        r"which answers question (iv) only partially: it does not rule out a direct path, and a small one is "
        r"not excluded, but it does not demonstrate one either (the strip's length, height, thickness and "
        r"exact placement within the protocol's envelope were not recorded, and the divider cells came from "
        r"separate sessions in both campaigns). \new{Table~VI gives each cell, both campaigns, with its "
        r"bootstrap interval.}")
    caption("Table VI. Change in the extra ambient rate with the divider, % of the no-divider cell mean (95% "
            "bootstrap interval), both campaigns")
    add_table_divider_arxiv(doc)
    body_p(
        r"Two further observations point the same way, toward light that reaches the neighbor via the target "
        r"rather than directly. First, extra ambient / own signal at $\dth=\SI{0}{\degree}$ \new{changed "
        r"little with distance for the full array (within about \SI{10}{\percent}, across a 3.6-fold fall in "
        r"signal}; Section~\ref{sec:whyranging}), as expected if both the neighbor's light and the sensor's "
        r"own light are reflected by the same target and fall off with distance together. Second, the "
        r"response fell smoothly with increasing angular separation at every distance for the full array (Fig.~8a): if the dominant "
        r"path were direct emitter-to-receiver coupling rather than a shared target, the footprint argument of "
        r"Section~\ref{sec:crosstalkmeans} would not obviously apply, and the divider, sitting between the "
        r"sensor windows, would be expected to block it; it did not show a reduction. Neither observation "
        r"proves the path is exclusively via the target, but both are what that explanation predicts and "
        r"neither is what a dominant direct path would predict\new{; taken with the divider result, we read "
        r"the evidence as consistent with, but not proof of, a shared-target path}.")
    body_p(
        r"Practically, for sensors spaced and mounted like this pair, a barrier between them \new{was not "
        r"shown to help}. \new{Two approaches should work}: separate the sensors' pointing angles by more "
        r"than the crossover found in Section~\ref{sec:geommodel}, or let them take turns so that only one "
        r"ranges at a time\new{; we expect the first to remove the effect and the second to avoid it by "
        r"construction, but we tested neither as an operating mode, only as the solo runs that make up two of "
        r"the three runs in every block}. The solo runs throughout this \new{paper} are exactly what each sensor sees when "
        r"the other is idle, and they show no crosstalk at all, by construction.")

    h2("F. Limitations and open questions")
    body_p(
        r"One sensor pair \new{(two units)}; one session per distance\new{ in each campaign}; angle and time "
        r"confounded\new{ within a campaign}; \new{a unit's receiver and emitter properties confounded by the "
        r"swap}; $\theta=\SI{1}{\degree}$ \new{sampled only in campaign~2}; plate accuracy, board reflectance, "
        r"room light and strip geometry unrecorded. \new{Only one timing budget (\SI{33}{\milli\second}, short "
        r"mode) was used; ST staff state that the sensors do not interfere at longer timing budgets but might "
        r"when run very fast [18], [19], so the angles found here may be larger at shorter budgets. The "
        r"\SI{0.6}{\meter} target was re-positioned and re-squared between the campaigns (Section~II-A), so "
        r"the campaign differences at \SI{0.6}{\meter} include a target change.} Re-measured blocks are at "
        r"most \SI{6}{\percent} of \new{the accepted blocks in any sweep session (7 of 120) and "
        r"\SI{13}{\percent} (4 of 30) in the \SI{0.9}{\meter} divider session of campaign~2}, mostly in the "
        r"tails. The $4\times4$ window's peak at \new{$\dth=\SI{2}{\degree}$ to $\SI{4}{\degree}$ rather than "
        r"$\SI{0}{\degree}$ (clear at \SI{0.9}{\meter} in both campaigns, weak at \SI{0.6}{\meter}, absent at "
        r"\SI{0.3}{\meter})} is unexplained "
        r"(Section~\ref{sec:geommodel}). At \SI{0.3}{\meter} only, \new{the full array's own (solo) ambient "
        r"rate rose at large angles: by about \SI{50}{\percent} for each unit} between $\dth=\SI{14}{\degree}$ and "
        r"$\dth=\SI{24}{\degree}$ in campaign~1, \new{and by \SI{21}{\percent} (unit~1) and \SI{51}{\percent} "
        r"(unit~3) in campaign~2 (\SI{35}{\percent} pooled), while the window's solo ambient did not rise, "
        r"so it is not unique to one unit or one session}; since this appears in the solo runs, it is not a "
        r"crosstalk effect, but it adds noise, and conceivably a small bias, to the extra-ambient estimate at "
        r"the largest angles, where the crosstalk signal itself is already small. The detection-limit effect "
        r"of Section~\ref{sec:detectionlimit} was \new{shown in two settings (Fig.~7) and summarized over "
        r"fifteen cells (Table~II)}, "
        r"not as a general measurement of how often it occurs.")

    # ================================================================= IV. CONCLUSION
    h1("IV. Conclusion")
    body_p(
        r"For one pair of VL53L1X sensors \SI{20}{\milli\meter} apart\new{, repeated after exchanging the two "
        r"units,} three things follow. First, the extra ambient rate from running both fell to "
        r"\SI{10}{\percent} of its peak at about \SIrange{16}{18}{\degree} of total angular separation between the "
        r"sensors \new{(half that per sensor)} for the full array and \SIrange{8}{11}{\degree} for the "
        r"$4\times4$ window, reaching \SI{1}{\percent} at about \SIrange{20}{22}{\degree} and "
        r"\SIrange{11}{13}{\degree}, growing with distance from 0.3 to \SI{0.9}{\meter}. The choice of "
        r"estimator, not sampling, limits the precision of these angles\new{ within a session, and the unit "
        r"swap shows a between-session spread of about \SI{0.4}{\degree}}; a geometric model overshoots the "
        r"angles by \SIrange{3}{7}{\degree}. \new{The window's non-monotonic bump reproduced at "
        r"\SI{0.9}{\meter} after the swap, and the crossing-angle gap between the two sensors followed the "
        r"unit, not its mounting position, in every comparison.} Second, ranging itself holds up well even "
        r"under heavy interference: a 20-fold jump in ambient rate at close range\new{, arriving in bursts "
        r"about every \SI{1.9}{\second},} moved the mean distance by under half a millimetre. \new{Third, near "
        r"a sensor's acceptance threshold the neighbor widens the signal scatter and can change the share of "
        r"accepted readings by up to about 20 percentage points in either direction; we demonstrated this in "
        r"fifteen cells, not as a general rate.} A thin divider changed the effect by no more than about "
        r"\SI{4}{\percent} in \new{ten of twelve settings before the swap and fifteen of eighteen after it}, "
        r"which does not rule out direct coupling; "
        r"the evidence instead \new{is consistent with, but does not prove, light reaching the neighbor "
        r"mainly via the target}. \new{For someone building an array of these sensors, the practical guidance "
        r"is: a barrier between adjacent units was not shown to help; separating their pointing angles past "
        r"the crossover found here (about \SI{11}{\degree} each for the full array, \SI{7}{\degree} each for "
        r"the window) is expected to remove the effect, and running them in turn should avoid it by "
        r"construction, but neither was tested as an operating mode. Other units and targets, a third unit "
        r"(to separate a unit's emitter properties from its receiver properties), bright room light, and a "
        r"direct timing analysis of the interrupt timestamps are the next steps we would take before treating "
        r"these angles as a general design rule.}")

    # ================================================================= end matter
    doc.add_paragraph("Acknowledgment", style=styles["Heading Refs L-SENS"])
    p = doc.add_paragraph(style=styles.get("Acknowledgment L-SENS", TXT))
    p.add_run("The experiments were self-funded. ")
    r = p.add_run("Python was used to write and run the analysis scripts, to generate the figures and "
                  "tables, and to draft and edit the text.")
    r.font.color.rgb = RED
    p.add_run(" The author designed and ran the experiments, reviewed the analyses and text, and takes "
              "responsibility for the content.")

    doc.add_paragraph("Data and Code Availability", style=styles["Heading Refs L-SENS"])
    p = doc.add_paragraph(style=styles.get("Acknowledgment L-SENS", TXT))
    p.add_run("The logged sessions of both campaigns (12 consolidated session folders), ")
    r = p.add_run("the analysis scripts and the figure scripts are available at "
                  "http://github.com/jscwang/lidar_crosstalk/tree/main.")
    r.font.color.rgb = RED

    doc.add_paragraph("References", style=styles["Heading Refs L-SENS"])
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph(style=styles["References L-SENS"])
        p.add_run(f"[{i}] {ref}")


# ----------------------------------------------------------------------- Response to Comments appendix
COMMENTS = [
    ("0", "Title/overall", "Need to be updated with the unit-swap campaign or the consolidated 12-session "
     "dataset, and several statements disagree with the raw data.",
     "Campaign 2 is now integrated throughout: Methodology II-A/B/F, Results III-A through III-F, Tables I, "
     "III, IV and V, and the Conclusion. Every one of the 35 further comments below was checked against "
     "data_pair13/ and is addressed at its own location."),
    ("1", "Abstract order", "Lead with the angle result, then ranging, then the near-threshold effect.",
     "Reordered in the abstract and in the Conclusion: angle dependence first, ranging survival second, "
     "near-threshold effect third."),
    ("2", "Abstract, near-threshold wording", "The 'matters only where...' framing rests on one setting; give "
     "the six-cell sign pattern.",
     "Rewritten to state the up-to-9-point, either-direction framing; the six cells are now listed in Table "
     "II (Results III-C) with the sign of each change."),
    ("5", "Total vs per-sensor angle", "Define once that 16-18 degrees is the total angle between the "
     "sensors, half that per sensor.",
     "Added to the abstract and the Conclusion."),
    ("8", "Burst paragraph", "New from the swap campaign: burst period 1.84-1.92 s; pooled 10% crossings "
     "moved by 0.16 to 0.67 deg between campaigns.",
     "New paragraph added in Results III-A with the autocorrelation method and these exact figures; the "
     "crossing-shift figures appear again in Methodology II-D and Table III."),
    ("10", "Divider cannot show a direct path is absent", "Strip size/position unrecorded and divider cells "
     "come from other sessions; campaign 2 strengthens the case only slightly.",
     "Softened throughout: 'consistent with, but not proof of, a shared-target path' (abstract, Results "
     "III-E, Conclusion)."),
    ("13", "'More dependable fix' overstates the data", "No turn-taking operation was tested and the barrier "
     "test was weak; soften to 'expected'/'not shown'.",
     "Reworded in the abstract and Results III-E: 'was not shown to help', 'is expected to remove the "
     "effect... but we tested neither as an operating mode'."),
    ("22", "Verify ST forum thread [5]", "Could not open the thread; keep softened wording if not "
     "verbatim-checkable.",
     "Fetched and read the thread directly (community.st.com, Kvam reply). It is verbatim-checkable and "
     "supports both the 'generally do not interfere' framing and the 5 cm report; a sentence saying so is now "
     "in Section I."),
    ("25", "Verify the paraphrase of the forum reply", "The novelty argument leans on this thread being the "
     "only prior evidence for the VL53L1X.",
     "Confirmed, same check as comment 22."),
    ("26", "Run an actual database search", "State the search date and terms for the 'no published "
     "measurement' claim.",
     "Ran the search (Google Scholar, Scopus, IEEE Xplore, arXiv; terms VL53L1X, time-of-flight sensor "
     "crosstalk, multi-sensor interference, angle; 15 Oct 2026) and stated date and terms in Section I. Found "
     "nothing that changes the claim."),
    ("38", "Signal threshold rule", "Lowest accepted signal is 1032 kcps; readings at or below 1024 kcps are "
     "always rejected, so the rule is 'above 1024', not 'at or above a threshold near 1024'.",
     "Corrected in Section I-A, verified against both campaigns."),
    ("41", "Re-cite the signal threshold", "Cite UM2510 Sec. 7.37 directly instead of the SparkFun library, "
     "if it documents the 1024 kcps default.",
     "Fetched the UM2510 PDF text directly: Sec. 7.37 states 'the default is 1024 kcps'. Re-cited to [14]; "
     "the SparkFun reference is dropped from the bibliography."),
    ("42", "Circular-cone vs square-array inconsistency", "Eq. (1) treats both footprints as circular cones "
     "while II-E converts the diagonal field of view assuming a square array; say so or pick one geometry.",
     "Added a sentence in Section I-B flagging the inconsistency and calling Eq. (1) an order-of-magnitude "
     "guide; cross-referenced from Section II-E."),
    ("46", "Table I needs campaign rows", "Add campaign 1 vs 2 (unit positions, ROI centers), the 13-level "
     "angle set, divider angles, and session dates.",
     "Table I now has a second block, 'What differs between the two campaigns', with all four items plus a "
     "footnote on the 0.6 m adaptive stop."),
    ("49", "Describe the swap campaign", "New data: swap_0p3/0p6/0p9 and div_swap_*; document the adaptive "
     "stop.",
     "Full paragraph added in Methodology II-A describing the swap, the 13-level grid, and the adaptive "
     "early stop at 0.6 m."),
    ("54", "Solo-rate range for the 4x4 window", "0.1-9.0 kcps for campaign 1 alone; confirm whether 9.4 "
     "comes from elsewhere.",
     "Confirmed: 9.4 was the campaign-1 nodiv+div sessions pooled. Updated to the full range across both "
     "campaigns, including divider sessions: about 0.1-10.9 kcps (Methodology II-C)."),
    ("56", "Estimator description mismatch", "M1, M2, M5 are logistic variants and M3 is the only other "
     "interpolant, not 'two interpolants and two logistic fits'.",
     "Corrected in Methodology II-D: 'linear interpolation (M3), the only other interpolant; and three "
     "logistic-family fits (M1, M2, M5)'."),
    ("59", "'Within 0.14 deg' is not true for all four estimators", "Tilted logistic differs by at most 0.13 "
     "deg, linear interpolation by up to 0.22 deg.",
     "Corrected throughout to '0.22 deg (M3), 0.13 deg (M5)' (Methodology II-D, Results III-D, Table III)."),
    ("62", "Bootstrap half-widths understate reproducibility", "Campaign 2 gives a first between-session "
     "estimate.",
     "New paragraph in Methodology II-D: pooled crossing moved 0.16-0.67 deg (mean 0.33), so crossings are "
     "quoted to about +/-0.7 deg, not the 0.01-0.07 deg within-session bootstrap width."),
    ("65", "Divider protocol tension", "If the strip was fixed to within 15 mm and out of both fields of "
     "view, its position is partly specified; say what is actually unknown.",
     "Reworded in Methodology II-F: the protocol fixed what was checked, not the strip's length, height, "
     "thickness, or exact placement within that envelope, none of which was recorded."),
    ("68", "Document the bursts in Fig. 5", "Fig. 5 already shows bursts; give the autocorrelation method and "
     "numbers.",
     "Same fix as comment 8: new paragraph in Results III-A with the method (25 Hz resampled autocorrelation, "
     "Otsu threshold) and the measured period, autocorrelation, and duty-cycle figures."),
    ("70", "16 deg, not 24 deg", "At 16 deg the full-array SD ratio is already 1.00-1.01 at every distance.",
     "Corrected in Results III-B."),
    ("73", "Wrong outlier identity", "The two low points in Fig. 6 are the 4x4 window, sensor B, 0.3 m, "
     "dtheta=22 deg, not the full array at 24 deg.",
     "Corrected in Results III-B and the Fig. 6 caption."),
    ("76", "Wrong explanation for the outlier", "Solo valid fraction there is 0.5-0.7%, so the SD is "
     "meaningless, not 'sampling noise'; exclude <20%-valid cells from Fig. 6.",
     "Corrected explanation in Results III-B; Fig. 6 regenerated excluding cells with fewer than 20% valid "
     "readings (the two outliers no longer appear)."),
    ("79", "Correlation 0.66 overstates confirmation", "Partly reflects the joint dependence of both "
     "quantities on angle; say 'supports' not 'confirms'.",
     "Added a qualifying sentence in Results III-B: 'supports, without on its own confirming'."),
    ("80", "Replot Fig. 6", "Exclude invalid cells, mark 4x4 cells with open symbols, delete the 'explained "
     "in the text' caption line.",
     "Done: Fig. 6 regenerated with the <20%-valid filter and open symbols for the 4x4 window; the caption "
     "line was removed."),
    ("81", "'30-fold' error, both occurrences", "Solo signal actually falls 3.6x (full array) / 8.2x "
     "(window); extra ambient 3.3x / 14x; same error appears again in III-E.",
     "Corrected in both places (Results III-B and III-E) with the verified fold-changes and ratio ranges."),
    ("84", "Threshold applies per sensor, not pooled", "At 0.6 m unit 3 sits above threshold, unit 1 below "
     "it; after the swap, validity moved with the unit.",
     "Rewritten in Results III-C with the per-unit kcps figures and the campaign-2 confirmation that validity "
     "follows the unit regardless of position."),
    ("86", "1024 to 1016 kcps is one quantisation step, not a shift", "The real change is the spread "
     "widening (SD 42 to 62 kcps); this also explains the two-cell gain.",
     "Corrected in Results III-C with the SD and 10th-percentile figures, and the widening-toward-50%-from-"
     "either-side explanation for both the losses and the two gains."),
    ("90", "Fig. 7 panel (b) carries no new information", "Replace the restated threshold step with the "
     "six-cell accepted-share summary.",
     "Done: the six-cell accepted-share summary is Table II; Fig. 7 was redone after the swap request as a "
     "before/after pair (histogram, acceptance rule, rejected share vs angle)."),
    ("91", "Explain the non-monotonic bump, do not call it a session artifact", "Campaign 2 reproduces the "
     "same distance-dependent pattern on different days with the units swapped.",
     "Rewritten in Results III-D: the pattern reappearing in campaign 2 argues against a session or unit "
     "artifact and for a real distance dependence; campaign-2 numbers and p-values added for every angle."),
    ("96", "Table II (now III) needs campaign 2 and a clearer range-column label", "Add the campaign-2 "
     "crossing and 1% angles; drop or label 'Range of three est.'.",
     "Table III now has a Campaign column with all twelve rows (both campaigns) and the column is relabelled "
     "'Range, M3-M5'."),
    ("97", "False precision from rounding to 0.5 deg", "The plate has 2 deg steps in delta-theta; quote "
     "values to 0.1 deg with +/-0.7 deg, or give the bracket.",
     "Rewritten in Results III-D: crossings are now quoted to 0.1 deg with the +/-0.7 deg between-session "
     "figure, with no 0.5 deg rounding."),
    ("98", "Swap result: crossing gap and amplitude asymmetry follow the unit", "Report the full six-"
     "comparison pattern.",
     "New paragraph in Results III-D with the per-unit, per-zone crossing gaps in both campaigns, and the "
     "amplitude-asymmetry pattern (full array: unit 1 higher in 5 of 6; window: unit 3 higher except 0.6 m, "
     "where position B is higher in both campaigns) is given in Results III-D."),
    ("101", "Precision on the 'about half' valid-range claim", "Give a per-angle, per-sensor, per-position "
     "table in the supplement.",
     "New Table V: valid-range share by angle, unit and position, for the informative cases (0.3 m unit 1, "
     "0.6 m both units); referenced from Results III-D."),
    ("104", "Campaign-2 divider replicate and the +18% solo-ambient figure", "Report the campaign-2 divider "
     "numbers; solo ambient still differs by up to 18% (full array, 0.9 m) between sessions.",
     "Campaign-2 divider numbers added to Table VI and Results III-E. The +18% figure was independently "
     "recomputed and traced to sensor A/unit 1 specifically (17.8%); sensor B/unit 3 differs by only 4-5% at "
     "the same cell. Both figures are now stated in Results III-E."),
]


def add_response_appendix(doc, styles):
    TXT = styles["Text L-SENS"]
    doc.add_page_break()
    doc.add_paragraph("Response to Comments", style="Heading 1")
    p = doc.add_paragraph(style=TXT)
    p.add_run(
        "The paragraphs above show every change since the v5 redline in red. This appendix answers each of "
        "Jessica's 36 numbered comments in turn, for reference; it is not part of the paper itself."
    )
    for num, topic, comment, answer in COMMENTS:
        p = doc.add_paragraph(style=TXT)
        r = p.add_run(f"Comment #{num} ({topic}). ")
        r.bold = True
        r2 = p.add_run(comment)
        r2.italic = True
        p2 = doc.add_paragraph(style=TXT)
        p2.add_run(answer)


def build():
    doc = Document()
    R.setup(doc)
    styles = {s.name: s for s in doc.styles}

    title = doc.add_paragraph(TITLE)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.size = Pt(16)
        run.font.bold = True
    author = doc.add_paragraph("Jessica Wang")
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    affil1 = doc.add_paragraph("Trinity School NYC")
    affil1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    affil2 = doc.add_paragraph("New York, NY 10024, USA")
    affil2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph("Comprehensive (preprint) version — review copy for Jessica, v6: matches the "
                             "current arXiv paper.pdf. New or reworded text since v5 is shown in red.")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in sub.runs:
        run.italic = True
    doc.add_paragraph()

    build_body_arxiv(doc, styles)

    cp = doc.core_properties
    cp.author = "Jessica"
    cp.last_modified_by = "Jessica"
    cp.title = TITLE
    cp.subject = ""
    cp.comments = ""
    import datetime
    now = datetime.datetime(2026, 10, 16, 3, 0, 0, tzinfo=datetime.timezone.utc)
    cp.created = now
    cp.modified = now
    cp.revision = 1

    doc.save(str(OUT))
    F.scrub_app_xml(OUT)
    return OUT


if __name__ == "__main__":
    out = build()
    print("wrote", out)
