"""Unsupervised rep quality classifier.

No labels needed: we flag "cheat" / "anomalous" reps by how far their
feature vector deviates from that athlete's personal median. Features are
low-dim and numerically stable, so a robust z-score works well.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional

import numpy as np

from core.exercise_analyzer import RepRecord

FEATURES = ("score", "min_angle", "duration_sec", "eccentric_sec", "concentric_sec")


def _rep_vector(r: RepRecord) -> np.ndarray:
    return np.array([getattr(r, f, 0.0) for f in FEATURES], dtype=float)


@dataclass
class QualityVerdict:
    is_anomaly: bool
    z: float            # robust z-score magnitude
    reason: str


class RepQualityClassifier:
    """Robust-z anomaly detector over recent reps of the same exercise.

    Call :py:meth:`fit` with the user's history of reps (same exercise).
    Then :py:meth:`classify` each new rep. Returns a verdict with a human
    reason string so the coaching UI can explain why a rep looked off.
    """

    def __init__(self, z_threshold: float = 3.0) -> None:
        self.z_threshold = z_threshold
        self._median: Optional[np.ndarray] = None
        self._mad: Optional[np.ndarray] = None   # median absolute deviation

    def fit(self, reps: Iterable[RepRecord]) -> "RepQualityClassifier":
        data = np.array([_rep_vector(r) for r in reps if r is not None], dtype=float)
        if len(data) < 5:
            self._median = None
            self._mad = None
            return self
        self._median = np.median(data, axis=0)
        self._mad = np.median(np.abs(data - self._median), axis=0) + 1e-6
        return self

    @property
    def is_ready(self) -> bool:
        return self._median is not None and self._mad is not None

    def classify(self, rep: RepRecord) -> QualityVerdict:
        if not self.is_ready:
            return QualityVerdict(False, 0.0, "not enough history")
        v = _rep_vector(rep)
        # Robust z-score per feature, then take the max magnitude.
        z = 0.6745 * (v - self._median) / self._mad   # type: ignore[operator]
        mag = np.abs(z)
        idx = int(mag.argmax())
        zi = float(z[idx])
        if mag[idx] < self.z_threshold:
            return QualityVerdict(False, float(mag[idx]), "normal")
        feat = FEATURES[idx]
        direction = "high" if zi > 0 else "low"
        human = {
            "score":          f"form score unusually {direction}",
            "min_angle":      f"depth unusually {direction}",
            "duration_sec":   f"rep duration unusually {direction}",
            "eccentric_sec":  f"descent phase unusually {direction}",
            "concentric_sec": f"ascent phase unusually {direction}",
        }[feat]
        return QualityVerdict(True, float(mag[idx]), human)

    def flag_reps(self, reps: List[RepRecord]) -> List[QualityVerdict]:
        return [self.classify(r) for r in reps]
