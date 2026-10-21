"""Long-term memory and reminders, saved as small JSON files."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class JsonStore:
    """A list of records kept in one JSON file. Each record gets a numeric id."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.items: list[dict[str, Any]] = []
        if path.exists():
            try:
                self.items = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # Keep the broken file for inspection rather than overwriting it.
                path.rename(path.with_suffix(".broken.json"))
                self.items = []

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        # ensure_ascii=False keeps Arabic text readable in the file.
        tmp.write_text(json.dumps(self.items, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, **fields: Any) -> dict[str, Any]:
        with self._lock:
            next_id = max((i["id"] for i in self.items), default=0) + 1
            item = {"id": next_id, "created": datetime.now().isoformat(timespec="seconds"), **fields}
            self.items.append(item)
            self._save()
            return item

    def remove(self, item_id: int) -> bool:
        with self._lock:
            before = len(self.items)
            self.items = [i for i in self.items if i["id"] != item_id]
            if len(self.items) != before:
                self._save()
                return True
            return False

    def update(self, item_id: int, **fields: Any) -> dict[str, Any] | None:
        with self._lock:
            for item in self.items:
                if item["id"] == item_id:
                    item.update(fields)
                    self._save()
                    return item
            return None


class Memory(JsonStore):
    """Facts Jarvis should remember about you between sessions."""

    def __init__(self, data_dir: Path):
        super().__init__(data_dir / "memory.json")

    def search(self, query: str) -> list[dict[str, Any]]:
        words = [w for w in query.lower().split() if w]
        if not words:
            return list(self.items)
        return [i for i in self.items if any(w in i["fact"].lower() for w in words)]


class Reminders(JsonStore):
    def __init__(self, data_dir: Path):
        super().__init__(data_dir / "reminders.json")

    def pending(self) -> list[dict[str, Any]]:
        return [r for r in self.items if not r.get("done")]

    def due(self, now: datetime | None = None) -> list[dict[str, Any]]:
        """Reminders whose time has passed and that haven't been shown yet."""
        now = now or datetime.now()
        out = []
        for r in self.pending():
            if r.get("notified"):
                continue
            try:
                when = datetime.fromisoformat(r["when"])
            except (KeyError, ValueError):
                continue
            if when.tzinfo is not None:
                when = when.astimezone().replace(tzinfo=None)
            if when <= now:
                out.append(r)
        return out
