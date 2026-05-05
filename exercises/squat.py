"""Squat form analyzer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.angle_calculator import calculate_angle, vertical_alignment
from core.exercise_analyzer import ExerciseAnalyzer
from core.pose_detector import Landmark
from core.rep_counter import RepCounter
from core.symmetry import asymmetry


class SquatAnalyzer(ExerciseAnalyzer):
    """Analyze squat form using knee and hip angles.

    Form rules:
      * Knee angle < ~100 at bottom = good depth.
      * Back (shoulder-hip vs vertical) should stay under ~45 degrees lean.
      * Knees should track roughly over ankles (not collapse inward).
    """

    name = "Squat"
    view_hint = "side"

    def _build_counter(self) -> RepCounter:
        # Knee angle: ~170 standing, ~90 deep squat.
        return RepCounter(down_threshold=100.0, up_threshold=160.0)

    def _primary_angle(self, landmarks: Dict[str, Landmark]) -> float:
        # Average of both knee angles for robustness.
        left = calculate_angle(
            landmarks["left_hip"].as_tuple(),
            landmarks["left_knee"].as_tuple(),
            landmarks["left_ankle"].as_tuple(),
        )
        right = calculate_angle(
            landmarks["right_hip"].as_tuple(),
            landmarks["right_knee"].as_tuple(),
            landmarks["right_ankle"].as_tuple(),
        )
        return (left + right) / 2.0

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
            return 0.0, ["Make sure your full body is visible"]

        feedback: List[str] = []
        score = 100.0

        knee_angle = self._primary_angle(landmarks)

        # Back lean: shoulders-midpoint to hips-midpoint vs vertical.
        shoulder_mid = (
            (landmarks["left_shoulder"].x + landmarks["right_shoulder"].x) / 2,
            (landmarks["left_shoulder"].y + landmarks["right_shoulder"].y) / 2,
        )
        hip_mid = (
            (landmarks["left_hip"].x + landmarks["right_hip"].x) / 2,
            (landmarks["left_hip"].y + landmarks["right_hip"].y) / 2,
        )
        back_lean = vertical_alignment(shoulder_mid, hip_mid)

        # At the bottom, check depth.
        if knee_angle < 140 and knee_angle > 110:
            feedback.append("Go deeper — bend knees further")
            score -= 20

        if back_lean > 45:
            feedback.append("Keep your chest up — reduce forward lean")
            score -= 25

        # Knees-over-ankles tracking (x-axis).
        knee_ankle_gap_l = abs(landmarks["left_knee"].x - landmarks["left_ankle"].x)
        knee_ankle_gap_r = abs(landmarks["right_knee"].x - landmarks["right_ankle"].x)
        if max(knee_ankle_gap_l, knee_ankle_gap_r) > 0.08:
            feedback.append("Keep knees aligned over toes")
            score -= 15

        # Left/right symmetry (knees).
        diff = asymmetry(landmarks, "knee")
        if diff is not None and diff > 15:
            feedback.append(f"Uneven squat — L/R knee differ by {diff:0.0f}°")
            score -= 15

        if not feedback:
            feedback.append("Good form!")

        return max(0.0, score), feedback
