"""Exercise analyzers registry."""
from __future__ import annotations

from typing import Dict, Type

from core.exercise_analyzer import ExerciseAnalyzer

from .bicep_curl import BicepCurlAnalyzer
from .lunge import LungeAnalyzer
from .plank import PlankAnalyzer
from .pushup import PushupAnalyzer
from .shoulder_press import ShoulderPressAnalyzer
from .squat import SquatAnalyzer

EXERCISES: Dict[str, Type[ExerciseAnalyzer]] = {
    "Squat": SquatAnalyzer,
    "Push-up": PushupAnalyzer,
    "Lunge": LungeAnalyzer,
    "Plank": PlankAnalyzer,
    "Bicep Curl": BicepCurlAnalyzer,
    "Shoulder Press": ShoulderPressAnalyzer,
}

__all__ = [
    "EXERCISES",
    "SquatAnalyzer",
    "PushupAnalyzer",
    "LungeAnalyzer",
    "PlankAnalyzer",
    "BicepCurlAnalyzer",
    "ShoulderPressAnalyzer",
]
