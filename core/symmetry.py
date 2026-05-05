"""Left/right symmetry analysis helpers."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.angle_calculator import calculate_angle
from core.pose_detector import Landmark


def joint_pair_angle(
    landmarks: Dict[str, Landmark], joint: str
) -> Tuple[Optional[float], Optional[float]]:
    """Return (left_angle, right_angle) at the named joint.

    Supported joints: ``knee``, ``elbow``, ``hip``.
    """
    chains = {
        "knee":  ("hip", "knee", "ankle"),
        "elbow": ("shoulder", "elbow", "wrist"),
        "hip":   ("shoulder", "hip", "knee"),
    }
    if joint not in chains:
        raise ValueError(f"unsupported joint: {joint}")
    a, b, c = chains[joint]

    def side(s: str) -> Optional[float]:
        keys = [f"{s}_{a}", f"{s}_{b}", f"{s}_{c}"]
        if not all(k in landmarks for k in keys):
            return None
        return calculate_angle(
            landmarks[keys[0]].as_tuple(),
            landmarks[keys[1]].as_tuple(),
            landmarks[keys[2]].as_tuple(),
        )

    return side("left"), side("right")


def asymmetry(
    landmarks: Dict[str, Landmark], joint: str
) -> Optional[float]:
    """Absolute degree difference between left and right at ``joint``.

    Returns ``None`` if either side is missing.
    """
    l, r = joint_pair_angle(landmarks, joint)
    if l is None or r is None:
        return None
    return abs(l - r)
