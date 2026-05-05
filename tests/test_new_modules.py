"""Smoke tests for the v4 modules that don't touch MediaPipe/OpenCV."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.exercise_analyzer import RepRecord  # noqa: E402
from core.program_runner import ProgramRunner, WorkoutProgram, load_programs  # noqa: E402
from core.rep_quality import RepQualityClassifier  # noqa: E402
from utils.progress import (  # noqa: E402
    detect_personal_records, progress_notes, streak_days, weak_side_report,
)
from utils.tcx_export import build_tcx  # noqa: E402


def _rep(n, score=85.0, dur=1.5, ang=100.0):
    return RepRecord(rep_number=n, score=score, grade="B",
                     feedback=[], min_angle=ang, duration_sec=dur,
                     eccentric_sec=dur / 2, concentric_sec=dur / 2)


class TestPrograms:
    def test_load_programs(self):
        progs = load_programs(Path(__file__).resolve().parent.parent / "programs")
        assert progs  # at least one YAML
        for name, p in progs.items():
            assert isinstance(p, WorkoutProgram)
            assert p.steps

    def test_runner_flow(self):
        prog = WorkoutProgram(
            name="t", description="",
            steps=[type("S", (), {"exercise": "Squat", "sets": 1,
                                  "reps": 5, "seconds": None, "rest_sec": 10,
                                  "target": 5})() for _ in range(3)],
        )
        r = ProgramRunner(prog)
        assert r.current is not None
        r.advance(); r.advance(); r.advance()
        assert r.done and r.current is None


class TestRepQuality:
    def test_not_ready_with_few_reps(self):
        clf = RepQualityClassifier().fit([_rep(i) for i in range(3)])
        assert not clf.is_ready

    def test_detects_outlier(self):
        reps = [_rep(i, score=85) for i in range(10)]
        reps.append(_rep(11, score=20, dur=0.3))    # outlier
        clf = RepQualityClassifier(z_threshold=2.5).fit(reps[:-1])
        v = clf.classify(reps[-1])
        assert v.is_anomaly
        assert v.z > 2.5


class TestProgress:
    def test_pr_detection_first_ever(self):
        insights = detect_personal_records(
            [], {"exercise": "Squat", "reps": 10, "avg_rep_score": 80})
        assert any("First-ever" in i.message for i in insights)

    def test_pr_detection_new_best(self):
        past = [{"exercise": "Squat", "reps": 8, "avg_rep_score": 70}]
        cur = {"exercise": "Squat", "reps": 12, "avg_rep_score": 85}
        msgs = [i.message for i in detect_personal_records(past, cur)]
        assert any("rep PR" in m for m in msgs)

    def test_weak_side(self):
        v = weak_side_report([80, 82, 78], [65, 60, 70])
        assert v is not None and ("right" in v.message or "left" in v.message)

    def test_progress_notes_trend(self):
        sessions = [
            {"exercise": "Squat", "reps": 8, "avg_rep_score": 70,
             "timestamp": "2024-01-01T09:00:00"},
            {"exercise": "Squat", "reps": 10, "avg_rep_score": 80,
             "timestamp": "2024-01-05T09:00:00"},
        ]
        notes = progress_notes(sessions)
        assert any("form score up" in n.message.lower() for n in notes)

    def test_streak(self):
        today = datetime.now().date().isoformat()
        assert streak_days([{"timestamp": f"{today}T09:00:00"}]) == 1
        assert streak_days([]) == 0


class TestTCX:
    def test_tcx_xml(self):
        xml = build_tcx(
            exercise="Squat", started_at=datetime(2024, 1, 1, 9, 0, 0),
            reps=[_rep(1), _rep(2)], duration_sec=3.0, avg_score=85.0,
        )
        assert xml.startswith("<?xml")
        assert "<Activity Sport=\"Other\">" in xml
        assert "GymGuruForm" in xml
