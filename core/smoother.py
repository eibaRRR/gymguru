"""Exponential moving average smoother for pose landmarks.

Reduces frame-to-frame jitter that makes joint angles look noisy and
causes spurious rep transitions.
"""
from __future__ import annotations

from typing import Dict, Optional

from core.pose_detector import Landmark


class LandmarkSmoother:
    """Per-landmark EMA. ``alpha`` is the weight given to the new sample.

    alpha=1.0 disables smoothing; alpha~0.5-0.7 is a good default for 15-30 FPS.
    """

    def __init__(self, alpha: float = 0.6) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._prev: Optional[Dict[str, Landmark]] = None

    def __call__(self, landmarks: Dict[str, Landmark]) -> Dict[str, Landmark]:
        if self._prev is None:
            self._prev = dict(landmarks)
            return landmarks
        a = self.alpha
        out: Dict[str, Landmark] = {}
        for name, lm in landmarks.items():
            prev = self._prev.get(name)
            if prev is None:
                out[name] = lm
            else:
                out[name] = Landmark(
                    x=a * lm.x + (1 - a) * prev.x,
                    y=a * lm.y + (1 - a) * prev.y,
                    z=a * lm.z + (1 - a) * prev.z,
                    visibility=lm.visibility,
                )
        self._prev = out
        return out

    def reset(self) -> None:
        self._prev = None
