"""Plank (timed hold) form analyzer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.angle_calculator import calculate_angle
from core.pose_detector import Landmark
from core.timed_analyzer import TimedExerciseAnalyzer


class PlankAnalyzer(TimedExerciseAnalyzer):
    """Forearm/high plank — counts seconds the body line is correct.

    Form rule: shoulder-hip-ankle should form a near-straight line (>=160°).
    Hips sagging or piking break the line.
    """

    name = "Plank"
    view_hint = "side"

    @staticmethod
    def _body_line(landmarks: Dict[str, Landmark]) -> float:
        def side(s: str) -> float:
            return calculate_angle(
                landmarks[f"{s}_shoulder"].as_tuple(),
                landmarks[f"{s}_hip"].as_tuple(),
                landmarks[f"{s}_ankle"].as_tuple(),
            )
        return (side("left") + side("right")) / 2.0

    def is_in_position(self, landmarks: Dict[str, Landmark]) -> bool:
        required = [
            "left_shoulder", "right_shoulder",
            "left_hip", "right_hip",
            "left_ankle", "right_ankle",
        ]
        if not self._visible(landmarks, required):
            return False
        return self._body_line(landmarks) >= 160.0

    def check_form(
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str]]:
        required = [
            "left_shoulder", "right_shoulder",
            "left_hip", "right_hip",
            "left_ankle", "right_ankle",
        ]
        if not self._visible(landmarks, required):
            return 0.0, ["Get into plank with full body in side-view"]

        line = self._body_line(landmarks)
        feedback: List[str] = []
        score = 100.0
        if line < 150:
            feedback.append("Hips sagging — engage core, lift hips")
            score -= 40
        elif line < 160:
            feedback.append("Almost — keep body straight")
            score -= 15
        elif line > 185:
            feedback.append("Hips piking — lower them in line")
            score -= 20
        if not feedback:
            feedback.append("Great hold!")
        return max(0.0, score), feedback
