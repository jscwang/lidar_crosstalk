"""Word version of the REVISED letter (sections/introduction.tex, methodology.tex, results_discussion.tex,
after Jessica's comments, Comments v1.docx, 14-15 Oct 2026), for her review. New or reworded text is shown in
red, exactly matching the \\new{...} markup in the .tex sources and the red text in main_revised_redline.pdf.

Plain single-column document (not the two-column IEEE template): the page-count question (this draft runs to
8 pages against the 4-page Sensors Letters limit) is still open, so this is a review copy, not a submission
file. Reuses the LaTeX-to-Word text helpers of fill_sensors_letters_docx.py; CITE_NUM/EQ_NUM/FIG_NUM/TAB_NUM
are monkey-patched to this revision's numbering before any text is converted.

Run:   python manuscript_ieee/scripts/make_revised_docx.py
Out:   manuscript_ieee/main_SensorsLetters_revised.docx

Author: Jessica
"""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fill_sensors_letters_docx as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
OUT = ROOT / "main_SensorsLetters_revised.docx"
TITLE = "Angle-Dependent Crosstalk Between Two Adjacent VL53L1X Time-of-Flight Sensors"
RED = RGBColor(0xC0, 0x00, 0x00)

# ----------------------------------------------------------------------- revision numbering (overrides F.*)
F.CITE_NUM = {
    "incoronato2022": 1, "padmanabhan2019": 2, "vl53l5cx": 3, "ds12385": 4, "stforum": 5, "wermke2019": 6,
    "whyte2010": 7, "li2015": 8, "kim2015a": 9, "kim2015b": 10, "popko2020": 11, "ogurcovs2025": 12,
    "fasolino2025": 13, "um2510": 14, "qwiicvl53l1x": 15, "tca9548a": 16, "fritsch1980": 17, "efron1993": 18,
}
F.SEC_NUM = {
    "sec:intro": "I", "sec:howitworks": "I-A", "sec:crosstalkmeans": "I-B",
    "sec:method": "II", "sec:crossoverdef": "II-D", "sec:geomref": "II-E",
    "sec:results": "III", "sec:whyranging": "III-B", "sec:detectionlimit": "III-C",
    "sec:geommodel": "III-D", "sec:source": "III-E", "sec:conclusion": "IV",
}
F.EQ_NUM = {"eq:geom": "1", "eq:extra": "2", "eq:pool": "3"}
F.FIG_NUM = {
    "fig:concept": "1", "fig:principle": "2", "fig:setup": "3", "fig:photo": "4", "fig:timetrace": "5",
    "fig:scatter": "6", "fig:threshold": "7", "fig:results": "8",
}
F.TAB_NUM = {"tab:settings": "I", "tab:cross": "II"}

REFERENCES = [
    "A. Incoronato, I. Cusini, K. Pasquinelli, and F. Zappa, \u201cSingle-shot pulsed-LiDAR SPAD sensor with "
    "on-chip peak detection for background rejection,\u201d IEEE J. Sel. Top. Quantum Electron., vol. 28, "
    "no. 5, Sep. 2022, art. no. 3804210.",
    "P. Padmanabhan, C. Zhang, and E. Charbon, \u201cModeling and analysis of a direct time-of-flight sensor "
    "architecture for LiDAR applications,\u201d Sensors, vol. 19, no. 24, p. 5464, Dec. 2019.",
    "STMicroelectronics, VL53L5CX: Time-of-flight 8\u00d78 multizone ranging sensor with wide field of view, "
    "Aug. 2021, datasheet DS13754, Rev. 2. Accessed: Oct. 15, 2026. [Online]. Available: "
    "https://www.st.com/en/imaging-and-photonics-solutions/vl53l5cx.html",
    "STMicroelectronics, VL53L1X: A new generation, long distance ranging time-of-flight sensor based on "
    "ST\u2019s FlightSense technology, Aug. 2024, datasheet DS12385, Rev. 8. Accessed: Oct. 11, 2026. [Online]. "
    "Available: https://www.st.com/resource/en/datasheet/vl53l1x.pdf",
    "J. E. Kvam, \u201cReply to \u2018VCSEL signals interferences for closed sensors (VL53L1X)\u2019,\u201d "
    "STMicroelectronics Community forum, Apr. 2021, accessed: Oct. 11, 2026. [Online]. Available: "
    "https://community.st.com/imaging-sensors-49/vcsel-signals-interferences-for-closed-sensors-vl53l1x-25089",
    "F. Wermke and B. Meffert, \u201cInterference model of two time-of-flight cameras,\u201d in Proc. IEEE "
    "SENSORS, Montreal, QC, Canada, Oct. 2019, pp. 1\u20134.",
    "R. Z. Whyte, A. D. Payne, A. A. Dorrington, and M. J. Cree, \u201cMultiple range imaging camera operation "
    "with minimal performance impact,\u201d in Proc. SPIE, Image Processing: Machine Vision Applications III, "
    "vol. 7538, Feb. 2010, p. 75380I.",
    "L. Li, S. Xiang, Y. Yang, and L. Yu, \u201cMulti-camera interference cancellation of time-of-flight (TOF) "
    "cameras,\u201d in Proc. IEEE Int. Conf. Image Process. (ICIP), Sep. 2015, pp. 556\u2013560.",
    "G. Kim, J. Eom, and Y. Park, \u201cAn experiment of mutual interference between automotive LIDAR "
    "scanners,\u201d in Proc. 12th Int. Conf. Inf. Technol.\u2014New Gener. (ITNG), Apr. 2015, pp. 680\u2013685.",
    "G. Kim, J. Eom, and Y. Park, \u201cInvestigation on the occurrence of mutual interference between pulsed "
    "terrestrial LIDAR scanners,\u201d in Proc. IEEE Intell. Veh. Symp. (IV), Jun. 2015, pp. 437\u2013442.",
    "G. B. Popko, T. K. Gaylord, and C. R. Valenta, \u201cInterference measurements between single-beam, "
    "mechanical scanning, time-of-flight lidars,\u201d Opt. Eng., vol. 59, no. 5, May 2020, art. no. 053106.",
    "A. Ogurcovs, I. Aulika, S. Cartiel, J. Garcia-Pueyo, and A. Mu\u00f1oz, \u201cCrosstalk effects in a dual "
    "ToF-based tactile\u2013proximity sensing platform integrated in a flat PMMA light guide,\u201d Sensors, "
    "vol. 25, no. 23, p. 7319, Dec. 2025.",
    "A. Fasolino, L. E. Andrada, R. Liguori, L. Di Benedetto, A. Rubino, D. Pau, and G. D. Licciardo, "
    "\u201cReal-time crosstalk compensation in multizone time-of-flight sensors,\u201d in Proc. SPIE, "
    "Real-time Processing of Image, Depth, and Video Information 2025, vol. 13526, May 2025, p. 135260D.",
    "STMicroelectronics, A guide to using the VL53L1X ultra lite driver, Dec. 2025, user manual UM2510, "
    "Rev. 7. Accessed: Oct. 3, 2026. [Online]. Available: "
    "https://www.st.com/resource/en/user_manual/um2510-a-guide-to-using-the-vl53l1x-ultra-lite-driver-"
    "stmicroelectronics.pdf",
    "SparkFun Electronics, \u201cQwiic_VL53L1X_Py: set_signal_threshold(),\u201d Python library documentation, "
    "2024, \u201cprograms a new signal threshold in kcps (default=1024 kcps).\u201d Accessed: Oct. 15, 2026. "
    "[Online]. Available: https://docs.sparkfun.com/qwiic_vl53l1x_py/classqwiic__vl53l1x_1_1_qwiic_v_l53_l1_x.html",
    "Texas Instruments, TCA9548A low-voltage 8-channel I2C switch with reset, Nov. 2019, datasheet SCPS207G. "
    "Accessed: Oct. 3, 2026. [Online]. Available: https://www.ti.com/lit/gpn/TCA9548A",
    "F. N. Fritsch and R. E. Carlson, \u201cMonotone piecewise cubic interpolation,\u201d SIAM J. Numer. Anal., "
    "vol. 17, no. 2, pp. 238\u2013246, 1980.",
    "B. Efron and R. J. Tibshirani, An Introduction to the Bootstrap. New York, NY, USA: Chapman & Hall, 1993.",
]

