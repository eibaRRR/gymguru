"""Base class for time-based (hold) exercises like planks."""
from __future__ import annotations

import time
from abc import abstractmethod
from typing import Dict, List, Optional, Tuple

from core.exercise_analyzer import ExerciseAnalyzer, RepRecord, grade_from_score
from core.pose_detector import Landmark
from core.rep_counter import RepCounter


class TimedExerciseAnalyzer(ExerciseAnalyzer):
    """Counts seconds in a valid hold position.

    Subclasses override :py:meth:`is_in_position` to declare whether the
    user is currently holding the position correctly. The aggregate
    "rep count" for the rest of the app becomes the integer number of
    seconds held; each whole second emits a :class:`RepRecord` so the
    same per-rep table / grading UI keeps working.
    """

    unit = "seconds"

    def __init__(self) -> None:
        super().__init__()
        self._held_sec: float = 0.0
        self._last_t: Optional[float] = None
        self._whole_seconds_emitted: int = 0
        self._second_score_sum: float = 0.0
        self._second_score_n: int = 0

    # --- subclass hooks -------------------------------------------------
    @abstractmethod
    def is_in_position(self, landmarks: Dict[str, Landmark]) -> bool:
        """Return True iff the user is currently holding the position."""

    def _build_counter(self) -> RepCounter:
        # Unused, but the parent class expects one.
        return RepCounter(down_threshold=0.0, up_threshold=1.0)

    def _primary_angle(self, landmarks: Dict[str, Landmark]) -> float:
        return 0.0

    # --- public API -----------------------------------------------------
    def update(  # type: ignore[override]
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str], Optional[RepRecord]]:
        score, feedback = self.check_form(landmarks)
        now = time.monotonic()

        in_pos = self.is_in_position(landmarks)
        if in_pos and self._last_t is not None:
            self._held_sec += now - self._last_t
            self._second_score_sum += score
            self._second_score_n += 1
        self._last_t = now if in_pos else None

        record: Optional[RepRecord] = None
        whole = int(self._held_sec)
        if whole > self._whole_seconds_emitted:
            avg = (self._second_score_sum / self._second_score_n
                   if self._second_score_n else score)
            record = RepRecord(
                rep_number=whole,
                score=avg,
                grade=grade_from_score(avg),
                feedback=list(feedback),
                min_angle=0.0,
                duration_sec=1.0,
                eccentric_sec=0.0,
                concentric_sec=0.0,
            )
            self._whole_seconds_emitted = whole
            self._second_score_sum = 0.0
            self._second_score_n = 0
        return score, feedback, record

    # Override rep_count to expose seconds held.
    @property
    def rep_count(self) -> int:  # type: ignore[override]
        return int(self._held_sec)

    def reset(self) -> None:  # type: ignore[override]
        super().reset()
        self._held_sec = 0.0
        self._last_t = None
        self._whole_seconds_emitted = 0
        self._second_score_sum = 0.0
        self._second_score_n = 0
