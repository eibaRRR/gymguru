"""Standing overhead shoulder press form analyzer."""
from __future__ import annotations

from typing import Dict, List, Tuple

from core.angle_calculator import calculate_angle, vertical_alignment
from core.exercise_analyzer import ExerciseAnalyzer
from core.pose_detector import Landmark
from core.rep_counter import RepCounter


class ShoulderPressAnalyzer(ExerciseAnalyzer):
    """Analyze overhead presses via the elbow angle.

    Note: we count UP=racked (elbow bent, low angle) and "rep complete" when
    extending overhead (high angle). To reuse the standard up/down state
    machine we treat *bent* as DOWN and *extended* as UP.

    Form rules:
      * At lockout, elbow ~165+ degrees (full extension).
      * Wrists should stay roughly above the shoulders (not flared / forward).
      * Torso vertical (no excessive back arch).
    """

    name = "Shoulder Press"
    view_hint = "front"

    def _build_counter(self) -> RepCounter:
        # Start UP = arms extended overhead. Down = bar racked at shoulders.
        return RepCounter(down_threshold=80.0, up_threshold=160.0)

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
        ]
        if not self._visible(landmarks, required):
            return 0.0, ["Keep your upper body fully in frame"]

        feedback: List[str] = []
        score = 100.0

        # Wrist-above-shoulder check (x-distance, normalized).
        for side in ("left", "right"):
            dx = abs(landmarks[f"{side}_wrist"].x - landmarks[f"{side}_shoulder"].x)
            if dx > 0.12:
                feedback.append("Wrists drifting — press straight up over shoulders")
                score -= 20
                break

        # Torso lean (excessive arch).
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
        if torso_lean > 20:
            feedback.append("Keep torso upright — engage your core")
            score -= 20

        # Lockout depth.
        elbow = self._primary_angle(landmarks)
        if 130 < elbow < 160:
            feedback.append("Press to full lockout overhead")
            score -= 10

        if not feedback:
            feedback.append("Good form!")
        return max(0.0, score), feedback
