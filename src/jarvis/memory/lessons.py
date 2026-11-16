"""lessons.md: rules Jarvis learned from the owner, one per line.

Line format:  - [L3] 2026-11-16 (owner_said) No meetings before 10
Lines that do not match are the owner's own notes: skipped on read, kept on write.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal, get_args

LessonSource = Literal["owner_said", "owner_edit"]

_LINE = re.compile(r"^- \[L(\d+)\] (\d{4}-\d{2}-\d{2}) \((\w+)\) (.+)$")
_NEXT_ID = re.compile(r"^<!-- next-id: (\d+) -->$")


@dataclass(frozen=True)
class Lesson:
    id: int
    text: str
    source: LessonSource
    at: date


def _parse(line: str) -> Lesson | None:
    m = _LINE.match(line)
    if not m or m.group(3) not in get_args(LessonSource):
        return None
    try:
        when = date.fromisoformat(m.group(2))
    except ValueError:
        return None
    return Lesson(int(m.group(1)), m.group(4), m.group(3), when)


class Lessons:
    def __init__(self, path: Path):
        self._path = path

    def _lines(self) -> list[str]:
        if not self._path.exists():
            return []
        return self._path.read_text(encoding="utf-8").splitlines()

    def _write(self, lines: list[str], next_id: int) -> None:
        body = [l for l in lines if not _NEXT_ID.match(l)]
        text = "\n".join([f"<!-- next-id: {next_id} -->", *body]) + "\n"
        self._path.write_text(text, encoding="utf-8")

    def _next_id(self, lines: list[str]) -> int:
        highest = max((l.id for l in map(_parse, lines) if l), default=0)
        recorded = next(
            (int(m.group(1)) for m in map(_NEXT_ID.match, lines) if m), 0
        )
        return max(highest + 1, recorded)

    def list(self) -> list[Lesson]:
        return [l for l in map(_parse, self._lines()) if l]

    def add(self, text: str, source: LessonSource, at: datetime) -> Lesson:
        if source not in get_args(LessonSource):
            raise ValueError(f"A lesson cannot come from {source!r}")
        clean = " ".join(text.split())
        if not clean:
            raise ValueError("A lesson needs some text")
        lines = self._lines()
        lesson = Lesson(self._next_id(lines), clean, source, at.date())
        lines.append(
            f"- [L{lesson.id}] {lesson.at.isoformat()} ({lesson.source}) {lesson.text}"
        )
        self._write(lines, lesson.id + 1)
        return lesson

    def forget(self, lesson_id: int) -> bool:
        lines = self._lines()
        kept = [l for l in lines if not ((p := _parse(l)) and p.id == lesson_id)]
        if len(kept) == len(lines):
            return False
        self._write(kept, self._next_id(lines))
        return True
