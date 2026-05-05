"""Load and iterate through multi-exercise workout programs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import yaml


@dataclass
class ProgramStep:
    exercise: str
    sets: int
    rest_sec: int
    reps: Optional[int] = None       # for rep-based exercises
    seconds: Optional[int] = None    # for timed exercises (plank)

    @property
    def target(self) -> int:
        return self.reps if self.reps is not None else (self.seconds or 0)


@dataclass
class WorkoutProgram:
    name: str
    description: str
    steps: List[ProgramStep] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> "WorkoutProgram":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        steps = [ProgramStep(**s) for s in data.get("steps", [])]
        return cls(name=data["name"], description=data.get("description", ""), steps=steps)


def load_programs(directory: Path) -> Dict[str, WorkoutProgram]:
    """Load all *.yaml programs in a directory."""
    out: Dict[str, WorkoutProgram] = {}
    if not directory.exists():
        return out
    for p in sorted(directory.glob("*.yaml")):
        try:
            prog = WorkoutProgram.from_file(p)
            out[prog.name] = prog
        except Exception:  # pragma: no cover
            continue
    return out


class ProgramRunner:
    """Sequences a workout through a :class:`WorkoutProgram`."""

    def __init__(self, program: WorkoutProgram) -> None:
        self.program = program
        self.step_index: int = 0
        self.done: bool = len(program.steps) == 0

    @property
    def current(self) -> Optional[ProgramStep]:
        if self.done or self.step_index >= len(self.program.steps):
            return None
        return self.program.steps[self.step_index]

    def advance(self) -> None:
        self.step_index += 1
        if self.step_index >= len(self.program.steps):
            self.done = True

    def reset(self) -> None:
        self.step_index = 0
        self.done = len(self.program.steps) == 0

    def remaining(self) -> Iterator[ProgramStep]:
        return iter(self.program.steps[self.step_index:])
