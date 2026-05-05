"""Up/down state machine for counting reps with tempo + ROM tracking."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class RepState(str, Enum):
    UP = "up"
    DOWN = "down"


@dataclass
class RepEvent:
    """Emitted when a rep completes. Carries tempo + range-of-motion info."""
    rep_number: int
    duration_sec: float       # total UP->DOWN->UP cycle
    eccentric_sec: float      # descending portion (UP -> bottom)
    concentric_sec: float     # ascending portion (bottom -> UP)
    min_angle: float          # deepest angle reached during the rep


class RepCounter:
    """Counts reps via hysteresis on a primary joint angle.

    Also tracks per-rep tempo and minimum angle (depth/ROM). Use
    :py:attr:`last_event` after :py:meth:`update` returns ``True``.
    """

    def __init__(
        self,
        down_threshold: float,
        up_threshold: float,
        start_state: RepState = RepState.UP,
    ) -> None:
        if down_threshold >= up_threshold:
            raise ValueError("down_threshold must be < up_threshold")
        self.down_threshold = down_threshold
        self.up_threshold = up_threshold
        self.state = start_state
        self.count = 0

        # Per-rep tracking.
        self._t_descent_start: Optional[float] = None
        self._t_min_angle: Optional[float] = None
        self._min_angle: Optional[float] = None
        self.last_event: Optional[RepEvent] = None

    # --- main loop ------------------------------------------------------
    def update(self, angle: float) -> bool:
        """Feed a new angle. Returns True iff a rep just completed."""
        now = time.monotonic()

        # Track minimum angle and its timestamp during the descent / bottom.
        if self.state == RepState.DOWN or angle < self.up_threshold:
            if self._min_angle is None or angle < self._min_angle:
                self._min_angle = angle
                self._t_min_angle = now

        counted = False
        if angle <= self.down_threshold and self.state == RepState.UP:
            self.state = RepState.DOWN
            self._t_descent_start = self._t_descent_start or now
            logger.debug("UP->DOWN at %.1f", angle)

        elif angle >= self.up_threshold and self.state == RepState.DOWN:
            self.state = RepState.UP
            self.count += 1
            counted = True

            t_start = self._t_descent_start or now
            t_min = self._t_min_angle or now
            duration = max(now - t_start, 1e-3)
            eccentric = max(t_min - t_start, 0.0)
            concentric = max(now - t_min, 0.0)
            self.last_event = RepEvent(
                rep_number=self.count,
                duration_sec=duration,
                eccentric_sec=eccentric,
                concentric_sec=concentric,
                min_angle=self._min_angle if self._min_angle is not None else angle,
            )
            logger.debug("Rep %d completed: %s", self.count, self.last_event)
            self._reset_rep_buffer()

        return counted

    def _reset_rep_buffer(self) -> None:
        self._t_descent_start = None
        self._t_min_angle = None
        self._min_angle = None

    def reset(self) -> None:
        self.count = 0
        self.state = RepState.UP
        self.last_event = None
        self._reset_rep_buffer()
