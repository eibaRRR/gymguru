"""PDF session report (reportlab)."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from core.exercise_analyzer import RepRecord


def build_pdf(
    *,
    athlete: str,
    summary: Dict,
    reps: List[RepRecord],
    coach_notes: str = "",
) -> bytes:
    """Return PDF bytes for a single session."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    small = ParagraphStyle("small", parent=body, fontSize=9, textColor=colors.grey)

    story = []
    story.append(Paragraph("GymGuru — Session Report", h1))
    story.append(Paragraph(
        f"<b>{athlete}</b> &nbsp;·&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        small))
    story.append(Spacer(1, 0.4 * cm))

    # Summary block.
    ex = summary.get("exercise", "?")
    kv = [
        ("Exercise", ex),
        ("Reps", summary.get("reps", 0)),
        ("Avg rep score", f"{summary.get('avg_rep_score', 0):.1f} / 100"),
        ("Avg tempo", f"{summary.get('avg_tempo_sec', 0):.2f} s"),
        ("Duration", f"{summary.get('duration_sec', 0):.0f} s"),
    ]
    table = Table([[Paragraph(f"<b>{k}</b>", body), Paragraph(str(v), body)] for k, v in kv],
                  colWidths=[4.5 * cm, 10 * cm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.4 * cm))

    # Top mistakes.
    mistakes = summary.get("top_mistakes") or []
    if mistakes:
        story.append(Paragraph("Top corrections", h2))
        for msg, count in mistakes:
            story.append(Paragraph(f"• {msg} <i>({count}x)</i>", body))
        story.append(Spacer(1, 0.3 * cm))

    # Coach notes.
    if coach_notes.strip():
        story.append(Paragraph("Coach notes", h2))
        story.append(Paragraph(coach_notes.replace("\n", "<br/>"), body))
        story.append(Spacer(1, 0.3 * cm))

    # Per-rep table.
    if reps:
        story.append(Paragraph("Per-rep details", h2))
        rows = [["#", "Grade", "Score", "Min angle", "Duration", "Issues"]]
        for r in reps:
            rows.append([
                str(r.rep_number),
                r.grade,
                f"{r.score:.0f}",
                f"{r.min_angle:.0f}°",
                f"{r.duration_sec:.2f}s",
                "; ".join(r.feedback)[:60] or "—",
            ])
        t = Table(rows, colWidths=[1.1 * cm, 1.5 * cm, 1.8 * cm, 2.0 * cm, 2.2 * cm, 7.0 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#233")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f4f4f4")]),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.15, colors.lightgrey),
        ]))
        story.append(t)

    doc.build(story)
    return buf.getvalue()
