"""Sensitivity of the geometric end-of-overlap prediction to its two unverified inputs.

The project's model (rig/geometry.py) says the overlap between sensor B's lit spot and sensor A's receive field
ends when  s + 2 d tan(dtheta/2) = d [tan(E/2) + tan(F/2)],  with s the aperture spacing, d the target distance,
F the receive field and E the emitter cone. geometry.py sets E = 27 deg and F = 27 deg (16x16) or 15 deg (4x4).

Checked against ST datasheet DS12385 Rev 8 (read 11 October 2026, from the PDF text):
  * Table 2 and Table 20 give the FoV as a DIAGONAL value: 27 / 20 / 15 deg for 16x16 / 8x8 / 4x4 SPADs.
  * No emitter beam angle or illumination cone is stated anywhere in the document (940 nm VCSEL, Class 1 only).
So geometry.py (a) uses diagonal values as if they were in-plane, and (b) takes E = 27 deg as an assumption.

The toe-out plane contains the array's horizontal axis only if the module is mounted square to the pucks, which
the project files do not record. This script therefore reports the prediction under explicit alternatives, as a
sensitivity analysis, not as a corrected prediction.

For a square array seen through a rectilinear lens with half-diagonal angle alpha, the half-angle along one array
axis is beta with tan(beta) = tan(alpha) / sqrt(2).

Run:   python manuscript_ieee/scripts/geometry_sensitivity.py
Out:   manuscript_ieee/analysis/geometry_sensitivity.csv

Author: Jessica
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "analysis"
OUT.mkdir(exist_ok=True)

S = 0.020
DIAG = {16: 27.0, 4: 15.0}          # datasheet diagonal FoV, degrees
E_ASSUMED = 27.0                    # emitter cone used by geometry.py, not in the datasheet


def axis_fov(diag_deg: float) -> float:
    """Full angle along one array axis for a square array with the given diagonal full angle."""
    a = math.radians(diag_deg / 2)
    return 2 * math.degrees(math.atan(math.tan(a) / math.sqrt(2)))


def end_of_overlap(e_deg: float, f_deg: float, d: float, s: float = S) -> float:
    k = (math.tan(math.radians(e_deg / 2)) + math.tan(math.radians(f_deg / 2))) / 2
    return 2 * math.degrees(math.atan(k - s / (2 * d)))


VARIANTS = {
    "V0 as implemented (E=27, F=diagonal value used in-plane)":
        lambda roi: (E_ASSUMED, DIAG[roi]),
    "V1 receive field in-plane (E=27 kept)":
        lambda roi: (E_ASSUMED, axis_fov(DIAG[roi])),
    "V2 emitter and receive field both in-plane (E=axis_fov(27))":
        lambda roi: (axis_fov(27.0), axis_fov(DIAG[roi])),
}


def main():
    rows = []
    for name, fn in VARIANTS.items():
        for roi in (16, 4):
            e, f = fn(roi)
            for d in (0.3, 0.6, 0.9):
                rows.append({"variant": name.split(" ")[0], "description": name, "zone": f"{roi}x{roi}",
                             "E_deg": round(e, 2), "F_deg": round(f, 2), "distance_m": d,
                             "end_of_overlap_deg": end_of_overlap(e, f, d)})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "geometry_sensitivity.csv", index=False)
    wide = df.pivot_table(index=["zone", "distance_m"], columns="variant", values="end_of_overlap_deg")
    print("In-plane FoV from the diagonal value:  27 deg -> %.2f deg,  15 deg -> %.2f deg" % (axis_fov(27), axis_fov(15)))
    print("\nPredicted end-of-overlap angle, dtheta (degrees):")
    print(wide.round(2).to_string())


if __name__ == "__main__":
    main()