ABSTRACT = (
    "Time-of-flight ranging sensors mounted side by side can disturb one another, but we found no published "
    "measurement of how this depends on the angle between them. We measured the extra ambient light one "
    "VL53L1X sensor sees when an identical neighbor 20 millimeters away also ranges. Three findings follow. "
    "First, ranging itself is barely disturbed: a large rise in ambient rate at close range shifted the mean "
    "distance by under half a millimeter. Second, the effect matters only where a sensor's own signal is "
    "already weak, near its detection limit, where a neighbor's small extra light can measurably change how "
    "many readings are accepted. Third, the extra light fell to 10 percent of its peak between 16 and 18 "
    "degrees of toe-out for a full sensor array and 8 to 11 degrees for a narrower window, and to 1 percent "
    "at about 20 to 22 and 11 to 13 degrees, growing with distance from 0.3 to 0.9 meters; a geometric model "
    "overestimated these angles by 3 to 7 degrees. A thin divider changed the effect by no more than about 4 "
    "percent in most settings, pointing to a shared-target path rather than direct coupling. Separating the "
    "sensors' pointing angles past this crossover, or letting them range in turn, is a more dependable fix "
    "than a barrier between them."
)

# ----------------------------------------------------------------------- red-run-aware text helpers
NEW_RE = re.compile(r"\\new\{")


def find_new_spans(text: str):
    spans = []
    i = 0
    while True:
        m = NEW_RE.search(text, i)
        if not m:
            break
        depth = 1
        j = m.end()
        while depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        spans.append((m.start(), j, m.end(), j - 1))
        i = j
    return spans


def split_red(text: str):
    spans = find_new_spans(text)
    if not spans:
        return [(text, False)]
    out, pos = [], 0
    for start, end, inner_start, inner_end in spans:
        if start > pos:
            out.append((text[pos:start], False))
        out.append((text[inner_start:inner_end], True))
        pos = end
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def add_rich_tracked(paragraph, raw_text: str, force_red: bool = False):
    for seg, is_red in split_red(raw_text):
        if not seg:
            continue
        red = force_red or is_red
        text = F.plain_sub(seg)
        pos = 0
        for m in F.EMPH_RE.finditer(text):
            if m.start() > pos:
                r = paragraph.add_run(text[pos:m.start()])
                if red:
                    r.font.color.rgb = RED
            r = paragraph.add_run(m.group(1))
            r.italic = True
            if red:
                r.font.color.rgb = RED
            pos = m.end()
        if pos < len(text):
            r = paragraph.add_run(text[pos:])
            if red:
                r.font.color.rgb = RED


# ----------------------------------------------------------------------- styles
def add_style(doc, name, size=11, bold=False, italic=False, align=None, after=6, left=None, first=None,
              base="Normal"):
    st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    st.base_style = doc.styles[base]
    st.font.name = "Times New Roman"
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.italic = italic
    st.font.color.rgb = RGBColor(0, 0, 0)
    pf = st.paragraph_format
    pf.space_after = Pt(after)
    pf.space_before = Pt(0)
    if align is not None:
        pf.alignment = align
    if left is not None:
        pf.left_indent = Inches(left)
    if first is not None:
        pf.first_line_indent = Inches(first)
    return st


def setup(doc):
    n = doc.styles["Normal"]
    n.font.name = "Times New Roman"
    n.font.size = Pt(11)
    for name, size, italic in (("Heading 1", 13, False), ("Heading 2", 11.5, True)):
        st = doc.styles[name]
        st.font.name = "Times New Roman"
        st.font.size = Pt(size)
        st.font.bold = not italic
        st.font.italic = italic
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.paragraph_format.space_before = Pt(12 if not italic else 8)
        st.paragraph_format.space_after = Pt(4)
    add_style(doc, "Text L-SENS", 11, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_style(doc, "Caption L-SENS", 9.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=8)
    add_style(doc, "Acknowledgment L-SENS", 11, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_style(doc, "References L-SENS", 10, left=0.35, first=-0.35, after=4)
    h = add_style(doc, "Heading Refs L-SENS", 13, bold=True, after=4)
    h.paragraph_format.space_before = Pt(12)
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(1.0)
    sec.top_margin = sec.bottom_margin = Inches(1.0)


def figure(doc, path, width_in):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width_in))
    return p


def placeholder_box(doc, text, height_in=2.0, width_in=6.4):
    t = doc.add_table(rows=1, cols=1)
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.rows[0].cells[0]
    cell.width = Inches(width_in)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.color.rgb = RED
    r.italic = True
    # pad vertically with empty paragraphs so the box has visible height
    for _ in range(3):
        pp = cell.add_paragraph()
    doc.add_paragraph()
    return t


def render_eq_colored(mathtext: str, name: str, fontsize=13, red=False):
    F.EQDIR.mkdir(exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["mathtext.fontset"] = "cm"
    color = "#C00000" if red else "black"
    fig = plt.figure(figsize=(0.01, 0.01))
    t = fig.text(0, 0, f"${mathtext}$", fontsize=fontsize, color=color)
    fig.canvas.draw()
    bbox = t.get_window_extent()
    w, h = bbox.width / fig.dpi + 0.1, bbox.height / fig.dpi + 0.08
    plt.close(fig)
    fig = plt.figure(figsize=(w, h))
    fig.text(0.02, 0.5, f"${mathtext}$", fontsize=fontsize, va="center", color=color)
    out = F.EQDIR / f"{name}.png"
    fig.savefig(out, dpi=220, transparent=True)
    plt.close(fig)
    return out, w, h


def add_equation(doc, styles, num: str, eqs: dict, red: bool = False):
    img, w, h = render_eq_colored(eqs[num], f"eq{num}_rev", fontsize=13, red=red)
    max_w = 5.8
    if w > max_w:
        h *= max_w / w
        w = max_w
    p = doc.add_paragraph(style=styles["Text L-SENS"])
    from docx.enum.text import WD_TAB_ALIGNMENT
    p.paragraph_format.tab_stops.add_tab_stop(Inches(3.1), WD_TAB_ALIGNMENT.CENTER)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.3), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    run = p.add_run()
    run.add_picture(str(img), width=Inches(w))
    num_run = p.add_run(f"\t({num})")
    if red:
        num_run.font.color.rgb = RED
    return p


