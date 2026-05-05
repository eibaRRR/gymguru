"""Track and draw the trajectory of the wrists (bar path proxy)."""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Tuple

import cv2
import numpy as np

from core.pose_detector import Landmark

Point = Tuple[float, float]


class BarPathTracker:
    """Keeps a rolling trail of the mid-wrist point in normalized coords.

    Useful for pressing / pulling / squat bar movements. For squats the
    "bar" is approximated by the midpoint between the two shoulders.
    """

    def __init__(self, maxlen: int = 150, source: str = "wrists") -> None:
        if source not in ("wrists", "shoulders"):
            raise ValueError("source must be 'wrists' or 'shoulders'")
        self.source = source
        self.trail: Deque[Point] = deque(maxlen=maxlen)

    def update(self, landmarks: Dict[str, Landmark]) -> None:
        keys = ("left_wrist", "right_wrist") if self.source == "wrists" else (
            "left_shoulder", "right_shoulder")
        if not all(k in landmarks and landmarks[k].visibility > 0.4 for k in keys):
            return
        a, b = landmarks[keys[0]], landmarks[keys[1]]
        self.trail.append(((a.x + b.x) / 2, (a.y + b.y) / 2))

    def deviation_px(self, w: int) -> float:
        """Std-dev of the horizontal coordinate of the trail, in pixels.

        Lower = straighter bar path. Great diagnostic for pressing work.
        """
        if len(self.trail) < 5:
            return 0.0
        xs = np.array([p[0] * w for p in self.trail])
        return float(xs.std())

    def draw(self, frame: np.ndarray, color=(0, 220, 220)) -> None:
        if len(self.trail) < 2:
            return
        h, w = frame.shape[:2]
        pts = np.array([(int(x * w), int(y * h)) for x, y in self.trail], dtype=np.int32)
        for i in range(1, len(pts)):
            cv2.line(frame, tuple(pts[i - 1]), tuple(pts[i]), color, 2, cv2.LINE_AA)
        cv2.circle(frame, tuple(pts[-1]), 6, color, -1, cv2.LINE_AA)

    def reset(self) -> None:
        self.trail.clear()
