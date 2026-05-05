"""Detect whether the user is in a side or front view of the camera.

Heuristic: the ratio of shoulder horizontal-spread to torso vertical-height.
- Front view: shoulders are far apart relative to torso height (>~0.45).
- Side view: shoulders are nearly stacked (<~0.25).
"""
from __future__ import annotations

from typing import Dict

from core.pose_detector import Landmark


def detect_view(landmarks: Dict[str, Landmark]) -> str:
    """Return one of ``"front"``, ``"side"``, or ``"unknown"``."""
    needed = ["left_shoulder", "right_shoulder", "left_hip", "right_hip"]
    if not all(k in landmarks and landmarks[k].visibility > 0.4 for k in needed):
        return "unknown"

    sh_dx = abs(landmarks["left_shoulder"].x - landmarks["right_shoulder"].x)
    torso_dy = abs(
        (landmarks["left_shoulder"].y + landmarks["right_shoulder"].y) / 2
        - (landmarks["left_hip"].y + landmarks["right_hip"].y) / 2
    ) + 1e-6
    ratio = sh_dx / torso_dy
    if ratio > 0.45:
        return "front"
    if ratio < 0.25:
        return "side"
    return "unknown"


def view_warning(detected: str, expected: str) -> str | None:
    """Return a coaching message if the camera view doesn't match the hint."""
    if expected == "any" or detected == "unknown" or detected == expected:
        return None
    if expected == "side":
        return "Turn to a side view of the camera for this exercise"
    if expected == "front":
        return "Face the camera (front view) for this exercise"
    return None
