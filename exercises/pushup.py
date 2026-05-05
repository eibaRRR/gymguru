"""Push-up form analyzer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.angle_calculator import calculate_angle
from core.exercise_analyzer import ExerciseAnalyzer
from core.pose_detector import Landmark
from core.rep_counter import RepCounter
from core.symmetry import asymmetry


class PushupAnalyzer(ExerciseAnalyzer):
    """Analyze push-up form using elbow angle and body straightness.

    Form rules:
      * Elbow angle ~90 at bottom, ~160+ at top.
      * Shoulder-hip-ankle should be roughly collinear (~175-180 deg).
      * Hips should not sag or pike.
    """

    name = "Push-up"
    view_hint = "side"

    def _build_counter(self) -> RepCounter:
        return RepCounter(down_threshold=95.0, up_threshold=155.0)

    def _primary_angle(self, landmarks: Dict[str, Landmark]) -> float:
        left = calculate_angle(
            landmarks["left_shoulder"].as_tuple(),
            landmarks["left_elbow"].as_tuple(),
            landmarks["left_wrist"].as_tuple(),
        )
        right = calculate_angle(
            landmarks["right_shoulder"].as_tuple(),
            landmarks["right_elbow"].as_tuple(),
            landmarks["right_wrist"].as_tuple(),
        )
        return (left + right) / 2.0

    def check_form(
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str]]:
        required = [
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
            "left_hip", "right_hip",
            "left_ankle", "right_ankle",
        ]
        if not self._visible(landmarks, required):
            return 0.0, ["Make sure your full body is visible from the side"]

        feedback: List[str] = []
        score = 100.0

        elbow_angle = self._primary_angle(landmarks)

        # Body-line angle: shoulder -> hip -> ankle (average sides).
        def body_line(side: str) -> float:
            return calculate_angle(
                landmarks[f"{side}_shoulder"].as_tuple(),
                landmarks[f"{side}_hip"].as_tuple(),
                landmarks[f"{side}_ankle"].as_tuple(),
            )

        line = (body_line("left") + body_line("right")) / 2.0

        if line < 160:
            feedback.append("Hips sagging or piking — keep body straight")
            score -= 30

        # Depth check at bottom-ish.
        if 100 < elbow_angle < 140:
            feedback.append("Lower your chest further")
            score -= 15

        # Symmetry: elbows should bend evenly.
        diff = asymmetry(landmarks, "elbow")
        if diff is not None and diff > 18:
            feedback.append(f"Uneven push-up — L/R elbow differ by {diff:0.0f}°")
            score -= 15

        if not feedback:
            feedback.append("Good form!")

        return max(0.0, score), feedback
