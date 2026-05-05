"""Persistent workout-session history (JSON file, per-athlete)."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

HISTORY_DIR = Path(os.environ.get(
    "GYMGURU_HISTORY_DIR",
    str(Path.home() / ".gymguru"),
))


def _slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip().lower()) or "default"
    return s[:40]


def _path_for(athlete: str) -> Path:
    return HISTORY_DIR / f"{_slug(athlete)}.json"


def _load_raw(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read history file %s", path)
        return []


def list_athletes() -> List[str]:
    """Return all athletes that have saved sessions."""
    if not HISTORY_DIR.exists():
        return []
    out: List[str] = []
    for f in sorted(HISTORY_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data and isinstance(data, list):
                # Use stored athlete name from first record if available.
                out.append(data[0].get("athlete", f.stem))
            else:
                out.append(f.stem)
        except Exception:
            out.append(f.stem)
    return out


def load_history(athlete: str = "default") -> List[Dict]:
    """Return all stored sessions for an athlete (most-recent last)."""
    return _load_raw(_path_for(athlete))


def save_session(summary: Dict, athlete: str = "default") -> None:
    """Append a session summary to the athlete's history file."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _path_for(athlete)
    sessions = _load_raw(path)
    record = dict(summary)
    record.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
    record.setdefault("athlete", athlete)
    sessions.append(record)
    path.write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    logger.info("Saved session for '%s' (total=%d)", athlete, len(sessions))


def clear_history(athlete: Optional[str] = None) -> None:
    if athlete is None:
        for f in HISTORY_DIR.glob("*.json"):
            f.unlink()
    else:
        path = _path_for(athlete)
        if path.exists():
            path.unlink()
