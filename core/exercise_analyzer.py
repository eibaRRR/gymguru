"""Base class for per-exercise form analyzers (with per-rep grading)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.pose_detector import Landmark
from core.rep_counter import RepCounter, RepEvent


def grade_from_score(score: float) -> str:
    """Map a 0-100 form score to a letter grade."""
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 65: return "C"
    if score >= 50: return "D"
    return "F"


@dataclass
class RepRecord:
    """Detailed record of a single completed rep."""
    rep_number: int
    score: float                     # form score captured at deepest point
    grade: str                       # letter grade derived from score
    feedback: List[str] = field(default_factory=list)
    min_angle: float = 0.0
    duration_sec: float = 0.0
    eccentric_sec: float = 0.0
    concentric_sec: float = 0.0


class ExerciseAnalyzer(ABC):
    """Base class. Subclasses implement form rules + rep counter config.

    The combined :py:meth:`update` method runs everything needed per-frame:
      * computes form score / feedback
      * tracks the *deepest* frame in the current rep
      * advances the rep state machine
      * on rep completion, returns a :class:`RepRecord` capturing form at
        the deepest point of that rep
    """

    name: str = "exercise"
    unit: str = "reps"             # display label, e.g. "reps" or "seconds"
    view_hint: str = "any"         # "side", "front", or "any"

    def __init__(self, min_quality_score: float = 0.0) -> None:
        """``min_quality_score``: reps below this form score are flagged as
        cheat reps and (optionally) not committed to the rep count."""
        self.counter: RepCounter = self._build_counter()
        self.min_quality_score = float(min_quality_score)
        # Buffer for "best" (deepest) frame in the current rep.
        self._best_angle: Optional[float] = None
        self._best_score: float = 0.0
        self._best_feedback: List[str] = []
        self.rejected_reps: int = 0

    # --- subclass hooks -------------------------------------------------
    @abstractmethod
    def check_form(
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str]]:
        """Return (score 0-100, feedback messages) for the current frame."""

    @abstractmethod
    def _primary_angle(self, landmarks: Dict[str, Landmark]) -> float:
        """Return the joint angle driving the rep state machine."""

    @abstractmethod
    def _build_counter(self) -> RepCounter:
        """Return a configured RepCounter."""

    # --- public API -----------------------------------------------------
    def update(
        self, landmarks: Dict[str, Landmark]
    ) -> Tuple[float, List[str], Optional[RepRecord]]:
        """Process a frame. Returns (score, feedback, completed_rep_or_None)."""
        score, feedback = self.check_form(landmarks)
        try:
            angle = self._primary_angle(landmarks)
        except Exception:
            return score, feedback, None

        # Track the deepest frame so far in the in-progress rep.
        if self._best_angle is None or angle < self._best_angle:
            self._best_angle = angle
            self._best_score = score
            self._best_feedback = list(feedback)

        completed = self.counter.update(angle)
        if not completed:
            return score, feedback, None

        evt: RepEvent = self.counter.last_event  # type: ignore[assignment]

        # Cheat-rep gating (#38): reject if quality below threshold.
        if self._best_score < self.min_quality_score:
            self.counter.count -= 1  # un-count it
            self.rejected_reps += 1
            self._best_angle = None
            self._best_score = 0.0
            self._best_feedback = []
            rejected_feedback = list(feedback) + ["Rep rejected — form below threshold"]
            return score, rejected_feedback, None

        record = RepRecord(
            rep_number=evt.rep_number,
            score=self._best_score,
            grade=grade_from_score(self._best_score),
            feedback=self._best_feedback,
            min_angle=evt.min_angle,
            duration_sec=evt.duration_sec,
            eccentric_sec=evt.eccentric_sec,
            concentric_sec=evt.concentric_sec,
        )
        # Reset per-rep buffer.
        self._best_angle = None
        self._best_score = 0.0
        self._best_feedback = []
        return score, feedback, record

    # Back-compat shims used by older code paths / tests.
    def detect_rep(self, landmarks: Dict[str, Landmark]) -> bool:
        return self.counter.update(self._primary_angle(landmarks))

    @property
    def rep_count(self) -> int:
        return self.counter.count

    def reset(self) -> None:
        self.counter.reset()
        self._best_angle = None
        self._best_score = 0.0
        self._best_feedback = []

    # --- helpers --------------------------------------------------------
    @staticmethod
    def _visible(
        landmarks: Dict[str, Landmark], keys: List[str], thresh: float = 0.4
    ) -> bool:
        return all(k in landmarks and landmarks[k].visibility >= thresh for k in keys)
