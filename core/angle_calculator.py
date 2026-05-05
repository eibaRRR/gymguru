"""Joint-angle math utilities for GymGuru.

All points are 2D or 3D sequences (x, y[, z]) in normalized image coordinates.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

Point = Sequence[float]


def calculate_angle(p1: Point, p2: Point, p3: Point, use_3d: bool = False) -> float:
    """Return the angle (in degrees) at vertex ``p2`` formed by p1-p2-p3.

    Args:
        p1/p2/p3: 2D or 3D points. If ``use_3d`` is True and 3D data is
            present, the angle is computed in 3D for more accurate depth
            handling (e.g. knee valgus detection from an angled view).
        use_3d: opt in to 3D computation (slightly costlier, more robust).

    Returns:
        Angle in degrees in the range [0, 180].
    """
    dims = 3 if use_3d else 2
    a = np.asarray(p1, dtype=float)[:dims]
    b = np.asarray(p2, dtype=float)[:dims]
    c = np.asarray(p3, dtype=float)[:dims]

    ba = a - b
    bc = c - b

    if use_3d:
        # 3D: use the norm of the cross product for the sine component.
        cross = np.cross(ba, bc)
        cross_mag = float(np.linalg.norm(cross))
        dot = float(np.dot(ba, bc))
        angle = math.degrees(math.atan2(cross_mag, dot))
    else:
        cross = ba[0] * bc[1] - ba[1] * bc[0]
        dot = ba[0] * bc[0] + ba[1] * bc[1]
        angle = math.degrees(math.atan2(abs(cross), dot))

    if angle < 0:
        angle += 360
    if angle > 180:
        angle = 360 - angle
    return float(angle)


def vertical_alignment(p1: Point, p2: Point) -> float:
    """Return angle (degrees) of segment p1->p2 relative to vertical axis.

    Useful for checking back straightness or tibia lean.
    0 degrees means perfectly vertical.
    """
    a = np.asarray(p1, dtype=float)[:2]
    b = np.asarray(p2, dtype=float)[:2]
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return float(math.degrees(math.atan2(abs(dx), abs(dy) + 1e-9)))
