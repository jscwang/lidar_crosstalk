"""Predicted crossover angle, identical to crossover() in build_rq3.py.

Overlap between B's lit spot and A's receive field ends when

    s + 2d * tan(dtheta/2) = d * [tan(E/2) + tan(F/2)]

(RQ3 design PDF), with s the aperture spacing, d the target distance, F the
receive field and E the emitter cone. The two-sensor procedure PDF prints the
form s = d*[tan(F/2 - dtheta/2) + tan(E/2 - dtheta/2)], which gives values
up to about 0.2 deg lower; this module keeps the build_rq3 form so the
numbers match every table already issued (23.4/25.6 deg full ROI,
17.3/19.7 deg 4x4, at 0.3/0.8 m).

Author: Jessica
"""
from __future__ import annotations

import math

EMITTER_CONE_DEG = 27.0
# Receive field for the two ROI sizes in the procedure. Other ROI sizes have
# no measured value, so no prediction is made for them.
RECEIVE_FIELD_DEG = {16: 27.0, 4: 15.0}


def crossover_deg(receive_field_deg: float, d_m: float, s_m: float = 0.020,
                  emitter_cone_deg: float = EMITTER_CONE_DEG) -> float:
    """Total toe-out dtheta (degrees) at which the overlap ends."""
    k = (math.tan(math.radians(emitter_cone_deg / 2)) + math.tan(math.radians(receive_field_deg / 2))) / 2
    return 2 * math.degrees(math.atan(k - s_m / (2 * d_m)))


def predicted_crossover(roi: int, d_m: float, s_m: float = 0.020):
    f = RECEIVE_FIELD_DEG.get(roi)
    return None if f is None else crossover_deg(f, d_m, s_m)
