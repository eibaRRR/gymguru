"""Per-session stats tracking with per-rep records."""
from __future__ import annotations

import csv
import io
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from core.exercise_analyzer import RepRecord


@dataclass
class SessionTracker:
    """Aggregate workout-session statistics with per-rep records."""

    exercise: str = ""
    started_at: float = field(default_factory=time.time)
    reps: List[RepRecord] = field(default_factory=list)
    _frame_scores: List[float] = field(default_factory=list)
    _mistakes: Counter = field(default_factory=Counter)

    # --- ingest ---------------------------------------------------------
    def log_frame(self, score: float, feedback: List[str]) -> None:
        self._frame_scores.append(float(score))
        for msg in feedback:
            if msg and msg != "Good form!":
                self._mistakes[msg] += 1

    def log_rep(self, record: RepRecord) -> None:
        self.reps.append(record)

    # --- queries --------------------------------------------------------
    @property
    def rep_count(self) -> int:
        return len(self.reps)

    @property
    def avg_frame_score(self) -> float:
        return sum(self._frame_scores) / len(self._frame_scores) if self._frame_scores else 0.0

    @property
    def avg_rep_score(self) -> float:
        return sum(r.score for r in self.reps) / len(self.reps) if self.reps else 0.0

    @property
    def avg_tempo(self) -> float:
        return sum(r.duration_sec for r in self.reps) / len(self.reps) if self.reps else 0.0

    @property
    def best_rep(self) -> Optional[RepRecord]:
        return max(self.reps, key=lambda r: r.score) if self.reps else None

    @property
    def worst_rep(self) -> Optional[RepRecord]:
        return min(self.reps, key=lambda r: r.score) if self.reps else None

    @property
    def duration_sec(self) -> float:
        return time.time() - self.started_at

    def top_mistakes(self, k: int = 3) -> List[tuple]:
        return self._mistakes.most_common(k)

    # --- export ---------------------------------------------------------
    def summary(self) -> Dict[str, object]:
        worst = self.worst_rep
        best = self.best_rep
        return {
            "exercise": self.exercise,
            "duration_sec": round(self.duration_sec, 1),
            "reps": self.rep_count,
            "avg_rep_score": round(self.avg_rep_score, 1),
            "avg_frame_score": round(self.avg_frame_score, 1),
            "avg_tempo_sec": round(self.avg_tempo, 2),
            "best_rep": {"#": best.rep_number, "score": best.score, "grade": best.grade} if best else None,
            "worst_rep": {"#": worst.rep_number, "score": worst.score, "grade": worst.grade,
                          "issues": worst.feedback} if worst else None,
            "top_mistakes": self.top_mistakes(),
        }

    def to_csv(self) -> str:
        """Per-rep CSV export."""
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([
            "rep", "score", "grade", "min_angle",
            "duration_sec", "eccentric_sec", "concentric_sec", "feedback",
        ])
        for r in self.reps:
            w.writerow([
                r.rep_number, f"{r.score:.1f}", r.grade, f"{r.min_angle:.1f}",
                f"{r.duration_sec:.2f}", f"{r.eccentric_sec:.2f}",
                f"{r.concentric_sec:.2f}", "; ".join(r.feedback),
            ])
        return buf.getvalue()

    def to_json(self) -> str:
        return json.dumps(
            {**self.summary(), "reps_detail": [asdict(r) for r in self.reps]},
            indent=2,
        )

    # --- lifecycle ------------------------------------------------------
    def reset(self, exercise: str = "") -> None:
        self.exercise = exercise
        self.started_at = time.time()
        self.reps.clear()
        self._frame_scores.clear()
        self._mistakes.clear()
