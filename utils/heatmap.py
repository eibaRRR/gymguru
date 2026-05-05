"""GitHub-style contribution heat-map for training days."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List

import altair as alt
import pandas as pd


def sessions_to_df(sessions: List[Dict], weeks: int = 26) -> pd.DataFrame:
    """Return a DataFrame with one row per calendar day over the last
    ``weeks`` weeks, with a ``count`` column for sessions that day.
    """
    today = date.today()
    start = today - timedelta(weeks=weeks)
    # Build the full calendar.
    rows = []
    for i in range((today - start).days + 1):
        d = start + timedelta(days=i)
        rows.append({"date": d, "count": 0})
    df = pd.DataFrame(rows)

    # Count sessions per day.
    counts: Dict[date, int] = {}
    for s in sessions:
        try:
            d = datetime.fromisoformat(s.get("timestamp", "")).date()
        except Exception:
            continue
        counts[d] = counts.get(d, 0) + 1

    df["count"] = df["date"].map(lambda d: counts.get(d, 0))
    df["weekday"] = df["date"].map(lambda d: d.strftime("%a"))
    # Week index (for the x-axis).
    df["week"] = df["date"].map(lambda d: (d - start).days // 7)
    return df


def heatmap_chart(sessions: List[Dict], weeks: int = 26):
    """Return an Altair heat-map chart of training days."""
    df = sessions_to_df(sessions, weeks=weeks)
    return (
        alt.Chart(df)
        .mark_rect(cornerRadius=2, stroke="white", strokeWidth=1)
        .encode(
            x=alt.X("week:O", title=None, axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y("weekday:O", title=None,
                    sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
            color=alt.Color(
                "count:Q",
                scale=alt.Scale(domain=[0, 1, 3], range=["#2b2b2b", "#2f6f2f", "#63d163"]),
                legend=None,
            ),
            tooltip=["date:T", "count:Q"],
        )
        .properties(height=150)
    )
