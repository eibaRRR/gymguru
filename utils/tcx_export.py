"""Export a session as a TCX file (ingestible by Strava, Apple Health, etc).

TCX is an XML format from Garmin originally, widely supported. Since
bodyweight exercises aren't a perfect fit (TCX is lap/time oriented),
we encode the session as a single ``Other`` sport activity with one lap
per set; each rep becomes a trackpoint with timestamps and a custom
``<Extensions>`` block containing the form score.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from core.exercise_analyzer import RepRecord

_TCX_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<TrainingCenterDatabase '
    'xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_tcx(
    *, exercise: str, started_at: datetime, reps: List[RepRecord],
    duration_sec: float, avg_score: float,
) -> str:
    """Return the TCX XML as a string."""
    start_iso = _iso(started_at)

    # Slice reps into "laps" of ~same length. For simplicity treat one lap
    # per rep so apps show per-rep times.
    lap_xml: List[str] = []
    t = started_at
    for r in reps:
        lap_start = _iso(t)
        end = t + timedelta(seconds=max(r.duration_sec, 0.5))
        cals = round(r.duration_sec * 0.12, 2)  # rough placeholder
        lap_xml.append(
            f'  <Lap StartTime="{lap_start}">\n'
            f'    <TotalTimeSeconds>{r.duration_sec:.2f}</TotalTimeSeconds>\n'
            f'    <DistanceMeters>0</DistanceMeters>\n'
            f'    <Calories>{int(cals)}</Calories>\n'
            f'    <Intensity>Active</Intensity>\n'
            f'    <TriggerMethod>Manual</TriggerMethod>\n'
            f'    <Track>\n'
            f'      <Trackpoint>\n'
            f'        <Time>{lap_start}</Time>\n'
            f'        <Extensions><GymGuruForm>'
            f'<Rep>{r.rep_number}</Rep>'
            f'<Score>{r.score:.1f}</Score>'
            f'<Grade>{r.grade}</Grade>'
            f'<MinAngle>{r.min_angle:.1f}</MinAngle>'
            f'</GymGuruForm></Extensions>\n'
            f'      </Trackpoint>\n'
            f'    </Track>\n'
            f'  </Lap>\n'
        )
        t = end

    notes = (f"GymGuru {exercise} — {len(reps)} reps, "
             f"avg form {avg_score:.0f}/100")
    body = (
        _TCX_HEADER
        + '<Activities>\n'
        + f'<Activity Sport="Other">\n'
        + f'  <Id>{start_iso}</Id>\n'
        + "".join(lap_xml)
        + f'  <Notes>{notes}</Notes>\n'
        + '</Activity>\n'
        + '</Activities>\n'
        + '</TrainingCenterDatabase>\n'
    )
    return body
