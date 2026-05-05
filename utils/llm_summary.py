"""Optional LLM-generated coaching summary.

If ``OPENAI_API_KEY`` is set we call the OpenAI chat API; otherwise we
return a local, template-based summary so the app works offline.
"""
from __future__ import annotations

import logging
import os
from typing import Dict, List

logger = logging.getLogger(__name__)


def _fallback_summary(summary: Dict, reps_detail: List[Dict]) -> str:
    ex = summary.get("exercise", "?")
    reps = summary.get("reps", 0)
    avg = summary.get("avg_rep_score", 0)
    worst = summary.get("worst_rep") or {}
    top = summary.get("top_mistakes") or []

    bits = [
        f"You completed **{reps} {ex.lower()} reps** at an average form score "
        f"of **{avg:.0f}/100**."
    ]
    if worst.get("issues"):
        bits.append("Biggest thing to work on next time: "
                    + worst["issues"][0].lower() + ".")
    if top:
        common = ", ".join(m for m, _ in top[:2])
        bits.append(f"Most frequent corrections during the session: {common}.")
    if avg >= 85:
        bits.append("Great consistency — keep it up!")
    elif avg >= 70:
        bits.append("Solid work — focus on the corrective cue above for next session.")
    else:
        bits.append("Form is shaky — drop a little volume or intensity and "
                    "prioritize clean reps next time.")
    return " ".join(bits)


def generate_summary(
    summary: Dict, reps_detail: List[Dict], *, model: str = "gpt-4o-mini"
) -> str:
    """Return a short coaching summary as markdown text."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return _fallback_summary(summary, reps_detail)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        user_msg = (
            "You are an experienced strength coach. Write a short (<=120 "
            "words) motivating yet precise summary of this workout. "
            "Highlight the top correction the athlete should focus on next "
            "session. Use markdown. Do not invent numbers.\n\n"
            f"Summary: {summary}\n"
            f"Per-rep: {reps_detail[:30]}"
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=220,
            temperature=0.6,
        )
        return resp.choices[0].message.content or _fallback_summary(summary, reps_detail)
    except Exception:
        logger.exception("LLM summary failed — falling back to local template")
        return _fallback_summary(summary, reps_detail)
