"""Overlay rendering helpers (skeleton + coaching HUD)."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.pose_detector import Landmark

# BGR colors.
GREEN = (0, 200, 0)
RED = (0, 0, 230)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (0, 220, 220)
ORANGE = (0, 165, 255)
BLUE = (230, 130, 0)

SKELETON_EDGES: List[Tuple[str, str]] = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"), ("right_knee", "right_ankle"),
]


def _to_px(lm: Landmark, w: int, h: int) -> Tuple[int, int]:
    return int(lm.x * w), int(lm.y * h)


def draw_skeleton(
    frame: np.ndarray,
    landmarks: Dict[str, Landmark],
    good_form: bool = True,
) -> np.ndarray:
    """Draw the skeleton overlay (green=good, red=bad)."""
    h, w = frame.shape[:2]
    color = GREEN if good_form else RED
    for a, b in SKELETON_EDGES:
        if a in landmarks and b in landmarks:
            cv2.line(frame, _to_px(landmarks[a], w, h),
                     _to_px(landmarks[b], w, h), color, 2, cv2.LINE_AA)
    for lm in landmarks.values():
        p = _to_px(lm, w, h)
        cv2.circle(frame, p, 4, color, -1, cv2.LINE_AA)
        cv2.circle(frame, p, 6, WHITE, 1, cv2.LINE_AA)
    return frame


def draw_hud(
    frame: np.ndarray,
    exercise: str,
    reps: int,
    score: float,
    feedback: Optional[List[str]] = None,
    *,
    set_idx: Optional[int] = None,
    total_sets: Optional[int] = None,
    target_reps: Optional[int] = None,
    rest_remaining: Optional[int] = None,
    last_grade: Optional[str] = None,
    rep_flash: bool = False,
    unit: str = "Reps",
    view_warning: Optional[str] = None,
    rejected_reps: int = 0,
    dropout_warning: Optional[str] = None,
) -> np.ndarray:
    """Render the coaching HUD on the frame.

    Args:
        rep_flash: when True, draws a green border (call right after a rep).
        rest_remaining: seconds; if > 0 a big REST timer is shown center-top.
    """
    h, w = frame.shape[:2]

    # Top-left translucent panel.
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (min(440, w), 150), BLACK, -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, f"Exercise: {exercise}", (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2, cv2.LINE_AA)

    rep_text = f"{unit.capitalize()}: {reps}"
    if target_reps:
        rep_text += f" / {target_reps}"
    cv2.putText(frame, rep_text, (12, 58),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, YELLOW, 2, cv2.LINE_AA)

    if set_idx and total_sets:
        cv2.putText(frame, f"Set: {set_idx}/{total_sets}", (220, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, BLUE, 2, cv2.LINE_AA)

    color = GREEN if score >= 80 else (YELLOW if score >= 50 else RED)
    cv2.putText(frame, f"Form: {score:0.0f}/100", (12, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)

    if last_grade:
        cv2.putText(frame, f"Last rep: {last_grade}", (220, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, ORANGE, 2, cv2.LINE_AA)

    if rejected_reps:
        cv2.putText(frame, f"Cheat reps: {rejected_reps}", (12, 125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, RED, 2, cv2.LINE_AA)

    # Feedback messages below the panel.
    if feedback:
        y = 175
        for msg in feedback[:3]:
            cv2.putText(frame, f"- {msg}", (12, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, WHITE, 2, cv2.LINE_AA)
            y += 26

    # Dropout warning (center-bottom).
    if dropout_warning:
        (tw, th), _ = cv2.getTextSize(dropout_warning, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(frame, ((w - tw) // 2 - 10, h - 50),
                      ((w + tw) // 2 + 10, h - 10), (0, 0, 0), -1)
        cv2.putText(frame, dropout_warning, ((w - tw) // 2, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, RED, 2, cv2.LINE_AA)

    # View-mismatch warning (top-right).
    if view_warning:
        (tw, th), _ = cv2.getTextSize(view_warning, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        x0 = w - tw - 16
        cv2.rectangle(frame, (x0 - 6, 8), (w - 4, 8 + th + 12), (0, 0, 0), -1)
        cv2.putText(frame, view_warning, (x0, 8 + th + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, ORANGE, 2, cv2.LINE_AA)

    # Rep flash (green border).
    if rep_flash:
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), GREEN, 12)

    # Big REST timer (translucent veil so the user can still see themselves).
    if rest_remaining and rest_remaining > 0:
        veil = frame.copy()
        cv2.rectangle(veil, (0, 0), (w, h), BLACK, -1)
        cv2.addWeighted(veil, 0.55, frame, 0.45, 0, frame)
        text = f"REST {rest_remaining}s"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 2.4, 6)
        cv2.putText(frame, text, ((w - tw) // 2, (h + th) // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.4, ORANGE, 6, cv2.LINE_AA)

    return frame
