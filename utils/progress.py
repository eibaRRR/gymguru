"""Analyze past sessions to produce coaching insights.

Pure-Python; operates on the dict summaries written by
:py:mod:`utils.history` so it stays decoupled from MediaPipe.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ProgressInsight:
    kind: str       # "pr" | "trend" | "streak" | "weakness"
    message: str


def detect_personal_records(sessions: List[Dict], current: Dict) -> List[ProgressInsight]:
    """Compare ``current`` session to all prior ones of the same exercise.

    Emits a PR insight when the current session beats previous bests in
    reps, avg score, or (for plank) total seconds.
    """
    insights: List[ProgressInsight] = []
    ex = current.get("exercise")
    if not ex:
        return insights

    priors = [s for s in sessions if s.get("exercise") == ex]
    if not priors:
        insights.append(ProgressInsight("pr", f"🎉 First-ever {ex} session logged!"))
        return insights

    best_reps = max((s.get("reps", 0) for s in priors), default=0)
    best_score = max((s.get("avg_rep_score", 0) for s in priors), default=0)

    if current.get("reps", 0) > best_reps:
        insights.append(ProgressInsight(
            "pr", f"🏆 New {ex} rep PR: {current['reps']} (prev {best_reps})"))
    if current.get("avg_rep_score", 0) > best_score + 2:
        insights.append(ProgressInsight(
            "pr", f"🏆 New {ex} form-score PR: {current['avg_rep_score']:.1f} "
                  f"(prev {best_score:.1f})"))
    return insights


def progress_notes(sessions: List[Dict], last_n: int = 5) -> List[ProgressInsight]:
    """Short-form written observations across the last ``last_n`` sessions."""
    out: List[ProgressInsight] = []
    if not sessions:
        return out

    # Group by exercise, take most recent N.
    by_ex: Dict[str, List[Dict]] = defaultdict(list)
    for s in sessions[-last_n * 3:]:
        by_ex[s.get("exercise", "?")].append(s)

    for ex, items in by_ex.items():
        if len(items) < 2:
            continue
        items = items[-last_n:]
        first, last = items[0], items[-1]
        d_score = last.get("avg_rep_score", 0) - first.get("avg_rep_score", 0)
        d_reps = last.get("reps", 0) - first.get("reps", 0)
        if d_score >= 5:
            out.append(ProgressInsight(
                "trend", f"📈 {ex}: form score up {d_score:+.0f} over last {len(items)} sessions"))
        elif d_score <= -5:
            out.append(ProgressInsight(
                "trend", f"📉 {ex}: form score down {d_score:+.0f} — recheck technique"))
        if d_reps >= 3:
            out.append(ProgressInsight(
                "trend", f"💪 {ex}: +{d_reps} reps over last {len(items)} sessions"))
    return out


def weak_side_report(per_rep_scores_l: List[float],
                     per_rep_scores_r: List[float]) -> Optional[ProgressInsight]:
    """Compare average left vs right scores from per-rep data.

    Input lists should be the per-rep form scores where each exercise's
    analyzer measured the left and right side independently. Returns a
    single insight when the delta is meaningful.
    """
    if len(per_rep_scores_l) < 3 or len(per_rep_scores_r) < 3:
        return None
    avg_l = sum(per_rep_scores_l) / len(per_rep_scores_l)
    avg_r = sum(per_rep_scores_r) / len(per_rep_scores_r)
    diff = avg_r - avg_l
    if abs(diff) < 8:
        return None
    weak = "left" if diff > 0 else "right"
    return ProgressInsight(
        "weakness",
        f"⚖️ Your {weak} side scored {abs(diff):.0f} points lower on average"
    )


def streak_days(sessions: List[Dict]) -> int:
    """Consecutive calendar-day streak ending today."""
    from datetime import date, datetime
    days = set()
    for s in sessions:
        ts = s.get("timestamp", "")
        try:
            days.add(datetime.fromisoformat(ts).date())
        except Exception:
            continue
    if not days:
        return 0
    streak = 0
    cur = date.today()
    while cur in days:
        streak += 1
        cur = date.fromordinal(cur.toordinal() - 1)
    return streak
