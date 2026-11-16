"""profile.md: durable facts about the owner, one dated line each."""

from datetime import datetime
from pathlib import Path


class Profile:
    def __init__(self, path: Path):
        self._path = path

    def read(self) -> str:
        if not self._path.exists():
            return ""
        return self._path.read_text(encoding="utf-8")

    def add_fact(self, text: str, at: datetime) -> None:
        line = f"- {at.date().isoformat()} {' '.join(text.split())}\n"
        current = self.read()
        if current and not current.endswith("\n"):
            current += "\n"
        self._path.write_text(current + line, encoding="utf-8")
