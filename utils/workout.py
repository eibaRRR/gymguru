"""Workout state machine: target sets x reps with auto rest timer."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    WORKING = "working"
    RESTING = "resting"
    DONE = "done"


@dataclass
class WorkoutPlan:
    """Configuration for a workout: ``sets`` x ``reps_per_set`` with rest."""
    sets: int = 3
    reps_per_set: int = 10
    rest_sec: int = 60


@dataclass
class WorkoutState:
    """Live state of an in-progress workout."""
    plan: WorkoutPlan
    current_set: int = 1
    reps_in_set: int = 0
    phase: Phase = Phase.WORKING
    rest_started_at: Optional[float] = None
    last_set_score_avg: float = 0.0

    def on_rep(self, total_reps: int) -> None:
        """Update on every completed rep (``total_reps`` is the cumulative count)."""
        if self.phase != Phase.WORKING:
            return
        # Reps in current set = total - reps in previous sets.
        reps_in_prev_sets = (self.current_set - 1) * self.plan.reps_per_set
        self.reps_in_set = max(0, total_reps - reps_in_prev_sets)
        if self.reps_in_set >= self.plan.reps_per_set:
            if self.current_set >= self.plan.sets:
                self.phase = Phase.DONE
            else:
                self.phase = Phase.RESTING
                self.rest_started_at = time.monotonic()

    def tick(self) -> None:
        """Advance the rest timer; transition back to WORKING when done."""
        if self.phase != Phase.RESTING or self.rest_started_at is None:
            return
        if time.monotonic() - self.rest_started_at >= self.plan.rest_sec:
            self.phase = Phase.WORKING
            self.current_set += 1
            self.reps_in_set = 0
            self.rest_started_at = None

    def rest_remaining(self) -> int:
        if self.phase != Phase.RESTING or self.rest_started_at is None:
            return 0
        elapsed = time.monotonic() - self.rest_started_at
        return max(0, int(self.plan.rest_sec - elapsed))

    def reps_remaining_in_set(self) -> int:
        return max(0, self.plan.reps_per_set - self.reps_in_set)

    def reset(self) -> None:
        self.current_set = 1
        self.reps_in_set = 0
        self.phase = Phase.WORKING
        self.rest_started_at = None
