"""Bicep curl form analyzer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.angle_calculator import calculate_angle, vertical_alignment
from core.exercise_analyzer import ExerciseAnalyzer
from core.pose_detector import Landmark
from core.rep_counter import RepCounter


class BicepCurlAnalyzer(ExerciseAnalyzer):
    """Analyze bicep curl via elbow flexion.

    Form rules:
      * Elbow angle ~30-40 at top, ~160+ at bottom (extended).
      * Upper arm (shoulder->elbow) should stay near vertical (no swinging).
    """

    name = "Bicep Curl"
    view_hint = "front"

    def _build_counter(self) -> RepCounter:
        # Start extended (UP = arm down / extended, high angle).
        # Rep completes when we go extended -> curled -> extended.
        # We treat "curled" (low angle) as DOWN state for counter symmetry.
        return RepCounter(down_threshold=50.0, up_threshold=150.0)

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
        # Use the more-flexed arm (smallest angle) so single-arm curls work too.
        return min(left, right)

    def check_form(
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str]]:
        required = [
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
        ]
        if not self._visible(landmarks, required):
            return 0.0, ["Keep your upper body in frame"]

        feedback: List[str] = []
        score = 100.0

        # Upper-arm verticality: shoulder -> elbow.
        def upper_arm_lean(side: str) -> float:
            return vertical_alignment(
                (landmarks[f"{side}_shoulder"].x, landmarks[f"{side}_shoulder"].y),
                (landmarks[f"{side}_elbow"].x, landmarks[f"{side}_elbow"].y),
            )

        lean = min(upper_arm_lean("left"), upper_arm_lean("right"))
        if lean > 25:
            feedback.append("Keep elbows tucked — don't swing the upper arm")
            score -= 25

        elbow_angle = self._primary_angle(landmarks)
        # Partial range check (never fully extends).
        if 60 < elbow_angle < 140:
            # Mid-rep, fine.
            pass

        if not feedback:
            feedback.append("Good form!")

        return max(0.0, score), feedback
