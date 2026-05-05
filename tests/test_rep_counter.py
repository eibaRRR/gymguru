"""Tests for RepCounter + ExerciseAnalyzer cheat-rep gating."""
from __future__ import annotations

import os
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.exercise_analyzer import ExerciseAnalyzer  # noqa: E402
from core.pose_detector import Landmark  # noqa: E402
from core.rep_counter import RepCounter, RepState  # noqa: E402


# ---------------------------------------------------------------------------
# RepCounter
# ---------------------------------------------------------------------------
class TestRepCounter:
    def test_threshold_validation(self):
        import pytest
        with pytest.raises(ValueError):
            RepCounter(down_threshold=160, up_threshold=100)

    def test_simple_squat_cycle(self):
        c = RepCounter(down_threshold=100, up_threshold=160)
        # standing — no rep yet
        for a in (170, 165, 162):
            assert not c.update(a)
        assert c.count == 0
        # descending past down_threshold
        for a in (140, 110, 95):
            c.update(a)
        assert c.state == RepState.DOWN
        # ascending past up_threshold completes rep 1
        assert not c.update(120)        # mid-way
        assert c.update(165)            # crosses up_threshold
        assert c.count == 1
        evt = c.last_event
        assert evt is not None
        assert evt.rep_number == 1
        assert evt.min_angle <= 95
        assert evt.duration_sec > 0

    def test_hysteresis_prevents_double_count(self):
        """Noise around a single threshold must NOT count multiple reps."""
        c = RepCounter(down_threshold=100, up_threshold=160)
        # Hover around 130 — between thresholds. Never should count.
        for a in [165, 130, 135, 128, 132, 129, 133]:
            c.update(a)
        assert c.count == 0

    def test_multiple_reps(self):
        c = RepCounter(down_threshold=100, up_threshold=160)
        cycle = [170, 90, 170, 90, 170, 90, 170]
        for a in cycle:
            c.update(a)
        assert c.count == 3

    def test_reset(self):
        c = RepCounter(down_threshold=100, up_threshold=160)
        for a in [170, 90, 170]:
            c.update(a)
        assert c.count == 1
        c.reset()
        assert c.count == 0
        assert c.state == RepState.UP
        assert c.last_event is None


# ---------------------------------------------------------------------------
# ExerciseAnalyzer cheat-rep gating
# ---------------------------------------------------------------------------
class _FakeAnalyzer(ExerciseAnalyzer):
    """Stub analyzer driven by an externally-set angle + score."""
    name = "fake"
    unit = "reps"
    view_hint = "any"

    def __init__(self, min_quality_score: float = 0.0) -> None:
        self._next_angle = 170.0
        self._next_score = 100.0
        super().__init__(min_quality_score=min_quality_score)

    def _build_counter(self) -> RepCounter:
        return RepCounter(down_threshold=100, up_threshold=160)

    def check_form(self, landmarks: Dict[str, Landmark]) -> Tuple[float, List[str]]:
        return self._next_score, []

    def _primary_angle(self, landmarks: Dict[str, Landmark]) -> float:
        return self._next_angle

    def feed(self, angle: float, score: float):
        self._next_angle = angle
        self._next_score = score
        return self.update({})


class TestCheatRepGating:
    def test_good_rep_counted(self):
        a = _FakeAnalyzer(min_quality_score=60.0)
        a.feed(170, 95)               # standing
        a.feed(90, 90)                # bottom (deepest score = 90)
        _, _, rec = a.feed(170, 95)   # back up — completes rep
        assert rec is not None
        assert rec.rep_number == 1
        assert rec.score == 90
        assert a.rejected_reps == 0
        assert a.counter.count == 1

    def test_low_quality_rep_rejected(self):
        a = _FakeAnalyzer(min_quality_score=80.0)
        a.feed(170, 95)
        a.feed(90, 40)                # ugly bottom
        _, _, rec = a.feed(170, 95)
        assert rec is None
        assert a.rejected_reps == 1
        # un-counted: counter.count back to 0
        assert a.counter.count == 0

    def test_rep_numbers_stay_sequential_after_rejection(self):
        a = _FakeAnalyzer(min_quality_score=80.0)
        # rep 1: rejected (score 40)
        a.feed(170, 95); a.feed(90, 40); a.feed(170, 95)
        # rep 2: clean (score 90) — should be logged as rep_number=1
        a.feed(170, 95); a.feed(90, 90)
        _, _, rec = a.feed(170, 95)
        assert rec is not None
        assert rec.rep_number == 1   # first *counted* rep
        assert a.rejected_reps == 1
        assert a.counter.count == 1