# ----------------------------------------------------------------------- tables
def set_cell(cell, text, bold=False, size=9, red=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = "Times New Roman"
    r.font.bold = bold
    if red:
        r.font.color.rgb = RED


def add_table_settings(doc):
    rows = [
        ("Sensors", "Two VL53L1X [4] on Pololu 3415 carriers", "Target distances d", "0.3, 0.6, 0.9 m (tape; see Section II)"),
        ("Host", "ESP32-S3, via TCA9548A I²C mux [16]", "Target", "Flat dark-grey board, 1.2 m wide"),
        ("I²C clock", "400 kHz", "Room lighting", "Not recorded or varied"),
        ("Driver mode", "Short distance, ultra-lite driver [14]", "Repeats per cell", "5 blocks (A alone, B alone, A+B)"),
        ("Timing budget", "33 ms; period 40 ms", "Run length", "30 s"),
        ("ROI (zone)", "16×16 (full array) and 4×4 (window)", "Warm-up", "600 s, both sensors, each distance"),
        ("Field of view (datasheet, diagonal)", "27° and 15°", "Sensor spacing s", "20 mm (nominal)"),
        ("Toe-out per sensor θ", "0–12° (relative angle Δθ = 2θ)", "Angle step", "1° (pin-set plate; accuracy not verified)"),
    ]
    t = doc.add_table(rows=1, cols=4)
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(["Parameter", "Value", "Parameter", "Value"]):
        set_cell(t.rows[0].cells[i], h, bold=True)
    for p1, v1, p2, v2 in rows:
        cells = t.add_row().cells
        for i, v in enumerate((p1, v1, p2, v2)):
            set_cell(cells[i], v)
    doc.add_paragraph()


def add_table_crossover(doc):
    headers = ["Zone", "d (m)", "Bracket", "Crossover\n(PCHIP)", "Range of\nthree est.", "1 % angle",
               "Model", "Model,\nF in-plane"]
    rows = [
        ["16×16", "0.3", "16–18", "16.15", "16.15–16.20", "19.9", "23.4", "19.5"],
        ["16×16", "0.6", "16–18", "16.97", "16.97–17.13", "20.9", "25.2", "21.3"],
        ["16×16", "0.9", "16–18", "17.90", "17.90–17.94", "21.6", "25.8", "21.9"],
        ["4×4", "0.3", "8–10", "8.22", "8.20–8.33", "11.4", "17.3", "15.2"],
        ["4×4", "0.6", "8–10", "9.47", "9.36–9.66", "12.5", "19.2", "17.1"],
        ["4×4", "0.9", "10–12", "10.80", "10.80–11.02", "13.1", "19.8", "17.7"],
    ]
    t = doc.add_table(rows=1, cols=len(headers))
    F.add_table_borders(t)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(8)
                r.font.name = "Times New Roman"
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = v
            for p in cells[i].paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    r.font.size = Pt(8)
                    r.font.name = "Times New Roman"
    note = doc.add_paragraph(style="Caption L-SENS")
    note.add_run("Bracket and range (linear, PCHIP and tilted logistic) as defined in Section II; bootstrap "
                 "95 % half-widths of the PCHIP value are 0.01–0.07° (within-session only).")
    doc.add_paragraph()


EQS = {
    "1": r"s+2d\,\tan(\Delta\theta_g/2)=d\,[\tan(E/2)+\tan(F/2)]",
    "2": r"\Delta a_s(b)=\bar{a}_s^{AB}(b)-\bar{a}_s^{solo}(b)",
    "3": r"\Delta a(b)=\frac{1}{2}\left[\Delta a_A(b)+\Delta a_B(b)\right]",
}


def build_body_revised(doc, styles):
    TXT = styles["Text L-SENS"]
    CAP = styles["Caption L-SENS"]
    HREF = styles["Heading Refs L-SENS"]
    ACK = styles.get("Acknowledgment L-SENS", TXT)
    REF = styles["References L-SENS"]

    def h1(text):
        return doc.add_paragraph(text, style="Heading 1")

    def h2(text):
        return doc.add_paragraph(text, style="Heading 2")

    def body_p(latex_text, red=False):
        p = doc.add_paragraph(style=TXT)
        add_rich_tracked(p, latex_text, force_red=red)
        return p

    def caption(latex_text, red=False):
        p = doc.add_paragraph(style=CAP)
        add_rich_tracked(p, latex_text, force_red=red)
        return p

    def fig(path, width_in=3.6):
        figure(doc, path, width_in)

    # ================================================================= I. INTRODUCTION
    h1("I. Introduction")
    body_p(
        r"\new{Ranging by the travel time of light is now a common way to measure distance without touching the "
        r"target. Automotive and robotic systems use pulsed time-of-flight sensors for obstacle detection and "
        r"navigation~\cite{incoronato2022}, and single-photon-avalanche-diode (SPAD) arrays of the kind inside "
        r"the sensor used here are a standard building block of these systems~\cite{padmanabhan2019}. Two "
        r"further points set the scene for this letter. First, not every such sensor scans or images a scene: a "
        r"scanning lidar sweeps a beam and is comparatively expensive, and a multizone sensor such as the "
        r"VL53L5CX reports a small grid of distances from a fixed mount~\cite{vl53l5cx}; but arrays of cheap, "
        r"single-point sensors like the VL53L1X remain common because each one is inexpensive and can be "
        r"pointed in any direction independently of the others. Second, when several such sensors are mounted "
        r"close together, as in a drone's collision-avoidance ring or a mobile robot's bumper, each can "
        r"potentially receive light meant for its neighbour.}")
    body_p(
        r"\new{The VL53L1X is a compact direct time-of-flight (ToF) sensor of exactly this kind: it} pairs a "
        r"\SI{940}{\nano\meter} laser emitter with an array of single-photon avalanche diodes (SPADs) and a "
        r"programmable region of interest (ROI)~\cite{ds12385}\new{, and is the sensor used throughout this "
        r"letter}. One developer building a drone with several of them asked on a manufacturer forum whether "
        r"the units disturb one another~\cite{stforum}. \new{Mutual interference of this kind has already been "
        r"studied for other sensor families: a} model of the distance error \new{exists} for two \new{ToF} "
        r"cameras~\cite{wermke2019} and methods for operating several \new{of them} were "
        r"developed~\cite{whyte2010,li2015}, and for scanning lidars, where it was "
        r"measured~\cite{kim2015a,kim2015b} and direct and scattered interference were "
        r"distinguished~\cite{popko2020}. Crosstalk between two multizone ToF sensors viewing through one light "
        r"guide has been characterised for a tactile and proximity skin~\cite{ogurcovs2025}, and crosstalk "
        r"compensation in multizone ToF sensors has been reported~\cite{fasolino2025}. \new{For small "
        r"single-point sensors such as the VL53L1X, by contrast, we found only the forum thread above:} a "
        r"manufacturer employee replied that units generally do not interfere, while relaying a report of "
        r"interference at \SI{5}{\centi\meter} when two face each other~\cite{stforum}. In the sources we "
        r"searched (web searches of the research literature, manufacturer documents and community posts, not a "
        r"bibliographic-database search) we found no published measurement of how the interaction between two "
        r"adjacent VL53L1X-class sensors depends on the angle between them. \new{This is the gap the letter "
        r"addresses.}")
    body_p(
        r"\new{We chose the VL53L1X for three reasons: it is inexpensive and widely used, so results for it "
        r"generalise to many existing designs; its field of view can be narrowed in software from the full "
        r"$16\times16$ SPAD array to a $4\times4$ window, so the same pair of units lets us test two optical "
        r"geometries without new hardware; and it reports the signal and ambient photon rates directly "
        r"(Section~\ref{sec:howitworks}), so the interference can be measured as a rate rather than inferred "
        r"from range alone.}")
    body_p(
        r"This letter measures that dependence for one pair of VL53L1X sensors \SI{20}{\milli\meter} apart, in "
        r"two ROI sizes and at three distances. \new{Four questions follow, with what we expected of each and "
        r"why. (i)~At what angle does the extra ambient rate fall to \SI{10}{\percent} and \SI{1}{\percent} of "
        r"its peak, and how precisely can that angle be pinned down? Here we expected a single monotonic "
        r"falloff, so a model-free bracket between sampled angles would already settle the question up to the "
        r"angle step, and the choice of interpolant would barely matter. (ii)~Does the response fall "
        r"monotonically with angle in both ROI sizes? We had no reason to think otherwise: two cones of light "
        r"can only lose overlap as the sensors turn apart, not regain it. (iii)~Does a geometric model built "
        r"from the datasheet's field-of-view figures predict the angle at which the effect disappears? The "
        r"datasheet figures are the only stated description of each sensor's optical extent, so we expected "
        r"them to get us close. (iv)~Does a thin opaque divider between the sensors reduce the effect, which "
        r"would point to light reaching the neighbour directly rather than only via the target? A divider "
        r"should help only if direct coupling is a real part of what is being measured.} As the results show, "
        r"the response is not always monotonic (ii), the geometric prediction is systematically too large "
        r"(iii), and the divider test does not show a clear benefit (iv); each of these departs from what we "
        r"expected, and is discussed with its evidence in Section~\ref{sec:results}.")

    h2("A. How the sensor works")
    body_p(
        r"\new{The VL53L1X emits laser pulses and times the returning photons with an array of "
        r"SPADs~\cite{ds12385}. Photons arriving within a narrow window after each pulse, reflected from the "
        r"target, cluster at one delay and form a sharp peak in the histogram of arrival times (Fig.~2a); "
        r"photons arriving at other times, from room light or any other unsynchronised source, are spread "
        r"roughly uniformly across the histogram and form a flat floor beneath the peak. The driver reports "
        r"three quantities from this histogram, each summed over the active SPADs and given in kilocounts per "
        r"second (kcps): the \emph{range}, from the position of the peak; the \emph{signal rate}, the height "
        r"of the peak above the floor; and the \emph{ambient rate}, the height of the floor itself. A reading "
        r"is accepted or rejected according to status codes defined by the manufacturer's "
        r"driver~\cite{um2510}; in the data reported here, every accepted reading has a signal rate at or "
        r"above a threshold near \SI{1024}{kcps}; a software library for this sensor family documents a "
        r"default signal-rate threshold of exactly this value~\cite{qwiicvl53l1x}, consistent with what we "
        r"observe (Section~\ref{sec:detectionlimit}).}")

    h2("B. What crosstalk means here")
    body_p(
        "When a second sensor is also ranging nearby, some of its emitted light can reach the first sensor's "
        "receiver, either directly or after reflecting off the target. Because the two sensors run on "
        "independent, unsynchronised clocks, the neighbour's photons arrive at random delays relative to the "
        "first sensor's own pulse, so they add to the flat floor rather than to the peak (Fig.~2a): the "
        "ambient rate rises, while the range, read from the peak, is affected only indirectly. This is what "
        "Section~\\ref{sec:method} measures as the \\emph{extra ambient rate}.", red=True)
    body_p(
        "A simple geometric picture bounds the angle at which this stops: sensor B's emitter illuminates a "
        "cone of half-angle $E/2$ and sensor A's receiver accepts light from a cone of half-angle $F/2$ "
        "(Fig.~2b); as the two sensors are turned apart by a relative angle $\\dth$, these cones' footprints "
        "on the target slide apart and eventually stop overlapping. Equating the point where the two "
        "footprint edges meet gives", red=True)
    add_equation(doc, styles, "1", EQS, red=True)
    body_p(
        "where $s$ is the sensor spacing, $d$ the target distance, and $\\dth_g$ the predicted end-of-overlap "
        "angle; this assumes both cones are circular and centred on each sensor's nominal axis. "
        "Section~\\ref{sec:geommodel} evaluates \\eqref{eq:geom} against the measured crossover angles.", red=True)

    fig(FIG / "fig_concept.png", 3.6)
    caption(r"\new{Fig. 1. Concept: sensors in an array point in different directions, but adjacent ones' "
            r"emitter and receive cones can still overlap on a shared target.}", red=True)
    fig(FIG / "fig_principle.png", 5.5)
    caption(r"\new{Fig. 2. Principle. (a) Sketch of the photon-arrival-time histogram one sensor builds: its "
            r"own return forms a sharp peak (the signal rate); unsynchronised light, including a neighbour's, "
            r"spreads across the window and raises the floor (the ambient rate). (b) The overlap geometry of "
            r"\eqref{eq:geom}: sensor B's emitter cone (half-angle $E/2$) and sensor A's receive cone "
            r"(half-angle $F/2$), toed out by a relative angle $\dth_g$, stop sharing a common footprint on "
            r"the target beyond the predicted angle.}", red=True)

    # ================================================================= II. METHODOLOGY
    h1("II. Methodology")
    body_p(
        r"\new{To answer the four questions above, one pair of VL53L1X sensors was turned apart by a known "
        r"angle and read while alone and together, at three distances and two field-of-view sizes, and the "
        r"extra ambient rate this produces was measured and related back to the overlap geometry of "
        r"Section~\ref{sec:crosstalkmeans}. The rest of this section gives the apparatus, the acquisition "
        r"protocol and acceptance rules, what was computed and why, how the crossover angle and its "
        r"uncertainty were estimated, and the divider check; full detail beyond what is needed to follow the "
        r"Results is in the supplementary material.}")

    h2("A. Apparatus and geometry")
    body_p(
        r"Two VL53L1X sensors~\cite{ds12385} on Pololu 3415 carrier boards (unit~3 at position~A, unit~1 at B) "
        r"were read by an ESP32-S3 through a TCA9548A I$^2$C multiplexer~\cite{tca9548a} at "
        r"\SI{400}{\kilo\hertz}. The STMicroelectronics ultra-lite driver~\cite{um2510} set short distance "
        r"mode, a \SI{33}{\milli\second} timing budget and a \SI{40}{\milli\second} period. Each "
        r"interrupt-timestamped reading gave the range, its status, and the total signal and ambient rates "
        r"(Section~\ref{sec:howitworks}). Two ROIs were used, the full $16\times16$ array and a $4\times4$ "
        r"window, each centred on the factory optical centre. \new{Table~\ref{tab:settings} lists every "
        r"setting; Fig.~3 is a schematic of the geometry it describes, and Fig.~4 shows the physical rig.}")
    caption("Table I. Hardware, settings and experimental parameters")
    add_table_settings(doc)
    body_p(
        r"The sensors, nominally $s=\SI{20}{\milli\meter}$ apart, sat on pucks turned by $-\theta$ (A) and "
        r"$+\theta$ (B), so their axes toed out by $\dth=2\theta$ (Fig.~3). Pins in a plate with holes at "
        r"\SI{1}{\degree} steps set the angles (accuracy not verified). The sweep covered $\theta=\SI{0}{"
        r"\degree}$ and \SIrange{2}{12}{\degree}, so $\dth=0,4,6,\dots,\SI{24}{\degree}$ (12 levels). The "
        r"target was a flat dark-grey board \SI{1.2}{\meter} wide at tape distances $d=0.3$, $0.6$ and "
        r"\SI{0.9}{\meter} (the sensors read \SIrange{9}{30}{\milli\meter} less). Before each setting a "
        r"guided check required, three times in a row, the mean $16\times16$ range within "
        r"\SI{15}{\milli\meter} of a stored value and B$-$A within \SI{10}{\milli\meter} of a per-distance "
        r"offset (2.5, 2.5 and \SI{3.0}{\milli\meter}, from a squared board), and a self-test to pass. Room "
        r"temperature was not recorded.")
    fig(FIG / "fig_setup.png", 3.6)
    caption("Fig. 3. Measurement geometry (schematic, not to scale): sensors A and B toe out by $\\dth=2\\theta$; "
            "the common footprint is where B's emitter cone and A's receive field overlap (Section~\\ref{sec:"
            "crosstalkmeans}). The divider was present only in the divider tests. Cone angles are generic.")
    fig(FIG / "fig_photo.png", 5.2)
    caption(r"\new{Fig. 4. Physical setup, close-up: the two sensor carriers on their angled pucks, the "
            r"pin-set angle-setting plate (a pin at each hole sets $\theta$), and the wiring to the TCA9548A "
            r"multiplexer above the frame. The target board, not shown in this crop, stands opposite at the "
            r"tape distance of Fig.~3.}", red=True)

    h2("B. Acquisition and acceptance")
    body_p(
        r"\new{Each distance was one campaign on its own day, angles ascending (resumed once after an "
        r"interruption at 0.3 and \SI{0.6}{\meter}), after a \SI{600}{\second} two-sensor warm-up. Each cell "
        r"(zone $\times$ $\dth$) had five blocks of three \SI{30}{\second} runs, A alone, B alone and A with "
        r"B, in seeded random order with the idle sensor stopped (\numrange{748}{766} readings per active "
        r"sensor). A run was accepted if its reading count and I$^2$C/read behaviour were within tolerance "
        r"and the idle sensor stayed silent; a block was accepted if its runs were and each sensor's solo "
        r"ambient rate was consistent with the previous accepted block at the same setting; full numerical "
        r"tolerances and the retry rule are in the supplement. Blocks failing three times (1, 6 and 7 of 120 "
        r"at 0.3, 0.6 and \SI{0.9}{\meter}) were re-measured in separate refill sessions and replaced; "
        r"excluding them moves no crossover by more than \SI{0.01}{\degree}.}")

    h2("C. What was computed, and why")
    body_p(
        r"\new{For each sensor and block, the \emph{extra ambient rate} is what Section~\ref{sec:"
        r"crosstalkmeans} calls the extra height of the histogram floor: the difference between that sensor's "
        r"ambient rate with both sensors running and its ambient rate alone (Eqs.~2–3 below). A "
        r"difference is used, not a ratio to the solo rate, because for the $4\times4$ window the solo rate is "
        r"only \SIrange{0.1}{9.4}{kcps}, comparable to its own run-to-run noise, and so a ratio would be "
        r"dominated by that noise rather than by the crosstalk. Range effects are the companion measurements "
        r"of whether ranging itself is disturbed: the difference of mean ranges (bias) and the ratio of range "
        r"standard deviations between two-sensor and solo runs, from valid readings only. The "
        r"rejected-reading fraction is tracked separately, since it depends on the signal threshold of "
        r"Section~\ref{sec:howitworks} rather than on the ambient floor. The block, not the individual "
        r"reading, is the unit of statistical analysis throughout, since readings within a 30-second run are "
        r"not independent.}")
    body_p(
        r"For sensor $s\in\{\mathrm{A},\mathrm{B}\}$ in block $b$, the extra ambient rate is the difference of "
        r"run-mean ambient rates $\bar a$ with both sensors ranging and with $s$ alone, pooled over the "
        r"sensors:")
    add_equation(doc, styles, "2", EQS)
    add_equation(doc, styles, "3", EQS)
    body_p("Five blocks give a cell mean $\\overline{\\Delta a}$ and standard deviation.")

    h2("D. Crossover and its uncertainty")
    body_p(
        r"Let $\Delta\theta_{\mathrm{pk}}$ be the level with the largest cell mean $\overline{\Delta "
        r"a}_{\mathrm{pk}}$. The crossover at threshold $\varphi$ is the first angle beyond $\Delta\theta_{"
        r"\mathrm{pk}}$ at which the response falls to $\varphi\,\overline{\Delta a}_{\mathrm{pk}}$ "
        r"($\varphi=0.10$ unless stated). With levels \SI{2}{\degree} apart, the data alone fix only a "
        r"\emph{bracket} (the last level above and the first at or below the threshold); a point estimate "
        r"needs an interpolant. \new{The primary estimate uses} shape-preserving piecewise cubic Hermite "
        r"interpolation (PCHIP)~\cite{fritsch1980} \new{of the cell means; four further estimators (two "
        r"further interpolants and two logistic fits, one of which can rise before it falls) are compared in "
        r"the supplement and agree with PCHIP within \SI{0.14}{\degree} in every cell, except a logistic "
        r"fitted to all levels and read at $\dth=0$, which can lie up to \SI{1}{\degree} away.} Sampling "
        r"uncertainty is a block bootstrap~\cite{efron1993}: the five blocks of every level are resampled "
        r"with replacement $B=2000$ times, with percentile 95\,\% intervals. This describes within-session "
        r"repeatability only: each distance was measured once with one sensor pair, so between-session and "
        r"between-unit variance are not estimated.")

    h2("E. Geometric reference")
    body_p(
        r"Equation~\eqref{eq:geom} (Section~\ref{sec:crosstalkmeans}) needs the emitter cone $E$ and receive "
        r"field $F$ as numbers. \new{We take $E=\SI{27}{\degree}$ (the datasheet's stated field of view, with "
        r"no separate emitter figure given) and $F$ as the datasheet's diagonal field-of-view value for each "
        r"zone; we also evaluate \eqref{eq:geom} with $F$ converted to an in-plane value for a square array, "
        r"$\tan\beta=\tan\alpha/\sqrt2$, and separately invert it for the $E$ that reproduces the measured "
        r"\SI{1}{\percent} angle. This is a sensitivity analysis, not a claim that either convention is "
        r"correct: the orientation of the array axes relative to the toe-out plane was not recorded.}")

    h2("F. Divider check")
    body_p(
        r"\new{The purpose of this check is to ask whether the light reaches the neighbouring sensor directly, "
        r"or only by reflecting off the target: if a barrier between the sensors reduced the effect, that "
        r"would point to a direct path.} At each distance a thin black strip stood on edge between the sensor "
        r"windows; the protocol required it to stay out of both fields of view and within about "
        r"\SI{15}{\milli\meter} of the sensor chips, but its size and position were not recorded. The cells "
        r"at $\theta=\SI{2}{\degree}$ and \SI{5}{\degree} ($\dth=4$ and \SI{10}{\degree}) were re-measured in "
        r"both zones, five blocks each, and compared with the no-divider cells through the difference of "
        r"cell means of \eqref{eq:pool}. At \SI{0.6}{\meter} the divider cells were measured twice, the "
        r"second time with the strip protruding less; the second set is used and the first reported as a "
        r"replicate.")
    body_p(
        r"\new{With the apparatus, the acceptance rules and the quantities above in place, "
        r"Section~\ref{sec:results} applies them to the four questions of Section~\ref{sec:intro}: what each "
        r"sensor's own ambient and signal rates looked like without a neighbour, what changed with one "
        r"present, and how that change depended on angle, zone and distance.}")

    # ================================================================= III. RESULTS AND DISCUSSION
    h1("III. Results and Discussion")
    h2("A. One measurement at the worst case")
    body_p(
        r"\new{Before the sweeps, one setting shows what the numbers below mean: the full array, "
        r"\SI{0.3}{\meter}, $\dth=\SI{0}{\degree}$. Fig.~5 plots sensor A's ambient rate and range across one "
        r"block, first running alone, then with B. The ambient rate jumps from a mean of \SI{43}{kcps} to "
        r"\SI{864}{kcps}, about 20 times higher, the moment B starts; the mean range moves by "
        r"\SI{0.4}{\milli\meter}, from \SI{287.9}{\milli\meter} to \SI{287.5}{\milli\meter}, "
        r"indistinguishable from no effect at this scale. The rest of this section asks why ranging survives "
        r"such a large jump in ambient light, when the effect matters despite that, how far apart the "
        r"sensors must point for it to disappear, and where the light is coming from.}")
    fig(FIG / "fig_timetrace.png", 3.6)
    caption(r"\new{Fig. 5. One block, full array, \SI{0.3}{\meter}, $\dth=\SI{0}{\degree}$: sensor A's "
            r"ambient rate (top) and range (bottom) against elapsed time, first alone then with B (dotted "
            r"line marks the switch). Ambient rate rises about 20-fold; range is not visibly affected.}", red=True)

    h2("B. Why ranging survives")
    body_p(
        r"\new{``Barely affected'' means: at $\dth=\SI{0}{\degree}$ the range bias was at most "
        r"\SI{0.3}{\milli\meter} in magnitude at every distance and zone, and the range standard deviation "
        r"was \SIrange{7}{10}{\percent} larger with both sensors ranging for the full array and "
        r"\SI{13}{\percent} larger for the window at \SI{0.3}{\meter}; by \SI{24}{\degree} both were "
        r"indistinguishable from no effect. Two points in this comparison (both sensor B, full "
        r"\SI{24}{\degree} toe-out at \SI{0.3}{\meter}, where the extra ambient is itself indistinguishable "
        r"from zero) have a range SD ratio near 0.37, about a third of solo scatter; this is not a crosstalk "
        r"effect, since there is essentially no extra ambient left at that angle, and most likely reflects "
        r"ordinary block-to-block sampling noise in a five-run solo standard deviation. No other points "
        r"depart from the main trend by a comparable amount.}")
    body_p(
        r"\new{The reason ranging survives is that the extra ambient a neighbour adds is small next to the "
        r"sensor's own signal (Section~\ref{sec:howitworks}): the histogram's peak, which fixes the range, is "
        r"barely moved by raising its floor. If this is the mechanism, the range standard deviation ratio "
        r"(A+B over solo) should track the size of the extra ambient relative to that signal, regardless of "
        r"distance or zone. Fig.~6 plots this for every accepted (block, sensor) in the sweep: the SD ratio "
        r"rises from about 1.0 toward 1.1–1.2 as extra ambient / own signal grows from 0 to about 0.07, "
        r"with broadly the same trend at all three distances and both zones (16x16 points: correlation "
        r"0.66).}")
    fig(FIG / "fig_scatter_ratio.png", 3.6)
    caption(r"\new{Fig. 6. Range SD ratio (A+B over solo) against extra ambient / own signal, every accepted "
            r"(block, sensor) in the sweep, both zones and all three distances. The two low points are "
            r"explained in the text.}", red=True)
    body_p(
        r"\new{At $\dth=\SI{0}{\degree}$, where the two beams overlap most, extra ambient / own signal is "
        r"0.056, 0.059 and 0.062 for the full array at 0.3, 0.6 and \SI{0.9}{\meter}, and 0.073, 0.060 and "
        r"0.044 for the window: despite the extra ambient rate and the solo signal rate each falling by more "
        r"than 30-fold from 0.3 to \SI{0.9}{\meter}, their ratio stays within about \SI{30}{\percent} across "
        r"that range. This is consistent with both the neighbour's light and the sensor's own light reaching "
        r"the sensor by the same route, reflected off the same target, so that whatever reduces one with "
        r"distance reduces the other by nearly the same factor; Section~\ref{sec:source} returns to this "
        r"point.}")

    h2("C. When it does matter: near the detection limit")
    body_p(
        r"\new{The SD-ratio trend above is small because the sensor's own signal is normally much stronger "
        r"than the extra background; it follows that the effect should matter more exactly when the signal "
        r"is weak, for a far or dark target, the narrower $4\times4$ window, or a brighter room. The "
        r"$4\times4$ window across the three distances already spans this range: its solo signal is far "
        r"above the \SI{1024}{kcps} acceptance threshold (Section~\ref{sec:howitworks}) at \SI{0.3}{\meter} "
        r"(about \SI{3800}{kcps}), close to it at \SI{0.6}{\meter} (about \SI{1100}{kcps}), and below it at "
        r"\SI{0.9}{\meter} (about \SI{470}{kcps}); only in the middle regime can the small extra ambient from "
        r"a neighbour plausibly tip a reading from one side of the threshold to the other, since far above it "
        r"nearly everything is accepted regardless and far below it nearly everything is rejected "
        r"regardless.}")
    body_p(
        r"\new{Fig.~7 demonstrates this in the one setting where it is visible: the $4\times4$ window at "
        r"\SI{0.6}{\meter}, sensor A, $\dth=\SI{6}{\degree}$. Alone, this sensor's per-reading signal "
        r"straddles the threshold (median \SI{1024}{kcps}) and \SI{47.8}{\percent} of its readings are "
        r"accepted; with B also running, the signal distribution shifts slightly down (median "
        r"\SI{1016}{kcps}) and the accepted fraction falls to \SI{38.7}{\percent}. The accepted fraction "
        r"itself follows the same sharp step against signal value whether the sensor is alone or with its "
        r"neighbour (Fig.~7b); what changes is how much of the reading-by-reading spread of signal values "
        r"falls on each side of that step. This was seen in this one setting, not as a general measurement: "
        r"it demonstrates the mechanism by which a detection threshold turns a small shift in ambient light "
        r"into a change in how many readings are returned at all, not a general figure for how often it "
        r"happens.}")
    fig(FIG / "fig_signal_threshold.png", 3.6)
    caption(r"\new{Fig. 7. $4\times4$ window, \SI{0.6}{\meter}, sensor A, $\dth=\SI{6}{\degree}$. (a) "
            r"Per-reading signal histogram, alone and with B, with the acceptance threshold (dotted). (b) "
            r"Accepted fraction against signal, binned; both conditions follow the same step, which falls "
            r"near the threshold.}", red=True)

    h2("D. How far apart the sensors need to point")
    body_p(
        r"\new{Having shown where the effect does and does not matter, we return to question (i) of "
        r"Section~\ref{sec:intro}: how it falls with angle, and where it stops. The extra ambient rate peaked "
        r"at} 1006, 665 and \SI{302}{kcps} for the $16\times16$ zone \new{(the full array)} and at 273, 65 "
        r"and \SI{24}{kcps} for the $4\times4$ window at 0.3, 0.6 and \SI{0.9}{\meter}. For the full array "
        r"that is 23, 8 and 3.5 times the solo rate; no ratio is given for the window, whose solo rate is "
        r"near the noise floor. The response fell with toe-out at every distance for the full array and at "
        r"\SI{0.3}{\meter} for the window (Fig.~8a,b). At 0.6 and \SI{0.9}{\meter} the window instead peaked "
        r"at $\dth=\SI{4}{\degree}$, above its value at \SI{0}{\degree} by \SI{4.5}{\percent} (Welch "
        r"$p=0.0024$) and \SI{23}{\percent} ($p<0.0001$); at \SI{0.3}{\meter} it was \SI{25}{\percent} lower"
        r"\new{, answering question (ii): the response is not always monotonic}. Distance and session "
        r"coincide, so this cannot be assigned to distance; the maximum lies between \SI{0}{\degree} and "
        r"\SI{6}{\degree} ($\theta=\SI{1}{\degree}$ was not measured).")
    fig(FIG / "fig_results.png", 6.4)
    caption(
        "Fig. 8. (a), (b) Extra ambient rate against the angle between the sensors, as a percentage of each "
        "cell's observed peak, for the $16\\times16$ and $4\\times4$ zones at three distances. Markers are "
        "cell means of five blocks (error bars, one standard deviation, are mostly hidden); lines are PCHIP "
        "interpolants; filled triangles mark the \\SI{10}{\\percent} crossing and open triangles the "
        "geometric end-of-overlap angle. (c) The \\SI{10}{\\percent} crossing (bar: model-free bracket) and "
        "the angle at \\SI{1}{\\percent} of the peak against distance, with the model (solid) and with the "
        "receive field converted to an in-plane value (dashed).")
    caption("Table II. Angle between the sensors (degrees) at which the extra ambient rate falls to "
            "\\SI{10}{\\percent} (crossover) and \\SI{1}{\\percent} of its peak, and the model's "
            "end-of-overlap angle")
    add_table_crossover(doc)
    body_p(
        r"The model-free bracket of the \SI{10}{\percent} crossing (Table~\ref{tab:cross}) was "
        r"\SIrange{16}{18}{\degree} for the full array at all three distances and \numrange{8}{10}, "
        r"\numrange{8}{10} and \SIrange{10}{12}{\degree} for the window. \new{Rounded to the nearest "
        r"\SI{0.5}{\degree}, the practical resolution of the angle plate, PCHIP puts the crossing at about "
        r"16.0, 17.0 and \SI{18.0}{\degree} (full array) and 8.0, 9.5 and \SI{11.0}{\degree} (window), "
        r"rising with distance in all five estimators (full precision in Table~\ref{tab:cross}); the other "
        r"four estimators compared in the supplement agree with PCHIP within \SI{0.14}{\degree} in every "
        r"cell, except a logistic read at $\dth=0$, which can lie up to \SI{1}{\degree} away and falls "
        r"outside the bracket at \SI{0.9}{\meter}.} Doubling or halving the threshold moves the crossing by "
        r"\SIrange{0.7}{1.7}{\degree}, so the \SI{10}{\percent} value is a convention. Analysed separately, "
        r"sensor~A crossed over \SIrange{1.0}{1.1}{\degree} earlier than B for the full array and "
        r"\SIrange{0.6}{1.0}{\degree} later for the window, with the same sign at every distance; unit and "
        r"path direction are confounded.")
    body_p(
        r"\new{The extra ambient fell to \SI{1}{\percent} of its peak at about} 19.9, 20.9 and "
        r"\SI{21.6}{\degree} (full array) and 11.4, 12.5 and \SI{13.1}{\degree} (window)\new{, rounding to "
        r"about 20.0, 21.0 and \SI{21.5}{\degree}, and 11.5, 12.5 and \SI{13.0}{\degree}.} At those angles "
        r"the full array's extra ambient was still 0.19, 0.09 and 0.04 times the solo rate. The window "
        r"returned valid ranges for about half of its readings at \SI{0.6}{\meter} and for none at "
        r"\SI{0.9}{\meter}, so range effects are not available for it there (Section~\ref{sec:detectionlimit} "
        r"explains why).")
    body_p(
        r"\new{Turning to question (iii), whether the geometric model predicts this angle: as} assumed in "
        r"Section~\ref{sec:crosstalkmeans}, the overlap model of \eqref{eq:geom} puts the end of overlap at "
        r"\SIrange{23.4}{25.8}{\degree} (full array) and \SIrange{17.3}{19.8}{\degree} (window), which is "
        r"\SIrange{3.4}{4.3}{\degree} and \SIrange{5.9}{6.8}{\degree} beyond the \SI{1}{\percent} angles: the "
        r"model overshoots in both zones\new{, so the agreement we expected does not fully hold}. Converting "
        r"the datasheet's diagonal field of view to an in-plane value moves the full-array values to "
        r"\SIrange{19.5}{21.9}{\degree}, within \SI{0.5}{\degree} of the \SI{1}{\percent} angles, but leaves "
        r"the window \SIrange{3.8}{4.6}{\degree} too late (Fig.~8c). Inverting the model for the emitter cone "
        r"gives \SIrange{26}{28}{\degree} for the full array and \SIrange{18}{20}{\degree} for the window: "
        r"nearly constant with distance within each zone (spread at most \SI{1.8}{\degree}) but not between "
        r"zones. \new{So the model reproduces how the required angle grows with distance, which follows "
        r"directly from \eqref{eq:geom}'s geometry, but not its dependence on zone, under either convention: "
        r"candidate explanations we did not test are soft beam edges, a window field that is not simply a "
        r"narrower copy of the full cone, and array axes outside the toe-out plane.} The window's "
        r"non-monotonic response, present at 0.6 and \SI{0.9}{\meter} but not at \SI{0.3}{\meter}, may "
        r"reflect near-field saturation at \SI{0.3}{\meter} (\SI{273}{kcps}) or session differences.")

    h2("E. Where the interfering light comes from, and how to avoid it")
    body_p(
        r"\new{Section~\ref{sec:geommodel} located where the effect stops; question (iv) asks where it comes "
        r"from in the first place, which the divider check was designed to test (Section~\ref{sec:method}). "
        r"In brief: with} the strip between the sensors the extra ambient changed by $-7.7$ to $+17.2$\,\% "
        r"across the twelve cells (both zones, $\dth=4$ and \SI{10}{\degree}, three distances), within "
        r"$\pm4.2$\,\% in ten of them; the exceptions are the window cells at \SI{10}{\degree}, where the "
        r"absolute changes were $-0.5$ and $+0.8$\,kcps. The sign followed the distance, not the zone or "
        r"angle: all four cells fell at \SI{0.3}{\meter} ($-0.7$ to $-7.7$\,\%), all rose at \SI{0.6}{\meter} "
        r"($+3.9$ to $+17.2$\,\%) and they changed by $-0.1$ to $+2.5$\,\% at \SI{0.9}{\meter}. The "
        r"\SI{95}{\percent} bootstrap intervals excluded zero in ten cells (all but the \SI{0.9}{\meter} "
        r"window), yet the sensors' solo ambient rate differed by $-20$ to $+18$\,\% between the divider and "
        r"no-divider sessions, so session differences are as large as the divider effects; \new{a thin "
        r"barrier, in other words, did not show a measurable benefit, which answers question (iv) only "
        r"partially: it does not rule out a direct path but does not demonstrate one either (the strip's "
        r"size and position were not recorded, and the divider cells came from separate sessions). Full "
        r"numbers are in the supplement (Table~S1).}")
    body_p(
        r"\new{Two further observations point the same way, toward light that reaches the neighbour via the "
        r"target rather than directly. First, extra ambient / own signal at $\dth=\SI{0}{\degree}$ stayed "
        r"within about \SI{30}{\percent} across a more-than-30-fold change in signal with distance "
        r"(Section~\ref{sec:whyranging}), as expected if both the neighbour's light and the sensor's own "
        r"light are reflected by the same target and fall off with distance together. Second, the response "
        r"fell smoothly with toe-out at every distance for the full array (Fig.~8a): if the dominant path "
        r"were direct emitter-to-receiver coupling rather than a shared target, the footprint argument of "
        r"Section~\ref{sec:crosstalkmeans} would not obviously apply, and the divider, sitting between the "
        r"sensor windows, would be expected to block it; it did not show a reduction. Neither observation "
        r"proves the path is exclusively via the target, but both are what that explanation predicts and "
        r"neither is what a dominant direct path would predict.}")
    body_p(
        r"\new{Practically, for sensors spaced and mounted like this pair, a barrier between them is not an "
        r"effective fix. Two things actually work: separate the sensors' pointing angles by more than the "
        r"crossover found in Section~\ref{sec:geommodel}, or let them take turns so that only one ranges at "
        r"a time. The solo runs throughout this letter are exactly what each sensor sees when the other is "
        r"idle, and they show no crosstalk at all, by construction.}")

    h2("F. Limitations and open questions")
    body_p(
        r"One sensor pair; one session per distance; angle and time confounded; unit and path direction "
        r"confounded; $\theta=\SI{1}{\degree}$ unsampled; plate accuracy, board reflectance, room light and "
        r"strip geometry unrecorded. Re-measured blocks are at most \SI{6}{\percent} of those accepted, "
        r"mostly in the tails. \new{The $4\times4$ window's peak at $\dth=\SI{4}{\degree}$ rather than "
        r"$\SI{0}{\degree}$, at two of three distances, is unexplained (Section~\ref{sec:geommodel}). At "
        r"\SI{0.3}{\meter} only, both sensors' own (solo) ambient rate rose by about \SIrange{40}{50}{"
        r"\percent} between $\dth=\SI{14}{\degree}$ and \SI{24}{\degree}; since this appears in the solo "
        r"runs, it is not a crosstalk effect, but it adds noise, and conceivably a small bias, to the "
        r"extra-ambient estimate at the largest angles, where the crosstalk signal itself is already small. "
        r"The detection-limit effect of Section~\ref{sec:detectionlimit} was seen in one setting and is a "
        r"demonstration of a mechanism, not a general measurement of how often it occurs.}")

    # ================================================================= IV. CONCLUSION
    h1("IV. Conclusion")
    body_p(
        r"\new{For one pair of VL53L1X sensors \SI{20}{\milli\meter} apart, three things follow. Ranging "
        r"itself holds up well even under heavy interference: a 20-fold jump in ambient rate at close range "
        r"moved the mean distance by under half a millimetre. The effect only bites where a sensor's own "
        r"signal is already weak, near the detection limit, where a neighbour's small extra ambient light "
        r"can measurably change how many readings get through; we demonstrated this in one setting, not as a "
        r"general rule. And the extra ambient rate from running both fell to \SI{10}{\percent} of its peak "
        r"at about \SIrange{16}{18}{\degree} of total toe-out for the full array and \SIrange{8}{11}{\degree} "
        r"for the $4\times4$ window, reaching \SI{1}{\percent} at about \SIrange{20}{22}{\degree} and "
        r"\SIrange{11.5}{13}{\degree}, growing with distance from 0.3 to \SI{0.9}{\meter}.} The choice of "
        r"estimator, not sampling, limits the precision of these angles, and a geometric model overshoots "
        r"them by \SIrange{3}{7}{\degree}. A thin divider changed the effect by no more than about "
        r"\SI{4}{\percent} in ten of twelve settings, which does not rule out direct coupling\new{; the "
        r"evidence instead points toward light reaching the neighbour via the target.} \new{For someone "
        r"building an array of these sensors, the practical guidance is: a barrier between adjacent units is "
        r"not a dependable fix; separating their pointing angles past the crossover found here, or running "
        r"them in turn rather than together, are. Other units and targets, a unit swap, $\theta=\SI{1}{"
        r"\degree}$, bright room light, and a direct timing analysis of the interrupt timestamps are the "
        r"next steps we would take before treating these angles as a general design rule.}")

    # ================================================================= DATA AND CODE AVAILABILITY
    h1("Data and Code Availability")
    body_p("[The logged sessions, merged data and all analysis and figure scripts will be deposited in an "
           "archive with a DOI, to be inserted.]")

    # ================================================================= ACKNOWLEDGMENT
    doc.add_paragraph("Acknowledgment", style=HREF)
    p = doc.add_paragraph(style=ACK)
    p.add_run("[Funding sources, if any, to be supplied by the authors.] [AI-use disclosure, required by "
              "IEEE and to be completed by the authors: an AI system, ")
    r = p.add_run("name and version to be supplied")
    r.italic = True
    p.add_run(", was used to write and run the analysis scripts, to generate the figures and tables, and to "
              "draft and edit the text. The authors designed and ran the experiment, reviewed the analyses "
              "and text, and take responsibility for the content.]")

    # ================================================================= REFERENCES
    doc.add_paragraph("References", style=HREF)
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph(style=REF)
        p.add_run(f"[{i}] {ref}")


def build():
    doc = Document()
    setup(doc)
    styles = {s.name: s for s in doc.styles}

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run(TITLE)
    r.bold = True
    r.font.size = Pt(17)
    a = doc.add_paragraph()
    a.alignment = WD_ALIGN_PARAGRAPH.CENTER
    a.add_run("[Author names and affiliations to be supplied]")
    n = doc.add_paragraph()
    n.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = n.add_run("Revised draft for review, following Jessica's comments (Comments v1.docx). New or reworded "
                  "text is shown in red. This is a review copy (8 pages); not the final submission layout, "
                  "which is still to be decided against the 4-page limit.")
    r.italic = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = RED

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run("Abstract—")
    r.bold = True
    r.italic = True
    rr = p.add_run(ABSTRACT)
    rr.font.color.rgb = RED
    p2 = doc.add_paragraph()
    r = p2.add_run("Index Terms—")
    r.bold = True
    r.italic = True
    p2.add_run("Crosstalk, interference, sensor arrays, time-of-flight sensors, VL53L1X.")

    build_body_revised(doc, styles)

    cp = doc.core_properties
    cp.author = "Jessica"
    cp.last_modified_by = "Jessica"
    cp.title = TITLE + " (revised draft)"
    cp.comments = ""
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    cp.created = now
    cp.modified = now
    cp.revision = 1

    doc.save(str(OUT))
    F.scrub_app_xml(OUT)
    F.prune_orphaned_media(OUT)
    return OUT


if __name__ == "__main__":
    print("wrote", build())
