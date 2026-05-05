"""Unit tests for core.angle_calculator."""
from __future__ import annotations

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.angle_calculator import calculate_angle, vertical_alignment  # noqa: E402


class TestCalculateAngle:
    def test_right_angle(self):
        assert calculate_angle((0, 1), (0, 0), (1, 0)) == pytest.approx(90.0, abs=1e-6)

    def test_straight_line(self):
        assert calculate_angle((0, 0), (1, 0), (2, 0)) == pytest.approx(180.0, abs=1e-6)

    def test_zero_angle(self):
        # p1 and p3 on the same side of p2 -> 0 degrees.
        assert calculate_angle((1, 0), (0, 0), (1, 0)) == pytest.approx(0.0, abs=1e-6)

    def test_forty_five_degrees(self):
        assert calculate_angle((1, 0), (0, 0), (1, 1)) == pytest.approx(45.0, abs=1e-6)

    def test_accepts_3d(self):
        # z should be ignored.
        angle = calculate_angle((0, 1, 0.5), (0, 0, 0.1), (1, 0, -0.2))
        assert angle == pytest.approx(90.0, abs=1e-6)

    def test_range(self):
        # Always in [0, 180] regardless of orientation.
        for theta in range(0, 360, 17):
            r = math.radians(theta)
            p3 = (math.cos(r), math.sin(r))
            a = calculate_angle((1, 0), (0, 0), p3)
            assert 0 <= a <= 180


class TestVerticalAlignment:
    def test_perfectly_vertical(self):
        assert vertical_alignment((0.5, 0.1), (0.5, 0.9)) == pytest.approx(0.0, abs=1e-6)

    def test_perfectly_horizontal(self):
        assert vertical_alignment((0.1, 0.5), (0.9, 0.5)) == pytest.approx(90.0, abs=1e-6)

    def test_forty_five(self):
        assert vertical_alignment((0, 0), (1, 1)) == pytest.approx(45.0, abs=1e-6)
