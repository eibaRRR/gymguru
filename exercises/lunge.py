"""Forward lunge form analyzer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.angle_calculator import calculate_angle, vertical_alignment
from core.exercise_analyzer import ExerciseAnalyzer
from core.pose_detector import Landmark
from core.rep_counter import RepCounter


class LungeAnalyzer(ExerciseAnalyzer):
    """Analyze lunges via the front-knee angle.

    Form rules:
      * Front knee ~90 at the bottom, ~165+ standing.
      * Torso (shoulder->hip) close to vertical (don't lean forward).
      * Front knee should not collapse far in front of the ankle.
    """

    name = "Lunge"
    view_hint = "side"

    def _build_counter(self) -> RepCounter:
        return RepCounter(down_threshold=110.0, up_threshold=160.0)

    @staticmethod
    def _front_side(landmarks: Dict[str, Landmark]) -> str:
        """Pick the more-flexed leg as the 'front' leg."""
        lk = calculate_angle(
            landmarks["left_hip"].as_tuple(),
            landmarks["left_knee"].as_tuple(),
            landmarks["left_ankle"].as_tuple(),
        )
        rk = calculate_angle(
            landmarks["right_hip"].as_tuple(),
            landmarks["right_knee"].as_tuple(),
            landmarks["right_ankle"].as_tuple(),
        )
        return "left" if lk < rk else "right"

    def _primary_angle(self, landmarks: Dict[str, Landmark]) -> float:
        side = self._front_side(landmarks)
        return calculate_angle(
            landmarks[f"{side}_hip"].as_tuple(),
            landmarks[f"{side}_knee"].as_tuple(),
            landmarks[f"{side}_ankle"].as_tuple(),
        )

    def check_form(
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str]]:
        required = [
            "left_shoulder", "right_shoulder",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
        ]
        if not self._visible(landmarks, required):
            return 0.0, ["Make sure your full body is visible from the side"]

        feedback: List[str] = []
        score = 100.0

        side = self._front_side(landmarks)
        knee_angle = self._primary_angle(landmarks)

        # Torso lean.
        torso_lean = vertical_alignment(
            (
                (landmarks["left_shoulder"].x + landmarks["right_shoulder"].x) / 2,
                (landmarks["left_shoulder"].y + landmarks["right_shoulder"].y) / 2,
            ),
            (
                (landmarks["left_hip"].x + landmarks["right_hip"].x) / 2,
                (landmarks["left_hip"].y + landmarks["right_hip"].y) / 2,
            ),
        )
        if torso_lean > 30:
            feedback.append("Keep torso upright — don't lean forward")
            score -= 25

        # Front knee should not drift far past the ankle (x-axis).
        if abs(landmarks[f"{side}_knee"].x - landmarks[f"{side}_ankle"].x) > 0.10:
            feedback.append("Front knee drifting past toes")
            score -= 15

        # Depth check (rough).
        if 110 < knee_angle < 140:
            feedback.append("Lunge deeper — front knee toward 90°")
            score -= 15

        if not feedback:
            feedback.append("Good form!")
        return max(0.0, score), feedback
